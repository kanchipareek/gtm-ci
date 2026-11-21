import json

import pytest

from scorer.mutate import (
    DEFAULT_MUTATIONS,
    ROOT,
    apply_mutation,
    changed_cases,
    load_mutations,
    summarize,
)


def test_every_committed_mutation_applies_exactly_once():
    rules_file, mutations = load_mutations(DEFAULT_MUTATIONS)
    text = (ROOT / rules_file).read_text(encoding="utf-8")
    for mutation in mutations:
        assert apply_mutation(text, mutation) is not None, mutation["id"]


def test_apply_refuses_missing_or_repeated_find():
    assert apply_mutation("a = 1;", {"find": "b", "replace": "c"}) is None
    assert apply_mutation("x x", {"find": "x", "replace": "y"}) is None
    assert apply_mutation("x y", {"find": "x", "replace": "z"}) == "z y"


def test_load_rejects_bad_split(tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"mutations": [
        {"id": "a", "split": "other", "find": "x", "replace": "y", "why": "w"}
    ]}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_mutations(path)


def test_changed_cases_lists_alert_and_reason_moves():
    base = [{"case_id": "e1", "alert": False, "reason": "junior_title"},
            {"case_id": "e2", "alert": True, "reason": "icp_fit"}]
    head = [{"case_id": "e1", "alert": False, "reason": "ambiguous_title"},
            {"case_id": "e2", "alert": True, "reason": "icp_fit"}]
    assert changed_cases(base, head) == {
        "e1": ["no alert (junior_title)", "no alert (ambiguous_title)"]
    }


def test_summarize_counts_per_split_and_skips_not_applied():
    results = [
        {"id": "m1", "split": "discovery", "outcome": "caught"},
        {"id": "m2", "split": "discovery", "outcome": "survived"},
        {"id": "h1", "split": "holdout", "outcome": "caught"},
        {"id": "h2", "split": "holdout", "outcome": "not_applied"},
    ]
    summary = summarize(results)
    assert summary["discovery"] == {"caught": 1, "applied": 2, "not_applied": 0, "survivors": ["m2"]}
    assert summary["holdout"] == {"caught": 1, "applied": 1, "not_applied": 1, "survivors": []}
    assert summary["all"]["caught"] == 2
