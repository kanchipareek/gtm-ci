"""Load and check golden fixture rows.

Column names follow Deepline's golden-dataset columns. Reason strings are
the ones plays/rules.ts returns.
This module is the one Python copy of those reason strings. Later scoring
code should import REASONS from here, not type the list again.
"""

import csv
import json
from pathlib import Path

# The first failing check in plays/rules.ts, then icp_fit when every check passes.
# One tuple so the validator and the scorer cannot drift apart.
REASONS = (
    "not_champion",
    "missing_domain",
    "same_company",
    "duplicate_person",
    "stale_event",
    "junior_title",
    "ambiguous_title",
    "company_not_found",
    "company_too_small",
    "company_too_big",
    "wrong_country",
    "icp_fit",
)

SPLITS = ("development", "holdout")

# Same list as plays/rules.ts. A free-mail host is not a company domain.
FREE_MAIL_DOMAINS = (
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "proton.me",
)

# RFC 2606 reserves these so they cannot be registered to a real company.
RESERVED_EXACT_DOMAINS = ("example.com", "example.org", "example.net")

# Every golden row has these input columns. Three of them may be null.
INPUT_FIELDS = (
    "input_person_id",
    "input_full_name",
    "input_was_champion",
    "input_old_company",
    "input_old_title",
    "input_new_company",
    "input_new_domain",
    "input_new_title",
    "input_start_date",
    "input_event_date",
    "input_country_hint",
    "input_company_employees",
    "input_company_country",
    "input_mock_email",
    "input_mock_email_status",
)

# No company snapshot, or no email found.
NULLABLE_INPUTS = (
    "input_company_employees",
    "input_company_country",
    "input_mock_email",
)

# The Play runner must never see the answer key or the review notes.
# If it could read expected_alert, it could copy the label and the gate would pass.
RUNNER_HIDDEN_FIELDS = (
    "split",
    "grading_notes",
    "notes",
    "trap",
)


def validate_fixture(row, seen_case_ids=None):
    """Raise ValueError if one golden row breaks the column contract.

    Pass the same set for every row in a file. That is how a repeated
    case_id is caught. A single row on its own has nothing to repeat.
    """
    if not isinstance(row, dict):
        raise ValueError("a fixture row must be a JSON object")

    case_id = _require_case_id(row, seen_case_ids)
    _require_split(row)
    _require_inputs(row)
    _require_expected(row)
    _require_synthetic_person(row, case_id)


def check_synthetic(rows):
    """Raise ValueError if an offline company domain could be a real one.

    Empty and free-mail domains are allowed. Those rows are the missing-domain
    cases. Anything else must be a reserved example domain: it ends with
    .example, or it is example.com, example.org, or example.net.
    """
    for row in rows:
        case_id = row.get("case_id", "")
        domain = row.get("input_new_domain")
        if _domain_is_allowed(domain):
            continue
        raise ValueError(
            f"input_new_domain {domain!r} is not a reserved example domain "
            f"(case_id {case_id!r}). Offline domains must end with .example, "
            "or be example.com, example.org, or example.net, "
            "unless the domain is empty or a free-mail domain."
        )


def row_for_runner(row):
    """Copy a row down to what a Play is allowed to see.

    Drops expected_*, grading_notes, notes, trap, and split. The validator
    reads those fields first. This copy is what the runner gets afterwards.
    """
    kept = {}
    for key, value in row.items():
        if key in RUNNER_HIDDEN_FIELDS or key.startswith("expected_"):
            continue
        kept[key] = value
    return kept


def load_fixtures(path, for_runner=False):
    """Load a golden JSONL file and fail on the first bad row.

    If a CSV with the same name sits beside the JSONL, its case_ids and
    expected answers must match. for_runner=True drops the answer key after
    the checks, so the caller cannot see expected_*, grading_notes, notes,
    trap, or split.
    """
    path = Path(path)
    rows = _read_jsonl(path)
    seen_case_ids = set()
    for line_number, row in rows:
        try:
            validate_fixture(row, seen_case_ids)
        except ValueError as exc:
            raise ValueError(f"{path} line {line_number}: {exc}") from exc

    loaded = [row for _, row in rows]
    check_synthetic(loaded)

    csv_path = path.with_suffix(".csv")
    if csv_path.is_file():
        check_csv_mirror(loaded, csv_path)

    if for_runner:
        return [row_for_runner(row) for row in loaded]
    return loaded


