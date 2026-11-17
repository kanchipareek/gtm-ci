"""Smoke tests for the starter kit.

They check the setup, not any project logic. They make no network calls
and no Deepline calls.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_python_is_3_11_or_newer():
    assert sys.version_info >= (3, 11)


def test_spec_and_tasks_exist():
    assert (ROOT / "docs" / "spec.md").is_file()
    assert (ROOT / "TASKS.md").is_file()
    assert (ROOT / ".cursor" / "rules" / "project.mdc").is_file()


def test_secret_files_are_gitignored():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in ignored
    assert ".env.deepline" in ignored


def test_env_example_has_no_key_value():
    # .env.example must list names only. A real key there would be committed.
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if line.startswith("DEEPLINE_API_KEY="):
            assert line == "DEEPLINE_API_KEY="
