# gtm-ci: build spec

CI for a GTM automation. Every pull request that changes a Deepline Play gets scored on a fixed test set with known answers, before and after the change. If the change makes the results worse, the pull request is blocked.

Build window: **Wed 18 Nov to Sun 22 Nov 2026** (5 days, solo, Windows laptop, PowerShell, Cursor). Budget: **about $10 to $20 of Deepline credits in total**, and $0 for everything else.

> Labels: **[Fact]** is in section 3 with a source URL. **[Open]** is in section 4 and has a task that answers it. **[Decision]** is a design choice we can defend. **[Hypothesis]** is not tested yet.

---

## 0. One-paragraph pitch (for the README top)

GTM teams now keep their automations in git. Deepline stores each workflow as a `*.play.ts` file, and its official GitHub workflow runs `deepline plays check` on every pull request. That check proves the Play is valid code. It does not tell you if the output got worse. If someone loosens one targeting rule, the Play still runs, and you only find out when the wrong people get a message. Deepline's own review skill already describes how to score a Play against a labelled golden set, by hand, live, in a Sheet. This repo automates that same method in pull request CI. A champion job-change tracker is built as a Deepline Play. Thirty synthetic job-change cases use Deepline's golden-dataset columns, with the right answer written down. A scorer runs the old rules and the new rules on the same cases, posts a before and after table on the pull request, and fails the check if false alerts go up overall, if false alerts go up for any trap type, or if any single case flips from pass to fail. Paid Deepline calls are capped per run and cached, and most CI runs cost 0 credits.

---

## 1. Scope

**In:**
- (A) A Deepline Play: a champion job-change tracker.
- (B) 30 synthetic job-change events with expected answers.
- (C) A Python scorer.
- (D) A GitHub Actions check on every pull request, with a before and after comment.
- (E) Cost guards: per-run credit cap, caching, and an offline mode that costs 0 credits.
- (F) A day 5 demo: a pull request that loosens one rule gets blocked by CI.

**Out (explicitly):**
- Real people's data. Every person in the test set is made up.
- Sending any email or message.
- Writing to any real CRM.
- Monitors. They are a separate Deepline product, and the Actions directory deploy cannot ship them (fact F13).
- Publishing or deploying the Play to production.
- An LLM-written brief. The brief is a fixed template, so it is free and gives the same text every time.
- Dashboards, a web app, and paid tools other than Deepline credits.

**[Decision] The gate runs offline. The live run is a proof, not the gate.** Deepline runs every Play in the cloud (fact F7), and every live run can spend credits. So the pass/fail check on every pull request runs the Play's own rule code on saved company facts, for 0 credits. A separate live job runs the real Play through Deepline only when the pull request has the label `live-eval`, with a hard credit cap. The README and any post must describe it exactly this way.

---

## 2. Architecture

```
fixtures/events.jsonl        30 synthetic golden-set rows (Deepline columns:
 (and events.csv)             case_id, split, input_*, expected_*, grading_notes,
                              notes, plus trap for scoring slices). The Play
                              runner never reads expected_*, grading_notes,
                              notes, trap, or split.
        │
        ├──────────── OFFLINE (every PR, 0 credits) ─────────────┐
        │                                                        │
        ▼                                                        ▼
 plays/rules.ts  ◄── imported by ──  plays/champion-tracker.play.ts
 (pure decision code,                 (the Deepline Play: company lookup via
  no deepline import)                 deepline.tools.execute with staleAfterSeconds,
        ▲                             email step, rules, brief, billing cap)
        │                                        │
 scripts/offline_run.ts                          │ LIVE (label `live-eval` only,
 (reads input_* fields,                      │  capped with --max-credits)
  calls the same rules.ts,                       ▼
  writes results JSON)               deepline plays run ... --json --full
        │                             deepline runs get <id> --full --json
        │                             deepline billing usage --run-id <id> --json
        ▼                                        │
 scorer/ (Python 3.11) ◄─────────────────────────┘
   run.py      calls the offline runner or the deepline CLI
   score.py    compares results with expected answers
   report.py   writes results JSON and a markdown table
   compare.py  base vs head, reads ci/thresholds.json, sets the exit code
        │
        ▼
 .github/workflows/gtm-ci.yml
   checks out base and head, scores both with the HEAD fixtures and HEAD scorer,
   posts one before/after comment on the PR, fails if a threshold is broken.
```

