"""Test the test set: break rules.ts on purpose and see if the gate notices.

Each mutation in ci/mutations.json is one small edit to plays/rules.ts,
like MIN_EMPLOYEES 50 -> 49. For each one this copies plays/ into a temp
folder, applies the edit, scores the copy offline, and runs the same
compare the pull request gate runs (base = the real rules, head = the
mutant). If compare exits 1, the mutation is caught. If it exits 0, the
gate would have let that change merge, and the test set has a hole.

Offline only. It never calls Deepline and spends 0 credits.

    python -m scorer.mutate
    python -m scorer.mutate --split holdout
    python -m scorer.mutate --fixtures fixtures/events.jsonl --out results/mutation

Exit code is 0 unless a mutation could not be applied (its find text is
not in the file), because a stale mutation list would quietly score as
"caught" or "survived" for the wrong reason. Survivors are a finding,
not a CI failure.
"""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

from scorer.compare import DEFAULT_THRESHOLDS, compare, load_thresholds
from scorer.fixtures import load_fixtures
from scorer.run import run_offline
from scorer.score import score

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MUTATIONS = ROOT / "ci" / "mutations.json"
DEFAULT_FIXTURES = ROOT / "fixtures" / "events.jsonl"
DEFAULT_PLAYS = ROOT / "plays"
DEFAULT_OUT = ROOT / "results" / "mutation"


