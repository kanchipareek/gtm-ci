"""Compare a base score with a head score and set the gate exit code.

A pull request is judged against the branch it came from. The head does
not have to reach a fixed score. It fails when it gets worse than base
by more than ci/thresholds.json allows.

The counts are the full set. score.py puts that on the top level, and
spec 5.D says the gate reads the full set, not one split.
"""

import argparse
import json
import sys
from pathlib import Path


# Repo root, so the default file is found from any working directory.
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_THRESHOLDS = ROOT / "ci" / "thresholds.json"

# Spec 5.D. live_max_credits is in the same file for the live job.
# This gate does not read it. A credit cap is not an alert rule.
GATE_KEYS = (
    "false_alerts_max_increase",
    "missed_alerts_max_increase",
    "false_alerts_max_increase_per_trap",
    "pass_to_fail_max",
)

# The counts score.py publishes, in that order. credits_spent is
# attached after the counts. The trap map becomes one row per name.
METRICS = (
    ("correct_alerts", "correct alerts"),
    ("false_alerts", "false alerts"),
    ("missed_alerts", "missed alerts"),
    ("correct_no_alerts", "correct no alerts"),
    ("wrong_reason", "wrong reason"),
    ("emails_found", "emails found"),
    ("total_events", "total events"),
    ("credits_spent", "credits"),
)


def compare(base, head, thresholds):
    """Return the comment and the exit code for these two scores.

    exit_code is 1 when a spec 5.D rule is broken, and 0 otherwise.
    The comment starts with the hidden marker the CI job uses to find
    the one pull request comment.

    base and head are score dicts, or report files with the score
    nested under "score".
    """
    base_score = _as_score(base, "base")
    head_score = _as_score(head, "head")
    limits = _limits(thresholds)

    false_increase = _count(head_score, "false_alerts") - _count(base_score, "false_alerts")
    missed_increase = _count(head_score, "missed_alerts") - _count(base_score, "missed_alerts")
    traps_up = _traps_up(base_score, head_score)
    flips = _pass_to_fail(base_score, head_score)
    new_false = _new_ids(base_score, head_score, "false_alert_case_ids")
    new_missed = _new_ids(base_score, head_score, "missed_alert_case_ids")

    broken = []
    broken_traps = []
    # Greater than, not greater-or-equal. A rise of exactly the allowed
    # amount still passes. A drop is an improvement.
    if false_increase > limits["false_alerts_max_increase"]:
        broken.append("false_alerts")
    if missed_increase > limits["missed_alerts_max_increase"]:
        broken.append("missed_alerts")
    trap_limit = limits["false_alerts_max_increase_per_trap"]
    for name, base_count, head_count in traps_up:
        # A drop in another trap does not cancel this rise.
        if head_count - base_count > trap_limit:
            broken_traps.append((name, base_count, head_count))
    if broken_traps:
        broken.append("trap")
    if len(flips) > limits["pass_to_fail_max"]:
        broken.append("pass_to_fail")

    verdict = _verdict(base_score, head_score, broken, broken_traps, flips)
    comment = _comment(
        verdict,
        _table_rows(base_score, head_score),
        new_false,
        new_missed,
        traps_up,
        flips,
    )
    return {
        "exit_code": 1 if broken else 0,
        "verdict": verdict,
        "comment": comment,
        "new_false_alert_case_ids": new_false,
        "new_missed_alert_case_ids": new_missed,
        "traps_up": [
            {"trap": name, "base": base_count, "head": head_count}
            for name, base_count, head_count in traps_up
        ],
        "pass_to_fail": flips,
    }


def load_thresholds(path):
    """Read the thresholds file. The gate uses these numbers as given."""
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"could not read thresholds at {file_path}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"thresholds file is not JSON: {file_path}") from exc
    _limits(data)
    return data


def main(argv=None):
    """Read two result files, write the comment, and return the exit code."""
    args = parse_args(argv)
    try:
        base = _load_json(args.base, "base")
        head = _load_json(args.head, "head")
        path = args.thresholds if args.thresholds else DEFAULT_THRESHOLDS
        result = compare(base, head, load_thresholds(path))
    except ValueError as exc:
        print(str(exc))
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Write even when the gate fails. The comment is how a reviewer
    # sees which cases moved.
    out.write_text(result["comment"], encoding="utf-8", newline="\n")
    print(result["comment"], end="")
    return result["exit_code"]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Compare base and head scores and write the pull request comment."
    )
    parser.add_argument("base", help="Base results JSON.")
    parser.add_argument("head", help="Head results JSON.")
    parser.add_argument("--out", required=True, help="Where to write the comment.")
    parser.add_argument(
        "--thresholds",
        default=None,
        help="Thresholds JSON. Default is ci/thresholds.json.",
    )
    return parser.parse_args(argv)


def _verdict(base, head, broken, broken_traps, flips):
    """One line. The first broken rule in spec order supplies the sentence.

    The lines under the table still name every case and every trap.
    """
    if not broken:
        return "Passed: no metric got worse"
    first = broken[0]
    if first == "false_alerts":
        return (
            "Blocked: false alerts went "
            f"{_show(_count(base, 'false_alerts'))} -> "
            f"{_show(_count(head, 'false_alerts'))}"
        )
    if first == "missed_alerts":
        return (
            "Blocked: missed alerts went "
            f"{_show(_count(base, 'missed_alerts'))} -> "
            f"{_show(_count(head, 'missed_alerts'))}"
        )
    if first == "trap":
        parts = [
            f"{name} went {_show(base_count)} -> {_show(head_count)}"
            for name, base_count, head_count in broken_traps
        ]
        return "Blocked: false alerts for " + ", ".join(parts)
    noun = "case" if len(flips) == 1 else "cases"
    return f"Blocked: {len(flips)} {noun} flipped from pass to fail"