**[Decision] Rules live in one plain TypeScript file.** `plays/rules.ts` has no Deepline import. The Play imports it, and the offline runner imports the same file. So the gate tests the exact rule code the Play runs. It is not a Python copy of it. Deepline allows imports inside the Play's folder (fact F19).

**[Decision] Base and head are scored with the head's test set and scorer.** Only the Play folder (`plays/`) comes from the base commit. Otherwise a pull request could edit the answers to make itself pass. If a pull request changes `fixtures/` or `ci/thresholds.json`, the comment says so in its first line, and the check fails unless the pull request has the label `test-set-change` (task 3.2).

---

## 3. Verified facts

Checked live on **Tue 17 Nov 2026** from the docs pages and the CLI help of `deepline@0.3.535`. Re-check before the post goes out, because the docs change often.

| # | Fact | Source |
|---|---|---|
| F1 | The npm package is `deepline`. The latest version is `0.3.535`. | `npm view deepline` · https://www.npmjs.com/package/deepline |
| F2 | Install: `npm install -g deepline@latest`, then `deepline setup --json`. The docs also give a variant with `--allow-scripts=esbuild`, because the package runs an esbuild install script. `deepline setup` is interactive (it needs a person to log in). `deepline auth status --json` and `deepline doctor --json` check the result. | https://deepline.com/docs/sdk-v2/coding-agents |
| F3 | A Play is a `.play.ts` file that imports `deepline` and default-exports an async function. Its input type is the input contract. The returned plain object is the result. The file can also export `const config` with literal values only: `name`, `description`, `billing`, `cron`, `webhook`, and more. | https://deepline.com/docs/sdk-v2/plays · https://deepline.com/docs/sdk-v2/reference/runtime |
| F4 | The manifest is `plays/deepline.json`: `{"plays": ["**/*.play.ts"], "monitors": []}`. Globs are relative to that folder. | https://deepline.com/docs/sdk-v2/github-deployments |
| F5 | `deepline plays check <file>` bundles and validates a local Play and "stops before any cloud run is created". The CLI help says it is free. It still needs an API key. Run on the box without a key, it returned `CONFIG_ERROR: No API key found`. `--json` gives `valid`, `inputSchema`, `outputSchema`, and more. | CLI help `deepline plays check --help` (0.3.535) |
| F6 | `deepline plays run <file> --dry-run` shows the execution plan "without API calls". It worked on the box with no key. The docs say this plan "does not simulate provider responses or validate business accuracy". | https://deepline.com/docs/sdk-v2/coding-agents · CLI help |
| F7 | A run of a local file is a cloud run: "Local files run an unpublished root", "This command starts cloud work and may spend Deepline credits". There is no local executor. | CLI help `deepline plays run --help` |
| F8 | Output for a script: `plays run` has `--json [fields]`, `--full`, `--run-id-file <path>` (it writes the run id as soon as the server accepts the run, and the file must not exist yet), `--no-wait`, and `--input @file.json`. You can read a run again with `deepline runs get <run-id> --json` (add `--full` for the complete result). `deepline runs export <run-id> --dataset <path> --out file.csv` exports a dataset without running again. | https://deepline.com/docs/sdk-v2/calling-plays · CLI help |
| F9 | Headless auth: set `DEEPLINE_API_KEY` (and optionally `DEEPLINE_HOST_URL`), or put both in a per-folder `.env.deepline` file. The official workflow uses `DEEPLINE_HOST_URL: https://code.deepline.com`. | https://deepline.com/docs/sdk-v2/reference · https://deepline.com/docs/sdk-v2/github-deployments |
| F10 | Cost cap: `billing.maxCreditsPerRun` in the Play config. `--max-credits <n>` replaces it for one run. Calls whose projected charge would go over the cap are refused. It is **not an all-in ceiling**: work already admitted, and compute, stay billable. | https://deepline.com/docs/cost-control |
| F11 | Caching: `staleAfterSeconds` on `deepline.tools.execute`, `deepline.step`, and `deepline.fetch`. Leaving it out means `0`, a fresh call. A positive number reuses a successful answer up to that many seconds old. `null` reuses forever. "A reused answer makes no provider call and no provider charge." Failed, empty, and unfinished answers are never reused. `--refresh-cache` skips the cache and bills again. | https://deepline.com/docs/sdk-v2/reference/authoring · CLI help |
| F12 | Spend for one run: `deepline billing usage --run-id <run-id> --json`. "Absent charge evidence is not zero", and an active run's usage is partial. | https://deepline.com/docs/cost-control |
| F13 | The official GitHub Actions workflow: on a pull request it installs a pinned `deepline@<version>` and runs `deepline plays check` on each tracked `*.play.ts`, with a separate `DEEPLINE_CHECK_API_KEY`. It skips pull requests from forks. On `main` it runs `deepline plays deploy`. Monitors cannot be deployed this way. **Nothing in that workflow runs the Play or scores its output.** | https://deepline.com/docs/sdk-v2/github-deployments |
| F14 | Deepline also has Git deploys (beta, a GitHub App): ready pull requests register draft revisions, and pushes to the production branch promote them. That page also describes no output scoring. | https://deepline.com/docs/sdk-v2/git-deploys |
| F15 | Prices: **$0.10 per credit** on every plan. Solo is $0/mo plus usage, with no credit card and no minimum. "Find people" and "Find companies" are free. Work email starts at $0.013 a result. Play compute costs $2 to $4 an hour, with "up to 250 h/mo included" (the page does not say which plan this applies to). Email-finder prices range from 0.06 credits (QuickEnrich) through 0.3 (Hunter) and 0.34 (LeadMagic) up to 2.78 credits. | https://deepline.com/pricing · https://deepline.com/docs/_generated/pricing-schedule · https://deepline.com/docs/_generated/pricing/capability-email_finding |
| F16 | "Concurrent runs for the same play are allowed." | CLI help `deepline plays run --help` |
| F17 | Deepline's own job-change guide suggests the statuses `moved`, `title_changed`, `possible_change`, and `no_change`, plus `new_email`, `evidence_url`, and `crm_action` columns. It calls them "a suggested custom workflow contract, not a fixed prebuilt API response". | https://deepline.com/docs/plays/play-job-change-alerts |
| F18 | `plays run` has a `--fixture-behavior <json>` flag marked "Internal/testing". It is not documented for customers. **We do not rely on it.** | CLI help |
| F19 | A Play's imports must stay inside its folder or child folders. Inputs up to 100 KB are stored inline. Inputs over 1 MiB are rejected. | https://deepline.com/docs/sdk-v2/git-deploys · https://deepline.com/docs/sdk-v2/reference |
| F20 | The tool price and fields come from `deepline describe <tool-id> --json`. To find a tool id, use `deepline search "<task>"`. | https://deepline.com/docs/_generated/pricing-schedule |

