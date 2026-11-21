"""Compare a live company lookup with the snapshot saved in the fixture.

Drift is how many employee counts and country codes are not the saved
values. A company that did not come back counts as two, because neither
field is there to match. A lookup that comes back no_result writes an
empty company. That empty answer is not a changed field.

The count is for the comment and the weekly issue. It is not a test
failure: headcount and country change in the world, and the offline
gate is what judges the rules.

The credit number in the comment is credits_spent on the live result.
That value was copied from billing usage. "unknown" stays "unknown".
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from scorer.fixtures import FREE_MAIL_DOMAINS, RESERVED_EXACT_DOMAINS


# The same first line compare.py writes. The comment script finds the
# pull request comment by it, so the live section has to keep it.
MARKER = "<!-- gtm-ci -->"

# These are the two company fields the rules read.
DRIFT_FIELDS = ("employees", "country")

# The weekly job keeps one issue. The title is how a later run finds it,
# so a second issue is not opened for the same drift.
ISSUE_TITLE = "company data drift"


def count_drift(rows, companies):
    """Return how many snapshot fields differ from the live rows.

    Joined by case_id, not by row order. employees and country are the
    only fields. A missing live row differs on both. An empty no_result
    lookup differs on neither.
    """
    return len(drift_changes(rows, companies))


def drift_changes(rows, companies):
    """Return one record per snapshot field that differs.

    A missing live row differs on both fields. A row that came back with
    no employees and no country is a no_result lookup, so it is left out.
    """
    live_by_id = _rows_by_id(rows)
    changes = []
    seen = set()
    for company in companies:
        case_id, snapshot = _snapshot(company, seen)
        row = live_by_id.get(case_id)
        if _empty_answer(row):
            continue
        live = _company_fields(row)
        if not _same_employees(live["employees"], snapshot.get("employees")):
            changes.append(
                _change_record(
                    company,
                    case_id,
                    "employees",
                    snapshot.get("employees"),
                    live["employees"],
                )
            )
        if not _same_country(live["country"], snapshot.get("country")):
            changes.append(
                _change_record(
                    company,
                    case_id,
                    "country",
                    snapshot.get("country"),
                    live["country"],
                )
            )
    return changes


def credits_over_cap(credits, cap):
    """True only when a real credit number is greater than the cap.

    "unknown" is not over the cap. A missing bill is not a zero, and it
    is not proof the run broke the limit. A value equal to the cap is
    still inside it.
    """
    if isinstance(cap, bool) or not isinstance(cap, (int, float)):
        raise ValueError(f"cap must be a number, got {cap!r}")
    if credits == "unknown" or credits is None:
        return False
    if isinstance(credits, bool) or not isinstance(credits, (int, float)):
        return False
    return credits > cap


def live_section(run_id, credits, drift_count):
    """The markdown block the live job appends to the pull request comment."""
    count = _require_count(drift_count)
    lines = [
        "## Live run",
        "",
        f"- run id: {_run_text(run_id)}",
        f"- credits: {_credit_text(credits)}",
        f"- drift: {count}",
    ]
    return "\n".join(lines) + "\n"


def append_live_section(comment, section):
    """Return the gate comment with the Live run section after it.

    The marker stays the first line. The comment script replaces the
    whole body, so this has to be the full comment, not a second post.
    """
    if not isinstance(comment, str) or not comment.startswith(MARKER):
        raise ValueError("the comment file does not start with the gtm-ci marker")
    body = comment
    if not body.endswith("\n"):
        body += "\n"
    if not body.endswith("\n\n"):
        body += "\n"
    return body + section


def issue_body(changes):
    """The markdown body for the one drift issue.

    One row per changed field: the company domain, the field, the saved
    value, the live value, and the snapshot source from the fixture.
    """
    lines = [
        "Fields that differ from the saved snapshot.",
        "",
        "| company | field | old value | new value | snapshot source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for change in changes:
        lines.append(
            "| {company} | {field} | {old} | {new} | {source} |".format(
                company=_cell(change.get("company")),
                field=_cell(change.get("field")),
                old=_cell(change.get("old")),
                new=_cell(change.get("new")),
                source=_cell(change.get("source")),
            )
        )
    return "\n".join(lines) + "\n"


def plan_drift_issue(changes, issues):
    """Decide how to keep a single issue titled company data drift.

    Changes open that issue or update the oldest match. No changes close
    every open match. A pull request is ignored, even with the same title.
    """
    titled = _drift_issues(issues)
    if changes:
        body = issue_body(changes)
        if not titled:
            return [{"action": "create", "body": body}]
        steps = [{"action": "update", "number": titled[0]["number"], "body": body}]
        for extra in titled[1:]:
            if extra.get("state") == "open":
                steps.append({"action": "close", "number": extra["number"]})
        return steps
    return [
        {"action": "close", "number": issue["number"]}
        for issue in titled
        if issue.get("state") == "open"
    ]


def sync_drift_issue(changes):
    """Open, update, or close the drift issue.

    GITHUB_TOKEN stays in the environment. It is not printed. Drift itself
    does not raise: a changed field is an update, not a failure.
    """
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo.count("/") != 1:
        raise ValueError("GITHUB_REPOSITORY is required")
    if "GITHUB_TOKEN" not in os.environ and "GH_TOKEN" not in os.environ:
        raise ValueError("GITHUB_TOKEN is required")
    steps = plan_drift_issue(changes, _list_issues(repo))
    if not steps:
        print("no drift, and no open issue to close")
        return
    for step in steps:
        action = step["action"]
        if action == "create":
            number = _create_issue(repo, step["body"])
            print(f"opened issue {number}")
        elif action == "update":
            _update_issue(repo, step["number"], step["body"])
            print(f"updated issue {step['number']}")
        elif action == "close":
            _close_issue(repo, step["number"])
            print(f"closed issue {step['number']}")
        else:
            raise ValueError(f"unknown issue action {action!r}")


def is_live_companies_file(path):
    """True when this path is the live company JSON, not a golden JSONL file.

    The golden loader rejects a real company domain. This file is the
    one place those domains are allowed, and only for a live run.
    """
    path = Path(path)
    if path.suffix.lower() != ".json":
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and "companies" in data and "email_mode" in data


def load_live_companies(path):
    """Read fixtures/live_companies.json and reject a row that is not safe to send.

    email_mode must be mock. Each person is synthetic. The domain is a
    real business domain, and the event's new_domain is that same host.
    was_champion must be true so the Play reaches the company lookup.
    A free check that fails earlier leaves company null, and drift would
    then be a skipped call rather than a change in the world.
    """
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ValueError(f"could not read live companies at {path}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"live companies file is not JSON: {path}") from exc
    if not isinstance(data, dict):
        raise ValueError("live companies file must be a JSON object")
    if data.get("email_mode") != "mock":
        raise ValueError("email_mode must be mock")
    raw = data.get("companies")
    if not isinstance(raw, list) or not raw:
        raise ValueError("companies must be a non-empty list")

    companies = []
    seen_ids = set()
    seen_domains = set()
    for index, item in enumerate(raw, start=1):
        companies.append(_one_company(item, index, seen_ids, seen_domains))
    return companies


def play_events_from_companies(companies):
    """Build the Play events. The snapshot is not included.

    The live Play looks the company up. Sending the saved employees and
    country would let the run echo the snapshot and hide drift.
    """
    events = []
    for company in companies:
        event = dict(company["event"])
        event["case_id"] = company["case_id"]
        for key in event:
            if key == "snapshot" or key.startswith("expected_") or key in (
                "grading_notes",
                "notes",
                "trap",
                "split",
            ):
                raise ValueError(f"live input includes {key}, which the Play must not see")
        events.append(event)
    return events


def write_live_result(label, document, results_dir):
    """Write results/<label>.json for the live job. Return the path."""
    _check_label(label)
    folder = Path(results_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{label}.json"
    path.write_text(
        json.dumps(document, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def main(argv=None):
    """Append the Live run section, sync the drift issue, or check the cap.

    Drift never changes the exit code. A missing comment file is reported
    and is not a failure. This command fails when the result cannot be
    read, the issue call fails, or --check-cap sees a bill over the cap.
    A failed Deepline run never gets here: the scorer exits first.
    """
    args = parse_args(argv)
    try:
        document = _load_result(args.result)
        if args.comment:
            _append_comment(args.comment, document)
        if args.sync_issue:
            if not args.fixtures:
                print("--sync-issue needs --fixtures")
                return 1
            rows = document.get("rows")
            if not isinstance(rows, list):
                print("live result has no rows to compare")
                return 1
            companies = load_live_companies(args.fixtures)
            # Changed fields update the issue and still exit 0 below.
            sync_drift_issue(drift_changes(rows, companies))
        if args.check_cap:
            if args.cap is None:
                print("--check-cap needs --cap")
                return 1
            credits = document.get("credits_spent")
            if credits_over_cap(credits, args.cap):
                print(f"credits {_credit_text(credits)} are over the cap {_credit_text(args.cap)}")
                return 1
            print(f"credits {_credit_text(credits)} are within the cap {_credit_text(args.cap)}")
    except (ValueError, RuntimeError) as exc:
        print(str(exc))
        return 1
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Append the Live run section, sync the drift issue, or check the credit cap."
    )
    parser.add_argument("result", help="Live result JSON from python -m scorer.")
    parser.add_argument(
        "--comment",
        default=None,
        help="Gate comment file. The Live run section is appended to it.",
    )
    parser.add_argument(
        "--fixtures",
        default=None,
        help="fixtures/live_companies.json. The snapshot the issue is compared with.",
    )
    parser.add_argument(
        "--sync-issue",
        action="store_true",
        help="Open, update, or close the one drift issue. Drift does not fail the command.",
    )
    parser.add_argument("--cap", type=float, default=None, help="live_max_credits.")
    parser.add_argument(
        "--check-cap",
        action="store_true",
        help="Exit 1 when credits_spent is greater than --cap.",
    )
    return parser.parse_args(argv)


def _append_comment(comment_path, document):
    path = Path(comment_path)
    if not path.is_file():
        print(f"no gate comment at {path}, so the Live run section was not added")
        return
    section = live_section(
        document.get("run_id"),
        document.get("credits_spent"),
        document.get("drift_count"),
    )
    updated = append_live_section(path.read_text(encoding="utf-8"), section)
    path.write_text(updated, encoding="utf-8", newline="\n")
    print(section, end="")


def _load_result(path):
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ValueError(f"could not read live result at {file_path}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"live result is not JSON: {file_path}") from exc
    if not isinstance(data, dict):
        raise ValueError("live result must be a JSON object")
    if "credits_spent" not in data or "drift_count" not in data:
        raise ValueError("live result is missing credits_spent or drift_count")
    _require_count(data.get("drift_count"))
    return data


def _rows_by_id(rows):
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    by_id = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("a live row must be an object")
        case_id = row.get("case_id")
        if not isinstance(case_id, str) or case_id.strip() == "":
            raise ValueError("a live row is missing case_id")
        if case_id in by_id:
            raise ValueError(f"case_id {case_id!r} is duplicated in the live rows")
        by_id[case_id] = row
    return by_id


def _snapshot(company, seen):
    if not isinstance(company, dict):
        raise ValueError("a snapshot must be an object")
    case_id = company.get("case_id")
    if not isinstance(case_id, str) or case_id.strip() == "":
        raise ValueError("a snapshot is missing case_id")
    if case_id in seen:
        raise ValueError(f"case_id {case_id!r} is duplicated")
    seen.add(case_id)
    snapshot = company.get("snapshot")
    if not isinstance(snapshot, dict):
        raise ValueError(f"case_id {case_id!r} has no snapshot")
    return case_id, snapshot


def _company_fields(row):
    if row is None:
        return {"employees": None, "country": None}
    company = row.get("company")
    if not isinstance(company, dict):
        return {"employees": None, "country": None}
    return {
        "employees": company.get("employees"),
        "country": company.get("country"),
    }


def _empty_answer(row):
    """True when this row is a lookup that came back with nothing.

    The Play writes null employees and a null country when LeadMagic
    returns no_result (Figma). That empty answer is not a new headcount.
    A missing row is not this case: there is no company object to read,
    and both fields still count.
    """
    if not isinstance(row, dict):
        return False
    company = row.get("company")
    if not isinstance(company, dict):
        return False
    return _blank(company.get("employees")) and _blank(company.get("country"))


def _blank(value):
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _change_record(company, case_id, field, old, new):
    domain = company.get("domain") if isinstance(company, dict) else None
    if not isinstance(domain, str) or domain.strip() == "":
        domain = case_id
    source = company.get("snapshot_source") if isinstance(company, dict) else None
    if not isinstance(source, str):
        source = ""
    return {
        "case_id": case_id,
        "company": domain,
        "field": field,
        "old": old,
        "new": new,
        "source": source,
    }


def _cell(value):
    """One markdown table cell. A pipe or a newline would break the row."""
    if value is None:
        text = "null"
    elif isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, float) and value.is_integer():
        text = str(int(value))
    else:
        text = str(value)
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _drift_issues(issues):
    if not isinstance(issues, list):
        raise ValueError("issue list was not a JSON array")
    found = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        # The issues API also returns pull requests. Those are not this issue.
        if "pull_request" in issue:
            continue
        if issue.get("title") != ISSUE_TITLE:
            continue
        number = issue.get("number")
        if isinstance(number, bool) or not isinstance(number, int):
            continue
        found.append(issue)
    found.sort(key=lambda item: item["number"])
    return found


def _list_issues(repo):
    output = _run_gh([
        "--paginate",
        "--slurp",
        "--method",
        "GET",
        f"repos/{repo}/issues?state=all&per_page=100",
    ])
    try:
        payload = json.loads(output) if output.strip() else []
    except json.JSONDecodeError as exc:
        raise ValueError("gh api did not return a JSON issue list") from exc
    return _objects_from_pages(payload, "issue")


def _objects_from_pages(payload, label):
    if not isinstance(payload, list):
        raise ValueError(f"{label} list was not a JSON array")
    if not payload:
        return []
    if isinstance(payload[0], dict):
        return payload
    items = []
    for page in payload:
        if not isinstance(page, list):
            raise ValueError(f"a {label} page was not a JSON array")
        items.extend(page)
    return items


def _create_issue(repo, body):
    payload = _json_file({"title": ISSUE_TITLE, "body": body})
    try:
        output = _run_gh([
            "--method",
            "POST",
            "--input",
            str(payload),
            f"repos/{repo}/issues",
        ])
    finally:
        payload.unlink(missing_ok=True)
    try:
        data = json.loads(output) if output.strip() else {}
    except json.JSONDecodeError as exc:
        raise ValueError("gh api did not return the new issue") from exc
    if not isinstance(data, dict):
        raise ValueError("gh api did not return the new issue")
    number = data.get("number")
    if isinstance(number, bool) or not isinstance(number, int):
        raise ValueError("the new issue has no number")
    return number


def _update_issue(repo, number, body):
    payload = _json_file({"title": ISSUE_TITLE, "body": body, "state": "open"})
    try:
        _run_gh([
            "--method",
            "PATCH",
            "--input",
            str(payload),
            f"repos/{repo}/issues/{number}",
        ])
    finally:
        payload.unlink(missing_ok=True)


def _close_issue(repo, number):
    payload = _json_file({"state": "closed"})
    try:
        _run_gh([
            "--method",
            "PATCH",
            "--input",
            str(payload),
            f"repos/{repo}/issues/{number}",
        ])
    finally:
        payload.unlink(missing_ok=True)


def _json_file(document):
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        delete=False,
    )
    with handle:
        json.dump(document, handle)
    return Path(handle.name)


def _run_gh(args):
    """Run gh api. A non-zero exit becomes an error. The token is not printed."""
    completed = subprocess.run(
        ["gh", "api", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or "").strip() or (completed.stdout or "").strip() or "gh api failed"
        raise RuntimeError(detail)
    return completed.stdout


def _same_employees(live, saved):
    # A bool is an int in Python. True must not match a headcount of 1.
    if isinstance(live, bool) or isinstance(saved, bool):
        return False
    if live is None and saved is None:
        return True
    if isinstance(live, (int, float)) and isinstance(saved, (int, float)):
        return live == saved
    return False


def _same_country(live, saved):
    # The rules compare country codes in upper case. "us" and "US" are
    # the same country, so they are not drift.
    if live is None and saved is None:
        return True
    if not isinstance(live, str) or not isinstance(saved, str):
        return False
    return live.strip().upper() == saved.strip().upper()


def _one_company(item, index, seen_ids, seen_domains):
    if not isinstance(item, dict):
        raise ValueError(f"company {index} must be an object")
    case_id = item.get("case_id")
    if not isinstance(case_id, str) or case_id.strip() == "":
        raise ValueError(f"company {index} is missing case_id")
    if case_id in seen_ids:
        raise ValueError(f"case_id {case_id!r} is duplicated")
    seen_ids.add(case_id)

    domain = _business_domain(item.get("domain"), case_id)
    if domain in seen_domains:
        raise ValueError(f"domain {domain!r} is duplicated")
    seen_domains.add(domain)

    snapshot = item.get("snapshot")
    if not isinstance(snapshot, dict):
        raise ValueError(f"case_id {case_id!r} has no snapshot")
    employees = snapshot.get("employees")
    if isinstance(employees, bool) or not isinstance(employees, (int, float)):
        raise ValueError(f"case_id {case_id!r} snapshot employees must be a number")
    country = snapshot.get("country")
    if not isinstance(country, str) or country.strip() == "":
        raise ValueError(f"case_id {case_id!r} snapshot country is empty")
    source = item.get("snapshot_source")
    if not isinstance(source, str) or source.strip() == "":
        raise ValueError(f"case_id {case_id!r} snapshot_source is empty")

    event = item.get("event")
    if not isinstance(event, dict):
        raise ValueError(f"case_id {case_id!r} has no event")
    _require_event(event, case_id, domain)

    return {
        "case_id": case_id,
        "domain": domain,
        "snapshot": {"employees": employees, "country": country.strip().upper()},
        "snapshot_source": source.strip(),
        "event": event,
    }


def _require_event(event, case_id, domain):
    if event.get("was_champion") is not True:
        raise ValueError(
            f"case_id {case_id!r} was_champion must be true so the company lookup runs"
        )
    name = event.get("full_name")
    if not isinstance(name, str) or not name.endswith("Testcase"):
        raise ValueError(
            f"full_name must end with 'Testcase', got {name!r} (case_id {case_id!r})"
        )
    email = event.get("email")
    local = email.split("@", 1)[0] if isinstance(email, str) and "@" in email else ""
    if not local.startswith("synthetic."):
        raise ValueError(
            "email local part must start with 'synthetic.', "
            f"got {email!r} (case_id {case_id!r})"
        )
    new_domain = event.get("new_domain")
    if not isinstance(new_domain, str) or new_domain.strip().lower() != domain:
        raise ValueError(f"case_id {case_id!r} new_domain does not match {domain}")
    for key in (
        "person_id",
        "old_company",
        "old_title",
        "new_company",
        "new_title",
        "start_date",
        "event_date",
        "country_hint",
        "email_status",
    ):
        value = event.get(key)
        if not isinstance(value, str) or value.strip() == "":
            raise ValueError(f"case_id {case_id!r} event {key} is empty")


def _business_domain(domain, case_id):
    if not isinstance(domain, str):
        raise ValueError(f"case_id {case_id!r} domain is missing")
    host = domain.strip().lower().rstrip(".")
    if host == "" or "." not in host:
        raise ValueError(f"case_id {case_id!r} domain is not a host, got {domain!r}")
    if host in RESERVED_EXACT_DOMAINS or host.endswith(".example"):
        raise ValueError(
            f"case_id {case_id!r} domain {host!r} is a reserved example domain. "
            "The live file is the real-company list."
        )
    for free in FREE_MAIL_DOMAINS:
        if host == free or host.endswith("." + free):
            raise ValueError(f"case_id {case_id!r} domain {host!r} is free mail")
    return host


def _require_count(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"drift count must be an integer, got {value!r}")
    if isinstance(value, float) and not value.is_integer():
        raise ValueError(f"drift count must be an integer, got {value!r}")
    count = int(value)
    if count < 0:
        raise ValueError("drift count must be zero or more")
    return count


def _run_text(run_id):
    if isinstance(run_id, str) and run_id.strip() != "":
        return run_id.strip()
    return "unknown"


def _credit_text(credits):
    if credits == "unknown" or credits is None:
        return "unknown"
    if isinstance(credits, bool) or not isinstance(credits, (int, float)):
        return "unknown"
    if isinstance(credits, float) and credits.is_integer():
        return str(int(credits))
    if isinstance(credits, float):
        return format(credits, "g")
    return str(credits)


def _check_label(label):
    if not isinstance(label, str) or label.strip() == "":
        raise ValueError("label is empty")
    if label in (".", "..") or "/" in label or "\\" in label:
        raise ValueError("label must be a file name, not a path")


if __name__ == "__main__":
    sys.exit(main())
