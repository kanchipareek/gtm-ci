"""Base versus head. The exit code follows ci/thresholds.json.

Equal scores pass. A rise in false alerts fails. A drop passes. A trap
can fail the gate while the total stays put, because a drop in one trap
does not cancel a rise in another. One pass-to-fail flip fails on its
own. The numbers come from the thresholds file.
"""

import json
import subprocess
import sys
from pathlib import Path

from scorer.compare import compare, load_thresholds, main
from scorer.run import ROOT
from scorer.score import score


EXPECTED_THRESHOLDS = (
    "{\n"
    '  "false_alerts_max_increase": 0,\n'
    '  "missed_alerts_max_increase": 0,\n'
    '  "false_alerts_max_increase_per_trap": 0,\n'
    '  "pass_to_fail_max": 0,\n'
    '  "paid_lookups_max_increase": 0,\n'
    '  "live_max_credits": 10\n'
    "}\n"
)


def defaults():
    return load_thresholds(ROOT / "ci" / "thresholds.json")


def blank_score(**overrides):
    """A full-set score with one false alert and one missed alert.

    Overrides replace a whole field. Tests that move one count say so
    in the call, so the expected exit code can be checked by eye.
    """
    score_dict = {
        "correct_alerts": 2,
        "false_alerts": 1,
        "missed_alerts": 1,
        "correct_no_alerts": 2,
        "wrong_reason": 0,
        "emails_found": 1,
        "total_events": 6,
        "credits_spent": 0,
        "false_alerts_by_trap": {"company_too_small": 1},
        "false_alert_case_ids": ["e02"],
        "missed_alert_case_ids": ["e03"],
        "cases": {
            "e01": "pass",
            "e02": "fail",
            "e03": "fail",
            "e04": "pass",
            "e05": "pass",
            "e06": "pass",
        },
    }
    score_dict.update(overrides)
    return score_dict


def cases_with(**marks):
    base = {
        "e01": "pass",
        "e02": "fail",
        "e03": "fail",
        "e04": "pass",
        "e05": "pass",
        "e06": "pass",
    }
    base.update(marks)
    return base


def test_equal_scores_pass():
    result = compare(blank_score(), blank_score(), defaults())
    lines = result["comment"].splitlines()

    assert result["exit_code"] == 0
    assert lines[0] == "<!-- gtm-ci -->"
    assert lines[1] == "Passed: no metric got worse"
    assert result["pass_to_fail"] == []
    for label in (
        "correct alerts",
        "false alerts",
        "missed alerts",
        "correct no alerts",
        "wrong reason",
        "emails found",
        "total events",
        "credits",
        "false alerts for company_too_small",
    ):
        assert f"| {label} |" in result["comment"]
    assert "| false alerts | 1 | 1 | 0 |" in result["comment"]
    assert "| metric | base | head | change |" in result["comment"]
    assert "New false alerts: none" in result["comment"]
    assert "New missed alerts: none" in result["comment"]
    assert "Traps with more false alerts: none" in result["comment"]
    assert "Flipped from pass to fail: none" in result["comment"]


def test_more_false_alerts_fail():
    base = blank_score(
        false_alerts=2,
        false_alerts_by_trap={"company_too_small": 2},
        false_alert_case_ids=["e02", "e07"],
    )
    head = blank_score(
        false_alerts=5,
        false_alerts_by_trap={"company_too_small": 5},
        false_alert_case_ids=["e02", "e07", "e08", "e09", "e10"],
        cases=cases_with(e04="fail", e05="fail", e06="fail"),
    )
    result = compare(base, head, defaults())

    assert result["exit_code"] == 1
    assert result["verdict"] == "Blocked: false alerts went 2 -> 5"
    assert result["comment"].splitlines()[1] == "Blocked: false alerts went 2 -> 5"
    assert result["new_false_alert_case_ids"] == ["e08", "e09", "e10"]
    assert "New false alerts: e08, e09, e10" in result["comment"]
    assert result["pass_to_fail"] == ["e04", "e05", "e06"]
    assert "Flipped from pass to fail: e04, e05, e06" in result["comment"]
    assert "| false alerts | 2 | 5 | +3 |" in result["comment"]