**From earlier notes, not re-checked today:** the job-change *monitor* price (about $12/mo to watch 1,000 contacts on the pricing page today). We do not use monitors, so it does not matter for this build.

---

## 4. Open questions (each one has a task that answers it)

| # | Question | Answered by |
|---|---|---|
| Q1 | What is the exact JSON shape of `deepline plays run <file> --json --full`? Where are the returned object, the run id, and the status? | 1.1 |
| Q2 | Does `deepline plays check` and `plays run` work in Windows PowerShell? Does the esbuild install script need `--allow-scripts=esbuild`? | 0.1, 1.1 |
| Q3 | Are there any signup credits? What is the smallest credit purchase? | 0.1 (read the Billing page, buy nothing without the owner) |
| Q4 | Which tool id looks up a company by domain and returns employee count and country? What does one call cost? | 1.2 |
| Q5 | Does `staleAfterSeconds` reuse work across two separate CLI runs of the same unpublished local file? Is the second run's provider charge 0? | 4.1 |
| Q6 | When `--max-credits` refuses a call, what does the JSON look like, and can the scorer detect it? | 4.2 |
| Q7 | Does a live run from GitHub Actions with `DEEPLINE_API_KEY` work for an unpublished local file? | 3.5 |
| Q8 | How much compute time does one 30-event run use? Does it show in `billing usage`? | 4.3 |
| Q9 | Free GitHub Actions minutes are limited on a private repo. A public repo is free. Which will the owner pick? | 3.3 (owner decides) |

**[Decision]** Base vs head runs **offline**, so the question "can the Play run twice in one Action" only matters if we later add a live base run. F16 says concurrent runs of the same Play are allowed. That is not tested yet.

---

## 5. Components

### 5.A The Play: `plays/champion-tracker.play.ts`

