"""Fail a pull request that edits the answer key or the pass limits.

Base and head are both scored on the head fixtures, so the Play is the
only thing that differs. That does not notice a pull request that
rewrites the expected answers, or loosens ci/thresholds.json, until both
sides pass. This module hashes those files and requires the
test-set-change label when the bytes differ.

The warning line is the first line of the pull request comment.
"""

import argparse
import hashlib
import sys
from pathlib import Path


# Spec section 2. One spelling, so the check and the comment match.
TEST_SET_LABEL = "test-set-change"

# The answer key is the whole fixtures folder, including a file added
# later such as live_companies.json. The pass limits are one file.
# A change under plays/ is what the gate is meant to score.
FIXTURES_DIR = "fixtures"
THRESHOLDS_FILE = "ci/thresholds.json"

# The first line of the one pull request comment (scorer/compare.py).
MARKER = "<!-- gtm-ci -->"


def changed_test_files(base_dir, head_dir):
    """Return fixture and threshold paths whose file hash differs.

    A path is included when the bytes differ, or the file exists on only
    one side. Deleting a case is a test-set change. The list is sorted
    and uses forward slashes, so the warning line is stable.
    """
    base = Path(base_dir)
    head = Path(head_dir)
    if not base.is_dir():
        raise ValueError(f"base checkout is not a folder: {base}")
    if not head.is_dir():
        raise ValueError(f"head checkout is not a folder: {head}")

    base_hashes = _watched_hashes(base)
    head_hashes = _watched_hashes(head)
    changed = []
    for rel in sorted(set(base_hashes) | set(head_hashes)):
        if base_hashes.get(rel) != head_hashes.get(rel):
            changed.append(rel)
    return changed


def warning_line(changed, labels):
    """One comment line when the test set changed. None when it did not.

    The line is printed either way. The label lets the check pass. It
    does not hide the change from the reviewer.
    """
    if not changed:
        return None
    paths = ", ".join(changed)
    if TEST_SET_LABEL in labels:
        return (
            f"Warning: test set changed ({paths}). "
            "The test-set-change label is present."
        )
    return (
        f"Warning: test set changed ({paths}) "
        "without the test-set-change label."
    )


def add_to_comment(comment, line, blocked):
    """Put the guard line right under the marker, above the score verdict.

    The compare verdict only judges the scores. Without this line a pull
    request can show "Passed: no metric got worse" next to a red check.
    """
    if line is None:
        return comment
    text = f"Blocked by the test set guard. {line}" if blocked else line
    first, sep, rest = comment.partition("\n")
    if first.strip() == MARKER:
        return f"{first}\n{text}\n{rest}"
    return f"{text}\n{comment}"


def main(argv=None):
    """Print the warning line and return 1 when the label is missing.

    With --comment, write the line into that comment file instead and
    return 0. The workflow runs the check once to set the exit code and
    once more to annotate the comment.
    """
    args = parse_args(argv)
    try:
        changed = changed_test_files(args.base, args.head)
    except ValueError as exc:
        print(str(exc))
        return 1
    labels = parse_labels(args.labels)
    line = warning_line(changed, labels)
    blocked = bool(changed) and TEST_SET_LABEL not in labels
    if args.comment:
        path = Path(args.comment)
        if not path.is_file():
            return 0
        updated = add_to_comment(path.read_text(encoding="utf-8"), line, blocked)
        path.write_text(updated, encoding="utf-8", newline="\n")
        return 0
    if line is not None:
        print(line)
    if blocked:
        return 1
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Fail if the test set changed without the test-set-change label."
    )
    parser.add_argument("base", help="Folder for the base checkout.")
    parser.add_argument("head", help="Folder for the head checkout.")
    parser.add_argument(
        "--labels",
        default="",
        help="Comma-separated pull request labels.",
    )
    parser.add_argument(
        "--comment",
        help="Write the warning into this comment file under the marker, and exit 0.",
    )
    return parser.parse_args(argv)


def parse_labels(text):
    """Split a comma-separated label list. Blank pieces are dropped."""
    if text is None:
        return []
    labels = []
    for part in str(text).split(","):
        name = part.strip()
        if name != "" and name not in labels:
            labels.append(name)
    return labels


def _watched_hashes(root):
    hashes = {}
    fixtures = root / FIXTURES_DIR
    if fixtures.is_dir():
        for path in fixtures.rglob("*"):
            if path.is_file():
                rel = path.relative_to(root).as_posix()
                hashes[rel] = _file_hash(path)
    elif fixtures.is_file():
        # Replacing the folder with a file is still a test-set change.
        hashes[FIXTURES_DIR] = _file_hash(fixtures)

    thresholds = root / THRESHOLDS_FILE
    if thresholds.is_file():
        hashes[THRESHOLDS_FILE] = _file_hash(thresholds)
    return hashes


def _file_hash(path):
    # Hash the bytes, not the modified time. Two checkouts of the same
    # commit have different timestamps, and that is not a change.
    # Parsing would also miss a file that is not valid JSON.
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    sys.exit(main())