# fixtures/real_events.json is a different file from fixtures/events.jsonl.
# check_synthetic still rejects a real domain on the golden JSONL. This
# loader is the only path that allows one, and only for that file name.
REAL_EVENT_NAME = "real_events.json"

# The Play input. old_domain, the answer key, and the stand-in stay here.
REAL_PLAY_FIELDS = (
    "person_id",
    "full_name",
    "was_champion",
    "old_company",
    "old_title",
    "new_company",
    "new_domain",
    "new_title",
    "start_date",
    "event_date",
    "country_hint",
)


def is_real_events_file(path):
    """True when the path is the real-events fixture, not the golden JSONL.

    The name is the switch. A golden file keeps going through load_fixtures
    and check_synthetic, even if someone copies a real domain into it.
    """
    return Path(path).name == REAL_EVENT_NAME


def load_real_events(path, for_runner=False):
    """Load fixtures/real_events.json. Real company domains are allowed.

    There is no CSV mirror. for_runner=True returns the Play events only.
    expected_*, split, trap, old_domain, and the stand-in fields are left
    out of that copy. The scorer still sees them when for_runner is false.
    """
    path = Path(path)
    data = _read_real_events_file(path)
    if data.get("email_mode") != "mock":
        raise ValueError(f"{path} email_mode must be mock")
    events = data.get("events")
    if not isinstance(events, list) or len(events) == 0:
        raise ValueError(f"{path} events must be a non-empty list")

    seen_case_ids = set()
    loaded = []
    for index, row in enumerate(events, start=1):
        try:
            _validate_real_event(row, seen_case_ids)
        except ValueError as exc:
            raise ValueError(f"{path} event {index}: {exc}") from exc
        loaded.append(row)

    if for_runner:
        return [real_event_for_play(row) for row in loaded]
    return loaded


def real_event_for_play(row):
    """Copy one real event down to the Play input.

    The stand-in count is not copied. Live mode looks the company up.
    The answer key is not copied, so the Play cannot read the label.
    """
    event = {"case_id": row["case_id"]}
    for name in REAL_PLAY_FIELDS:
        event[name] = row[name]
    event["email"] = row["email"]
    event["email_status"] = row["email_status"]
    for key in event:
        if key.startswith("expected_") or key.startswith("stand_in") or key in (
            "old_domain",
            "split",
            "trap",
            "grading_notes",
            "notes",
        ):
            raise RuntimeError(f"play input includes {key}")
    return event


def real_event_offline_row(row):
    """Map one real event onto the offline runner's input_* row.

    A stand-in count is the company snapshot for this offline pass.
    A row with stand_in false sends a null company. The answer key is
    not on this row.
    """
    if row.get("stand_in") is True:
        employees = row["stand_in_employees"]
        country = row["stand_in_country"]
    else:
        employees = None
        country = None
    offline = {
        "case_id": row["case_id"],
        "input_person_id": row["person_id"],
        "input_full_name": row["full_name"],
        "input_was_champion": row["was_champion"],
        "input_old_company": row["old_company"],
        "input_old_title": row["old_title"],
        "input_new_company": row["new_company"],
        "input_new_domain": row["new_domain"],
        "input_new_title": row["new_title"],
        "input_start_date": row["start_date"],
        "input_event_date": row["event_date"],
        "input_country_hint": row["country_hint"],
        "input_company_employees": employees,
        "input_company_country": country,
        "input_mock_email": row["email"],
        "input_mock_email_status": row["email_status"],
    }
    for key in offline:
        if key.startswith("expected_") or key.startswith("stand_in"):
            raise RuntimeError(f"offline row includes {key}")
    return offline


