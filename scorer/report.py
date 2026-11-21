"""Turn one score into JSON and a markdown table.

Both functions take the same score dict and the same meta, and the command
writes both files from those return values. The table cannot show a
different count from the JSON.

Offline mode never calls Deepline. The markdown credits cell says so in
words. A bare 0 would read like a live bill that happened to be free.
The JSON still stores credits_spent as the number score() was given.
A live cell prints that number, or "unknown" when there is no bill.
"""

import json
from pathlib import Path


# The human table, in the order the report always uses.
# credits is separate: its cell depends on the mode.
TABLE_ROWS = (
    ("correct_alerts", "correct alerts"),
    ("false_alerts", "false alerts"),
    ("missed_alerts", "missed alerts"),
    ("correct_no_alerts", "correct no alerts"),
    ("emails_found", "emails found"),
)

# Spec 5.D. The words are the point. The 0 is not a measured live cost.
OFFLINE_CREDITS = "0 (offline, no Deepline calls)"

SPLIT_ORDER = ("development", "holdout", "all")


def to_json(score, meta):
    """Return the text of results/<label>.json.

    The score object is nested under "score" so the counts stay the dict
    score() returned. Meta sits beside it: label, mode, plays folder,
    git sha (null when git could not say), and the date.
    """
    document = {
        "label": meta["label"],
        "mode": meta["mode"],
        "plays_dir": meta["plays_dir"],
        "git_sha": meta["git_sha"],
        "date": meta["date"],
        "score": score,
    }
    return json.dumps(document, indent=2) + "\n"


def to_markdown(score, meta):
    """Return the text of results/<label>.md, ending with one newline."""
    lines = [
        f"# {meta['label']}",
        "",
        f"- mode: {meta['mode']}",
        f"- plays: {meta['plays_dir']}",
        f"- git sha: {_sha_text(meta['git_sha'])}",
        f"- date: {meta['date']}",
        f"- events: {score['total_events']}",
        "",
        "| metric | value |",
        "| --- | --- |",
    ]
    for key, label in TABLE_ROWS:
        lines.append(f"| {label} | {score[key]} |")
    lines.append(f"| credits | {_credits_cell(score, meta)} |")
    if "paid_lookups" in score:
        lines.append(f"| paid company lookups | {score['paid_lookups']} |")
    lines.append("")
    lines.extend(_split_lines(score))
    lines.append(
        f"wrong reason (shown, not gated): {score['wrong_reason']}"
    )
    lines.append(_id_line("false alert case ids", score["false_alert_case_ids"]))
    lines.append(_id_line("missed alert case ids", score["missed_alert_case_ids"]))
    lines.append(_join_line(score))
    lines.append("")
    return "\n".join(lines)


def write_report(label, score, meta, results_dir):
    """Write results/<label>.json and results/<label>.md. Return the markdown."""
    _check_label(label)
    folder = Path(results_dir)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{label}.json").write_text(
        to_json(score, meta), encoding="utf-8", newline="\n"
    )
    markdown = to_markdown(score, meta)
    (folder / f"{label}.md").write_text(markdown, encoding="utf-8", newline="\n")
    return markdown


def _credits_cell(score, meta):
    """Offline always uses the fixed sentence.

    Live prints credits_spent. That value is the billing number, or the
    string "unknown". It is not replaced with 0. A live 0 is only shown
    when the usage JSON itself said 0, and it does not get the offline
    sentence, because that sentence means "we did not call Deepline".
    """
    if meta["mode"] == "offline":
        return OFFLINE_CREDITS
    return _show_credits(score["credits_spent"])


def _show_credits(spent):
    if spent is None:
        return "unknown"
    if isinstance(spent, bool) or not isinstance(spent, (int, float, str)):
        return "unknown"
    if isinstance(spent, str):
        if spent.strip() == "":
            return "unknown"
        return spent
    return _format_number(spent)


def _format_number(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _sha_text(git_sha):
    if git_sha is None or (isinstance(git_sha, str) and git_sha.strip() == ""):
        return "unavailable"
    return git_sha


def _split_lines(score):
    """Headline counts again, once per split.

    Task 2.4 asked for this breakout in the report. The CI gate reads
    the top-level counts, which match the all row, not one split.
    """
    by_split = score.get("by_split")
    if not isinstance(by_split, dict):
        return []
    header_labels = [label for _, label in TABLE_ROWS]
    lines = [
        "By split. The gate uses the full set, which is the all row.",
        "",
        "| split | " + " | ".join(header_labels) + " |",
        "| --- | " + " | ".join("---" for _ in header_labels) + " |",
    ]
    for name in SPLIT_ORDER:
        bucket = by_split.get(name)
        if not isinstance(bucket, dict):
            continue
        cells = [str(bucket[key]) for key, _ in TABLE_ROWS]
        lines.append("| " + name + " | " + " | ".join(cells) + " |")
    lines.append("")
    return lines


def _id_line(label, case_ids):
    if not case_ids:
        return f"{label}: none"
    return f"{label}: {', '.join(case_ids)}"


def _join_line(score):
    errors = score.get("join_errors") or {}
    missing = errors.get("missing", 0)
    duplicate = errors.get("duplicate", 0)
    extra = errors.get("extra", 0)
    return (
        f"join errors: missing {missing}, duplicate {duplicate}, extra {extra}"
    )


def _check_label(label):
    """A label is a file name under results/. It must not be a path.

    results/head.json is the normal name. A label like ../secrets would
    write outside that folder.
    """
    if not isinstance(label, str) or label.strip() == "":
        raise ValueError(f"label is empty, got {label!r}")
    if label in (".", "..") or "/" in label or "\\" in label:
        raise ValueError(f"label must be a file name, not a path, got {label!r}")