Input: `{ events: JobChangeEvent[], email_mode: "mock" | "live" }`. Each event is built from the golden row's `input_*` fields and `case_id`. In mock mode, the event also carries `{ email, email_status }` copied from `input_mock_email` and `input_mock_email_status`. `expected_*`, `grading_notes`, `notes`, `trap`, and `split` are never sent to the Play. 30 cases are far under the 100 KB inline limit (F19).

One event:

```json
{
  "case_id": "e01",
  "person_id": "p01",
  "full_name": "Maya Testcase",
  "was_champion": true,
  "old_company": "Old Co",
  "old_title": "Head of Revenue Operations",
  "new_company": "Northwind Example",
  "new_domain": "northwind.example",
  "new_title": "VP Revenue Operations",
  "start_date": "2026-10-20",
  "event_date": "2026-11-01",
  "country_hint": "US"
}
```

Steps, in order:
1. **Company lookup.** `deepline.tools.execute` with the tool from task 1.2 and `staleAfterSeconds: 604800` (7 days). It is skipped when `new_domain` is empty or a free-mail domain.
2. **Email.** In `mock` mode, it uses the event's mock result and makes no call. In `live` mode, it finds the work email with one email tool. **Synthetic people are never sent to a live email tool** (section 6).
3. **Rules.** `decide(event, company, email, seenPersonIds)` from `plays/rules.ts`.
4. **Brief.** A fixed template from `rules.ts`, for example: "Maya was a champion at Old Co. She is now VP Revenue Operations at Northwind Example (about 300 people, US). Reach out because a past champion now owns the budget at an ICP account." It makes no model call.

Config: `export const config = { name: 'champion-tracker', description: ..., billing: { maxCreditsPerRun: 10 } }`.

Output, one row per event:

```json
{ "case_id": "e01", "alert": true, "status": "moved", "reason": "icp_fit",
  "email": "synthetic.p01@northwind.example", "email_status": "found",
  "company": { "employees": 300, "country": "US" }, "brief": "..." }
```

### 5.B Rules: `plays/rules.ts`

Plain exported constants and functions. These are the starting values, and day 5 loosens one of them on purpose:

- `MIN_EMPLOYEES = 50`, `MAX_EMPLOYEES = 5000`
- `ALLOWED_COUNTRIES = ["US", "CA", "GB"]`
- `MAX_EVENT_AGE_DAYS = 120` (the time between start_date and event_date)
- `JUNIOR_WORDS = ["intern", "student", "trainee", "apprentice", "working student"]`
- `SENIOR_WORDS = ["vp", "vice president", "head of", "director", "chief", "cro", "revops lead"]`. "Senior" also needs a function word (revenue, sales, growth, gtm, operations, marketing).
- `FREE_MAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "proton.me"]`

The order of checks (the first one that fails gives the reason):

1. `not_champion`
2. `missing_domain`
3. `same_company` (a title change only, with status `title_changed`)
4. `duplicate_person` (the person already alerted in this run)
5. `stale_event`
6. `junior_title`
7. `ambiguous_title`
8. `company_not_found`
9. `company_too_small`
10. `company_too_big`
11. `wrong_country`
12. otherwise alert, with reason `icp_fit`.

Every reason is a fixed string, so the scorer can count reasons.

### 5.C Test set: `fixtures/events.jsonl` (CSV mirror: `fixtures/events.csv`)

The test set uses Deepline's own golden-dataset column contract, so a Sheet import and the CI scorer share the same rows. The review skill recommends these columns:

> Package repeated case-specific expectations as a golden dataset with columns
> `case_id | split | input_* | expected_* | grading_notes | notes`. Join outputs
> by stable `case_id`, never row position. Use `development` cases for repeated
> candidate work and reserve `holdout` cases for acceptance.

Sources: https://deepline.com/skills/deepline-plays-review and https://skillbundle.dev/site/code.deepline.com/deepline-plays-improve. The improve skill also says: use a non-empty, unique `case_id`; use only `development` and `holdout` for `split`; a single unpartitioned golden set invites overfitting.

**Columns** (one row per case; JSONL and CSV have the same names):

