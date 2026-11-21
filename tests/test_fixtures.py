"""Checks for the golden-row loader.

Rows here are small and inline. They use the golden-dataset column names.
A good row passes. Each kind of bad row raises ValueError.
"""

import csv
import json
from pathlib import Path

import pytest

from scorer.fixtures import (
    REASONS,
    check_csv_mirror,
    check_synthetic,
    load_fixtures,
    row_for_runner,
    validate_fixture,
)


def good_row(**overrides):
    row = {
        "case_id": "e01",
        "split": "development",
        "input_person_id": "p01",
        "input_full_name": "Maya Testcase",
        "input_was_champion": True,
        "input_old_company": "Old Co One",
        "input_old_title": "Head of Revenue Operations",
        "input_new_company": "Northwind Example",
        "input_new_domain": "northwind.example",
        "input_new_title": "VP Revenue Operations",
        "input_start_date": "2026-10-01",
        "input_event_date": "2026-11-02",
        "input_country_hint": "US",
        "input_company_employees": 300,
        "input_company_country": "US",
        "input_mock_email": "synthetic.p01@northwind.example",
        "input_mock_email_status": "found",
        "expected_alert": True,
        "expected_reason": "icp_fit",
        "grading_notes": "Join by case_id.",
        "notes": "Synthetic clean case.",
        "trap": "clean_alert",
    }
    row.update(overrides)
    return row


def write_jsonl(path, rows):
    lines = [json.dumps(row) for row in rows]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path, rows):
    fieldnames = list(good_row().keys())
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            written = dict(row)
            alert = written["expected_alert"]
            if alert is True:
                written["expected_alert"] = "true"
            elif alert is False:
                written["expected_alert"] = "false"
            writer.writerow(written)


def test_good_row_passes():
    seen = set()
    validate_fixture(good_row(), seen)
    validate_fixture(good_row(case_id="e02", split="holdout"), seen)
    assert seen == {"e01", "e02"}


def test_null_company_and_email_pass():
    # No snapshot, and no email when the status is not_found.
    # An empty domain is the missing-domain case. It is present, not null.
    row = good_row(
        input_new_domain="",
        input_company_employees=None,
        input_company_country=None,
        input_mock_email=None,
        input_mock_email_status="not_found",
    )
    validate_fixture(row)
    check_synthetic([row])


def test_missing_case_id_fails():
    row = good_row()
    del row["case_id"]
    with pytest.raises(ValueError, match="case_id is missing"):
        validate_fixture(row)


def test_empty_case_id_fails():
    with pytest.raises(ValueError, match="case_id is empty"):
        validate_fixture(good_row(case_id="  "))


def test_duplicate_case_id_fails():
    seen = set()
    validate_fixture(good_row(), seen)
    with pytest.raises(ValueError, match="case_id 'e01' is duplicated"):
        validate_fixture(good_row(input_full_name="Noah Testcase"), seen)


def test_bad_split_fails():
    with pytest.raises(ValueError, match="development or holdout"):
        validate_fixture(good_row(split="train"))


def test_missing_input_fails():
    row = good_row()
    del row["input_new_title"]
    with pytest.raises(ValueError, match="input_new_title is missing"):
        validate_fixture(row)


def test_null_required_input_fails():
    with pytest.raises(ValueError, match="input_full_name is null"):
        validate_fixture(good_row(input_full_name=None))


def test_expected_alert_must_be_bool():
    with pytest.raises(ValueError, match="expected_alert must be a bool"):
        validate_fixture(good_row(expected_alert="true"))
    with pytest.raises(ValueError, match="expected_alert must be a bool"):
        validate_fixture(good_row(expected_alert=1))


def test_bad_reason_fails():
    with pytest.raises(ValueError, match="rules.ts"):
        validate_fixture(good_row(expected_reason="looks_good"))


def test_every_reason_string_passes():
    # REASONS is the only copy. This loop uses it; it does not restate it.
    seen = set()
    for index, reason in enumerate(REASONS, start=1):
        validate_fixture(
            good_row(case_id=f"e{index:02d}", expected_reason=reason),
            seen,
        )


def test_email_must_be_synthetic():
    with pytest.raises(ValueError, match="synthetic\\."):
        validate_fixture(
            good_row(input_mock_email="maya.chen@northwind.example")
        )


def test_name_must_end_with_testcase():
    with pytest.raises(ValueError, match="Testcase"):
        validate_fixture(good_row(input_full_name="Maya Chen"))