def test_fewer_false_alerts_pass():
    """e04 was already failing and now passes. That is not a flip."""
    base = blank_score(
        false_alerts=5,
        false_alerts_by_trap={"company_too_small": 5},
        false_alert_case_ids=["e02", "e04", "e08", "e09", "e10"],
        cases=cases_with(e04="fail"),
    )
    result = compare(base, blank_score(), defaults())

    assert result["exit_code"] == 0
    assert result["verdict"] == "Passed: no metric got worse"
    assert result["pass_to_fail"] == []
    assert "| false alerts | 5 | 1 | -4 |" in result["comment"]
    assert "Flipped from pass to fail: none" in result["comment"]


def test_per_trap_rise_fails_when_the_total_is_unchanged():
    """e02 is fixed and e08 is a new false alert on a different trap.

    The total stays 1. e08 was not graded on base, so it is not a
    pass-to-fail flip. The rise on stale_event is the only broken rule.
    The drop on company_too_small does not cancel it.
    """
    base = blank_score(
        false_alerts=1,
        false_alerts_by_trap={"company_too_small": 1},
        false_alert_case_ids=["e02"],
    )
    head = blank_score(
        false_alerts=1,
        false_alerts_by_trap={"stale_event": 1},
        false_alert_case_ids=["e08"],
        cases=cases_with(e02="pass", e08="fail"),
    )
    result = compare(base, head, defaults())

    assert result["exit_code"] == 1
    assert result["pass_to_fail"] == []
    assert result["verdict"] == "Blocked: false alerts for stale_event went 0 -> 1"
    assert "| false alerts | 1 | 1 | 0 |" in result["comment"]
    assert "| false alerts for company_too_small | 1 | 0 | -1 |" in result["comment"]
    assert "| false alerts for stale_event | 0 | 1 | +1 |" in result["comment"]
    assert "New false alerts: e08" in result["comment"]
    assert "Traps with more false alerts: stale_event 0 -> 1" in result["comment"]


def test_one_pass_to_fail_flip_fails():
    """e04 starts failing and e02 starts passing.

    False alerts stay 1, on the same trap. Missed alerts stay 1.
    The flip is the only broken rule.
    """
    head = blank_score(
        false_alert_case_ids=["e04"],
        cases=cases_with(e02="pass", e04="fail"),
    )
    result = compare(blank_score(), head, defaults())

    assert result["exit_code"] == 1
    assert result["verdict"] == "Blocked: 1 case flipped from pass to fail"
    assert result["pass_to_fail"] == ["e04"]
    assert "| false alerts | 1 | 1 | 0 |" in result["comment"]
    assert "| missed alerts | 1 | 1 | 0 |" in result["comment"]
    assert "Traps with more false alerts: none" in result["comment"]
    assert "New false alerts: e04" in result["comment"]
    assert "Flipped from pass to fail: e04" in result["comment"]


def test_more_missed_alerts_fail_without_a_flip():
    """e09 was not graded on base, so the new miss is not a flip."""
    head = blank_score(
        missed_alerts=2,
        missed_alert_case_ids=["e03", "e09"],
        cases=cases_with(e09="fail"),
    )
    result = compare(blank_score(), head, defaults())

    assert result["exit_code"] == 1
    assert result["pass_to_fail"] == []
    assert result["verdict"] == "Blocked: missed alerts went 1 -> 2"
    assert result["new_missed_alert_case_ids"] == ["e09"]
    assert "New missed alerts: e09" in result["comment"]


def test_wrong_reason_is_shown_and_not_gated():
    head = blank_score(wrong_reason=4)
    result = compare(blank_score(), head, defaults())

    assert result["exit_code"] == 0
    assert "| wrong reason | 0 | 4 | +4 |" in result["comment"]


def test_thresholds_file_is_the_spec_default():
    text = (ROOT / "ci" / "thresholds.json").read_text(encoding="utf-8")
    assert text == EXPECTED_THRESHOLDS


