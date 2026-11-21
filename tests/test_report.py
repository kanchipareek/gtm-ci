"""The markdown table and the JSON come from one score.

These tests do not call Deepline. The offline command test feeds rows
in memory. A live test that reached the CLI would spend credits.
"""

import json
import subprocess
from pathlib import Path

import pytest

from scorer.fixtures import load_fixtures
from scorer.report import to_json, to_markdown, write_report
from scorer.run import ROOT

MINI = ROOT / "tests" / "fixtures" / "mini_events.jsonl"


def meta(mode="offline", git_sha="abc123"):
    return {
        "label": "head",
        "mode": mode,
        "plays_dir": "plays",
        "git_sha": git_sha,
        "date": "2026-11-18",
    }


def counted_score():
    """Two correct alerts, one false, one missed, two quiet, one email.

    The numbers are chosen so each table cell can be checked by eye.
    by_split is only here so the report has a second table to render.
    """
    development = {
        "correct_alerts": 1,
        "false_alerts": 1,
        "missed_alerts": 1,
        "correct_no_alerts": 0,
        "emails_found": 1,
    }
    holdout = {
        "correct_alerts": 1,
        "false_alerts": 0,
        "missed_alerts": 0,
        "correct_no_alerts": 2,
        "emails_found": 0,
    }
    full = {
        "correct_alerts": 2,
        "false_alerts": 1,
        "missed_alerts": 1,
        "correct_no_alerts": 2,
        "emails_found": 1,
    }
    score = {
        "correct_alerts": 2,
        "false_alerts": 1,
        "missed_alerts": 1,
        "correct_no_alerts": 2,
        "wrong_reason": 1,
        "emails_found": 1,
        "total_events": 6,
        "credits_spent": 0,
        "false_alerts_by_trap": {"company_too_small": 1},
        "false_alert_case_ids": ["e02"],
        "missed_alert_case_ids": ["e03"],
        "cases": {},
        "join_errors": {
            "missing": 0,
            "duplicate": 0,
            "extra": 0,
            "missing_case_ids": [],
            "duplicate_case_ids": [],
            "extra_case_ids": [],
        },
        "by_split": {
            "development": development,
            "holdout": holdout,
            "all": full,
        },
    }
    return score


def test_markdown_lists_the_six_rows_and_the_offline_credits_sentence():
    text = to_markdown(counted_score(), meta())

    assert "| correct alerts | 2 |" in text
    assert "| false alerts | 1 |" in text
    assert "| missed alerts | 1 |" in text
    assert "| correct no alerts | 2 |" in text
    assert "| emails found | 1 |" in text
    assert "| credits | 0 (offline, no Deepline calls) |" in text
    assert "false alert case ids: e02" in text
    assert "missed alert case ids: e03" in text
    assert "- git sha: abc123" in text
    assert "- date: 2026-11-18" in text
    assert "- plays: plays" in text


def test_live_credits_cell_is_the_bill_not_the_offline_sentence():
    score = counted_score()
    score["credits_spent"] = 0.3
    text = to_markdown(score, meta(mode="live"))
    assert "| credits | 0.3 |" in text
    assert "offline, no Deepline calls" not in text

    score["credits_spent"] = "unknown"
    text = to_markdown(score, meta(mode="live"))
    assert "| credits | unknown |" in text
    assert "offline, no Deepline calls" not in text

    # A live usage file that says 0 is a real zero. It is not the offline label.
    score["credits_spent"] = 0
    text = to_markdown(score, meta(mode="live"))
    assert "| credits | 0 |" in text
    assert "offline, no Deepline calls" not in text


def test_json_holds_meta_and_the_same_score():
    score = counted_score()
    document = json.loads(to_json(score, meta(git_sha=None)))

    assert document["label"] == "head"
    assert document["mode"] == "offline"
    assert document["plays_dir"] == "plays"
    assert document["git_sha"] is None
    assert document["date"] == "2026-11-18"
    assert document["score"]["false_alerts"] == 1
    assert document["score"]["missed_alert_case_ids"] == ["e03"]
    assert document["score"]["credits_spent"] == 0
    assert document["score"] == score


def test_missing_git_sha_is_unavailable_in_the_table():
    text = to_markdown(counted_score(), meta(git_sha=None))
    assert "- git sha: unavailable" in text


def test_write_report_creates_both_files(tmp_path):
    score = counted_score()
    markdown = write_report("head", score, meta(), tmp_path)

    json_path = tmp_path / "head.json"
    md_path = tmp_path / "head.md"
    assert json_path.is_file()
    assert md_path.is_file()
    assert md_path.read_text(encoding="utf-8") == markdown
    saved = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved["score"]["correct_alerts"] == 2
    assert "0 (offline, no Deepline calls)" in markdown


def test_label_cannot_escape_the_results_folder(tmp_path):
    with pytest.raises(ValueError, match="file name"):
        write_report("../outside", counted_score(), meta(), tmp_path)


