"""Drift is a count of company fields that moved. It is not a gate.

The rows in these tests are fake. Nothing here calls Deepline. The
live companies file is read from disk only to check that the five
people are synthetic and the snapshots stay out of the Play input.
"""

import json
from pathlib import Path

import pytest

from scorer.drift import (
    ISSUE_TITLE,
    append_live_section,
    count_drift,
    credits_over_cap,
    drift_changes,
    issue_body,
    live_section,
    load_live_companies,
    main,
    plan_drift_issue,
)
from scorer.run import ROOT, play_input_from_fixtures


LIVE_FILE = ROOT / "fixtures" / "live_companies.json"
MARKER = "<!-- gtm-ci -->"


def snapshot(case_id, employees, country):
    return {
        "case_id": case_id,
        "snapshot": {"employees": employees, "country": country},
    }


def live_row(case_id, employees, country):
    return {
        "case_id": case_id,
        "company": {"employees": employees, "country": country},
    }


def test_matching_fields_have_zero_drift():
    companies = [snapshot("c01", 10, "US")]
    rows = [live_row("c01", 10, "us")]
    assert count_drift(rows, companies) == 0


def test_one_field_differs():
    companies = [snapshot("c01", 10, "US")]
    assert count_drift([live_row("c01", 11, "US")], companies) == 1
    assert count_drift([live_row("c01", 10, "CA")], companies) == 1


def test_both_fields_differ():
    companies = [snapshot("c01", 10, "US")]
    assert count_drift([live_row("c01", 4, "DE")], companies) == 2


def test_two_companies_add_up():
    # Joined by case_id. The row order is the reverse of the snapshots.
    companies = [snapshot("c01", 10, "US"), snapshot("c02", 20, "CA")]
    rows = [live_row("c02", 20, "GB"), live_row("c01", 99, "US")]
    assert count_drift(rows, companies) == 2


def test_a_missing_live_row_counts_both_fields():
    companies = [snapshot("c01", 10, "US")]
    assert count_drift([], companies) == 2


def test_no_result_empty_answer_is_not_drift():
    # Figma comes back with both fields empty. That is no_result, not a
    # headcount that moved. One field still present is a real answer.
    companies = [snapshot("c04", 1886, "US")]
    empty = {
        "case_id": "c04",
        "reason": "company_not_found",
        "company": {"employees": None, "country": None},
    }
    assert count_drift([empty], companies) == 0
    partial = {"case_id": "c04", "company": {"employees": None, "country": "US"}}
    assert count_drift([partial], companies) == 1


def test_issue_body_lists_company_field_old_new_and_source():
    companies = load_live_companies(LIVE_FILE)
    hubspot = next(item for item in companies if item["domain"] == "hubspot.com")
    rows = []
    for company in companies:
        saved = company["snapshot"]
        if company["case_id"] == "c04":
            rows.append({
                "case_id": "c04",
                "company": {"employees": None, "country": None},
            })
            continue
        employees = 1 if company["case_id"] == "c03" else saved["employees"]
        rows.append(live_row(company["case_id"], employees, saved["country"]))
    body = issue_body(drift_changes(rows, companies))
    assert body == (
        "Fields that differ from the saved snapshot.\n"
        "\n"
        "| company | field | old value | new value | snapshot source |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| hubspot.com | employees | " + str(hubspot["snapshot"]["employees"]) + " | 1 | "
        + hubspot["snapshot_source"]
        + " |\n"
    )
    assert "figma.com" not in body


