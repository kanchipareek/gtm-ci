"""The test set cannot quietly grade itself.

Two temp folders stand in for the base checkout and the head checkout.
Same bytes pass. An edited fixture or an edited ci/thresholds.json is a
change. The command exits 1 unless the labels include test-set-change.
A change under plays/ is not a test-set change.
"""

import os
import subprocess
import sys

from scorer.guard import changed_test_files, main
from scorer.run import ROOT


def test_same_bytes_are_not_a_change(tmp_path, capsys):
    base = tmp_path / "base"
    head = tmp_path / "head"
    _checkout(base)
    _checkout(head)
    # A fresh checkout stamps a new modified time. The hash ignores that.
    os.utime(head / "fixtures" / "events.jsonl", (1_700_000_000, 1_700_000_000))

    assert changed_test_files(base, head) == []
    assert main([str(base), str(head), "--labels", ""]) == 0
    assert capsys.readouterr().out == ""


def test_edited_fixture_fails_without_the_label(tmp_path, capsys):
    base = tmp_path / "base"
    head = tmp_path / "head"
    _checkout(base)
    _checkout(head, events="e01 changed\n")

    assert changed_test_files(base, head) == ["fixtures/events.jsonl"]
    code = main([str(base), str(head), "--labels", "live-eval"])
    assert code == 1
    line = capsys.readouterr().out.strip()
    assert line == (
        "Warning: test set changed (fixtures/events.jsonl) "
        "without the test-set-change label."
    )


def test_edited_thresholds_fail_without_the_label(tmp_path, capsys):
    base = tmp_path / "base"
    head = tmp_path / "head"
    _checkout(base)
    _checkout(head, thresholds='{"false_alerts_max_increase": 5}\n')

    assert changed_test_files(base, head) == ["ci/thresholds.json"]
    code = main([str(base), str(head)])
    assert code == 1
    assert "ci/thresholds.json" in capsys.readouterr().out


def test_label_lets_the_check_pass_and_still_warns(tmp_path, capsys):
    base = tmp_path / "base"
    head = tmp_path / "head"
    _checkout(base)
    _checkout(head, events="e01 changed\n", thresholds='{"pass_to_fail_max": 1}\n')

    changed = changed_test_files(base, head)
    assert changed == ["ci/thresholds.json", "fixtures/events.jsonl"]
    code = main([str(base), str(head), "--labels", " live-eval, test-set-change "])
    assert code == 0
    line = capsys.readouterr().out.strip()
    assert line == (
        "Warning: test set changed (ci/thresholds.json, fixtures/events.jsonl). "
        "The test-set-change label is present."
    )


def test_added_and_deleted_fixture_files_count(tmp_path):
    base = tmp_path / "base"
    head = tmp_path / "head"
    _checkout(base, extra={"events.csv": "e01\n"})
    _checkout(head, extra={"nested/hidden.jsonl": "e99\n"})

    assert changed_test_files(base, head) == [
        "fixtures/events.csv",
        "fixtures/nested/hidden.jsonl",
    ]


def test_a_rules_edit_is_not_a_test_set_change(tmp_path, capsys):
    base = tmp_path / "base"
    head = tmp_path / "head"
    _checkout(base, rules="export const MIN_EMPLOYEES = 50\n")
    _checkout(head, rules="export const MIN_EMPLOYEES = 10\n")

    assert changed_test_files(base, head) == []
    assert main([str(base), str(head), "--labels", ""]) == 0
    assert capsys.readouterr().out == ""


def test_missing_checkout_is_an_error(tmp_path, capsys):
    base = tmp_path / "base"
    _checkout(base)
    code = main([str(base), str(tmp_path / "missing"), "--labels", "test-set-change"])
    assert code == 1
    assert "head checkout is not a folder" in capsys.readouterr().out


def test_module_command_exits_1_without_the_label(tmp_path):
    base = tmp_path / "base"
    head = tmp_path / "head"
    _checkout(base)
    _checkout(head, events="rewritten answer\n")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scorer.guard",
            str(base),
            str(head),
            "--labels",
            "live-eval",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert completed.returncode == 1, completed.stderr
    assert completed.stdout.strip() == (
        "Warning: test set changed (fixtures/events.jsonl) "
        "without the test-set-change label."
    )


def _checkout(folder, events="e01\n", thresholds="{}\n", extra=None, rules=None):
    """A tiny checkout: fixtures, the thresholds file, and an optional rule."""
    fixture_dir = folder / "fixtures"
    fixture_dir.mkdir(parents=True)
    (fixture_dir / "events.jsonl").write_bytes(events.encode("utf-8"))
    for name, text in (extra or {}).items():
        path = fixture_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    thresholds_path = folder / "ci" / "thresholds.json"
    thresholds_path.parent.mkdir(parents=True, exist_ok=True)
    thresholds_path.write_bytes(thresholds.encode("utf-8"))
    if rules is not None:
        rules_path = folder / "plays" / "rules.ts"
        rules_path.parent.mkdir(parents=True, exist_ok=True)
        rules_path.write_bytes(rules.encode("utf-8"))


def test_add_to_comment_puts_blocked_line_under_marker():
    from scorer.guard import add_to_comment

    comment = "<!-- gtm-ci -->\nPassed: no metric got worse\n\n| metric |\n"
    line = "Warning: test set changed (fixtures/events.jsonl) without the test-set-change label."
    out = add_to_comment(comment, line, blocked=True)
    assert out.splitlines()[0] == "<!-- gtm-ci -->"
    assert out.splitlines()[1] == "Blocked by the test set guard. " + line
    assert out.splitlines()[2] == "Passed: no metric got worse"


def test_add_to_comment_labelled_change_is_a_plain_warning_and_no_change_is_untouched():
    from scorer.guard import add_to_comment

    comment = "<!-- gtm-ci -->\nPassed: no metric got worse\n"
    line = "Warning: test set changed (ci/thresholds.json). The test-set-change label is present."
    assert add_to_comment(comment, line, blocked=False).splitlines()[1] == line
    assert add_to_comment(comment, None, blocked=False) == comment


def test_comment_mode_exits_zero_and_writes_the_file(tmp_path):
    from scorer.guard import main

    base = tmp_path / "base"
    head = tmp_path / "head"
    for root, text in ((base, "a"), (head, "b")):
        (root / "fixtures").mkdir(parents=True)
        (root / "fixtures" / "events.jsonl").write_text(text, encoding="utf-8")
    comment = tmp_path / "comment.md"
    comment.write_text("<!-- gtm-ci -->\nPassed: no metric got worse\n", encoding="utf-8")
    assert main([str(base), str(head), "--comment", str(comment)]) == 0
    assert "Blocked by the test set guard." in comment.read_text(encoding="utf-8")
    assert main([str(base), str(head)]) == 1
