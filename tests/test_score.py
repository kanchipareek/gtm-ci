"""Score counts you can check on one hand.

Six golden rows cover every headline bucket, one false alert filed under
its trap, and a reason mismatch that is still a pass. A second scoring of
those rows is the pass-to-fail setup compare.py will read later.
"""

import pytest

from scorer.score import score


def golden(case_id, split, trap, expected_alert, expected_reason):
    return {
        "case_id": case_id,
        "split": split,
        "trap": trap,
        "expected_alert": expected_alert,
        "expected_reason": expected_reason,
    }


def result(case_id, alert, reason, email_status="not_found"):
    return {
        "case_id": case_id,
        "alert": alert,
        "reason": reason,
        "email_status": email_status,
    }


def six_fixtures():
    # e01 alert, right reason, email found -> correct alert
    # e02 should be quiet, but it alerts -> false alert on company_too_small
    # e03 should alert, and it does not -> missed alert (email does not count)
    # e04 quiet for a different reason -> correct no-alert, wrong_reason
    # e05 quiet, reason matches after a stray space -> correct no-alert
    # e06 alerts with the wrong reason and no email -> correct alert, still a pass
    return [
        golden("e01", "development", "clean_alert", True, "icp_fit"),
        golden("e02", "development", "company_too_small", False, "company_too_small"),
        golden("e03", "development", "junior_title", True, "icp_fit"),
        golden("e04", "holdout", "stale_event", False, "stale_event"),
        golden("e05", "holdout", "ambiguous_title", False, "ambiguous_title"),
        golden("e06", "holdout", "clean_alert", True, "icp_fit"),
    ]


def six_rows():
    return [
        result("e01", True, "icp_fit", "found"),
        result("e02", True, "icp_fit", "found"),
        result("e03", False, "junior_title", "found"),
        result("e04", False, "company_too_big", "not_found"),
        result("e05", False, " ambiguous_title ", "not_found"),
        result("e06", True, "company_too_big", "not_found"),
    ]


def test_six_rows_match_a_finger_count():
    scored = score(six_rows(), six_fixtures(), "unknown")

    assert scored["correct_alerts"] == 2
    assert scored["false_alerts"] == 1
    assert scored["missed_alerts"] == 1
    assert scored["correct_no_alerts"] == 2
    assert scored["wrong_reason"] == 1
    assert scored["emails_found"] == 2
    assert scored["total_events"] == 6
    assert scored["credits_spent"] == "unknown"

    assert scored["false_alerts_by_trap"] == {"company_too_small": 1}
    assert scored["false_alert_case_ids"] == ["e02"]
    assert scored["missed_alert_case_ids"] == ["e03"]
    assert scored["cases"] == {
        "e01": "pass",
        "e02": "fail",
        "e03": "fail",
        "e04": "pass",
        "e05": "pass",
        "e06": "pass",
    }
    assert scored["join_errors"] == {
        "missing": 0,
        "duplicate": 0,
        "extra": 0,
        "missing_case_ids": [],
        "duplicate_case_ids": [],
        "extra_case_ids": [],
    }

    development = scored["by_split"]["development"]
    assert development["correct_alerts"] == 1
    assert development["false_alerts"] == 1
    assert development["missed_alerts"] == 1
    assert development["correct_no_alerts"] == 0
    assert development["wrong_reason"] == 0
    assert development["emails_found"] == 2
    assert development["total_events"] == 3
    assert development["false_alerts_by_trap"] == {"company_too_small": 1}
    assert development["false_alert_case_ids"] == ["e02"]
    assert development["missed_alert_case_ids"] == ["e03"]

    holdout = scored["by_split"]["holdout"]
    assert holdout["correct_alerts"] == 1
    assert holdout["false_alerts"] == 0
    assert holdout["missed_alerts"] == 0
    assert holdout["correct_no_alerts"] == 2
    assert holdout["wrong_reason"] == 1
    assert holdout["emails_found"] == 0
    assert holdout["total_events"] == 3
    assert holdout["false_alerts_by_trap"] == {}
    assert holdout["false_alert_case_ids"] == []
    assert holdout["missed_alert_case_ids"] == []

    # The gate reads the top level. It is the full set, same as "all".
    assert scored["by_split"]["all"]["false_alerts"] == scored["false_alerts"]
    assert scored["by_split"]["all"]["missed_alerts"] == scored["missed_alerts"]
    assert scored["by_split"]["all"]["total_events"] == 6


def test_row_order_does_not_change_the_score():
    fixtures = six_fixtures()
    rows = six_rows()
    forward = score(rows, fixtures, 0)
    backward = score(list(reversed(rows)), list(reversed(fixtures)), 0)
    assert forward == backward