- `case_id`: stable, non-empty, unique. The join key for actual vs expected. Values stay `e01` to `e30`.
- `split`: `development` or `holdout`.
- `input_*`: Play inputs and the offline stand-ins for enrichment. Fields: `input_person_id`, `input_full_name`, `input_was_champion`, `input_old_company`, `input_old_title`, `input_new_company`, `input_new_domain`, `input_new_title`, `input_start_date`, `input_event_date`, `input_country_hint`, `input_company_employees`, `input_company_country`, `input_mock_email`, `input_mock_email_status`. Company fields are `null` (empty in CSV) when there is no snapshot. `input_mock_email` is `null` when the status is `not_found`.
- `expected_alert` (boolean) and `expected_reason` (one of the reason strings in 5.B). These are the labels. Written by hand **before** the rules are run on the set. If a rule and an answer disagree, the answer is not edited to match the code. Either the rule is wrong, or the answer was wrong, and the reason goes in `docs/LEARNING.md`.
- `grading_notes`: how to grade this row. Default: deterministic, normalized equality on `expected_alert` and `expected_reason`, join by `case_id`. A few rows add a short extra rule (duplicates must run together, email is not part of the alert decision, and so on).
- `notes`: reviewer text. Starts with `DRAFT.` until the owner accepts the set. Also holds the trap name, source ids, and the one-line why. The Play runner never reads this column.
- `trap`: the trap type name (for example `advisor_side_role`). This is not a Deepline golden column. It is a separate metadata field that the Play runner never reads. The scorer uses it only to report slices and to gate false alerts per trap type. Source ids stay in `notes`, not here.

The draft of the 30 rows lives in `data/fixtures_draft.jsonl` and `data/fixtures_draft.csv` until the owner reviews them. Task 2.2 copies the accepted files into `fixtures/`.

**People are synthetic.** Names use the surname `Testcase`, and the mock emails use the local part `synthetic.<id>`. No real person's data is used.

**Companies.** Use fictional names on reserved example domains (`*.example`, `example.com`, `example.org`, as set by RFC 2606) for the offline set. Use a separate small file, `fixtures/live_companies.json`, with 5 real public company domains (businesses only, no people) for the live job. **[Decision]** This keeps every offline answer stable and stops a mock email from looking like a real person's address.

**Split (20 development / 10 holdout).** The Play runner always runs all 30 cases in one pass, so in-run state such as `duplicate_person` still works. `split` is for reporting and for any later optimize-style loop: tune on development, accept on holdout, and do not retune after looking at holdout failures. The pull request gate scores the full set, then also reports each split.

Holdout (10): `e02`, `e04`, `e08`, `e13`, `e19`, `e22`, `e24`, `e26`, `e28`, `e30`. That is 4 should-alert and 6 should-not-alert.

Development (20): the other cases, including the `e11`/`e12` duplicate pair. 8 should-alert and 12 should-not-alert.

Trap types with two or more cases are represented in both splits where possible (clean alerts, company size, event age, fake titles, junior titles, missing domains). Types that could not be split: the duplicate pair must stay together and stays in development, because `duplicate_person` is in-run state; `wrong_country` and `missing_country` stay together in development until the owner decides the missing-country call; single-case types (`not_champion`, `same_company`, `company_not_found`, the two email cases) sit in one split only. `advisor_side_role` is in holdout so it is a protected acceptance case.

**Target mix** (task 2.2 writes the exact table into `docs/test_set.md`): 12 should-alert and 18 should-not-alert, with at least 1 case for every reason in 5.B, and these tricky cases:
  - too small (49 employees, just under the line) and exactly 50 (alert)
  - wrong country, and a country missing from the snapshot
  - a duplicate person (the same `input_person_id`, two cases)
  - a student or intern, and a "Working Student, Sales Ops" title
  - fake or ambiguous titles ("Revenue Ninja", "Growth Hacker in Residence", "Head of Vibes")
  - a missing domain, and a free-mail domain (gmail.com)
  - a title change at the same company
  - a stale event (a start date 200 days before the event)
  - a company that was not found (the company input fields are `null`)
  - an email not found, but the alert still fires (the email is not part of the decision)

### 5.D Scorer: `scorer/` (Python 3.11, standard library and pytest only)