def test_thresholds_are_read_and_not_hard_coded(tmp_path):
    """The same scores change exit code when the file changes.

    An increase equal to the max still passes. Greater than the max fails.
    """
    base = blank_score(
        false_alerts=2,
        false_alerts_by_trap={"company_too_small": 2},
        false_alert_case_ids=["e02", "e07"],
    )
    head = blank_score(
        false_alerts=3,
        false_alerts_by_trap={"company_too_small": 2},
        false_alert_case_ids=["e02", "e07"],
    )
    blocked = compare(base, head, defaults())
    assert blocked["exit_code"] == 1
    assert blocked["verdict"] == "Blocked: false alerts went 2 -> 3"

    # Rise of 1 is not greater than a max of 1.
    allowed = compare(base, head, _loose(tmp_path, "false-one.json", false_alerts_max_increase=1))
    assert allowed["exit_code"] == 0
    assert allowed["verdict"] == "Passed: no metric got worse"

    head_two = blank_score(
        false_alerts=4,
        false_alerts_by_trap={"company_too_small": 2},
        false_alert_case_ids=["e02", "e07"],
    )
    still_blocked = compare(
        base, head_two, _loose(tmp_path, "false-one-again.json", false_alerts_max_increase=1)
    )
    assert still_blocked["exit_code"] == 1

    trap_base = blank_score()
    trap_head = blank_score(
        false_alerts_by_trap={"stale_event": 1},
        false_alert_case_ids=["e08"],
        cases=cases_with(e02="pass", e08="fail"),
    )
    assert compare(trap_base, trap_head, defaults())["exit_code"] == 1
    trap_allowed = compare(
        trap_base,
        trap_head,
        _loose(tmp_path, "trap-one.json", false_alerts_max_increase_per_trap=1),
    )
    assert trap_allowed["exit_code"] == 0

    flip_head = blank_score(
        false_alert_case_ids=["e04"],
        cases=cases_with(e02="pass", e04="fail"),
    )
    assert compare(blank_score(), flip_head, defaults())["exit_code"] == 1
    flip_allowed = compare(
        blank_score(),
        flip_head,
        _loose(tmp_path, "flip-one.json", pass_to_fail_max=1),
    )
    assert flip_allowed["exit_code"] == 0

    miss_head = blank_score(
        missed_alerts=2,
        missed_alert_case_ids=["e03", "e09"],
        cases=cases_with(e09="fail"),
    )
    assert compare(blank_score(), miss_head, defaults())["exit_code"] == 1
    miss_allowed = compare(
        blank_score(),
        miss_head,
        _loose(tmp_path, "miss-one.json", missed_alerts_max_increase=1),
    )
    assert miss_allowed["exit_code"] == 0


def test_main_reads_report_files_and_the_thresholds_flag(tmp_path):
    base = blank_score(
        false_alerts=2,
        false_alerts_by_trap={"company_too_small": 2},
        false_alert_case_ids=["e02", "e07"],
    )
    head = blank_score(
        false_alerts=3,
        false_alerts_by_trap={"company_too_small": 2},
        false_alert_case_ids=["e02", "e07"],
    )
    base_path = tmp_path / "base.json"
    head_path = tmp_path / "head.json"
    out = tmp_path / "comment.md"
    base_path.write_text(
        json.dumps({"label": "base", "score": base}), encoding="utf-8"
    )
    head_path.write_text(
        json.dumps({"label": "head", "score": head}), encoding="utf-8"
    )
    loose = _loose_path(tmp_path, "loose.json", false_alerts_max_increase=1)

    code = main(
        [str(base_path), str(head_path), "--out", str(out), "--thresholds", str(loose)]
    )
    assert code == 0
    assert out.read_text(encoding="utf-8").splitlines()[1] == "Passed: no metric got worse"

    code = main(
        [
            str(base_path),
            str(head_path),
            "--out",
            str(out),
            "--thresholds",
            str(ROOT / "ci" / "thresholds.json"),
        ]
    )
    assert code == 1
    written = out.read_text(encoding="utf-8")
    assert written.splitlines()[0] == "<!-- gtm-ci -->"
    assert written.splitlines()[1] == "Blocked: false alerts went 2 -> 3"