def test_check_synthetic_allows_reserved_empty_and_freemail():
    domains = [
        "northwind.example",
        "example.com",
        "example.org",
        "example.net",
        "shop.example",
        "gmail.com",
        "yahoo.com",
        "outlook.com",
        "hotmail.com",
        "proton.me",
        "",
        None,
    ]
    rows = []
    for index, domain in enumerate(domains, start=1):
        rows.append(
            good_row(case_id=f"e{index:02d}", input_new_domain=domain)
        )
    check_synthetic(rows)


def test_check_synthetic_rejects_a_real_looking_domain():
    with pytest.raises(ValueError, match="reserved example domain"):
        check_synthetic([good_row(input_new_domain="acme.com")])


def test_check_synthetic_rejects_a_lookalike_of_example_com():
    # shop.example.com does not end with .example, and it is not example.com.
    with pytest.raises(ValueError, match="reserved example domain"):
        check_synthetic([good_row(input_new_domain="shop.example.com")])


def test_load_fixtures_returns_rows(tmp_path):
    path = tmp_path / "events.jsonl"
    write_jsonl(
        path,
        [good_row(), good_row(case_id="e02", split="holdout")],
    )
    rows = load_fixtures(path)
    assert [row["case_id"] for row in rows] == ["e01", "e02"]
    assert rows[0]["expected_alert"] is True


def test_load_fixtures_rejects_a_bad_line(tmp_path):
    path = tmp_path / "events.jsonl"
    write_jsonl(path, [good_row(), good_row(split="all")])
    with pytest.raises(ValueError, match="line 2"):
        load_fixtures(path)


def test_load_fixtures_rejects_a_real_looking_domain(tmp_path):
    path = tmp_path / "events.jsonl"
    write_jsonl(path, [good_row(input_new_domain="acme.com")])
    with pytest.raises(ValueError, match="reserved example domain"):
        load_fixtures(path)


def test_runner_path_drops_the_answer_key(tmp_path):
    path = tmp_path / "events.jsonl"
    write_jsonl(path, [good_row()])
    rows = load_fixtures(path, for_runner=True)
    assert set(rows[0]) == {
        "case_id",
        "input_person_id",
        "input_full_name",
        "input_was_champion",
        "input_old_company",
        "input_old_title",
        "input_new_company",
        "input_new_domain",
        "input_new_title",
        "input_start_date",
        "input_event_date",
        "input_country_hint",
        "input_company_employees",
        "input_company_country",
        "input_mock_email",
        "input_mock_email_status",
    }
    hidden = row_for_runner(good_row())
    for key in ("expected_alert", "expected_reason", "grading_notes", "notes", "trap", "split"):
        assert key not in hidden


def test_runner_path_still_validates_labels(tmp_path):
    # Dropping the answer key happens after the check, so a bad label still fails.
    path = tmp_path / "events.jsonl"
    write_jsonl(path, [good_row(expected_reason="looks_good")])
    with pytest.raises(ValueError, match="rules.ts"):
        load_fixtures(path, for_runner=True)


def test_csv_mirror_matches(tmp_path):
    jsonl_path = tmp_path / "events.jsonl"
    csv_path = tmp_path / "events.csv"
    rows = [
        good_row(),
        good_row(case_id="e02", split="holdout", expected_alert=False, expected_reason="stale_event"),
    ]
    write_jsonl(jsonl_path, rows)
    write_csv(csv_path, rows)
    loaded = load_fixtures(jsonl_path)
    assert [row["case_id"] for row in loaded] == ["e01", "e02"]


def test_csv_mirror_rejects_a_different_answer(tmp_path):
    jsonl_path = tmp_path / "events.jsonl"
    csv_path = tmp_path / "events.csv"
    write_jsonl(jsonl_path, [good_row()])
    write_csv(csv_path, [good_row(expected_reason="stale_event")])
    with pytest.raises(ValueError, match="expected_reason"):
        load_fixtures(jsonl_path)


def test_csv_mirror_rejects_a_different_case_id(tmp_path):
    jsonl_path = tmp_path / "events.jsonl"
    rows = [good_row()]
    write_jsonl(jsonl_path, rows)
    write_csv(tmp_path / "events.csv", [good_row(case_id="e99")])
    with pytest.raises(ValueError, match="case_ids do not match"):
        check_csv_mirror(rows, tmp_path / "events.csv")


def test_missing_csv_is_fine(tmp_path):
    path = tmp_path / "events.jsonl"
    write_jsonl(path, [good_row()])
    rows = load_fixtures(path)
    assert len(rows) == 1
