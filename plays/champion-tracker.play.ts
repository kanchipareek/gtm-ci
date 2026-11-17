import deepline from 'deepline';

import { FREE_MAIL_DOMAINS, decide, writeBrief } from './rules.ts';
import type { CompanySnapshot, EmailSnapshot, JobChangeEvent } from './rules.ts';

// The answer key stays out of this file. The scorer joins on case_id later.
// expected_*, grading_notes, notes, trap, and split are never read here.

export const config = {
  name: 'champion-tracker',
  description: 'Score a champion job change against the ICP rules and write a fixed brief.',
  billing: { maxCreditsPerRun: 10 },
};

// Written out in this file on purpose. plays check builds the input schema from
// this annotation, and an imported type was dropped, so case_id and the rest
// never became allowed fields. The shape matches JobChangeEvent.
// Spec 5.A also copies the golden mock email on as email and email_status.
// mock_email is that same copy when the caller used that name instead.
type PlayEvent = {
  case_id: string;
  person_id: string;
  full_name: string;
  was_champion: boolean;
  old_company: string;
  old_title: string;
  new_company: string;
  new_domain: string;
  new_title: string;
  start_date: string;
  event_date: string;
  country_hint: string;
  email?: string | null;
  email_status?: string | null;
  mock_email?: string | null;
  mock_email_status?: string | null;
};

type PlayInput = {
  events: PlayEvent[];
  email_mode: 'mock' | 'live';
};

// docs/tools.md: companies is the list, and each row has these two fields.
type CompanyLookupResult = {
  status: string;
  fields?: {
    companies?: {
      values?: unknown[];
    };
  };
};

function companyHost(domain: string | null | undefined): string {
  if (domain == null) {
    return '';
  }
  return domain.trim().toLowerCase().replace(/^@/, '');
}

// A free-mail host is not a company. Subdomains count, matching the rules,
// so we do not pay for a domain decide() will reject as missing_domain.
function isFreeMail(domain: string): boolean {
  return FREE_MAIL_DOMAINS.some((free) => domain === free || domain.endsWith('.' + free));
}

function firstSet(primary: string | null | undefined, fallback: string | null | undefined): string | null {
  if (primary !== undefined) {
    return primary;
  }
  if (fallback !== undefined) {
    return fallback;
  }
  return null;
}

function mockEmail(event: PlayEvent): EmailSnapshot {
  return {
    email: firstSet(event.mock_email, event.email),
    email_status: firstSet(event.mock_email_status, event.email_status),
  };
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return null;
}

function companyList(result: CompanyLookupResult): unknown[] {
  const fromFields = result.fields?.companies?.values;
  if (Array.isArray(fromFields)) {
    return fromFields;
  }
  return [];
}

function snapshotFromCompany(row: unknown): CompanySnapshot | null {
  const record = asRecord(row);
  if (record === null) {
    return null;
  }

  // rows() wraps the provider object. The count and country sit on the object itself.
  const nested = asRecord(record.response);
  const source =
    nested !== null && ('linkedin_employee_count' in nested || 'hq_country_code' in nested)
      ? nested
      : record;

  const employees = source.linkedin_employee_count;
  const country = source.hq_country_code;
  return {
    employees: typeof employees === 'number' ? employees : null,
    country: typeof country === 'string' && country.trim() !== '' ? country.trim() : null,
  };
}

async function lookupCompany(domain: string): Promise<CompanySnapshot | null> {
  // Only company_domain. That is the one-company lookup, 0.15 credits per result.
  // A filter or a limit would ask for a page and charge for every row.
  // The id stays one static string. plays check rejects an id built from the
  // domain. The domain inside the input is what makes each lookup its own call.
  // 604800 seconds is 7 days, so an unchanged domain is not paid for twice.
  const result = (await deepline.tools.execute({
    id: 'company',
    tool: 'leadmagic_search_companies',
    input: { company_domain: domain },
    description: 'Look up one company by domain.',
    staleAfterSeconds: 604800,
  })) as CompanyLookupResult;

  if (result.status !== 'completed' && result.status !== 'no_result') {
    throw new Error('Company lookup did not complete: ' + result.status);
  }

  const companies = companyList(result);
  if (companies.length === 0) {
    return null;
  }
  // One domain is one row. More than one means this was a search page.
  if (companies.length !== 1) {
    throw new Error('Company lookup returned ' + String(companies.length) + ' companies for ' + domain + '.');
  }
  return snapshotFromCompany(companies[0]);
}

export default async function (input: PlayInput) {
  // Live mode would send a person to an email tool. That is task 4.5, and it is
  // cut. Throw before any lookup so this request spends nothing.
  // Synthetic people never reach an email tool.
  if (input.email_mode !== 'mock') {
    throw new Error('live email is only allowed in task 4.5');
  }

  const seenPersonIds = new Set<string>();
  const rows = [];

  for (const event of input.events) {
    const domain = companyHost(event.new_domain);
    const company = domain === '' || isFreeMail(domain) ? null : await lookupCompany(domain);
    const email = mockEmail(event);
    // PlayEvent has the same decision fields as JobChangeEvent, plus the mock email.
    const ruleEvent: JobChangeEvent = event;
    const decision = decide(ruleEvent, company, email, seenPersonIds);

    rows.push({
      case_id: event.case_id,
      alert: decision.alert,
      status: decision.status,
      reason: decision.reason,
      email: email.email,
      email_status: email.email_status,
      company: {
        employees: company === null ? null : company.employees,
        country: company === null ? null : company.country,
      },
      brief: decision.alert ? writeBrief(ruleEvent, company) : '',
    });
  }

  return { rows };
}
