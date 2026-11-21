import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import type { CompanySnapshot, EmailSnapshot, JobChangeEvent } from "../plays/rules.ts";

// This runner reads case_id and the input_* fields only.
// It must never read expected_*, grading_notes, notes, trap, or split.
// Those columns are the answer key and the review notes. Reading them would
// let this file copy the label instead of deciding. The scorer joins on case_id later.
//
// The second argument is the plays folder whose rules.ts to import.
// Day 3 scores base/plays and head/plays with this same script. Without the
// folder, both sides would load whichever rules.ts sits next to the script,
// and the diff would always be empty. When the argument is omitted, that
// nearby folder is used, so the older one-argument command still works.

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

type RulesModule = {
  decide: (
    event: JobChangeEvent,
    company: CompanySnapshot | null,
    email: EmailSnapshot | null,
    seenPersonIds: Set<string>,
  ) => { alert: boolean; status: string; reason: string };
  writeBrief: (event: JobChangeEvent, company: CompanySnapshot | null) => string;
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

function defaultPlaysDir(): string {
  const here = path.dirname(fileURLToPath(import.meta.url));
  return path.resolve(here, "../plays");
}

async function loadRules(playsDir: string): Promise<RulesModule> {
  const rulesFile = path.join(playsDir, "rules.ts");
  try {
    // A file URL so the folder can sit outside this repo (base/ vs head/).
    return (await import(pathToFileURL(rulesFile).href)) as RulesModule;
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    process.stderr.write(`could not import rules from ${rulesFile}: ${message}\n`);
    process.exit(1);
  }
}

async function main(): Promise<void> {
  const fixturePath = process.argv[2];
  if (!fixturePath) {
    process.stderr.write(
      "usage: npx tsx scripts/offline_run.ts <events.jsonl> [plays_dir]\n",
    );
    process.exit(1);
  }

  const playsDir = process.argv[3] ? path.resolve(process.argv[3]) : defaultPlaysDir();
  const rules = await loadRules(playsDir);

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
    // Same two calls as the Play. The first call has no company. Only a
    // company_not_found reason pays for the LeadMagic lookup, then decide
    // runs again with the snapshot. would_lookup is that paid call, so the
    // gate can see a change that makes the Play spend more.
    let decision = rules.decide(event, null, email, seenPersonIds);
    const wouldLookup = decision.reason === "company_not_found";
    if (wouldLookup) {
      decision = rules.decide(event, company, email, seenPersonIds);
    }

    results.push({
      case_id: event.case_id,
      alert: decision.alert,
      status: decision.status,
      reason: decision.reason,
      would_lookup: wouldLookup,
      email: email.email,
      email_status: email.email_status,
      company: {
        employees: company.employees,
        country: company.country,
      },
      brief: decision.alert ? rules.writeBrief(event, company) : "",
    });
  }

  process.stdout.write(`${JSON.stringify(results)}\n`);
}

main().catch((err: unknown) => {
  const message = err instanceof Error ? err.message : String(err);
  process.stderr.write(`${message}\n`);
  process.exit(1);
});