def test_plan_reuses_one_drift_issue():
    change = {
        "company": "asana.com",
        "field": "employees",
        "old": 4400,
        "new": 4500,
        "source": "notes",
    }
    closed = [{"number": 7, "title": ISSUE_TITLE, "state": "closed"}]
    steps = plan_drift_issue([change], closed)
    assert steps[0]["action"] == "update"
    assert steps[0]["number"] == 7
    assert "asana.com" in steps[0]["body"]
    assert "4400" in steps[0]["body"]
    assert "4500" in steps[0]["body"]
    assert "notes" in steps[0]["body"]

    opened = [{"number": 7, "title": ISSUE_TITLE, "state": "open"}]
    assert plan_drift_issue([], opened) == [{"action": "close", "number": 7}]
    assert plan_drift_issue([], closed) == []
    assert plan_drift_issue([change], [])[0]["action"] == "create"
    pull = [{"number": 3, "title": ISSUE_TITLE, "state": "open", "pull_request": {}}]
    assert plan_drift_issue([change], pull)[0]["action"] == "create"


def test_sync_issue_exits_zero_when_a_field_changed(tmp_path, monkeypatch):
    raw = json.loads(LIVE_FILE.read_text(encoding="utf-8"))
    path = tmp_path / "live_companies.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    companies = load_live_companies(path)
    rows = []
    for company in companies:
        saved = company["snapshot"]
        if company["case_id"] == "c04":
            rows.append({
                "case_id": "c04",
                "company": {"employees": None, "country": None},
            })
            continue
        employees = saved["employees"] + 1 if company["case_id"] == "c01" else saved["employees"]
        rows.append(live_row(company["case_id"], employees, saved["country"]))
    result = tmp_path / "live.json"
    result.write_text(
        json.dumps({"credits_spent": 1, "drift_count": 1, "rows": rows}),
        encoding="utf-8",
    )
    seen = {}

    def fake_sync(changes):
        seen["changes"] = changes

    monkeypatch.setattr("scorer.drift.sync_drift_issue", fake_sync)
    assert main([str(result), "--fixtures", str(path), "--sync-issue"]) == 0
    assert [item["company"] for item in seen["changes"]] == ["asana.com"]


def test_unknown_credits_are_not_over_the_cap():
    assert credits_over_cap("unknown", 10) is False
    assert credits_over_cap(None, 10) is False
    assert credits_over_cap(0, 10) is False
    assert credits_over_cap(10, 10) is False
    assert credits_over_cap(10.1, 10) is True


def test_live_section_names_the_run_the_credits_and_the_drift():
    text = live_section("run-123", "unknown", 3)
    assert text.startswith("## Live run\n")
    assert "- run id: run-123\n" in text
    assert "- credits: unknown\n" in text
    assert "- drift: 3\n" in text

    numbered = live_section(None, 0.3, 0)
    assert "- run id: unknown\n" in numbered
    assert "- credits: 0.3\n" in numbered
    assert "- drift: 0\n" in numbered


def test_append_keeps_the_gate_comment():
    comment = MARKER + "\nPassed: no metric got worse\n"
    updated = append_live_section(comment, live_section("run-123", "unknown", 1))
    assert updated.startswith(MARKER + "\nPassed: no metric got worse\n")
    assert "\n## Live run\n" in updated
    assert updated.endswith("- drift: 1\n")


def test_append_rejects_a_comment_without_the_marker():
    with pytest.raises(ValueError, match="marker"):
        append_live_section("a person's note\n", live_section("run-1", 1, 0))


def test_live_file_is_five_synthetic_people():
    companies = load_live_companies(LIVE_FILE)
    assert [item["case_id"] for item in companies] == ["c01", "c02", "c03", "c04", "c05"]
    assert [item["domain"] for item in companies] == [
        "asana.com",
        "shopify.com",
        "hubspot.com",
        "figma.com",
        "twilio.com",
    ]
    # These two are the LeadMagic fields from the spike, not a filing.
    by_domain = {item["domain"]: item["snapshot"] for item in companies}
    assert by_domain["asana.com"] == {"employees": 4400, "country": "US"}
    assert by_domain["shopify.com"] == {"employees": 29663, "country": "CA"}
    assert companies[0]["snapshot_source"].startswith("docs/spike/NOTES.md")

    for item in companies:
        event = item["event"]
        assert event["full_name"].endswith("Testcase")
        assert event["email"].split("@", 1)[0].startswith("synthetic.")
        assert event["was_champion"] is True
        assert isinstance(item["snapshot"]["employees"], int)
        assert item["snapshot"]["country"].isalpha()

    payload = play_input_from_fixtures(LIVE_FILE)
    assert payload["email_mode"] == "mock"
    assert [event["case_id"] for event in payload["events"]] == [
        "c01",
        "c02",
        "c03",
        "c04",
        "c05",
    ]
    for event in payload["events"]:
        assert "snapshot" not in event
        assert "employees" not in event
        assert "snapshot_source" not in event