def test_parse_args_defaults():
    from scorer.__main__ import parse_args

    args = parse_args(["--mode", "offline", "--label", "head"])
    assert args.mode == "offline"
    assert args.label == "head"
    assert args.plays == "plays"
    assert args.fixtures == "fixtures/events.jsonl"
    assert args.max_credits is None
    assert args.yes is False


def test_offline_command_writes_the_table(tmp_path, monkeypatch, capsys):
    from scorer.__main__ import main

    golden = load_fixtures(MINI)
    rows = []
    for item in golden:
        rows.append(
            {
                "case_id": item["case_id"],
                "alert": item["expected_alert"],
                "reason": item["expected_reason"],
                "email_status": item["input_mock_email_status"],
            }
        )

    def fake_offline(plays_dir, fixtures_path):
        assert plays_dir == "plays"
        assert Path(fixtures_path) == MINI
        return {"rows": rows, "mode": "offline", "credits_spent": 0}

    def fail_live(*_args, **_kwargs):
        raise AssertionError("offline mode called run_live")

    monkeypatch.setattr("scorer.__main__.run_offline", fake_offline)
    monkeypatch.setattr("scorer.__main__.run_live", fail_live)
    monkeypatch.setattr("scorer.__main__.git_sha", lambda: "abc123")
    monkeypatch.setattr("scorer.__main__.RESULTS_DIR", tmp_path)

    code = main(
        [
            "--mode",
            "offline",
            "--label",
            "head",
            "--fixtures",
            str(MINI),
        ]
    )
    assert code == 0

    printed = capsys.readouterr().out
    assert "| correct alerts | 1 |" in printed
    assert "| false alerts | 0 |" in printed
    assert "| missed alerts | 0 |" in printed
    assert "| correct no alerts | 2 |" in printed
    assert "| emails found | 1 |" in printed
    assert "| credits | 0 (offline, no Deepline calls) |" in printed

    saved = json.loads((tmp_path / "head.json").read_text(encoding="utf-8"))
    assert saved["mode"] == "offline"
    assert saved["git_sha"] == "abc123"
    assert saved["score"]["credits_spent"] == 0
    assert saved["score"]["total_events"] == 3
    assert (tmp_path / "head.md").is_file()


def test_live_stops_unless_the_answer_is_yes(monkeypatch, capsys):
    from scorer.__main__ import main

    def fail_live(*_args, **_kwargs):
        raise AssertionError("run_live was called without a yes")

    monkeypatch.setattr("scorer.__main__.run_live", fail_live)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "no")

    code = main(
        ["--mode", "live", "--label", "head", "--max-credits", "10"]
    )
    assert code == 1
    out = capsys.readouterr().out
    assert "planned max credits: 10" in out
    assert "no Deepline call was made" in out


def test_live_yes_flag_skips_the_question(tmp_path, monkeypatch, capsys):
    from scorer.__main__ import main

    golden = load_fixtures(MINI)
    rows = [
        {
            "case_id": item["case_id"],
            "alert": item["expected_alert"],
            "reason": item["expected_reason"],
            "email_status": "not_found",
        }
        for item in golden
    ]

    def fake_live(fixtures_path, max_credits):
        assert max_credits == 10
        assert Path(fixtures_path) == MINI
        return {"rows": rows, "mode": "live", "credits_spent": "unknown"}

    def fail_input(_prompt=""):
        raise AssertionError("--yes still asked for a keyboard answer")

    monkeypatch.setattr("scorer.__main__.run_live", fake_live)
    monkeypatch.setattr("builtins.input", fail_input)
    monkeypatch.setattr("scorer.__main__.git_sha", lambda: None)
    monkeypatch.setattr("scorer.__main__.RESULTS_DIR", tmp_path)

    code = main(
        [
            "--mode",
            "live",
            "--label",
            "try",
            "--yes",
            "--max-credits",
            "10",
            "--fixtures",
            str(MINI),
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "planned max credits: 10" in out
    assert "| credits | unknown |" in out
    assert "offline, no Deepline calls" not in out
    saved = json.loads((tmp_path / "try.json").read_text(encoding="utf-8"))
    assert saved["score"]["credits_spent"] == "unknown"
    assert saved["git_sha"] is None


def test_live_without_a_cap_does_not_call_deepline(monkeypatch, capsys):
    from scorer.__main__ import main

    def fail_live(*_args, **_kwargs):
        raise AssertionError("run_live was called with no cap")

    monkeypatch.setattr("scorer.__main__.run_live", fail_live)
    code = main(["--mode", "live", "--label", "head"])
    assert code == 1
    assert "needs --max-credits" in capsys.readouterr().out


def test_results_folder_is_ignored_except_the_readme():
    readme = (ROOT / "results" / "README.md").read_text(encoding="utf-8")
    assert "live_<date>" in readme
    assert "demo_comment.md" in readme

    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "results/head.json"],
        cwd=ROOT,
        check=False,
    )
    kept = subprocess.run(
        ["git", "check-ignore", "-q", "results/README.md"],
        cwd=ROOT,
        check=False,
    )
    assert ignored.returncode == 0
    assert kept.returncode == 1
