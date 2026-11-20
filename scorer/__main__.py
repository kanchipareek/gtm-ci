"""python -m scorer: score one run and write results/<label>.json and .md.

Offline is the path that spends nothing. It does not ask for confirmation.
Live mode calls Deepline, so it prints the planned cap and waits until
the keyboard answer is the word yes, unless --yes was already passed.
"""

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from scorer.drift import (
    count_drift,
    is_live_companies_file,
    live_section,
    load_live_companies,
    write_live_result,
)
from scorer.fixtures import is_real_events_file, load_fixtures, load_real_events
from scorer.report import write_report
from scorer.run import ROOT, run_live, run_offline
from scorer.score import score

RESULTS_DIR = ROOT / "results"


def main(argv=None):
    args = parse_args(argv)
    problem = _reject_early(args)
    if problem is not None:
        print(problem)
        return 1

    # The live company file has real domains. The golden loader rejects
    # those on purpose. Offline mode must not be pointed at it.
    if args.mode == "offline" and is_live_companies_file(args.fixtures):
        print("this file is the live company list, so it only runs in live mode")
        return 1

    if args.mode == "live":
        print(f"planned max credits: {_format_number(args.max_credits)}")
        if not args.yes and not confirm_live():
            # Do not call Deepline. A live run can spend credits.
            print("stopped. no Deepline call was made.")
            return 1

    if args.mode == "offline":
        ran = run_offline(args.plays, args.fixtures)
    else:
        ran = run_live(args.fixtures, args.max_credits)

    # A refused call has no rows. A score of those missing rows would
    # look like a finished run that alerted on nobody.
    if ran.get("status") == "refused_by_cap":
        # No rows, so this is not a score. The real-events files still
        # record the refusal and the bill. A zero-alert score would be a lie.
        if is_real_events_file(args.fixtures):
            _write_refused_real(args, ran)
        print("Live run refused by the credit cap")
        return 1

    # Five real companies have no expected_alert. Drift is the check.
    # An alert mismatch does not fail this command. The workflow fails
    # the job later, and only when the bill is over the cap.
    if args.mode == "live" and is_live_companies_file(args.fixtures):
        return _finish_live_companies(args, ran)

    fixtures = _load_for_score(args.fixtures)
    scored = score(ran["rows"], fixtures, ran["credits_spent"])
    meta = {
        "label": args.label,
        "mode": ran["mode"],
        "plays_dir": args.plays,
        "git_sha": git_sha(),
        "date": date.today().isoformat(),
    }
    markdown = write_report(args.label, scored, meta, RESULTS_DIR)
    if args.mode == "live" and is_real_events_file(args.fixtures):
        markdown = _note_leadmagic(args.label, ran, fixtures, RESULTS_DIR, markdown)
    print(markdown, end="")
    return 0


def _write_refused_real(args, ran):
    """Write the real-events result when the cap refuses the call.

    The files say the run was refused. They do not contain alert counts.
    """
    folder = RESULTS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    run_id = ran.get("run_id")
    if not isinstance(run_id, str) or run_id.strip() == "":
        run_id = None
    document = {
        "label": args.label,
        "mode": "live",
        "status": "refused_by_cap",
        "plays_dir": args.plays,
        "git_sha": git_sha(),
        "date": date.today().isoformat(),
        "cap": ran.get("cap"),
        "credits_spent": ran.get("credits_spent"),
        "run_id": run_id,
    }
    (folder / f"{args.label}.json").write_text(
        json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    run_text = run_id if run_id else "unavailable"
    credits = ran.get("credits_spent")
    text = (
        f"# {args.label}\n\n"
        "Live run refused by the credit cap. It was not scored.\n\n"
        f"- cap: {ran.get('cap')}\n"
        f"- credits: {credits}\n"
        f"- run id: {run_text}\n"
    )
    (folder / f"{args.label}.md").write_text(text, encoding="utf-8", newline="\n")


def _load_for_score(path):
    """Load the answer key for the file this command was given.

    The golden JSONL still goes through check_synthetic. The real-events
    file is the other loader, so a real company domain is allowed there.
    """
    if is_real_events_file(path):
        return load_real_events(path)
    return load_fixtures(path)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Score the champion tracker and write a results file."
    )
    parser.add_argument("--mode", choices=("offline", "live"), required=True)
    parser.add_argument(
        "--label",
        default="live",
        help="Result file name. The live job omits this and writes results/live.json.",
    )
    parser.add_argument("--plays", default="plays")
    parser.add_argument("--fixtures", default="fixtures/events.jsonl")
    parser.add_argument("--max-credits", type=_credits_arg, default=None)
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Live mode only. Skip the keyboard check.",
    )
    return parser.parse_args(argv)


def confirm_live():
    """Return True only when the person types yes.

    Anything else, including a blank line or a closed stdin, means stop.
    The check is exact so a half-answer cannot start a paid run.
    """
    try:
        answer = input("Type yes to run: ")
    except EOFError:
        return False
    return answer.strip() == "yes"


