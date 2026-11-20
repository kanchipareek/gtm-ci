"""The real-events file is a separate loader from the golden JSONL.

check_synthetic still rejects a real domain in fixtures/events.jsonl.
This file may use a real company domain. The Play still does not see
the answer key or the offline stand-in.
"""

import json
from pathlib import Path

import pytest

from scorer.fixtures import (
    check_synthetic,
    is_real_events_file,
    load_fixtures,
    load_real_events,
    real_event_offline_row,
)
from scorer.run import play_input_from_fixtures, run_offline

ROOT = Path(__file__).resolve().parent.parent
REAL = ROOT / "fixtures" / "real_events.json"
GOLDEN = ROOT / "fixtures" / "events.jsonl"

HIDDEN = (
    "expected_alert",
    "expected_reason",
    "split",
    "trap",
    "old_domain",
    "stand_in",
    "stand_in_employees",
    "stand_in_country",
    "stand_in_note",
)


def test_golden_loader_still_rejects_a_real_domain():
    assert is_real_events_file(GOLDEN) is False
    assert is_real_events_file(REAL) is True
    with pytest.raises(ValueError, match="reserved example domain"):
        check_synthetic(
            [
                {
                    "case_id": "e01",
                    "input_new_domain": "cockroachlabs.com",
                }
            ]
        )
    loaded = load_fixtures(GOLDEN)
    assert loaded[0]["input_new_domain"].endswith(".example") or loaded[0][
        "input_new_domain"
    ] in ("example.com", "example.org", "example.net", "")


def test_real_events_allow_real_domains_and_keep_the_key():
    rows = load_real_events(REAL)
    assert [row["case_id"] for row in rows] == [f"r{i:02d}" for i in range(1, 11)]
    assert rows[0]["new_domain"] == "cockroachlabs.com"
    assert rows[0]["full_name"] == "r01 Testcase"
    assert rows[9]["old_company"] == "LearnUpon"
    assert rows[9]["new_company"] == "LearnUpon"
    assert rows[9]["old_company"] == rows[9]["new_company"]
    assert rows[5]["stand_in_employees"] == 30
    assert rows[6]["stand_in_country"] == "IL"
    assert rows[7]["stand_in_employees"] == 10000
    assert rows[8]["stand_in"] is False
    assert "stand_in_employees" not in rows[8]
    assert "stand_in_employees" not in rows[9]


def test_real_events_ignore_a_csv_mirror(tmp_path):
    text = REAL.read_text(encoding="utf-8")
    path = tmp_path / "real_events.json"
    path.write_text(text, encoding="utf-8")
    (tmp_path / "real_events.csv").write_text(
        "case_id,expected_alert,expected_reason\nr99,true,icp_fit\n",
        encoding="utf-8",
    )
    rows = load_real_events(path)
    assert len(rows) == 10


def test_runner_drops_the_answer_key_and_the_stand_in():
    play_rows = load_real_events(REAL, for_runner=True)
    assert len(play_rows) == 10
    for event in play_rows:
        for key in HIDDEN:
            assert key not in event
        assert event["full_name"].endswith("Testcase")
        assert event["email"].startswith("synthetic.")
        assert "employees" not in event

    offline = real_event_offline_row(load_real_events(REAL)[5])
    assert offline["input_company_employees"] == 30
    assert offline["input_company_country"] == "US"
    assert "expected_alert" not in offline
    assert "stand_in" not in offline

    quiet = real_event_offline_row(load_real_events(REAL)[8])
    assert quiet["input_company_employees"] is None
    assert quiet["input_company_country"] is None

    payload = play_input_from_fixtures(REAL)
    assert payload["email_mode"] == "mock"
    assert len(payload["events"]) == 10
    blob = json.dumps(payload)
    assert "expected_alert" not in blob
    assert "stand_in" not in blob
    assert "old_domain" not in blob
    assert "cockroachlabs.com" in blob


def test_a_real_name_is_rejected(tmp_path):
    data = json.loads(REAL.read_text(encoding="utf-8"))
    data["events"][0]["full_name"] = "Ada Lovelace"
    path = tmp_path / "real_events.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="Testcase"):
        load_real_events(path)


def test_offline_real_events_match_the_stand_ins():
    if __import__("shutil").which("npx") is None:
        pytest.skip("npx is not found, so the TypeScript runner cannot run")

    result = run_offline(ROOT / "plays", REAL)
    assert result["credits_spent"] == 0
    by_id = {row["case_id"]: row for row in result["rows"]}
    expected = {row["case_id"]: row["expected_reason"] for row in load_real_events(REAL)}
    for case_id, reason in expected.items():
        assert by_id[case_id]["reason"] == reason
    assert by_id["r09"]["company"] == {"employees": None, "country": None}
    assert by_id["r10"]["company"] == {"employees": None, "country": None}
    assert by_id["r06"]["company"]["employees"] == 30
    assert by_id["r07"]["company"]["country"] == "IL"
