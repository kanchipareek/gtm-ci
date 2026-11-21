"""Join Play rows to golden fixtures and count the outcomes.

The join key is case_id. Row order is not used. A case_id that is missing,
duplicated, or not in the golden set is a join error. It is counted on its
own and is not turned into a false alert or a missed alert.

credits_spent is copied onto the result. Offline passes 0. A live run with
no bill passes "unknown". This module does not invent 0.

The top-level counts are the full set. That is what the CI gate reads.
by_split repeats the headline counts for development, holdout, and all.
"""

from scorer.fixtures import REASONS, SPLITS


def score(rows, fixtures, credits_spent):
    """Count alerts, join errors, and pass or fail for each joined case.

    Pass means the alert boolean matches expected_alert. The reason is
    not part of pass or fail. wrong_reason is only the case where both
    sides say no alert and the reason labels differ. The gate does not
    use that count. It is there so the report can show it.
    """
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    if not isinstance(fixtures, list):
        raise ValueError("fixtures must be a list")

    golden = [_checked_fixture(item) for item in fixtures]
    golden_by_id = _group(golden, "fixture")
    rows_by_id = _group(rows, "row")
    missing_ids, duplicate_ids, extra_ids, pairs = _join(golden_by_id, rows_by_id)

    by_split = {
        "development": _empty_counts(),
        "holdout": _empty_counts(),
        "all": _empty_counts(),
    }
    # total_events is the golden set. A missing row stays in the total.
    # The join-error lists name it. It is not dropped, and it is not a miss.
    for item in golden:
        by_split[item["split"]]["total_events"] += 1
        by_split["all"]["total_events"] += 1

    cases = {}
    for item, row in pairs:
        _count_pair(item, row, by_split, cases)

    for bucket in by_split.values():
        _sort_bucket(bucket)

    published = {
        "development": _copy_counts(by_split["development"]),
        "holdout": _copy_counts(by_split["holdout"]),
        "all": _copy_counts(by_split["all"]),
    }
    # Top level is the full set, same numbers as by_split["all"].
    result = _copy_counts(by_split["all"])
    result["credits_spent"] = credits_spent
    result["cases"] = {case_id: cases[case_id] for case_id in sorted(cases)}
    result["join_errors"] = {
        "missing": len(missing_ids),
        "duplicate": len(duplicate_ids),
        "extra": len(extra_ids),
        "missing_case_ids": missing_ids,
        "duplicate_case_ids": duplicate_ids,
        "extra_case_ids": extra_ids,
    }
    result["by_split"] = published
    result["paid_lookups"], result["paid_lookup_case_ids"] = _paid_lookups(pairs)
    return result


def _paid_lookups(pairs):
    """Count joined rows that would pay for the company lookup.

    The offline runner marks would_lookup with the Play's own two-call
    flow. A live row has no such field, and an older runner did not write
    it, so the count is "unknown" then, never 0 by guess.
    """
    ids = []
    for item, row in pairs:
        flag = row.get("would_lookup")
        if not isinstance(flag, bool):
            return "unknown", []
        if flag:
            ids.append(item["case_id"])
    return len(ids), sorted(ids)


def _count_pair(item, row, by_split, cases):
    case_id = item["case_id"]
    split = item["split"]
    expected_alert = item["expected_alert"]
    got_alert = _got_alert(row, case_id)
    buckets = (by_split[split], by_split["all"])

    if expected_alert and got_alert:
        for bucket in buckets:
            bucket["correct_alerts"] += 1
    elif (not expected_alert) and got_alert:
        for bucket in buckets:
            bucket["false_alerts"] += 1
            bucket["false_alert_case_ids"].append(case_id)
            trap = item["trap"]
            traps = bucket["false_alerts_by_trap"]
            traps[trap] = traps.get(trap, 0) + 1
    elif expected_alert and not got_alert:
        for bucket in buckets:
            bucket["missed_alerts"] += 1
            bucket["missed_alert_case_ids"].append(case_id)
    else:
        # Both say no alert. The rep was not asked to act.
        # A different reject reason is shown, and it is still a pass.
        for bucket in buckets:
            bucket["correct_no_alerts"] += 1
            if not _reasons_match(item["expected_reason"], row.get("reason")):
                bucket["wrong_reason"] += 1

    # emails_found counts alerts that came back with an email.
    # A no-alert row can carry email_status "found" and still not count.
    if got_alert and row.get("email_status") == "found":
        for bucket in buckets:
            bucket["emails_found"] += 1

    if got_alert == expected_alert:
        cases[case_id] = "pass"
    else:
        cases[case_id] = "fail"