def git_sha():
    """Return HEAD, or None when git cannot say.

    The report records which commit was scored. A laptop without git,
    or a folder that is not a repo, still gets a report. The sha is
    then null and the markdown says unavailable.
    """
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            shell=False,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    sha = (completed.stdout or "").strip()
    if sha == "":
        return None
    return sha


def _finish_live_companies(args, ran):
    """Write results/<label>.json and print the Live run section.

    Exit 0 even when credits are over the cap or some fields drifted.
    The workflow appends this section to the comment, then exits 1 only
    for a bill over the cap. A failed Deepline command never gets here.
    """
    companies = load_live_companies(args.fixtures)
    drift_count = count_drift(ran["rows"], companies)
    run_id = ran.get("run_id")
    if not isinstance(run_id, str) or run_id.strip() == "":
        run_id = None
    # rows stay on the result so a later drift command can name each
    # changed field. The comment only needs the count.
    document = {
        "label": args.label,
        "mode": "live",
        "plays_dir": args.plays,
        "git_sha": git_sha(),
        "date": date.today().isoformat(),
        "run_id": run_id,
        "credits_spent": ran["credits_spent"],
        "drift_count": drift_count,
        "rows": ran["rows"],
    }
    write_live_result(args.label, document, RESULTS_DIR)
    print(live_section(run_id, ran["credits_spent"], drift_count), end="")
    return 0


def _note_leadmagic(label, ran, fixtures, results_dir, markdown):
    """Append the live company snapshot to the real-events report.

    The score counts stay as score() wrote them. This section only records
    what LeadMagic returned. A mismatch is written down. The rules are not
    edited from it.
    """
    by_id = {}
    for row in ran["rows"]:
        case_id = row.get("case_id")
        if isinstance(case_id, str):
            by_id[case_id] = row

    snapshots = []
    mismatches = []
    for item in fixtures:
        case_id = item["case_id"]
        row = by_id.get(case_id, {})
        company = row.get("company") if isinstance(row.get("company"), dict) else {}
        employees = company.get("employees") if isinstance(company, dict) else None
        country = company.get("country") if isinstance(company, dict) else None
        reason = row.get("reason")
        expected = item["expected_reason"]
        snapshots.append(
            {
                "case_id": case_id,
                "employees": employees,
                "country": country,
                "reason": reason,
                "expected_reason": expected,
            }
        )
        if reason != expected:
            mismatches.append(snapshots[-1])

    folder = Path(results_dir)
    json_path = folder / f"{label}.json"
    document = json.loads(json_path.read_text(encoding="utf-8"))
    run_id = ran.get("run_id")
    document["run_id"] = run_id if isinstance(run_id, str) and run_id.strip() else None
    document["leadmagic"] = snapshots
    json_path.write_text(
        json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    lines = [
        "",
        "LeadMagic snapshots. Stand-ins were not sent. Rules were not changed.",
        "",
        "| case_id | employees | country | reason | expected reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for snap in snapshots:
        employees = snap["employees"]
        country = snap["country"]
        emp = "" if employees is None else str(employees)
        cou = "" if not isinstance(country, str) else country
        got = "" if snap["reason"] is None else str(snap["reason"])
        lines.append(
            f"| {snap['case_id']} | {emp} | {cou} | {got} | {snap['expected_reason']} |"
        )
    if not mismatches:
        lines.append("")
        lines.append("Disagreeing snapshots: none")
    else:
        lines.append("")
        lines.append("Disagreeing snapshots:")
        for snap in mismatches:
            employees = snap["employees"]
            country = snap["country"]
            emp = "none" if employees is None else str(employees)
            cou = "none" if not isinstance(country, str) or country.strip() == "" else country
            lines.append(
                f"- {snap['case_id']}: employees {emp}, country {cou}, "
                f"reason {snap['reason']}, expected {snap['expected_reason']}"
            )
    run_text = document["run_id"] if document["run_id"] else "unavailable"
    lines.append("")
    lines.append(f"run id: {run_text}")
    lines.append("")
    section = "\n".join(lines)
    if not markdown.endswith("\n"):
        markdown += "\n"
    updated = markdown + section
    (folder / f"{label}.md").write_text(updated, encoding="utf-8", newline="\n")
    return updated


def _reject_early(args):
    """Stop before any Deepline call when the command is not runnable."""
    if not isinstance(args.label, str) or args.label.strip() == "":
        return "label is empty"
    if args.label in (".", "..") or "/" in args.label or "\\" in args.label:
        return "label must be a file name, not a path"
    if args.mode == "live" and args.max_credits is None:
        return "live mode needs --max-credits"
    return None


def _credits_arg(text):
    try:
        value = float(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"max credits must be a number, got {text!r}"
        ) from exc
    if value < 0:
        raise argparse.ArgumentTypeError("max credits must be zero or more")
    return value


def _format_number(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


if __name__ == "__main__":
    sys.exit(main())
