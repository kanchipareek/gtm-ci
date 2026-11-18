"""python -m scorer: score one run and write results/<label>.json and .md.

Offline is the path that spends nothing. It does not ask for confirmation.
Live mode calls Deepline, so it prints the planned cap and waits until
the keyboard answer is the word yes, unless --yes was already passed.
"""

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

from scorer.fixtures import load_fixtures
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

    fixtures = load_fixtures(args.fixtures)
    scored = score(ran["rows"], fixtures, ran["credits_spent"])
    meta = {
        "label": args.label,
        "mode": ran["mode"],
        "plays_dir": args.plays,
        "git_sha": git_sha(),
        "date": date.today().isoformat(),
    }
    markdown = write_report(args.label, scored, meta, RESULTS_DIR)
    print(markdown, end="")
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Score the champion tracker and write a results file."
    )
    parser.add_argument("--mode", choices=("offline", "live"), required=True)
    parser.add_argument("--label", required=True)
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