def check_csv_mirror(rows, csv_path):
    """Raise ValueError if the CSV does not carry the same labels as the JSONL.

    Compared fields are case_id, expected_alert, and expected_reason.
    Joined by case_id, not by row order.
    """
    csv_path = Path(csv_path)
    csv_by_id = _read_csv_by_case_id(csv_path)
    json_by_id = {}
    for row in rows:
        case_id = row.get("case_id")
        if case_id in json_by_id:
            raise ValueError(f"case_id {case_id!r} is duplicated")
        json_by_id[case_id] = row

    json_ids = set(json_by_id)
    csv_ids = set(csv_by_id)
    missing = sorted(json_ids - csv_ids)
    extra = sorted(csv_ids - json_ids)
    if missing or extra:
        raise ValueError(
            f"{csv_path} case_ids do not match the JSONL: "
            f"missing {missing or 'none'}, extra {extra or 'none'}"
        )

    for case_id in sorted(json_ids):
        json_row = json_by_id[case_id]
        csv_row = csv_by_id[case_id]
        csv_alert = _parse_alert(csv_row.get("expected_alert"), csv_path, case_id)
        json_alert = json_row.get("expected_alert")
        if json_alert != csv_alert:
            raise ValueError(
                f"{csv_path} case_id {case_id!r} expected_alert is "
                f"{json_alert!r} in JSONL and {csv_alert!r} in CSV"
            )
        json_reason = json_row.get("expected_reason")
        csv_reason = csv_row.get("expected_reason")
        if json_reason != csv_reason:
            raise ValueError(
                f"{csv_path} case_id {case_id!r} expected_reason is "
                f"{json_reason!r} in JSONL and {csv_reason!r} in CSV"
            )


def _read_real_events_file(path):
    if not path.is_file():
        raise ValueError(f"{path} does not exist")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not JSON ({exc.msg})") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a JSON object")
    return data


def _validate_real_event(row, seen_case_ids):
    if not isinstance(row, dict):
        raise ValueError("an event must be a JSON object")
    case_id = _require_case_id(row, seen_case_ids)
    for field in REAL_PLAY_FIELDS:
        if field not in row:
            raise ValueError(f"{field} is missing")
        if row[field] is None:
            raise ValueError(f"{field} is null")
    if row["was_champion"] is not True:
        raise ValueError("was_champion must be true")
    if "old_domain" not in row or not isinstance(row["old_domain"], str) or row["old_domain"].strip() == "":
        raise ValueError("old_domain is missing")
    if not isinstance(row["new_domain"], str) or row["new_domain"].strip() == "":
        raise ValueError("new_domain is missing")

    name = row["full_name"]
    if not isinstance(name, str) or not name.endswith("Testcase"):
        raise ValueError(
            f"full_name must end with 'Testcase', got {name!r} "
            f"(case_id {case_id!r})"
        )
    email = row.get("email")
    local = email.split("@", 1)[0] if isinstance(email, str) else ""
    if not local.startswith("synthetic."):
        raise ValueError(
            "email local part must start with 'synthetic.', "
            f"got {email!r} (case_id {case_id!r})"
        )
    if "email_status" not in row or not isinstance(row["email_status"], str) or row["email_status"].strip() == "":
        raise ValueError("email_status is missing")

    _require_expected(row)
    _require_split(row)
    trap = row.get("trap")
    if not isinstance(trap, str) or trap.strip() == "":
        raise ValueError("trap is missing")

    stand_in = row.get("stand_in")
    if not isinstance(stand_in, bool):
        raise ValueError(f"stand_in must be a bool, got {stand_in!r}")
    if stand_in:
        employees = row.get("stand_in_employees")
        country = row.get("stand_in_country")
        if isinstance(employees, bool) or not isinstance(employees, int):
            raise ValueError(
                f"stand_in_employees must be an int, got {employees!r}"
            )
        if not isinstance(country, str) or country.strip() == "":
            raise ValueError("stand_in_country is missing")
    else:
        if "stand_in_employees" in row or "stand_in_country" in row:
            raise ValueError("a stand-in count is set without stand_in true")


