"""Post the before/after comment, or replace the one already on the pull request.

compare.py writes results/comment.md. The first line is the hidden marker
<!-- gtm-ci -->. This script lists the pull request's comments, finds the
one that starts with that marker, and edits it. The first run creates it.

GitHub-hosted runners already have the gh CLI. It authenticates with
GITHUB_TOKEN, the token GitHub creates for the job. The token stays in
the environment and is never printed.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


# The same first line compare.py writes. A person's comment does not
# start with it, so a later push does not edit their comment.
MARKER = "<!-- gtm-ci -->"

# The live job appends this heading. The gate writes a fresh comment, so
# an update has to copy the heading and everything under it back on.
LIVE_HEADING = "## Live run"


def find_marked_comment(comments):
    """Return the first comment whose body starts with the marker, or None.

    comments is a list of dicts, the same shape as the GitHub API: each
    one has "id" and "body". The API lists comments oldest first. Editing
    the first match keeps a single comment when this runs again.
    """
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        body = comment.get("body")
        if isinstance(body, str) and body.startswith(MARKER):
            return comment
    return None


def keep_live_section(new_body, old_body):
    """Return the new comment with the old Live run section still at the end.

    The gate writes a fresh file that has no live block. Replacing the
    pull request comment with that file would drop the last live run.
    The old section is copied as it was written. A new body that already
    has the heading is left alone, so a second section is not added.
    """
    if _live_section(new_body) is not None:
        return new_body
    section = _live_section(old_body)
    if section is None:
        return new_body
    body = new_body
    if not body.endswith("\n"):
        body += "\n"
    if not body.endswith("\n\n"):
        body += "\n"
    return body + section


def _live_section(body):
    """The Live run block, from its heading line through the end, or None."""
    if not isinstance(body, str) or body == "":
        return None
    lines = body.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.rstrip("\r\n") == LIVE_HEADING:
            section = "".join(lines[index:])
            if not section.endswith("\n"):
                section += "\n"
            return section
    return None


def comments_from_pages(pages):
    """Turn gh api --paginate --slurp output into one list of comments.

    The gh api manual says each page is its own JSON array, and --slurp
    wraps those pages in one outer array. One page looks like
    [[{...}, {...}]]. A bare list of comment objects is accepted too,
    so a single unwrapped page still searches every comment.
    """
    if not isinstance(pages, list):
        raise ValueError("comment list was not a JSON array")
    if not pages:
        return []
    if isinstance(pages[0], dict):
        return pages
    comments = []
    for page in pages:
        if not isinstance(page, list):
            raise ValueError("a comment page was not a JSON array")
        comments.extend(page)
    return comments


def main(argv=None):
    """Read the comment file, then create or update the one pull request comment."""
    args = parse_args(argv)
    comment_path = Path(args.comment_file)
    try:
        body = comment_path.read_text(encoding="utf-8")
    except OSError:
        print(f"could not read the comment file: {comment_path}")
        return 1
    if not body.startswith(MARKER):
        print("the comment file does not start with the gtm-ci marker")
        return 1

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    number = os.environ.get("PR_NUMBER", "")
    if repo.count("/") != 1 or not number.isdigit():
        print("GITHUB_REPOSITORY and PR_NUMBER are required")
        return 1
    # gh reads GITHUB_TOKEN from the environment. Do not pass it as an argument.
    if "GITHUB_TOKEN" not in os.environ and "GH_TOKEN" not in os.environ:
        print("GITHUB_TOKEN is required")
        return 1

    try:
        comments = list_comments(repo, number)
        found = find_marked_comment(comments)
        if found is None:
            create_comment(repo, number, body)
            print("created the pull request comment")
        else:
            comment_id = found.get("id")
            if comment_id is None:
                print("the marked comment has no id")
                return 1
            # The file is the new gate text. The comment on GitHub may
            # already end with a Live run block from an earlier live job.
            body = keep_live_section(body, found.get("body"))
            update_comment(repo, comment_id, body)
            print(f"updated comment {comment_id}")
    except (RuntimeError, ValueError) as exc:
        print(str(exc))
        return 1
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Post or update the one gtm-ci comment on the pull request."
    )
    parser.add_argument(
        "comment_file",
        help="Markdown file whose first line is the gtm-ci marker.",
    )
    return parser.parse_args(argv)


def list_comments(repo, number):
    """Every issue comment on the pull request, oldest first.

    --paginate follows the next page. --slurp joins the pages into one
    JSON value. per_page=100 is the API maximum, so a short thread is
    one request.
    """
    output = run_gh([
        "--paginate",
        "--slurp",
        "--method",
        "GET",
        f"repos/{repo}/issues/{number}/comments?per_page=100",
    ])
    try:
        payload = json.loads(output) if output.strip() else []
    except json.JSONDecodeError as exc:
        raise ValueError("gh api did not return a JSON comment list") from exc
    return comments_from_pages(payload)


def create_comment(repo, number, body):
    """POST a new issue comment on the pull request."""
    payload = _body_file(body)
    try:
        run_gh([
            "--method",
            "POST",
            "--input",
            str(payload),
            f"repos/{repo}/issues/{number}/comments",
        ])
    finally:
        payload.unlink(missing_ok=True)


def update_comment(repo, comment_id, body):
    """PATCH the existing comment. The whole body is replaced."""
    payload = _body_file(body)
    try:
        run_gh([
            "--method",
            "PATCH",
            "--input",
            str(payload),
            f"repos/{repo}/issues/comments/{comment_id}",
        ])
    finally:
        payload.unlink(missing_ok=True)


def _body_file(body):
    """Write {"body": ...} to a temp file for gh api --input.

    The comment is markdown. A file keeps the quotes and newlines intact.
    Inline JSON breaks under PowerShell quoting, and the same file works
    on the Ubuntu runner.
    """
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        delete=False,
    )
    with handle:
        json.dump({"body": body}, handle)
    return Path(handle.name)


def run_gh(args):
    """Run gh api. A non-zero exit becomes an error. The token is not printed."""
    completed = subprocess.run(
        ["gh", "api", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "gh api failed"
        raise RuntimeError(detail)
    return completed.stdout


if __name__ == "__main__":
    sys.exit(main())