def _join(golden_by_id, rows_by_id):
    """Pair each case_id that appears once on each side.

    A repeated id is not graded. Taking either copy would depend on
    which one was written first, which is row position again.
    """
    missing = []
    duplicate = []
    extra = []
    pairs = []

    for case_id, golden_rows in golden_by_id.items():
        actual_rows = rows_by_id.get(case_id, [])
        if len(golden_rows) > 1 or len(actual_rows) > 1:
            duplicate.append(case_id)
        if len(actual_rows) == 0:
            missing.append(case_id)
            continue
        if len(golden_rows) == 1 and len(actual_rows) == 1:
            pairs.append((golden_rows[0], actual_rows[0]))

    for case_id, actual_rows in rows_by_id.items():
        if case_id in golden_by_id:
            continue
        extra.append(case_id)
        if len(actual_rows) > 1:
            duplicate.append(case_id)

    return sorted(missing), sorted(duplicate), sorted(extra), pairs


def _group(items, kind):
    grouped = {}
    for item in items:
        case_id = _case_id(item, kind)
        if case_id not in grouped:
            grouped[case_id] = []
        grouped[case_id].append(item)
    return grouped


def _checked_fixture(item):
    case_id = _case_id(item, "fixture")
    return {
        "case_id": case_id,
        "split": _split(item, case_id),
        "expected_alert": _expected_alert(item, case_id),
        "expected_reason": _expected_reason(item, case_id),
        "trap": _trap(item, case_id),
    }


def _empty_counts():
    return {
        "correct_alerts": 0,
        "false_alerts": 0,
        "missed_alerts": 0,
        "correct_no_alerts": 0,
        "wrong_reason": 0,
        "emails_found": 0,
        "total_events": 0,
        "false_alerts_by_trap": {},
        "false_alert_case_ids": [],
        "missed_alert_case_ids": [],
    }


def _copy_counts(bucket):
    return {
        "correct_alerts": bucket["correct_alerts"],
        "false_alerts": bucket["false_alerts"],
        "missed_alerts": bucket["missed_alerts"],
        "correct_no_alerts": bucket["correct_no_alerts"],
        "wrong_reason": bucket["wrong_reason"],
        "emails_found": bucket["emails_found"],
        "total_events": bucket["total_events"],
        "false_alerts_by_trap": dict(bucket["false_alerts_by_trap"]),
        "false_alert_case_ids": list(bucket["false_alert_case_ids"]),
        "missed_alert_case_ids": list(bucket["missed_alert_case_ids"]),
    }


def _sort_bucket(bucket):
    bucket["false_alert_case_ids"] = sorted(bucket["false_alert_case_ids"])
    bucket["missed_alert_case_ids"] = sorted(bucket["missed_alert_case_ids"])
    traps = bucket["false_alerts_by_trap"]
    bucket["false_alerts_by_trap"] = {
        name: traps[name] for name in sorted(traps)
    }


def _reasons_match(expected, actual):
    if not isinstance(actual, str):
        return False
    label = actual.strip()
    # REASONS is the spec 5.B list. An unknown label is not a match.
    if label not in REASONS:
        return False
    return label == expected


def _case_id(item, kind):
    if not isinstance(item, dict):
        raise ValueError(f"a {kind} must be a dict")
    if "case_id" not in item or item["case_id"] is None:
        raise ValueError(f"a {kind} has no case_id")
    case_id = item["case_id"]
    if not isinstance(case_id, str) or case_id.strip() == "":
        raise ValueError(f"a {kind} has an empty case_id, got {case_id!r}")
    return case_id


def _split(item, case_id):
    split = item.get("split")
    if split not in SPLITS:
        raise ValueError(
            f"case_id {case_id!r} split must be development or holdout, "
            f"got {split!r}"
        )
    return split


def _expected_alert(item, case_id):
    if "expected_alert" not in item or item["expected_alert"] is None:
        raise ValueError(f"case_id {case_id!r} expected_alert is missing")
    alert = item["expected_alert"]
    # bool is a subclass of int. 1 and 0 must not pass as labels.
    if not isinstance(alert, bool):
        raise ValueError(
            f"case_id {case_id!r} expected_alert must be a bool, got {alert!r}"
        )
    return alert


def _expected_reason(item, case_id):
    reason = item.get("expected_reason")
    if reason not in REASONS:
        raise ValueError(
            f"case_id {case_id!r} expected_reason must be one of the "
            f"reason strings in spec 5.B, got {reason!r}"
        )
    return reason


def _trap(item, case_id):
    trap = item.get("trap")
    if not isinstance(trap, str) or trap.strip() == "":
        raise ValueError(f"case_id {case_id!r} trap is missing")
    return trap.strip()


def _got_alert(row, case_id):
    if "alert" not in row:
        raise ValueError(f"case_id {case_id!r} result has no alert")
    alert = row["alert"]
    # Same rule as expected_alert. The string "true" or the number 1
    # would quietly become an alert if we only checked truthiness.
    if not isinstance(alert, bool):
        raise ValueError(
            f"case_id {case_id!r} alert must be a bool, got {alert!r}"
        )
    return alert
