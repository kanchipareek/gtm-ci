import { readFileSync } from "node:fs";

import { decide, writeBrief } from "../plays/rules.ts";
import type { CompanySnapshot, EmailSnapshot, JobChangeEvent } from "../plays/rules.ts";

// This runner reads case_id and the input_* fields only.
// It must never read expected_*, grading_notes, notes, trap, or split.
// Those columns are the answer key and the review notes. Reading them would
// let this file copy the label instead of deciding. The scorer joins on case_id later.

type InputRow = {
  case_id: string;
  input_person_id: string;
  input_full_name: string;
  input_was_champion: boolean;
  input_old_company: string;
  input_old_title: string;
  input_new_company: string;
  input_new_domain: string;
  input_new_title: string;
  input_start_date: string;
  input_event_date: string;
  input_country_hint: string;
  input_company_employees: number | null;
  input_company_country: string | null;
  input_mock_email: string | null;
  input_mock_email_status: string | null;
};

function eventFromRow(row: InputRow): JobChangeEvent {
  return {
    case_id: row.case_id,
    person_id: row.input_person_id,
    full_name: row.input_full_name,
    was_champion: row.input_was_champion,
    old_company: row.input_old_company,
    old_title: row.input_old_title,
    new_company: row.input_new_company,
    new_domain: row.input_new_domain,
    new_title: row.input_new_title,
    start_date: row.input_start_date,
    event_date: row.input_event_date,
    country_hint: row.input_country_hint,
  };
}

function companyFromRow(row: InputRow): CompanySnapshot {
  return {
    employees: row.input_company_employees ?? null,
    country: row.input_company_country ?? null,
  };
}

function emailFromRow(row: InputRow): EmailSnapshot {
  return {
    email: row.input_mock_email ?? null,
    email_status: row.input_mock_email_status ?? null,
  };
}

function main(): void {
  const fixturePath = process.argv[2];
  if (!fixturePath) {
    process.stderr.write("usage: npx tsx scripts/offline_run.ts <events.jsonl>\n");
    process.exit(1);
  }

  const text = readFileSync(fixturePath, "utf8");
  const seenPersonIds = new Set<string>();
  const results = [];

  for (const line of text.split(/\r?\n/)) {
    if (line.trim() === "") {
      continue;
    }
    const row = JSON.parse(line) as InputRow;
    const event = eventFromRow(row);
    const company = companyFromRow(row);
    const email = emailFromRow(row);
    const decision = decide(event, company, email, seenPersonIds);

    results.push({
      case_id: event.case_id,
      alert: decision.alert,
      status: decision.status,
      reason: decision.reason,
      email: email.email,
      email_status: email.email_status,
      company: {
        employees: company.employees,
        country: company.country,
      },
      brief: decision.alert ? writeBrief(event, company) : "",
    });
  }

  process.stdout.write(`${JSON.stringify(results)}\n`);
}

main();