- `run.py`: `run_offline(plays_dir, fixtures_path)` calls `npx tsx scripts/offline_run.ts` and reads its JSON. `run_live(...)` calls `deepline plays run plays/champion-tracker.play.ts --input @<tmp>.json --max-credits <cap> --json --full --run-id-file <tmp>`. Then it reads usage with `deepline billing usage --run-id <id> --json`.
- `score.py` joins actual rows to golden rows by `case_id`, never by row position. A missing, duplicate, or extra `case_id` is reported separately from an incorrect answer, and is an error for the CI score, not a silent skip. It counts:
  - `correct_alerts` (`expected_alert` true, got alert)
  - `false_alerts` (`expected_alert` false, got alert)
  - `missed_alerts` (`expected_alert` true, got no alert)
  - `correct_no_alerts`
  - `wrong_reason` (both say no alert, but the reasons differ; shown, not gated)
  - `emails_found` (alerts with `email_status == "found"`)
  - `credits_spent`
  - `false_alerts_by_trap`: false alert counts keyed by the `trap` field
  - per-case pass or fail, where pass means the alert boolean matches `expected_alert`
  - the same headline counts also broken out by `split` (`development`, `holdout`, and all)
- `credits_spent` is `0` in offline mode and is labelled `offline (no Deepline calls)`. In live mode it is the number from `billing usage`, or the string `"unknown"` if there is no charge evidence. **It is never 0 by guess.**
- `report.py` writes `results/<label>.json` and `results/<label>.md`.
- `compare.py` reads two result files and `ci/thresholds.json` and writes `results/comment.md`. It exits 1 if a threshold is broken.

Default `ci/thresholds.json`:

```json
{
  "false_alerts_max_increase": 0,
  "missed_alerts_max_increase": 0,
  "false_alerts_max_increase_per_trap": 0,
  "pass_to_fail_max": 0,
  "live_max_credits": 10
}
```

Gate rules, all measured on the full 30-case set (base vs head):

1. Fail if `head.false_alerts - base.false_alerts` is greater than `false_alerts_max_increase`.
2. Fail if `head.missed_alerts - base.missed_alerts` is greater than `missed_alerts_max_increase`.
3. Fail if, for any trap type, head false alerts minus base false alerts is greater than `false_alerts_max_increase_per_trap`. A drop in one trap does not cancel a rise in another.
4. Fail if the number of cases that were a pass on base and a fail on head is greater than `pass_to_fail_max`. A case that was already failing on base is not a pass-to-fail flip. Fail-to-pass is an improvement and does not fail the gate.

### 5.E CI: `.github/workflows/gtm-ci.yml`

- `on: pull_request`. `permissions: contents: read, pull-requests: write`.
- Job `offline-gate` (always runs, 0 credits):
  1. Check out head into `head/` and the base commit (`github.event.pull_request.base.sha`) into `base/`.
  2. Set up Node 22 and Python 3.11.
  3. Score `base/plays` and `head/plays`, both with `head/fixtures` and the `head/scorer`.
  4. Compare, write the comment, and post or update **one** comment (find it by a hidden marker `<!-- gtm-ci -->`) with `gh api`.
  5. Fail if the thresholds are broken (total false alerts, total missed alerts, false alerts per trap type, or any pass-to-fail flip), or if the test set changed without the `test-set-change` label.
- Job `plays-check` runs `deepline plays check plays/champion-tracker.play.ts` with `DEEPLINE_API_KEY`. It is free (F5), but it needs the key, so it only runs on same-repo pull requests.
- Job `live-eval` runs only if the pull request has the label `live-eval` and comes from the same repo (forks get no secrets). It runs the head Play live on `fixtures/live_companies.json` with `--max-credits` from the thresholds file, then appends live credits and drift to the comment. It does not gate on alerts. It fails only if the run failed or the credits went over the cap.
- Pin the CLI: `npm install --global deepline@0.3.535` (or the version proven on day 1), like the official workflow (F13).

### 5.F Cost guards

- `billing.maxCreditsPerRun: 10` in the Play config, and `--max-credits` on every live run (F10). Say plainly in the README that it is not an all-in ceiling.
- `staleAfterSeconds: 604800` on the company lookup, so unchanged domains are not paid for twice (F11). Prove it in task 4.1 with real `billing usage` numbers, or write down that it did not work.
- Offline mode by default. Tests, local runs, and the gate cost 0 credits.
- A local spend log, `docs/spend.md`: every live run gets a line with the date, the run id, the credits from `billing usage`, and why it ran.

---

## 6. Honesty rules (never break)

1. Every number in the README, a pull request comment, or a post comes from a committed file in `results/` or `docs/spend.md`. Do not round in your favour.
2. Synthetic means synthetic: no real person's name, email, or profile goes in any fixture or any live call.
3. Say what runs where. The gate runs the Play's rule code offline on saved company facts. The live job runs the real Play on Deepline. Do not write "every PR reruns the play on Deepline" unless that is what happens.
4. 30 events is a small, hand-made set. It shows the method. It does not prove the tracker is accurate on real data.
5. A missing credit number is "unknown", not 0.
6. Do not tune the rules to the test set and then report the score as if it were a fair test. The day 5 demo is about the change, not about a high score.