def test_live_file_rejects_a_real_name_and_live_email(tmp_path):
    raw = json.loads(LIVE_FILE.read_text(encoding="utf-8"))
    raw["companies"] = [raw["companies"][0]]
    raw["email_mode"] = "live"
    path = tmp_path / "live_companies.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="mock"):
        load_live_companies(path)

    raw["email_mode"] = "mock"
    raw["companies"][0]["event"]["full_name"] = "Ada Lovelace"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="Testcase"):
        load_live_companies(path)


def test_live_command_records_drift_and_still_exits_zero(tmp_path, monkeypatch):
    from scorer.__main__ import main as score_main

    raw = json.loads(LIVE_FILE.read_text(encoding="utf-8"))
    raw["companies"] = [raw["companies"][0]]
    path = tmp_path / "live_companies.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    def fake_live(fixtures_path, max_credits):
        assert Path(fixtures_path) == path
        assert max_credits == 10
        # One field off, and a bill over the cap. Neither one fails this command.
        return {
            "rows": [live_row("c01", 1, "US")],
            "mode": "live",
            "credits_spent": 11,
            "run_id": "run-over",
        }

    def fail_score(*_args, **_kwargs):
        raise AssertionError("the live company file was scored as an answer key")

    monkeypatch.setattr("scorer.__main__.run_live", fake_live)
    monkeypatch.setattr("scorer.__main__.score", fail_score)
    monkeypatch.setattr("scorer.__main__.git_sha", lambda: None)
    monkeypatch.setattr("scorer.__main__.RESULTS_DIR", tmp_path / "results")

    code = score_main(
        ["--mode", "live", "--yes", "--fixtures", str(path), "--max-credits", "10"]
    )
    assert code == 0
    saved = json.loads((tmp_path / "results" / "live.json").read_text(encoding="utf-8"))
    assert saved["label"] == "live"
    assert saved["run_id"] == "run-over"
    assert saved["credits_spent"] == 11
    assert saved["drift_count"] == 1


def test_offline_mode_refuses_the_live_file(monkeypatch):
    from scorer.__main__ import main as score_main

    def fail_offline(*_args, **_kwargs):
        raise AssertionError("offline mode started on the live company file")

    monkeypatch.setattr("scorer.__main__.run_offline", fail_offline)
    code = score_main(["--mode", "offline", "--fixtures", str(LIVE_FILE)])
    assert code == 1


def test_check_cap_exits_only_when_the_number_is_over(tmp_path):
    result = tmp_path / "live.json"
    comment = tmp_path / "comment.md"
    comment.write_text(MARKER + "\nPassed: no metric got worse\n", encoding="utf-8")
    result.write_text(
        json.dumps({"run_id": "run-1", "credits_spent": 11, "drift_count": 4}),
        encoding="utf-8",
    )

    assert main([str(result), "--comment", str(comment)]) == 0
    text = comment.read_text(encoding="utf-8")
    assert text.startswith(MARKER + "\n")
    assert "- run id: run-1\n" in text
    assert "- credits: 11\n" in text
    assert "- drift: 4\n" in text

    assert main([str(result), "--cap", "10", "--check-cap"]) == 1

    result.write_text(
        json.dumps({"run_id": "run-1", "credits_spent": "unknown", "drift_count": 4}),
        encoding="utf-8",
    )
    assert main([str(result), "--cap", "10", "--check-cap"]) == 0