def test_pairing_by_index_would_get_these_two_wrong():
    """The no-alert row is first. An index join would call e01 a miss."""
    fixtures = [
        golden("e01", "development", "clean_alert", True, "icp_fit"),
        golden("e02", "development", "junior_title", False, "junior_title"),
    ]
    rows = [
        result("e02", False, "junior_title"),
        result("e01", True, "icp_fit", "found"),
    ]
    scored = score(rows, fixtures, 0)
    assert scored["correct_alerts"] == 1
    assert scored["correct_no_alerts"] == 1
    assert scored["missed_alerts"] == 0
    assert scored["false_alerts"] == 0
    assert scored["emails_found"] == 1
    assert scored["cases"] == {"e01": "pass", "e02": "pass"}


def test_pass_to_fail_setup():
    """e02 is a pass on base and a fail on head.

    compare.py will treat that as one pass-to-fail flip, and as one new
    false alert on the company_too_small trap.
    """
    fixtures = six_fixtures()
    base_rows = six_rows()
    base_rows[1] = result("e02", False, "company_too_small", "found")
    head_rows = six_rows()

    base = score(base_rows, fixtures, 0)
    head = score(head_rows, fixtures, 0)

    assert base["cases"]["e02"] == "pass"
    assert head["cases"]["e02"] == "fail"
    assert base["false_alerts"] == 0
    assert head["false_alerts"] == 1
    assert base["false_alerts_by_trap"] == {}
    assert head["false_alerts_by_trap"] == {"company_too_small": 1}
    assert base["false_alert_case_ids"] == []
    assert head["false_alert_case_ids"] == ["e02"]
    assert base["missed_alerts"] == 1
    assert head["missed_alerts"] == 1
    assert base["cases"]["e01"] == "pass"
    assert head["cases"]["e01"] == "pass"


def test_missing_duplicate_and_extra_are_not_answer_errors():
    """b01 is in the rows twice, with two different alerts.

    b04 never comes back. b99 is not in the golden set.
    None of those three is a false alert or a missed alert.
    """
    fixtures = [
        golden("b01", "development", "clean_alert", True, "icp_fit"),
        golden("b02", "development", "company_too_small", False, "company_too_small"),
        golden("b03", "holdout", "clean_alert", True, "icp_fit"),
        golden("b04", "holdout", "junior_title", True, "icp_fit"),
    ]
    alert_copy = result("b01", True, "icp_fit", "found")
    quiet_copy = result("b01", False, "junior_title", "found")
    rest = [
        result("b02", False, "company_too_small"),
        result("b03", False, "icp_fit"),
        result("b99", True, "icp_fit", "found"),
    ]

    first = score([alert_copy, quiet_copy] + rest, fixtures, 0)
    second = score([quiet_copy, alert_copy] + rest, fixtures, 0)
    assert first == second

    assert first["join_errors"]["missing"] == 1
    assert first["join_errors"]["duplicate"] == 1
    assert first["join_errors"]["extra"] == 1
    assert first["join_errors"]["missing_case_ids"] == ["b04"]
    assert first["join_errors"]["duplicate_case_ids"] == ["b01"]
    assert first["join_errors"]["extra_case_ids"] == ["b99"]

    assert first["correct_alerts"] == 0
    assert first["false_alerts"] == 0
    assert first["missed_alerts"] == 1
    assert first["missed_alert_case_ids"] == ["b03"]
    assert first["correct_no_alerts"] == 1
    assert first["wrong_reason"] == 0
    assert first["emails_found"] == 0
    assert first["total_events"] == 4
    assert first["cases"] == {"b02": "pass", "b03": "fail"}
    assert "b01" not in first["cases"]
    assert "b04" not in first["cases"]
    assert "b99" not in first["cases"]


def test_two_golden_rows_for_one_id_are_not_graded():
    """The two labels disagree. Picking the first would make this a hit or a miss."""
    fixtures = [
        golden("d01", "development", "clean_alert", True, "icp_fit"),
        golden("d01", "development", "junior_title", False, "junior_title"),
    ]
    rows = [result("d01", True, "icp_fit", "found")]
    scored = score(rows, fixtures, 0)

    assert scored["join_errors"]["duplicate"] == 1
    assert scored["join_errors"]["duplicate_case_ids"] == ["d01"]
    assert scored["join_errors"]["missing"] == 0
    assert scored["correct_alerts"] == 0
    assert scored["false_alerts"] == 0
    assert scored["emails_found"] == 0
    assert scored["total_events"] == 2
    assert "d01" not in scored["cases"]


def test_credits_spent_is_copied_through():
    fixtures = six_fixtures()
    rows = six_rows()
    assert score(rows, fixtures, "unknown")["credits_spent"] == "unknown"
    assert score(rows, fixtures, 0)["credits_spent"] == 0
    assert score(rows, fixtures, 0.3)["credits_spent"] == 0.3


def test_alert_must_be_a_bool():
    fixtures = [golden("e01", "development", "clean_alert", True, "icp_fit")]
    rows = [result("e01", 1, "icp_fit", "found")]
    with pytest.raises(ValueError, match="bool"):
        score(rows, fixtures, 0)
