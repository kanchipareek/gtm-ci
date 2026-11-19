"""Find the one comment this check owns.

Fake lists stand in for the GitHub API. Nothing here calls gh or GitHub.
The marker has to be the start of the body. A comment that only mentions
it later belongs to a person and must be left alone.
"""

import pytest

from scripts.post_comment import (
    comments_from_pages,
    find_marked_comment,
    keep_live_section,
)


MARKER = "<!-- gtm-ci -->"


def test_empty_list_has_no_marked_comment():
    assert find_marked_comment([]) is None


def test_other_comments_are_not_ours():
    comments = [
        {"id": 1, "body": "looks good"},
        {"id": 2, "body": "please rename this"},
    ]
    assert find_marked_comment(comments) is None


def test_marker_at_the_start_is_ours():
    body = MARKER + "\nBlocked: false alerts went 0 -> 2\n"
    comments = [
        {"id": 7, "body": "a review note"},
        {"id": 11, "body": body},
    ]
    found = find_marked_comment(comments)
    assert found["id"] == 11
    assert found["body"].startswith(MARKER)


def test_marker_later_in_the_body_is_not_ours():
    comments = [
        {"id": 4, "body": "the check writes\n" + MARKER + "\nat the top"},
        {"id": 5, "body": "hello " + MARKER},
    ]
    assert find_marked_comment(comments) is None


def test_first_marked_comment_wins():
    # The API lists oldest first. A second marked comment is a leftover.
    # Editing the first one is what stops the next push adding another.
    comments = [
        {"id": 1, "body": MARKER + "\nPassed: no metric got worse\n"},
        {"id": 2, "body": "ship it"},
        {"id": 9, "body": MARKER + "\nBlocked: false alerts went 0 -> 1\n"},
    ]
    assert find_marked_comment(comments)["id"] == 1


def test_missing_or_blank_body_is_skipped():
    comments = [
        {"id": 1},
        {"id": 2, "body": None},
        {"id": 3, "body": ""},
        "not a comment",
        {"id": 4, "body": MARKER},
    ]
    assert find_marked_comment(comments)["id"] == 4


def test_slurped_pages_are_one_list():
    # gh api --paginate --slurp wraps each page. The marker can sit on
    # a later page. Searching only the first page would create a duplicate.
    pages = [
        [{"id": 1, "body": "first page"}],
        [],
        [{"id": 40, "body": MARKER + "\nPassed: no metric got worse\n"}],
    ]
    comments = comments_from_pages(pages)
    assert [comment["id"] for comment in comments] == [1, 40]
    assert find_marked_comment(comments)["id"] == 40


def test_a_bare_comment_list_is_accepted():
    comments = comments_from_pages([
        {"id": 3, "body": "note"},
        {"id": 8, "body": MARKER + "\nPassed: no metric got worse\n"},
    ])
    assert find_marked_comment(comments)["id"] == 8


def test_empty_pages_are_no_comments():
    assert comments_from_pages([]) == []
    assert comments_from_pages([[]]) == []
    assert find_marked_comment(comments_from_pages([[]])) is None


def test_an_update_keeps_the_live_run_section():
    old = (
        MARKER + "\nPassed: no metric got worse\n\n"
        "## Live run\n\n"
        "- run id: run-123\n"
        "- credits: unknown\n"
        "- drift: 2\n"
    )
    new = MARKER + "\nBlocked: false alerts went 0 -> 1\n"
    kept = keep_live_section(new, old)
    assert kept.startswith(MARKER + "\nBlocked: false alerts went 0 -> 1\n")
    assert "\n## Live run\n" in kept
    assert "- run id: run-123\n" in kept
    assert "- credits: unknown\n" in kept
    assert kept.endswith("- drift: 2\n")


def test_a_comment_without_a_live_section_is_unchanged():
    new = MARKER + "\nPassed: no metric got worse\n"
    assert keep_live_section(new, MARKER + "\nPassed: no metric got worse\n") == new
    assert keep_live_section(new, None) == new
    assert keep_live_section(new, "see ## Live run in the docs") == new


def test_a_new_live_section_is_not_duplicated():
    old = MARKER + "\n\n## Live run\n\n- run id: old-run\n"
    new = MARKER + "\nPassed: no metric got worse\n\n## Live run\n\n- run id: new-run\n"
    assert keep_live_section(new, old) == new


def test_a_bad_page_shape_is_rejected():
    with pytest.raises(ValueError, match="JSON array"):
        comments_from_pages({"body": MARKER})
    with pytest.raises(ValueError, match="page"):
        comments_from_pages([[{"id": 1, "body": "ok"}], {"id": 2}])