def test_module_command_on_equal_scores(tmp_path):
    payload = json.dumps({"score": blank_score()})
    base_path = tmp_path / "base.json"
    head_path = tmp_path / "head.json"
    out = tmp_path / "comment.md"
    base_path.write_text(payload, encoding="utf-8")
    head_path.write_text(payload, encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scorer.compare",
            str(base_path),
            str(head_path),
            "--out",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    text = out.read_text(encoding="utf-8")
    assert text.startswith("<!-- gtm-ci -->\nPassed: no metric got worse\n")


def test_scored_rows_name_the_new_false_alert():
    """The dict score() returns is the dict compare() reads."""
    fixtures = [
        {
            "case_id": "e01",
            "split": "development",
            "trap": "clean_alert",
            "expected_alert": True,
            "expected_reason": "icp_fit",
        },
        {
            "case_id": "e02",
            "split": "development",
            "trap": "company_too_small",
            "expected_alert": False,
            "expected_reason": "company_too_small",
        },
    ]
    quiet = [
        {"case_id": "e01", "alert": True, "reason": "icp_fit", "email_status": "found"},
        {"case_id": "e02", "alert": False, "reason": "company_too_small", "email_status": "not_found"},
    ]
    noisy = [
        {"case_id": "e01", "alert": True, "reason": "icp_fit", "email_status": "found"},
        {"case_id": "e02", "alert": True, "reason": "icp_fit", "email_status": "found"},
    ]
    result = compare(score(quiet, fixtures, 0), score(noisy, fixtures, 0), defaults())

    assert result["exit_code"] == 1
    assert result["verdict"] == "Blocked: false alerts went 0 -> 1"
    assert result["new_false_alert_case_ids"] == ["e02"]
    assert result["pass_to_fail"] == ["e02"]
    assert result["traps_up"] == [{"trap": "company_too_small", "base": 0, "head": 1}]


def _loose(tmp_path, name, **changes):
    return load_thresholds(_loose_path(tmp_path, name, **changes))


def _loose_path(tmp_path, name, **changes):
    data = {
        "false_alerts_max_increase": 0,
        "missed_alerts_max_increase": 0,
        "false_alerts_max_increase_per_trap": 0,
        "pass_to_fail_max": 0,
        "live_max_credits": 10,
    }
    data.update(changes)
    path = Path(tmp_path) / name
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def test_more_paid_lookups_blocks_even_when_alerts_are_right():
    base = blank_score(paid_lookups=3, paid_lookup_case_ids=["e01", "e04", "e05"])
    head = blank_score(paid_lookups=4, paid_lookup_case_ids=["e01", "e02", "e04", "e05"])
    result = compare(base, head, defaults())
    assert result["exit_code"] == 1
    assert result["verdict"] == "Blocked: paid company lookups went 3 -> 4"
    assert result["new_paid_lookup_case_ids"] == ["e02"]
    assert "| paid company lookups | 3 | 4 | +1 |" in result["comment"]
    assert "New paid company lookups: e02" in result["comment"]


def test_fewer_paid_lookups_pass():
    base = blank_score(paid_lookups=4, paid_lookup_case_ids=["e01", "e02", "e04", "e05"])
    head = blank_score(paid_lookups=3, paid_lookup_case_ids=["e01", "e04", "e05"])
    assert compare(base, head, defaults())["exit_code"] == 0


def test_unknown_paid_lookups_are_not_gated():
    base = blank_score(paid_lookups="unknown", paid_lookup_case_ids=[])
    head = blank_score(paid_lookups=9, paid_lookup_case_ids=["e01"])
    assert compare(base, head, defaults())["exit_code"] == 0


def test_lookup_rule_is_optional_in_thresholds():
    limits = {
        "false_alerts_max_increase": 0,
        "missed_alerts_max_increase": 0,
        "false_alerts_max_increase_per_trap": 0,
        "pass_to_fail_max": 0,
    }
    base = blank_score(paid_lookups=1, paid_lookup_case_ids=["e01"])
    head = blank_score(paid_lookups=5, paid_lookup_case_ids=["e01"])
    assert compare(base, head, limits)["exit_code"] == 0