def _comment(verdict, rows, new_false, new_missed, traps_up, flips):
    lines = [
        "<!-- gtm-ci -->",
        verdict,
        "",
        "| metric | base | head | change |",
        "| --- | --- | --- | --- |",
    ]
    for label, base_cell, head_cell, change_cell in rows:
        lines.append(f"| {label} | {base_cell} | {head_cell} | {change_cell} |")
    lines.append("")
    lines.append(_id_line("New false alerts", new_false))
    lines.append(_id_line("New missed alerts", new_missed))
    lines.append(_trap_line(traps_up))
    lines.append(_id_line("Flipped from pass to fail", flips))
    lines.append("")
    return "\n".join(lines)


def _table_rows(base, head):
    rows = []
    for key, label in METRICS:
        base_value = _metric(base, key)
        head_value = _metric(head, key)
        rows.append(
            (label, _show(base_value), _show(head_value), _change(base_value, head_value))
        )
    for name in _trap_names(base, head):
        base_count = _trap_map(base).get(name, 0)
        head_count = _trap_map(head).get(name, 0)
        rows.append(
            (
                f"false alerts for {name}",
                _show(base_count),
                _show(head_count),
                _change(base_count, head_count),
            )
        )
    return rows


def _traps_up(base, head):
    rose = []
    base_traps = _trap_map(base)
    head_traps = _trap_map(head)
    for name in sorted(set(base_traps) | set(head_traps)):
        base_count = base_traps.get(name, 0)
        head_count = head_traps.get(name, 0)
        if head_count > base_count:
            rose.append((name, base_count, head_count))
    return rose


def _trap_names(base, head):
    return sorted(set(_trap_map(base)) | set(_trap_map(head)))


def _pass_to_fail(base, head):
    """A flip is a case that passed on base and failed on head.

    A case that was already failing is not a flip. Fail to pass is an
    improvement. A case missing on either side was not graded, so it
    is not a flip either.
    """
    base_cases = _cases(base)
    head_cases = _cases(head)
    flipped = []
    for case_id, mark in head_cases.items():
        if base_cases.get(case_id) == "pass" and mark == "fail":
            flipped.append(case_id)
    return sorted(flipped)


def _new_ids(base, head, key):
    already = set(_id_list(base, key))
    fresh = []
    for case_id in _id_list(head, key):
        if case_id not in already and case_id not in fresh:
            fresh.append(case_id)
    return sorted(fresh)


def _as_score(document, label):
    if not isinstance(document, dict):
        raise ValueError(f"{label} result must be a JSON object")
    if "false_alerts" in document:
        return document
    nested = document.get("score")
    if isinstance(nested, dict) and "false_alerts" in nested:
        return nested
    raise ValueError(f"{label} result has no score")


def _limits(thresholds):
    if not isinstance(thresholds, dict):
        raise ValueError("thresholds must be a JSON object")
    limits = {}
    for key in GATE_KEYS:
        limits[key] = _threshold_number(thresholds, key)
    return limits


def _threshold_number(thresholds, key):
    if key not in thresholds:
        raise ValueError(f"thresholds missing {key}")
    value = thresholds[key]
    if not _is_number(value):
        raise ValueError(f"{key} must be a number, got {value!r}")
    return value


def _count(score, key):
    value = _metric(score, key)
    if not _is_number(value):
        raise ValueError(f"{key} must be a number, got {value!r}")
    return value


def _metric(score, key):
    if key not in score:
        raise ValueError(f"score has no {key}")
    return score[key]


def _trap_map(score):
    traps = score.get("false_alerts_by_trap")
    if not isinstance(traps, dict):
        raise ValueError("false_alerts_by_trap must be a dict")
    cleaned = {}
    for name, count in traps.items():
        if not isinstance(name, str) or name.strip() == "":
            raise ValueError(f"trap name is missing, got {name!r}")
        if not _is_number(count):
            raise ValueError(f"trap {name!r} count must be a number, got {count!r}")
        cleaned[name] = count
    return cleaned


def _cases(score):
    cases = score.get("cases")
    if not isinstance(cases, dict):
        raise ValueError("cases must be a dict")
    return cases


def _id_list(score, key):
    value = score.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    for case_id in value:
        if not isinstance(case_id, str) or case_id.strip() == "":
            raise ValueError(f"{key} has an empty case_id, got {case_id!r}")
    return value


def _change(base_value, head_value):
    if not _is_number(base_value) or not _is_number(head_value):
        return "n/a"
    return _format_delta(head_value - base_value)


def _format_delta(delta):
    if isinstance(delta, float) and delta.is_integer():
        delta = int(delta)
    if isinstance(delta, int):
        if delta > 0:
            return f"+{delta}"
        return str(delta)
    text = f"{delta:.10g}"
    if text.startswith("-") or text == "0":
        return text
    return f"+{text}"


def _show(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _is_number(value):
    # bool is a subclass of int. True must not pass as a threshold.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _id_line(label, case_ids):
    if not case_ids:
        return f"{label}: none"
    return f"{label}: {', '.join(case_ids)}"


def _trap_line(traps_up):
    if not traps_up:
        return "Traps with more false alerts: none"
    bits = [
        f"{name} {_show(base_count)} -> {_show(head_count)}"
        for name, base_count, head_count in traps_up
    ]
    return "Traps with more false alerts: " + ", ".join(bits)


def _load_json(path, label):
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"could not read {label} result at {file_path}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} result is not JSON: {file_path}") from exc
    return data


if __name__ == "__main__":
    sys.exit(main())