def _require_case_id(row, seen_case_ids):
    if "case_id" not in row or row["case_id"] is None:
        raise ValueError("case_id is missing")
    case_id = row["case_id"]
    if not isinstance(case_id, str) or case_id.strip() == "":
        raise ValueError(f"case_id is empty, got {case_id!r}")
    if seen_case_ids is not None:
        if case_id in seen_case_ids:
            raise ValueError(f"case_id {case_id!r} is duplicated")
        seen_case_ids.add(case_id)
    return case_id


def _require_split(row):
    if "split" not in row or row["split"] is None:
        raise ValueError("split is missing")
    split = row["split"]
    if split not in SPLITS:
        raise ValueError(
            f"split must be development or holdout, got {split!r}"
        )


def _require_inputs(row):
    for field in INPUT_FIELDS:
        if field not in row:
            raise ValueError(f"{field} is missing")
        if row[field] is None and field not in NULLABLE_INPUTS:
            raise ValueError(f"{field} is null")


def _require_expected(row):
    if "expected_alert" not in row or row["expected_alert"] is None:
        raise ValueError("expected_alert is missing")
    alert = row["expected_alert"]
    # bool is a subclass of int. 1 and 0 must not pass as labels.
    if not isinstance(alert, bool):
        raise ValueError(f"expected_alert must be a bool, got {alert!r}")

    if "expected_reason" not in row or row["expected_reason"] is None:
        raise ValueError("expected_reason is missing")
    reason = row["expected_reason"]
    if reason not in REASONS:
        raise ValueError(
            "expected_reason must be one of the reason strings in rules.ts, "
            f"got {reason!r}"
        )


def _require_synthetic_person(row, case_id):
    name = row["input_full_name"]
    if not isinstance(name, str) or not name.endswith("Testcase"):
        raise ValueError(
            f"input_full_name must end with 'Testcase', got {name!r} "
            f"(case_id {case_id!r})"
        )

    email = row["input_mock_email"]
    if email is None:
        return
    if isinstance(email, str) and email.strip() == "":
        return
    local = email.split("@", 1)[0] if isinstance(email, str) else ""
    if not local.startswith("synthetic."):
        raise ValueError(
            "input_mock_email local part must start with 'synthetic.', "
            f"got {email!r} (case_id {case_id!r})"
        )


def _domain_is_allowed(domain):
    if domain is None:
        return True
    if not isinstance(domain, str):
        return False
    host = domain.strip().lower().rstrip(".")
    if host == "":
        return True
    if _is_free_mail(host):
        return True
    if host in RESERVED_EXACT_DOMAINS:
        return True
    # *.example is the reserved TLD. example.com is not covered by that suffix.
    return host.endswith(".example")


def _is_free_mail(host):
    # A subdomain of a free-mail host is still not a company, same as rules.ts.
    for free in FREE_MAIL_DOMAINS:
        if host == free or host.endswith("." + free):
            return True
    return False


def _read_jsonl(path):
    if not path.is_file():
        raise ValueError(f"{path} does not exist")
    rows = []
    text = path.read_text(encoding="utf-8")
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.strip() == "":
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{path} line {line_number}: invalid JSON ({exc.msg})"
            ) from exc
        if not isinstance(row, dict):
            raise ValueError(
                f"{path} line {line_number}: each line must be a JSON object"
            )
        rows.append((line_number, row))
    return rows


def _read_csv_by_case_id(csv_path):
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        for column in ("case_id", "expected_alert", "expected_reason"):
            if column not in fieldnames:
                raise ValueError(f"{csv_path} is missing column {column}")
        by_id = {}
        for row in reader:
            case_id = (row.get("case_id") or "").strip()
            if case_id == "":
                raise ValueError(f"{csv_path} has a row with an empty case_id")
            if case_id in by_id:
                raise ValueError(f"{csv_path} duplicates case_id {case_id!r}")
            by_id[case_id] = row
    return by_id


def _parse_alert(value, csv_path, case_id):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text == "true":
            return True
        if text == "false":
            return False
    raise ValueError(
        f"{csv_path} case_id {case_id!r} expected_alert must be true or false, "
        f"got {value!r}"
    )