def load_mutations(path):
    """Read the mutation list and check each entry has what apply needs."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    mutations = data.get("mutations")
    if not isinstance(mutations, list) or not mutations:
        raise ValueError("mutations file has no mutations list")
    seen = set()
    for item in mutations:
        for key in ("id", "split", "find", "replace", "why"):
            if not isinstance(item.get(key), str):
                raise ValueError(f"mutation {item.get('id')!r} is missing {key}")
        if item["find"] == "":
            raise ValueError(f"mutation {item['id']} has an empty find")
        if item["split"] not in ("discovery", "holdout"):
            raise ValueError(f"mutation {item['id']} split must be discovery or holdout")
        if item["id"] in seen:
            raise ValueError(f"duplicate mutation id {item['id']}")
        seen.add(item["id"])
    return data.get("file", "plays/rules.ts"), mutations


def apply_mutation(text, mutation):
    """Return text with the mutation applied, or None if find is not there once.

    Exactly one match is required. Zero means the list is stale. Two means
    the edit is ambiguous and could break a different line than intended.
    """
    if text.count(mutation["find"]) != 1:
        return None
    return text.replace(mutation["find"], mutation["replace"], 1)


def changed_cases(base_rows, head_rows):
    """Case ids whose alert or reason moved, as {case_id: [before, after]}."""
    base = {row["case_id"]: (row["alert"], row["reason"]) for row in base_rows}
    moved = {}
    for row in head_rows:
        before = base.get(row["case_id"])
        after = (row["alert"], row["reason"])
        if before is not None and before != after:
            moved[row["case_id"]] = [_label(before), _label(after)]
    return dict(sorted(moved.items()))


def run_mutations(mutations, rules_file, plays_dir, fixtures_path, thresholds):
    """Score every mutation. Returns one result dict per mutation, in order."""
    plays_dir = Path(plays_dir)
    fixtures = load_fixtures(fixtures_path)
    base_run = run_offline(plays_dir, fixtures_path)
    base_score = score(base_run["rows"], fixtures, 0)
    rules_name = Path(rules_file).name
    original = (plays_dir / rules_name).read_text(encoding="utf-8")

    results = []
    with tempfile.TemporaryDirectory(prefix="gtm-ci-mutant-") as tmp:
        mutant_dir = Path(tmp) / "plays"
        for mutation in mutations:
            mutated = apply_mutation(original, mutation)
            entry = {
                "id": mutation["id"],
                "split": mutation["split"],
                "why": mutation["why"],
            }
            if mutated is None:
                entry.update(outcome="not_applied", changed_cases={}, reasons=[])
                results.append(entry)
                continue
            if mutant_dir.exists():
                shutil.rmtree(mutant_dir)
            shutil.copytree(plays_dir, mutant_dir)
            (mutant_dir / rules_name).write_text(mutated, encoding="utf-8", newline="\n")
            head_run = run_offline(mutant_dir, fixtures_path)
            head_score = score(head_run["rows"], fixtures, 0)
            verdict = compare(base_score, head_score, thresholds)
            entry.update(
                outcome="caught" if verdict["exit_code"] == 1 else "survived",
                changed_cases=changed_cases(base_run["rows"], head_run["rows"]),
                reasons=_broken(verdict),
            )
            results.append(entry)
    return results


def summarize(results):
    """Caught over applied, overall and per split. not_applied is listed apart."""
    summary = {}
    for split in ("discovery", "holdout", "all"):
        rows = [r for r in results if split == "all" or r["split"] == split]
        applied = [r for r in rows if r["outcome"] != "not_applied"]
        caught = [r for r in applied if r["outcome"] == "caught"]
        summary[split] = {
            "caught": len(caught),
            "applied": len(applied),
            "not_applied": len(rows) - len(applied),
            "survivors": [r["id"] for r in applied if r["outcome"] == "survived"],
        }
    return summary


def to_markdown(results, summary, fixtures_label):
    lines = [
        "## Mutation score",
        "",
        f"Fixtures: `{fixtures_label}`. Each mutation is one edit to `plays/rules.ts`. "
        "Caught means the offline gate would have blocked the pull request.",
        "",
        "| split | caught | applied | not applied |",
        "| --- | --- | --- | --- |",
    ]
    for split in ("discovery", "holdout", "all"):
        row = summary[split]
        lines.append(f"| {split} | {row['caught']} | {row['applied']} | {row['not_applied']} |")
    lines += [
        "",
        "| id | split | mutation | outcome | cases that moved |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in results:
        moved = ", ".join(
            f"{case} {before} -> {after}" for case, (before, after) in r["changed_cases"].items()
        )
        lines.append(f"| {r['id']} | {r['split']} | {r['why']} | {r['outcome']} | {moved or 'none'} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    args = parse_args(argv)
    try:
        rules_file, mutations = load_mutations(args.mutations)
        if args.split != "all":
            mutations = [m for m in mutations if m["split"] == args.split]
        thresholds = load_thresholds(args.thresholds)
        results = run_mutations(mutations, rules_file, args.plays, args.fixtures, thresholds)
    except (ValueError, RuntimeError, OSError) as exc:
        print(str(exc))
        return 1

    summary = summarize(results)
    fixtures_label = _relative(args.fixtures)
    markdown = to_markdown(results, summary, fixtures_label)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(
        json.dumps({"fixtures": fixtures_label, "summary": summary, "results": results}, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    out.with_suffix(".md").write_text(markdown, encoding="utf-8", newline="\n")
    print(markdown, end="")

    stale = [r["id"] for r in results if r["outcome"] == "not_applied"]
    if stale:
        print(f"not applied (find text missing or not unique): {', '.join(stale)}")
        return 1
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mutations", default=str(DEFAULT_MUTATIONS))
    parser.add_argument("--plays", default=str(DEFAULT_PLAYS))
    parser.add_argument("--fixtures", default=str(DEFAULT_FIXTURES))
    parser.add_argument("--thresholds", default=str(DEFAULT_THRESHOLDS))
    parser.add_argument("--split", choices=("discovery", "holdout", "all"), default="all")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="path without extension")
    return parser.parse_args(argv)


def _label(pair):
    alert, reason = pair
    return f"{'alert' if alert else 'no alert'} ({reason})"


def _broken(verdict):
    """Which gate rules the mutant broke, from compare's own result."""
    reasons = []
    if verdict.get("new_false_alert_case_ids"):
        reasons.append("false alert: " + ", ".join(verdict["new_false_alert_case_ids"]))
    if verdict.get("new_missed_alert_case_ids"):
        reasons.append("missed alert: " + ", ".join(verdict["new_missed_alert_case_ids"]))
    if verdict.get("pass_to_fail"):
        reasons.append("pass to fail: " + ", ".join(verdict["pass_to_fail"]))
    return reasons


def _relative(path):
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return Path(path).as_posix()


if __name__ == "__main__":
    sys.exit(main())
