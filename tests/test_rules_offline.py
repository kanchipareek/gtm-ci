"""Hand checks for the offline rules runner.

The three results below are written out from spec 5.B. This test does not
read expected_*, grading_notes, notes, trap, or split from the fixture.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "mini_events.jsonl"

ALERT_BRIEF = (
    "Maya was a champion at Old Co. "
    "Maya is now VP Revenue Operations at Northwind Example "
    "(about 300 people, US). "
    "Reach out because a past champion now owns the budget at an ICP account."
)


def test_offline_runner_on_mini_events():
    npx = shutil.which("npx")
    if npx is None:
        pytest.skip("npx is not found, so the TypeScript runner cannot run")

    # Windows runs npx through npx.cmd, which CreateProcess cannot start directly.
    completed = subprocess.run(
        [npx, "tsx", "scripts/offline_run.ts", str(FIXTURE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        shell=(sys.platform == "win32"),
    )
    assert completed.returncode == 0, completed.stderr

    rows = json.loads(completed.stdout)
    by_id = {row["case_id"]: row for row in rows}

    alert = by_id["m01"]
    assert alert["alert"] is True
    assert alert["status"] == "moved"
    assert alert["reason"] == "icp_fit"
    assert alert["email"] == "synthetic.p01@northwind.example"
    assert alert["email_status"] == "found"
    assert alert["company"] == {"employees": 300, "country": "US"}
    assert alert["brief"] == ALERT_BRIEF

    too_small = by_id["m02"]
    assert too_small["alert"] is False
    assert too_small["reason"] == "company_too_small"
    assert too_small["brief"] == ""

    duplicate = by_id["m03"]
    assert duplicate["alert"] is False
    assert duplicate["reason"] == "duplicate_person"
    assert duplicate["brief"] == ""
