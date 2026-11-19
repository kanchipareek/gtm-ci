"""Run the champion-tracker rules offline, or the real Play on Deepline.

Both functions return rows, mode, and credits_spent. The scorer joins
on case_id and reads credits_spent. It does not grow a second path for
"where did these rows come from".

Offline credits_spent is 0 because this mode never calls Deepline.
Live credits_spent is run.spent_credits from `deepline billing usage`.
If that number is missing, the value is "unknown". It is never 0 by guess.
Live also returns run_id, from the run-id file or from run.id. That id
is how the comment names the run. It is not a credit number.
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from scorer.drift import (
    is_live_companies_file,
    load_live_companies,
    play_events_from_companies,
)
from scorer.fixtures import load_fixtures

ROOT = Path(__file__).resolve().parent.parent
PLAY_FILE = "plays/champion-tracker.play.ts"

# Spec 5.A. These are the Play inputs. The company snapshot is an offline
# stand-in for the lookup, so it is not sent. The live Play looks that up.
EVENT_FIELDS = (
    "person_id",
    "full_name",
    "was_champion",
    "old_company",
    "old_title",
    "new_company",
    "new_domain",
    "new_title",
    "start_date",
    "event_date",
    "country_hint",
)

# The answer key and the review notes. A live input that included these
# could be graded by copying the label.
HIDDEN_FIELDS = ("grading_notes", "notes", "trap", "split")


def run_offline(plays_dir, fixtures_path):
    """Run rules.ts from plays_dir on a golden jsonl file. Spends nothing.

    plays_dir is which copy of the rules to import. Day 3 passes base/plays
    and head/plays through the same script.
    """
    plays_dir = Path(plays_dir).resolve()
    fixtures_path = Path(fixtures_path).resolve()
    command = [
        _program("npx"),
        "tsx",
        "scripts/offline_run.ts",
        str(fixtures_path),
        str(plays_dir),
    ]
    completed = _run(command)
    rows = _parse_json(completed.stdout, command)
    if not isinstance(rows, list):
        raise RuntimeError("offline runner did not print a JSON array of rows")
    return {
        "rows": rows,
        "mode": "offline",
        "credits_spent": 0,
    }


def run_live(fixtures_or_input_path, max_credits):
    """Run the Play on Deepline and return rows plus the usage number.

    email_mode is always mock. A synthetic person must not reach an email tool.
    """
    if isinstance(max_credits, bool) or not isinstance(max_credits, (int, float)):
        raise RuntimeError(f"max_credits must be a number, got {max_credits!r}")

    payload = play_input_from_fixtures(fixtures_or_input_path)
    # The run-id file must not exist yet. The CLI creates it when the
    # server accepts the run (spec F8). A dropped connection still leaves an id.
    with tempfile.TemporaryDirectory(prefix="gtm-ci-live-") as tmp:
        tmp_dir = Path(tmp)
        input_path = tmp_dir / "input.json"
        run_id_path = tmp_dir / "run_id.json"
        input_path.write_text(json.dumps(payload), encoding="utf-8")
        command = [
            _program("deepline"),
            "plays",
            "run",
            PLAY_FILE,
            "--input",
            f"@{input_path}",
            "--max-credits",
            str(max_credits),
            "--json",
            "--full",
            "--run-id-file",
            str(run_id_path),
        ]
        completed = _run(command)
        output = _parse_json(completed.stdout, command)
        rows = rows_from_run_output(output)
        run_id = _read_run_id(run_id_path, output)
        credits = _credits_for_run(run_id)

    return {
        "rows": rows,
        "mode": "live",
        "credits_spent": credits,
        "run_id": run_id if isinstance(run_id, str) and run_id.strip() else None,
    }


def play_input_from_fixtures(fixtures_path):
    """Build the Play input from golden rows, or from the live company file.

    Each golden event is case_id, the Play's input fields, and email plus
    email_status copied from input_mock_email and input_mock_email_status.
    expected_*, grading_notes, notes, trap, and split are left out.
    The live company file keeps its snapshot out of the input. The Play
    looks that company up, and drift compares the result with the snapshot.
    """
    if is_live_companies_file(fixtures_path):
        companies = load_live_companies(fixtures_path)
        return {"email_mode": "mock", "events": play_events_from_companies(companies)}
    rows = load_fixtures(fixtures_path)
    events = [_event_from_row(row) for row in rows]
    return {"email_mode": "mock", "events": events}


def rows_from_run_output(payload):
    """Read result.rows from `deepline plays run --json --full`.

    That path is the one in docs/spike/NOTES.md. diagnostics.result and
    steps[0].status are different objects and are not the rows.
    """
    if not isinstance(payload, dict):
        raise RuntimeError("play output is not a JSON object")
    result = payload.get("result")
    if not isinstance(result, dict) or "rows" not in result:
        raise RuntimeError("play output has no result.rows")
    rows = result["rows"]
    if not isinstance(rows, list):
        raise RuntimeError("result.rows is not a list")
    return rows


def credits_from_usage(payload):
    """Return run.spent_credits, or "unknown" when the bill is not there.

    0 is returned only when the usage JSON itself says 0. A missing field
    is not evidence the run was free. diagnostics.billing.totalCredits is
    a different number and is not read here.
    """
    if not isinstance(payload, dict):
        return "unknown"
    run = payload.get("run")
    if not isinstance(run, dict) or "spent_credits" not in run:
        return "unknown"
    spent = run["spent_credits"]
    if isinstance(spent, bool) or not isinstance(spent, (int, float)):
        return "unknown"
    return spent


def _credits_for_run(run_id):
    """Ask billing usage for one run id. No id, or no number, is "unknown"."""
    if not isinstance(run_id, str) or run_id.strip() == "":
        return "unknown"
    command = [
        _program("deepline"),
        "billing",
        "usage",
        "--run-id",
        run_id,
        "--json",
    ]
    completed = _run(command)
    payload = _parse_json(completed.stdout, command)
    return credits_from_usage(payload)


def _event_from_row(row):
    event = {"case_id": row["case_id"]}
    for name in EVENT_FIELDS:
        event[name] = row["input_" + name]
    event["email"] = row["input_mock_email"]
    event["email_status"] = row["input_mock_email_status"]
    # The keys above are chosen by name. This stops a later edit from
    # slipping the answer key into the file the Play receives.
    for key in event:
        if key in HIDDEN_FIELDS or key.startswith("expected_"):
            raise RuntimeError(f"live input includes {key}, which the Play must not see")
    return event


def _read_run_id(run_id_path, output):
    """Prefer the run-id file. Fall back to run.id in the finished output.

    The file is written when the server accepts the run. The output has the
    same id at run.id once the run has finished. Either one is enough to
    ask billing. Neither one is a credit number.
    """
    if run_id_path.is_file():
        try:
            data = json.loads(run_id_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            run_id = data.get("runId")
            if isinstance(run_id, str) and run_id.strip() != "":
                return run_id
    if isinstance(output, dict):
        run = output.get("run")
        if isinstance(run, dict):
            run_id = run.get("id")
            if isinstance(run_id, str) and run_id.strip() != "":
                return run_id
    return None


def _program(name):
    found = shutil.which(name)
    if found is None:
        raise RuntimeError(f"{name} is not on PATH")
    return found


def _run(command):
    """Run a command from a list. A shell string would re-parse the paths.

    A fixture path or an @input path can contain spaces. Passed as one list
    item, it stays one argument. shell is left off so those characters are
    not commands.
    """
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            shell=False,
        )
    except OSError as exc:
        shown = " ".join(command)
        raise RuntimeError(f"could not start {shown}: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or "").strip()
        if detail == "":
            detail = (completed.stdout or "").strip()
        shown = " ".join(command)
        raise RuntimeError(
            f"{shown} failed with exit code {completed.returncode}.\n{detail}"
        )
    return completed


def _parse_json(text, command):
    try:
        return json.loads(text.lstrip("\ufeff"))
    except json.JSONDecodeError as exc:
        snippet = (text or "").strip()[:500]
        shown = " ".join(command)
        raise RuntimeError(
            f"{shown} did not print JSON ({exc.msg}).\n{snippet}"
        ) from exc