---

## 7. Timeline

**Day 0, tonight or before task 1.1:** set up the machine (task 0.1).

**Day 1, Wed 18 Nov: prove Deepline works end to end, then build the Play**
- Exit: one real Play run's JSON is saved in `docs/spike/`, and `deepline plays check plays/champion-tracker.play.ts` is valid.

**Day 2, Thu 19 Nov: the test set and the scorer**
- Exit: `python -m scorer --mode offline --label head` prints a table for 30 events.

**Day 3, Fri 20 Nov: the GitHub check**
- Exit: a test pull request shows the before and after comment, and the check fails on a planted bad change.

**Day 4, Sat 21 Nov: cost guards and one real run**
- Exit: `docs/spend.md` has real credit numbers, and caching is proven or written down as not working.

**Day 5, Sun 22 Nov: demo and write-up**
- Exit: the loosened-rule pull request is red, the README limits are written, and the recording plan and post draft are saved, not posted.

**Budget cuts already made (17 Nov, owner decision):** task 4.5 skipped, live runs capped at 10 credits, 5 live companies, task 4.3 records the task 4.1 run instead of a new run, and credits are bought only if the 25 free ones run out.

**Cut list, if still behind (in this order):**
1. Task 3.5 (the live CI job), which becomes a manual live run from the laptop.
2. Task 3.2 (the test-set-change label), which becomes a warning line in the comment only.

**Never cut:** the offline base-vs-head gate, the 30 fixtures with answers written before the code, or the honest limits section.

---

## 8. Budget

- Deepline: start with the 25 free signup credits ($2.50). Worst case if every cap is hit is about 38 credits (1.1 = 2, 1.5 = 5, 3.5 = 10, 4.1 = 2 x 10, 4.2 under 1), so at most about 13 credits ($1.30) bought. The owner buys credits herself, only if the free ones run out, and only after she says yes.
- Company lookup, from task 1.2 (`docs/tools.md`, `deepline` 0.3.537, 17 Nov 2026): `leadmagic_search_companies` is 0.15 credits per result on managed access. One domain lookup is described as one company row, so the sum uses one result per company. The task prompt's formula is 0.15 × 10 live companies × about 5 runs = 7.5 credits ($0.75 at $0.10 per credit, F15). Spec section 5.C and the 17 Nov cut use 5 live companies, so the estimate this repo uses is 0.15 × 5 × 5 = 3.75 credits ($0.375). That is lookups only. It sits inside the caps above. It does not add 3.75 on top of the 38, and it does not include email or compute. A miss is not priced here, because `describe` does not say a miss is free.
- GitHub Actions: free on a public repo. A private repo uses free minutes.
- Everything else (Python, Node, tsx, pytest) is free.

---

## 9. Standalone

- This repo uses no code, data, or links from any other repo of the owner.
- It needs no CRM, no email account, and no other paid tool.

---

## 10. What makes this not generic

1. It is a test harness, not another pipeline. The usual published project is the job-change flow itself. This repo follows Deepline's own golden-set eval method and runs it automatically on every pull request.
2. It fills a gap in Deepline's own tooling: the official workflow validates code (F13), and the review skill describes scoring output by hand in a Sheet. This one validates **output** in CI.
3. Base vs head on the same frozen test set, with the head's answers. A pull request cannot grade itself.
4. The rules are shared between the Play and the offline runner, so the gate tests the real code for 0 credits.
5. Cost is part of the test: per-run caps, caching proven with real usage numbers, and "unknown" instead of a fake 0.
6. A drift check: the live job compares real enrichment with the saved snapshots, so you can see when the world changed and the test set needs a refresh.

---

## 11. Demo and post rules

- The demo pull request loosens one rule (for example `MIN_EMPLOYEES` from 50 to 10, or it removes the country check). The comment's numbers are whatever the scorer says. Do not predict them in advance.
- The 20 to 40 second recording plan is in `writeup/recording_plan.md` (task 5.3).
- The post draft lives in `writeup/post_draft.md`, with "Not posted. Waiting for the owner." on top. Nobody posts it without the owner's approval of the exact text and video.
