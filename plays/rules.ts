// The Play and scripts/offline_run.ts both import this file.
// It does not import Deepline, so the offline gate can load it with tsx and spend nothing.

export const MIN_EMPLOYEES = 50;
export const MAX_EMPLOYEES = 5000;
export const ALLOWED_COUNTRIES = ["US", "CA", "GB"];
// Days from start_date to event_date. 120 is still fresh. 121 is stale.
export const MAX_EVENT_AGE_DAYS = 120;
export const JUNIOR_WORDS = ["intern", "student", "trainee", "apprentice", "working student"];
export const SENIOR_WORDS = ["vp", "vice president", "head of", "director", "chief", "cro", "revops lead"];
// A seniority word is not enough on its own. "Head of Vibes" has "head of" and still is not senior.
export const FUNCTION_WORDS = ["revenue", "sales", "growth", "gtm", "operations", "marketing"];
export const FREE_MAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "proton.me"];

export type JobChangeEvent = {
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
};

export type CompanySnapshot = {
  employees: number | null;
  country: string | null;
};

export type EmailSnapshot = {
  email: string | null;
  email_status: string | null;
};

export type Decision = {
  alert: boolean;
  status: string;
  reason: string;
};

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// Whole words only, so "intern" does not match "internal".
function containsPhrase(title: string, phrase: string): boolean {
  const pattern = new RegExp(
    `(^|[^a-z0-9])${escapeRegExp(phrase.toLowerCase())}([^a-z0-9]|$)`,
    "i",
  );
  return pattern.test(title.toLowerCase());
}

export function classifyTitle(title: string): "senior" | "junior" | "ambiguous" {
  const text = title ?? "";

  // Junior wins over a function word. "Working Student, Sales Ops" contains "sales"
  // and is still junior, because the junior check comes before the senior one.
  for (const word of JUNIOR_WORDS) {
    if (containsPhrase(text, word)) {
      return "junior";
    }
  }

  // These two phrases already name the function (revenue, revops), so they do not
  // need a second function word beside them.
  if (containsPhrase(text, "cro") || containsPhrase(text, "revops lead")) {
    return "senior";
  }

  const senior = SENIOR_WORDS.some((word) => containsPhrase(text, word));
  const functionWord = FUNCTION_WORDS.some((word) => containsPhrase(text, word));
  if (senior && functionWord) {
    return "senior";
  }

  return "ambiguous";
}

// A free-mail domain is not a company, so the lookup is skipped and the reason is missing_domain.
function domainMissing(domain: string | null): boolean {
  if (domain == null) {
    return true;
  }
  const host = domain.trim().toLowerCase().replace(/^@/, "");
  if (host === "") {
    return true;
  }
  return FREE_MAIL_DOMAINS.some((free) => host === free || host.endsWith(`.${free}`));
}

function isSameCompany(oldName: string, newName: string): boolean {
  const oldCompany = (oldName ?? "").trim().toLowerCase();
  const newCompany = (newName ?? "").trim().toLowerCase();
  if (oldCompany === "" || newCompany === "") {
    return false;
  }
  return oldCompany === newCompany;
}

function eventAgeDays(startDate: string, eventDate: string): number {
  const start = Date.parse(`${startDate}T00:00:00Z`);
  const event = Date.parse(`${eventDate}T00:00:00Z`);
  // A date we cannot read is not a fresh move, so it fails the age check.
  if (Number.isNaN(start) || Number.isNaN(event)) {
    return MAX_EVENT_AGE_DAYS + 1;
  }
  return Math.round((event - start) / 86400000);
}

function countryAllowed(country: string | null): boolean {
  if (country == null || country.trim() === "") {
    return false;
  }
  return ALLOWED_COUNTRIES.includes(country.trim().toUpperCase());
}

function firstName(fullName: string): string {
  const trimmed = (fullName ?? "").trim();
  const space = trimmed.indexOf(" ");
  if (space === -1) {
    return trimmed;
  }
  return trimmed.slice(0, space);
}

export function decide(
  event: JobChangeEvent,
  company: CompanySnapshot | null,
  email: EmailSnapshot | null,
  seenPersonIds: Set<string>,
): Decision {
  // The email is not part of the alert. A missing email still alerts.
  // The argument stays so the Play and the runner call one function.
  void email;

  // The first failing check wins. A later check does not get a vote.
  // status is the kind of change. reason is why we did or did not alert.
  // same_company uses title_changed. An ICP alert uses moved.

  if (event.was_champion !== true) {
    return { alert: false, status: "no_change", reason: "not_champion" };
  }

  if (domainMissing(event.new_domain)) {
    return { alert: false, status: "possible_change", reason: "missing_domain" };
  }

  if (isSameCompany(event.old_company, event.new_company)) {
    return { alert: false, status: "title_changed", reason: "same_company" };
  }

  // "Already alerted" means an earlier row in this run returned an alert.
  // A rejected row does not count, so it cannot hide a later good move.
  if (seenPersonIds.has(event.person_id)) {
    return { alert: false, status: "moved", reason: "duplicate_person" };
  }

  // Age is event_date minus start_date. Equal to 120 is still inside the window.
  if (eventAgeDays(event.start_date, event.event_date) > MAX_EVENT_AGE_DAYS) {
    return { alert: false, status: "moved", reason: "stale_event" };
  }

  // Title is checked before company size. An advisor at a 4-person company
  // is ambiguous_title, not company_too_small.
  const titleKind = classifyTitle(event.new_title);
  if (titleKind === "junior") {
    return { alert: false, status: "moved", reason: "junior_title" };
  }
  if (titleKind === "ambiguous") {
    return { alert: false, status: "possible_change", reason: "ambiguous_title" };
  }

  // employees null means the lookup found nothing. A present count of 0 is a real company.
  if (company == null || company.employees == null) {
    return { alert: false, status: "possible_change", reason: "company_not_found" };
  }

  if (company.employees < MIN_EMPLOYEES) {
    return { alert: false, status: "moved", reason: "company_too_small" };
  }

  if (company.employees > MAX_EMPLOYEES) {
    return { alert: false, status: "moved", reason: "company_too_big" };
  }

  // The country rule uses the company snapshot, not country_hint.
  // A blank country has no reason of its own, so it fails this list.
  if (!countryAllowed(company.country)) {
    return { alert: false, status: "moved", reason: "wrong_country" };
  }

  seenPersonIds.add(event.person_id);
  return { alert: true, status: "moved", reason: "icp_fit" };
}

export function writeBrief(event: JobChangeEvent, company: CompanySnapshot | null): string {
  // The sentence is fixed so a brief never calls a model and cannot change between runs.
  // The first name is repeated on purpose. The template does not guess a pronoun.
  // A missing snapshot is never an ICP alert, so there is no sentence.
  // The caller also stores "" when decide did not alert, because a reject can still have a company.
  if (
    company == null ||
    company.employees == null ||
    company.country == null ||
    company.country.trim() === ""
  ) {
    return "";
  }

  const name = firstName(event.full_name);
  return (
    `${name} was a champion at ${event.old_company}. ` +
    `${name} is now ${event.new_title} at ${event.new_company} ` +
    `(about ${company.employees} people, ${company.country}). ` +
    "Reach out because a past champion now owns the budget at an ICP account."
  );
}
