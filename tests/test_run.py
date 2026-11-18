"""Offline runner, and JSON parsing for a live run.

run_live is not called. A live test that started the CLI would spend credits.
The rows come from the saved play output. The credit number comes from the
saved billing file. Both files are in docs/spike/.
"""

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from scorer.run import (
    credits_from_usage,
    play_input_from_fixtures,
    rows_from_run_output,
    run_offline,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "mini_events.jsonl"
PLAY_OUTPUT = ROOT / "docs" / "spike" / "play_run_output.json"
BILLING = ROOT / "docs" / "spike" / "play_billing_usage.json"

ALERT_BRIEF = (
    "Maya was a champion at Old Co. "
    "Maya is now VP Revenue Operations at Northwind Example "
    "(about 300 people, US). "
    "Reach out because a past champion now owns the budget at an ICP account."
)

# The Play must not receive the answer key or the review notes.
HIDDEN = ("expected_alert", "expected_reason", "grading_notes", "notes", "trap", "split")


def test_run_offline_on_mini_events():
    if shutil.which("npx") is None:
        pytest.skip("npx is not found, so the TypeScript runner cannot run")

    result = run_offline(ROOT / "plays", FIXTURE)

    assert result["mode"] == "offline"
    assert result["credits_spent"] == 0
    assert set(result) == {"rows", "mode", "credits_spent"}

    by_id = {row["case_id"]: row for row in result["rows"]}

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


def test_run_offline_imports_the_plays_folder(tmp_path):
    if shutil.which("npx") is None:
        pytest.skip("npx is not found, so the TypeScript runner cannot run")

    # An empty folder has no rules.ts. If the script ignored the argument
    # and imported plays/rules.ts anyway, this would return rows.
    with pytest.raises(RuntimeError, match="rules"):
        run_offline(tmp_path, FIXTURE)


def test_offline_command_is_an_argument_list(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["shell"] = kwargs.get("shell")
        return SimpleNamespace(returncode=0, stdout="[]\n", stderr="")

    monkeypatch.setattr("scorer.run.subprocess.run", fake_run)
    result = run_offline(ROOT / "plays", FIXTURE)

    command = captured["command"]
    assert isinstance(command, list)
    assert all(isinstance(part, str) for part in command)
    assert captured["shell"] is False
    assert command[1:3] == ["tsx", "scripts/offline_run.ts"]
    assert command[3] == str(FIXTURE.resolve())
    assert command[4] == str((ROOT / "plays").resolve())
    assert result["rows"] == []
    assert result["mode"] == "offline"
    assert result["credits_spent"] == 0


def test_rows_from_saved_play_output():
    payload = json.loads(PLAY_OUTPUT.read_text(encoding="utf-8"))
    rows = rows_from_run_output(payload)
    by_id = {row["case_id"]: row for row in rows}

    assert len(rows) == 2

    asana = by_id["l01"]
    assert asana["alert"] is True
    assert asana["reason"] == "icp_fit"
    assert asana["company"] == {"employees": 4400, "country": "US"}
    assert asana["email"] == "synthetic.p01@asana.com"

    shopify = by_id["l02"]
    assert shopify["alert"] is False
    assert shopify["reason"] == "company_too_big"
    assert shopify["company"] == {"employees": 29663, "country": "CA"}

    # The run overview's billing block says 0. That is not the usage number.
    # A missing run.spent_credits on this file is "unknown", not that 0.
    assert credits_from_usage(payload) == "unknown"


def test_credits_come_from_billing_usage():
    usage = json.loads(BILLING.read_text(encoding="utf-8"))
    assert credits_from_usage(usage) == 0.3
    assert credits_from_usage({"run": {"spent_credits": 0}}) == 0
    assert credits_from_usage({}) == "unknown"
    assert credits_from_usage({"run": {}}) == "unknown"
    assert credits_from_usage({"billing": {"totalCredits": 0}}) == "unknown"


def test_play_input_drops_the_answer_key():
    payload = play_input_from_fixtures(FIXTURE)
    assert set(payload) == {"email_mode", "events"}
    assert payload["email_mode"] == "mock"
    assert [event["case_id"] for event in payload["events"]] == ["m01", "m02", "m03"]

    first = payload["events"][0]
    assert first["person_id"] == "p01"
    assert first["full_name"] == "Maya Testcase"
    assert first["new_domain"] == "northwind.example"
    assert first["email"] == "synthetic.p01@northwind.example"
    assert first["email_status"] == "found"
    assert "employees" not in first
    assert "company_employees" not in first

    for event in payload["events"]:
        for key in event:
            assert not key.startswith("expected_")
            assert not key.startswith("input_")
            assert key not in HIDDEN
