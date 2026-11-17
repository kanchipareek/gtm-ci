# Tasks

Work top to bottom. One task per Cursor Agent session. Do not start the next task until the done-when command passes and you can answer the questions.

After every task the agent explains, in plain English, what it built, how the pieces connect, and why. It appends a few lines to `docs/LEARNING.md`. Commit messages are lowercase, short, and plain (`add icp rules`). No `feat:` prefix, no emoji, no long body.

The spec is `docs/spec.md`. It wins if a task and the spec disagree.

Commands are for PowerShell in the VS Code terminal. Activate the venv first: `.\.venv\Scripts\Activate.ps1`.

## Cut list

From spec §7, in this order, and only if you are behind:

1. Real email proof (task 4.5).
2. Live CI job (task 3.5), which becomes a manual live run from the laptop.
3. Full live run (task 4.3), which drops to 5 companies.
4. The test-set-change label (task 3.2), which becomes a warning line in the comment only.

Never cut: the offline base-vs-head gate (tasks 3.1, 3.3, 3.4), the 30 fixtures with answers written before the code (task 2.2), or the honest limits section (task 5.2).

## Where each piece is built

| Piece | Tasks |
|---|---|
| Setup and spike | 0.1, 1.1, 1.2 |
| A. The Play | 1.3, 1.4, 1.5 |
| B. Test set | 2.1, 2.2 |
| C. Scorer | 2.3, 2.4, 2.5 |
| D. GitHub check | 3.1-3.5 |
| E. Cost guards | 4.1, 4.2, 4.3 |
| F. Demo and write-up | 5.1-5.4 |

## Live runs that spend credits

Only these tasks run Deepline for real: 1.1, 1.2 (`describe` and `search` only, which should be free, so check), 1.5, 3.5, 4.1, 4.2, 4.3, 4.5. Each one sets `--max-credits` and adds a line to `docs/spend.md`.

---

## Day 0 - setup, before Wed 18 Nov

### 0.1 - environment, Deepline login, and Cursor

**Goal:** Python 3.11, Node 22, and the `deepline` CLI are installed. `pytest` passes. You are logged in to Deepline, and the key lives only in `.env.deepline`.

**Files:** `.env.deepline` (on your machine, never committed). The repo already has `pyproject.toml`, `.env.example`, `.gitignore`, and `tests/test_smoke.py`.

**Cut:** no

**Prompt:**

```
Follow @docs/spec.md sections 3 (F1, F2, F9) and 4 (Q2, Q3), and @.cursor/rules/project.mdc.

Goal: set up the machine. Do not write Play or scorer code.

1. Check python --version is 3.11. Create .venv, activate it in PowerShell, pip install -e ., and run pytest.
2. Check node --version is 22 or newer. If not, tell me how to install Node 22 LTS on Windows.
3. Install the CLI: npm install -g deepline@0.3.535. If the esbuild install script warning or error appears, use the --allow-scripts=esbuild variant from the docs (spec F2). Then run deepline --version.
4. Tell me to run deepline setup myself, because it needs me to log in. Do not run it for me. Afterwards run deepline auth status --json and deepline doctor --json, and show me only the status fields, not any key.
5. Copy .env.example to .env.deepline. Leave DEEPLINE_API_KEY for me to paste. Do not print it. Confirm .env.deepline is gitignored.
6. Run deepline billing balance --json. Tell me my balance and whether there are any signup credits. Do not buy anything. Write the answer to spec question Q3 in docs/LEARNING.md.

When you finish, explain in plain English what each tool is for (Python, Node, the deepline CLI) and why the key is in .env.deepline and not in the code. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. If you commit, use a short lowercase message with no prefix and no emoji.
```

**Done when:** `pytest` exits 0, `deepline --version` prints a version, `deepline auth status --json` shows you are connected, and `git check-ignore .env.deepline` prints `.env.deepline`.

**Understand it:**

- Why is `.env.deepline` gitignored while `.env.example` is committed?
- Why does the CLI version get pinned, and not left as `latest`?
- Why should you run `deepline setup` yourself instead of the agent?

---

## Day 1 - Wed 18 Nov: prove Deepline works, then build the Play

Exit for the day, from the spec: one real Play run's JSON is saved in `docs/spike/`, and `deepline plays check plays/champion-tracker.play.ts` says it is valid.

### 1.1 - spike: one real Play run, end to end

**Goal:** One tiny Play runs on Deepline from your laptop. We save its real output, so the scorer is built on the real JSON shape, not a guess.

**Files:** `spike/hello-company.play.ts`, `spike/input.json`, `docs/spike/run_output.json` (real output, with ids kept and anything personal removed), `docs/spike/NOTES.md`, `docs/spend.md` (create it).

**Cut:** no. Everything after this depends on it.

**Prompt:**

```
Follow @docs/spec.md sections 3 (F3, F5 to F12) and 4 (Q1, Q2), and @.cursor/rules/project.mdc.

Goal: prove one Play runs end to end and capture the real output shape. This is a throwaway spike, so keep it tiny.

1. Write spike/hello-company.play.ts. It takes { domain: string } and does one deepline.step called "echo" that returns { domain, checked_at }, with staleAfterSeconds: 0. It returns { ok: true, echo }. No provider tool yet, so it should cost almost nothing. Add export const config with a description and billing: { maxCreditsPerRun: 2 }.
2. Write spike/input.json with { "domain": "example.com" }.
3. Run deepline plays check .\spike\hello-company.play.ts --json and show me valid, inputSchema, and outputSchema.
4. Run deepline plays run .\spike\hello-company.play.ts --dry-run and explain the plan.
5. Only after I say yes, run it for real: deepline plays run .\spike\hello-company.play.ts --input @spike\input.json --max-credits 2 --json --full --run-id-file docs\spike\run_id.json > docs\spike\run_output.json
6. Run deepline runs get <run-id> --full --json and deepline billing usage --run-id <run-id> --json. Save both to docs/spike/.
7. In docs/spike/NOTES.md write, from the real files only: where the run id is, where the status is, where my returned object is, and what billing usage said (or "unknown"). Answer spec Q1 and Q2 there. If PowerShell broke anything, write the fix.
8. Add a line to docs/spend.md: date, run id, credits (from billing usage, or "unknown"), and the reason "spike".

Do not invent any field name. If the output shape is different from what the spec assumes, say so and list what the spec needs to change.

When you finish, explain in plain English what a "run" is compared with a "Play", and why we saved the real JSON before writing the scorer. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** `docs/spike/run_output.json` and `docs/spike/NOTES.md` exist, `NOTES.md` names the JSON path of the returned object, and `docs/spend.md` has one line.

**Understand it:**

- What is the difference between `plays check`, `--dry-run`, and a real run?
- Why do we save the run id before reading the result?
- Why is "unknown" a better answer than 0 when usage is missing?

### 1.2 - find the company lookup tool and its price

**Goal:** We know the exact tool id that turns a company domain into employee count and country, what it costs per call, and which fields it returns.

**Files:** `docs/tools.md`.

**Cut:** no

**Prompt:**

```
Follow @docs/spec.md sections 3 (F15, F20), 4 (Q4) and 8, and @.cursor/rules/project.mdc.

Goal: pick the company lookup tool for the Play, and price it from Deepline itself.

1. Run deepline search "company enrichment by domain employee count country" and show the top results.
2. For the best 2 or 3, run deepline describe <tool-id> --json. Write down: tool id, required input, the output fields for employee count and country, credits per call, and whether it is managed or BYOK.
3. Check that search and describe did not spend credits: run deepline billing usage --json before and after, and compare.
4. Pick one tool. Say why, in two lines. Prefer free or cheapest, as long as it returns employee count and country.
5. Also note one email-finder tool id and price from describe, for task 4.5 only. Do not call it.
6. Write it all to docs/tools.md with the date and the CLI version. Update spec section 8 with a real estimate: credits per lookup × 10 live companies × about 5 runs. Show the maths.

Do not run any tool for real in this task.

When you finish, explain in plain English the difference between a tool and a Play, and what managed versus BYOK means for cost. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** `docs/tools.md` names one company tool id, its credits per call, and its output field names, all copied from `describe` output.

**Understand it:**

- Why do we price from `deepline describe` and not from the pricing page?
- Which two fields does the ICP rule need from this tool?
- What does the budget estimate look like, with the maths?

### 1.3 - the rules file

**Goal:** `plays/rules.ts` decides alert or no alert for one event, with one fixed reason string, and writes the brief. It has no Deepline import.

**Files:** `plays/rules.ts`, `package.json` (dev dependencies: `tsx`, `typescript`, `deepline` pinned), `scripts/offline_run.ts`, `tests/test_rules_offline.py`, `tests/fixtures/mini_events.jsonl` (3 to 5 synthetic events).

**Cut:** no

**Prompt:**

```
Follow @docs/spec.md sections 5.A, 5.B and 5.C, and @.cursor/rules/project.mdc.

Goal: write the decision rules once, in plain TypeScript, so both the Play and the offline runner use the same code.

1. plays/rules.ts exports the constants in spec 5.B (MIN_EMPLOYEES = 50 and the rest) and three plain functions:
   - classifyTitle(title) returns "senior", "junior", or "ambiguous"
   - decide(event, company, email, seenPersonIds) returns { alert, status, reason }, checking in the exact order in spec 5.B
   - writeBrief(event, company) returns the fixed template sentence, or "" when there is no alert
   No classes. No Deepline import. Short comments that say why.
2. scripts/offline_run.ts reads a golden-set .jsonl file (path from argv). It uses input_company_employees and input_company_country as the company snapshot, and input_mock_email plus input_mock_email_status as the email. It maps input_* plus case_id into the event object for decide and writeBrief, and prints one JSON array of result rows in the spec 5.A output shape (including case_id). It must never read expected_*, grading_notes, notes, trap, or split. Add a comment saying so.
3. Add package.json with tsx and typescript as dev dependencies. Run npm install.
4. tests/test_rules_offline.py runs: npx tsx scripts/offline_run.ts tests/fixtures/mini_events.jsonl and checks a few rows by hand: one alert, one company_too_small, one duplicate_person. Skip the test with a clear message if npx is not found.

When you finish, run pytest. Explain why the rules are in their own file with no Deepline import, and why the runner must not read expected_*, grading_notes, notes, trap, or split. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** `pytest tests/test_rules_offline.py` passes.

**Understand it:**

- Why does the order of checks matter? Give one event where a different order gives a different reason.
- Why is the brief a template and not an AI call?
- What would go wrong if the runner could see `expected_*`?

### 1.4 - the Play file

**Goal:** `plays/champion-tracker.play.ts` wires the company lookup, email step, rules, and brief together, and passes `deepline plays check`.

**Files:** `plays/champion-tracker.play.ts`, `plays/deepline.json`.

**Cut:** no

**Prompt:**

```
Follow @docs/spec.md sections 3 (F3, F4, F10, F11, F19), 5.A and 5.F, and @docs/tools.md, and @.cursor/rules/project.mdc.

Goal: write the Play. It imports ./rules (same folder, spec F19).

- Input: { events: JobChangeEvent[], email_mode: "mock" | "live" }.
- export const config = { name: 'champion-tracker', description: '...', billing: { maxCreditsPerRun: 20 } }. Literal values only.
- For each event, in order:
  1. If new_domain is empty or in FREE_MAIL_DOMAINS, company = null. Otherwise call deepline.tools.execute with the tool id from docs/tools.md, a stable id like "company_" + domain, a description, and staleAfterSeconds: 604800.
  2. Email: if email_mode is "mock", use the mock email copied from the golden row's input_mock_email and input_mock_email_status (you may attach them on the event as mock_email). If "live", throw an error for now that says live email is only allowed in task 4.5. Synthetic people must never reach an email tool. Never pass expected_*, grading_notes, notes, trap, or split into the Play.
  3. decide(...) and writeBrief(...) from rules.ts. Keep a seenPersonIds set across the loop.
- Return { rows } in the spec 5.A output shape.
- plays/deepline.json is exactly: { "plays": ["**/*.play.ts"], "monitors": [] }.

Use a plain for loop unless the spike showed that a dataset is needed. If you think deepline.dataset is better, explain why first and wait for me.

Run deepline plays check .\plays\champion-tracker.play.ts --json and deepline plays run .\plays\champion-tracker.play.ts --dry-run. Do not do a real run in this task.

When you finish, explain each step of the Play and where credits could be spent. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** `deepline plays check .\plays\champion-tracker.play.ts --json` shows `"valid": true`, and `pytest` still passes.

**Understand it:**

- Which line in the Play can cost money, and which line stops it costing money twice?
- Why does the live email mode throw an error for now?
- What does `deepline.json` tell Deepline?

### 1.5 - first real run of the Play

**Goal:** The real Play runs once on Deepline with 2 events that use real public company domains. We save the output and the credits.

**Files:** `spike/live_two.json` (2 synthetic people at real public company domains, mock emails), `docs/spike/play_run_output.json`, `docs/spike/NOTES.md`, `docs/spend.md`.

**Cut:** no

**Prompt:**

```
Follow @docs/spec.md sections 5.A, 5.F and 6, @docs/spike/NOTES.md and @docs/tools.md, and @.cursor/rules/project.mdc.

Goal: run the real Play once, small and capped.

1. Write spike/live_two.json: { "email_mode": "mock", "events": [two synthetic events] }. Use surname Testcase. Pick 2 well-known public company domains (businesses, no people).
2. Show me the exact command and the max credits before running. Only after I say yes, run:
   deepline plays run .\plays\champion-tracker.play.ts --input @spike\live_two.json --max-credits 5 --json --full --run-id-file docs\spike\play_run_id.json > docs\spike\play_run_output.json
3. Read credits with deepline billing usage --run-id <id> --json. Add a line to docs/spend.md.
4. In docs/spike/NOTES.md, write the JSON path to rows and the real field names the company tool returned. If they differ from docs/tools.md, fix docs/tools.md and rules.ts, then rerun pytest.

When you finish, explain what came back, what it cost, and whether the rules got the fields they need. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** `docs/spike/play_run_output.json` has 2 rows, and `docs/spend.md` has its credits (a number or "unknown").

**Understand it:**

- Why real company domains but synthetic people?
- What did the run cost, and where did that number come from?
- If `--max-credits 5` was too low, what would you have seen?

---

## Day 2 - Thu 19 Nov: the test set and the scorer

Exit for the day: `python -m scorer --mode offline --label head` prints a table for 30 events.

### 2.1 - fixture format and a validator

**Goal:** Every fixture line has the same shape, and a bad line fails loudly.

**Files:** `scorer/__init__.py`, `scorer/fixtures.py`, `tests/test_fixtures.py`.

**Cut:** no

**Prompt:**

```
Follow @docs/spec.md sections 5.B and 5.C, and @.cursor/rules/project.mdc.

Goal: load and check the Deepline golden-dataset file fixtures/events.jsonl with plain Python functions. The column contract is case_id, split, input_*, expected_*, grading_notes, notes, plus trap (scorer-only metadata). A CSV mirror may also exist at fixtures/events.csv. Validate the JSONL; if the CSV is present, check it has the same case_ids and expected answers.

- load_fixtures(path) returns a list of dicts, one per golden row.
- validate_fixture(row) raises ValueError with a clear message if: case_id is missing, empty, or duplicated across the file; split is not development or holdout; a required input_* field is missing (input_company_* and input_mock_email may be null as in spec 5.C); expected_alert is not a bool; expected_reason is not one of the reason strings in spec 5.B; input_mock_email's local part does not start with "synthetic." when an email is present; or input_full_name does not end with "Testcase".
- The Play-runner path of the loader may be asked to drop expected_*, grading_notes, notes, trap, and split. The validator itself may read those fields. The runner must never see them.
- check_synthetic(rows) also fails if any offline input_new_domain is not a reserved example domain (ends with .example, or is example.com, example.org, or example.net), unless it is empty or a free-mail domain.
- Tests use small inline rows in the golden column shape: good ones pass, and each bad kind fails.

Standard library only.

When you finish, run pytest tests/test_fixtures.py. Explain why the validator checks that the data is synthetic. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** `pytest tests/test_fixtures.py` passes.

**Understand it:**

- Why does a fixture check fail loudly instead of skipping a bad line?
- Why are reserved example domains safer than made-up real-looking ones?
- Where is the list of allowed reason strings, and why only one place?

### 2.2 - write the 30 events and their answers

**Goal:** 30 synthetic events with expected answers, written by hand before running the rules on them, covering every reason and the tricky cases.

**Files:** `fixtures/events.jsonl`, `docs/test_set.md`.

**Cut:** no. Never cut.

**Prompt:**

```
Follow @docs/spec.md sections 5.B, 5.C and 6, and @.cursor/rules/project.mdc.

Goal: after the owner has reviewed data/fixtures_draft.jsonl (and the CSV mirror data/fixtures_draft.csv), copy the accepted golden set to fixtures/events.jsonl and fixtures/events.csv. 30 lines, in the spec 5.C Deepline column shape: case_id, split, input_*, expected_*, grading_notes, notes, trap.

- Do not invent new answers. Keep every expected_alert, expected_reason, and trap from the reviewed draft. If the owner changed a draft answer, use her version.
- About 12 should alert and about 18 should not. At least one case for every reason in spec 5.B.
- Include every tricky case in spec 5.C: 49 employees and exactly 50, wrong country and a missing country, a duplicate person, an intern and "Working Student, Sales Ops", fake titles ("Revenue Ninja", "Growth Hacker in Residence", "Head of Vibes"), a missing domain and a gmail.com domain, a same-company title change, a stale event, a null company snapshot, and an alert where the email was not found.
- Keep the development/holdout split from the reviewed draft (20/10, with e11 and e12 in the same split and e11 first).
- Synthetic only: surname Testcase, emails synthetic.<person_id>@<domain>, offline domains on reserved example domains.
- expected_* was written by reading the rules in spec 5.B, NOT by running plays/rules.ts. Do not run the offline runner on this file in this task, and do not edit an expected answer to match the code.
- docs/test_set.md: a table with case_id, split, trap, what it tests, expected_alert, and expected_reason, plus the counts per reason and per split.

Run python -c "from scorer.fixtures import load_fixtures, check_synthetic; r=load_fixtures('fixtures/events.jsonl'); check_synthetic(r); print(len(r))".

When you finish, explain three of the trickiest cases and why their answer is right. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** the command above prints `30`, and `docs/test_set.md` has a count for every reason.

**Understand it:**

- Why must the answers be written before you run the code on them?
- Which case is the closest call, and why?
- Why does "email not found" still alert?

### 2.3 - the runner: offline and live

**Goal:** One Python module runs the Play's rules offline, or the real Play live, and always returns the same list of result rows.

**Files:** `scorer/run.py`, `tests/test_run.py`.

**Cut:** no

**Prompt:**

```
Follow @docs/spec.md sections 5.D and 5.F, @docs/spike/NOTES.md, and @.cursor/rules/project.mdc.

Goal: scorer/run.py with two plain functions.

- run_offline(plays_dir, fixtures_path) calls npx tsx scripts/offline_run.ts with an argument that says which plays folder's rules.ts to import (needed for base vs head on day 3), and returns the parsed rows plus { "mode": "offline", "credits_spent": 0 }.
- run_live(fixtures_or_input_path, max_credits) builds an input file from the golden rows: { email_mode: "mock", events: [each case mapped to an event with case_id, the input_* fields, and mock email copied from input_mock_email and input_mock_email_status, and never expected_*, grading_notes, notes, trap, or split] }. Then it runs deepline plays run plays/champion-tracker.play.ts --input @<file> --max-credits <n> --json --full --run-id-file <new temp file>, reads rows from the JSON path written in docs/spike/NOTES.md, then calls deepline billing usage --run-id <id> --json. credits_spent is the number from usage, or "unknown". Never 0 by guess.
- Use subprocess with a list of arguments, not a shell string. Raise a clear error if the CLI fails.
- Tests: run_offline on tests/fixtures/mini_events.jsonl. For run_live, test only the JSON parsing, using the saved docs/spike/play_run_output.json. Tests must not call Deepline.

Update scripts/offline_run.ts so it can take the plays folder as an argument.

When you finish, run pytest tests/test_run.py. Explain why both modes return the same shape. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** `pytest tests/test_run.py` passes, with no Deepline call (check `docs/spend.md` is unchanged).

**Understand it:**

- Why does the offline runner take a plays folder as input?
- Why use a list of arguments in subprocess and not one string?
- Where does `credits_spent` come from in each mode?

### 2.4 - scoring

**Goal:** Compare result rows with expected answers by case_id, and count correct alerts, false alerts, missed alerts, emails found, credits, false alerts per trap type, and per-case pass or fail.

**Files:** `scorer/score.py`, `tests/test_score.py`.

**Cut:** no

**Prompt:**

```
Follow @docs/spec.md sections 5.D and 6, and @.cursor/rules/project.mdc.

Goal: scorer/score.py with score(rows, fixtures, credits_spent).

- Match rows to golden fixtures by case_id, never by row position. A missing, duplicate, or extra case_id is an error, not a silent skip. Report those counts separately from incorrect answers.
- Count: correct_alerts, false_alerts, missed_alerts, correct_no_alerts, wrong_reason, emails_found, total_events, credits_spent (passed through, can be "unknown").
- Also count false_alerts_by_trap, using the trap field on each golden row, and a per-case pass or fail (pass means the alert boolean matches expected_alert).
- Also return lists of the case_ids behind false_alerts and missed_alerts, so the comment can name them.
- Break the headline counts out by split (development, holdout, and all) for the report. The CI gate in task 3.1 uses the full set.
- Plain dicts, no classes. Tests use 4 to 6 hand-made golden rows where you can count the answer on your fingers, including one per-trap false-alert case and one pass-to-fail setup for compare.py later.

When you finish, run pytest tests/test_score.py. Explain what a false alert and a missed alert mean for a sales team, in one line each. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** `pytest tests/test_score.py` passes.

**Understand it:**

- Which costs a GTM team more: a false alert or a missed alert? Why?
- Why is a missing case_id an error?
- Why is `wrong_reason` shown but not gated?

### 2.5 - report and the command line

**Goal:** `python -m scorer --mode offline --label head` writes `results/head.json` and `results/head.md` and prints the table.

**Files:** `scorer/report.py`, `scorer/__main__.py`, `tests/test_report.py`.

**Cut:** no

**Prompt:**

```
Follow @docs/spec.md section 5.D, and @.cursor/rules/project.mdc.

Goal: a markdown table and a JSON file from one score.

- report.py: to_json(score, meta) and to_markdown(score, meta). meta has label, mode, plays_dir, git sha if available, and the date. The table rows are correct alerts, false alerts, missed alerts, correct no alerts, emails found, and credits. In offline mode, the credits cell says "0 (offline, no Deepline calls)".
- __main__.py: argparse with --mode offline|live, --label, --plays (default plays), --fixtures (default fixtures/events.jsonl), --max-credits. Live mode prints the planned max credits and asks for "yes" on the keyboard unless --yes is given.
- results/ is gitignored, except results/README.md, which says committed result files are only added on purpose (task 4.3 and 5.1).
- Run it offline on the 30 cases. If any expected answer disagrees with the rules, list the case_ids and do NOT change either one. Tell me which you think is wrong and why, and wait.

When you finish, run pytest. Paste the real table. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** `python -m scorer --mode offline --label head` exits 0 and `results/head.md` exists.

**Understand it:**

- Why does live mode ask for "yes" before running?
- If the first score is not perfect, what do you do, and what do you never do?
- Why is the offline credits cell worded the way it is?

---

## Day 3 - Fri 20 Nov: the GitHub check

Exit for the day: a test pull request shows the before and after comment, and the check fails on a planted bad change.

### 3.1 - compare base vs head

**Goal:** Two result files go in, a before and after markdown comment comes out, and the exit code is 1 when a threshold is broken.

**Files:** `scorer/compare.py`, `ci/thresholds.json`, `tests/test_compare.py`.

**Cut:** no. Never cut.

**Prompt:**

```
Follow @docs/spec.md sections 5.D and 5.E, and @.cursor/rules/project.mdc.

Goal: scorer/compare.py with compare(base, head, thresholds) and a small main.

- ci/thresholds.json is exactly the default in spec 5.D.
- The comment starts with the hidden marker <!-- gtm-ci -->, then one verdict line: "Blocked: false alerts went 2 -> 5" or "Passed: no metric got worse", using the real numbers.
- Then a table with metric, base, head, and change, for every metric in score.py, plus the case_ids that newly became false alerts or missed alerts, any trap type whose false alerts went up, and any case_id that flipped from pass to fail.
- Exit 1 if any of these break the thresholds in spec 5.D: total false alerts went up by more than false_alerts_max_increase; total missed alerts went up by more than missed_alerts_max_increase; false alerts for any trap type went up by more than false_alerts_max_increase_per_trap; or the number of pass-to-fail flips is greater than pass_to_fail_max. Otherwise exit 0.
- python -m scorer.compare results/base.json results/head.json --out results/comment.md
- Tests: equal scores pass, more false alerts fail, fewer false alerts pass, a per-trap false-alert rise fails even when the total is unchanged, a single pass-to-fail flip fails, and the thresholds file is read and not hard-coded.

When you finish, run pytest tests/test_compare.py. Explain why the gate compares against base and not against a fixed number. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** `pytest tests/test_compare.py` passes.

**Understand it:**

- Why compare to the base branch instead of "false alerts must be 0"?
- Why name the case_ids in the comment?
- What would you change to allow one extra missed alert?

### 3.2 - the test set cannot grade itself

**Goal:** If a pull request changes `fixtures/` or `ci/thresholds.json`, the comment says so first, and the check fails unless the pull request has the label `test-set-change`.

**Files:** `scorer/guard.py`, `tests/test_guard.py`.

**Cut:** 4th on the cut list. If cut, it becomes a warning line only, with no fail.

**Prompt:**

```
Follow @docs/spec.md section 2 (base and head decision) and 5.E, and @.cursor/rules/project.mdc.

Goal: scorer/guard.py with changed_test_files(base_dir, head_dir) that compares fixtures/ and ci/thresholds.json by file hash, and returns the changed paths.

- python -m scorer.guard base head --labels "<comma separated labels>" prints a warning line for the comment and exits 1 if files changed and "test-set-change" is not in the labels.
- Tests use two temp folders.

When you finish, run pytest tests/test_guard.py. Explain the attack this stops, in one plain sentence. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** `pytest tests/test_guard.py` passes.

**Understand it:**

- Why do base and head both use the head's fixtures?
- Then why do we still need this guard?
- Who should be allowed to add the `test-set-change` label?

### 3.3 - the workflow: offline gate

**Goal:** `.github/workflows/gtm-ci.yml` scores base and head on every pull request and fails when a threshold is broken. It costs 0 credits.

**Files:** `.github/workflows/gtm-ci.yml`.

**Cut:** no. Never cut.

**Prompt:**

```
Follow @docs/spec.md sections 3 (F13) and 5.E, and @.cursor/rules/project.mdc.

Goal: the offline-gate job only. No secrets are needed.

- on: pull_request. permissions: contents: read, pull-requests: write.
- actions/checkout@v4 twice: the head into head/, and github.event.pull_request.base.sha into base/.
- actions/setup-node@v4 (node 22) and actions/setup-python@v5 (3.11). npm ci in head/, pip install -e head/.
- From head/: python -m scorer --mode offline --label base --plays ../base/plays, then --label head --plays plays. Then guard, then compare, writing results/comment.md.
- Upload results/ as an artifact.
- The job fails if compare or guard exits 1. Run the comment step with if: always() so the comment posts even when it fails (task 3.4 adds the comment step; leave a clear placeholder step).
- Add comments in the yaml that say why each step exists.

Then tell me, step by step, how I create the GitHub repo myself (public or private, spec Q9), push, and open a test pull request that changes nothing. Do not create the repo or push for me.

When you finish, explain the order of the steps and why the base scoring uses the head's scorer. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** on your test pull request that changes nothing, the `offline-gate` check is green.

**Understand it:**

- Why does this job need no Deepline key?
- What does `base.sha` point to?
- What would happen if base used its own old scorer?

### 3.4 - one comment on the pull request

**Goal:** The pull request gets one before and after comment, updated on every push and never duplicated.

**Files:** `.github/workflows/gtm-ci.yml`, `scripts/post_comment.py`, `tests/test_post_comment.py`.

**Cut:** no. Never cut.

**Prompt:**

```
Follow @docs/spec.md section 5.E, and @.cursor/rules/project.mdc.

Goal: post or update a single comment.

- scripts/post_comment.py uses the gh CLI (already on GitHub runners) with GITHUB_TOKEN: it lists the PR's comments with gh api, finds the one that starts with <!-- gtm-ci -->, and edits it, or creates one if none exists.
- Keep the "find the marker" logic in a plain function and test it with fake comment lists. Tests must not call GitHub.
- Wire it into the workflow with if: always().

Then plant a bad change on a test branch: set MIN_EMPLOYEES to 1 in plays/rules.ts. Tell me how to open that pull request myself. Do not push for me.

When you finish, explain why one updated comment is better than one comment per push. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** the test pull request with `MIN_EMPLOYEES = 1` shows a red X and one comment whose verdict line says "Blocked", with the real numbers.

**Understand it:**

- How does the script find its own comment?
- Why is `GITHUB_TOKEN` enough here, with no personal token?
- Why post the comment even when the check fails?

### 3.5 - the live job (label only, capped)

**Goal:** When a pull request has the label `live-eval`, the real Play runs on Deepline with a hard cap, and its credits and drift are added to the comment.

**Files:** `.github/workflows/gtm-ci.yml`, `fixtures/live_companies.json`, `scorer/drift.py`, `tests/test_drift.py`.

**Cut:** 2nd on the cut list. If cut, run the live mode from the laptop and paste the result into `docs/spend.md`.

**Prompt:**

```
Follow @docs/spec.md sections 3 (F9, F10, F12, F13), 4 (Q7) and 5.E, and @.cursor/rules/project.mdc.

Goal: the live-eval job and the plays-check job.

- plays-check: on same-repo pull requests only, install deepline@<pinned version>, run deepline plays check plays/champion-tracker.play.ts with DEEPLINE_API_KEY from secrets.
- live-eval: if: contains(github.event.pull_request.labels.*.name, 'live-eval') and the PR is from the same repo. Runs python -m scorer --mode live --yes --fixtures fixtures/live_companies.json --max-credits <live_max_credits from ci/thresholds.json>.
- fixtures/live_companies.json: up to 10 real public company domains (businesses only), each with one synthetic person, mock email mode, and the snapshot we expect for employee count and country.
- scorer/drift.py: compares live company fields with the snapshot and counts how many differ. Tests use fake data.
- The live job adds a "Live run" section to the comment: run id, credits (or "unknown"), and drift count. It fails only if the run failed or credits > cap.

Tell me how to add DEEPLINE_API_KEY as a repository secret myself. Never print the key. Do not add the label or push for me.

When you finish, explain why the live job is opt-in by label, and why it does not gate on alerts. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** `pytest tests/test_drift.py` passes, and one labelled pull request shows a "Live run" section with a run id and credits from `billing usage`.

**Understand it:**

- Why do forks never get the live job?
- What is drift, and why is it not a test failure?
- Where in the comment does the real credit number come from?

---

## Day 4 - Sat 21 Nov: cost guards and one real run

Exit for the day: `docs/spend.md` has real credit numbers, and caching is proven or written down as not working.

### 4.1 - prove caching with real usage

**Goal:** Two live runs on the same companies, one after the other. The second one's provider charge is lower or 0, shown by `billing usage`, or we write down that it was not.

**Files:** `docs/spend.md`, `docs/cost.md`.

**Cut:** no

**Prompt:**

```
Follow @docs/spec.md sections 3 (F11, F12), 4 (Q5) and 5.F, and @.cursor/rules/project.mdc.

Goal: test staleAfterSeconds with real numbers.

1. Show me the plan and the cap. After I say yes, run python -m scorer --mode live --fixtures fixtures/live_companies.json --max-credits <cap> twice, a few minutes apart, without --refresh-cache.
2. For each run, save the run id and the billing usage JSON. Add both to docs/spend.md.
3. docs/cost.md: a small table of run 1 and run 2 credits, from the files only. Say plainly whether the cache worked, did not work, or is unclear, and why (for example, whether an unpublished local file counts as the same Play).

Do not change staleAfterSeconds to make the result look better.

When you finish, explain what a cache hit means for cost. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** `docs/cost.md` has both runs' credits copied from `billing usage` output, and a one-line verdict.

**Understand it:**

- What does `staleAfterSeconds: 604800` mean in days?
- What would `--refresh-cache` do to the bill?
- If the cache did not work, what does the README have to say?

### 4.2 - prove the credit cap

**Goal:** A run with a cap that is too low gets refused, and the scorer reports it clearly instead of crashing or showing a fake score.

**Files:** `scorer/run.py`, `tests/test_run.py`, `docs/cost.md`, `docs/spend.md`.

**Cut:** no

**Prompt:**

```
Follow @docs/spec.md sections 3 (F10), 4 (Q6) and 5.F, and @.cursor/rules/project.mdc.

Goal: see what a refused call looks like, and handle it.

1. After I say yes, run one live run with --max-credits set below one lookup's price from docs/tools.md (for example, 0.01). Use --refresh-cache only if the cache would hide the call, and tell me first.
2. Save the real JSON. Find where the refusal shows up.
3. Update run_live so a refusal becomes { "status": "refused_by_cap", "cap": ..., "credits_spent": ... } and the scorer prints "Live run refused by the credit cap" instead of a score. Add a test using the saved refusal JSON.
4. docs/cost.md: one paragraph about what the cap stops and what it does not (spec F10).

When you finish, run pytest. Explain why the cap is not an all-in ceiling. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** `pytest tests/test_run.py` passes with the refusal test, and `docs/cost.md` shows the real refusal.

**Understand it:**

- What exactly does `--max-credits` refuse?
- What can still be billed after a refusal?
- Why is a refused run not scored as 0 alerts?

### 4.3 - one full live run and its record

**Goal:** One capped live run on all live companies, committed as a result, so the README can quote real cost and drift numbers.

**Files:** `results/live_<date>.json`, `results/live_<date>.md` (committed on purpose), `docs/spend.md`, `docs/cost.md`.

**Cut:** 3rd on the cut list. If cut, use 5 companies.

**Prompt:**

```
Follow @docs/spec.md sections 4 (Q8), 5.F and 6, and @.cursor/rules/project.mdc.

Goal: one recorded live run.

1. After I say yes, run python -m scorer --mode live --fixtures fixtures/live_companies.json --max-credits <cap> --label live_<date>.
2. Commit the two result files on purpose (force-add, since results/ is gitignored).
3. docs/cost.md: credits for the whole run, credits per company, drift count, and compute time if billing usage shows it (spec Q8), otherwise "not shown".
4. Total spend so far from docs/spend.md, against the $10 to $20 budget.

When you finish, explain the real cost per company and what it would mean for 1,000 contacts, clearly marked as a rough sum and not a quote. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** `results/live_<date>.json` is committed, and `docs/cost.md` has the run's credits and drift count from that file.

**Understand it:**

- Why commit this one result file and not every run?
- How much of the budget is left?
- Why is "per 1,000 contacts" a rough sum and not a price?

### 4.4 - dress rehearsal

**Goal:** Three pull requests behave as expected: no change is green, a planted bad rule is red, and a fixture edit is flagged.

**Files:** whatever breaks. `docs/rehearsal.md`.

**Cut:** no

**Prompt:**

```
Follow @docs/spec.md section 5.E, and @.cursor/rules/project.mdc.

Goal: test the whole check like a stranger would.

Give me exact steps to open three pull requests myself:
1. A README typo fix, which should pass.
2. ALLOWED_COUNTRIES gets "IN" added, which should be blocked if any India case expects no alert, otherwise passed. Say which, from docs/test_set.md, before I open it.
3. One expected answer edited in fixtures/events.jsonl with no label, which should be blocked by the guard.

After each, I paste the comment back to you. Fix anything that breaks, with tests. Write docs/rehearsal.md with the three outcomes copied from the real comments.

When you finish, explain anything that broke and the fix. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** `docs/rehearsal.md` shows all three outcomes as expected, copied from real comments.

**Understand it:**

- Why test a pull request that changes nothing?
- Did your prediction for pull request 2 match? If not, why not?
- What does the guard protect in pull request 3?

### 4.5 - real email path (optional)

**Goal:** The live email step works once, on one consenting real person (you), or we write down that it is not proven.

**Files:** `plays/champion-tracker.play.ts`, `docs/cost.md`, `docs/spend.md`.

**Cut:** 1st on the cut list.

**Prompt:**

```
Follow @docs/spec.md sections 5.A and 6, and @docs/tools.md, and @.cursor/rules/project.mdc.

Goal: allow email_mode "live" for an explicit allow-list of person_ids only, and test it once on me, with my consent, outside the fixtures.

- Keep the throw for every person not in the allow-list. Synthetic people must never reach the email tool.
- After I say yes, run one live run with my own details from a local file that is gitignored, with --max-credits 2.
- Record credits in docs/spend.md. Commit no personal data. The output file stays local.

If I say skip, write in docs/cost.md: "Live email finding is built but not proven in this repo."

When you finish, explain why the allow-list exists. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** `docs/cost.md` says either that the email path was proven with its credits, or that it is not proven.

**Understand it:**

- Why can't the test set use real email lookups?
- What stops a synthetic person from reaching the tool?
- What do you say in an interview if this was skipped?

---

## Day 5 - Sun 22 Nov: demo and write-up

Exit for the day: the loosened-rule pull request is red, the README limits are written, and the recording plan and post draft are saved, not posted.

### 5.1 - the demo pull request

**Goal:** One clean pull request loosens one ICP rule, and CI blocks it. The real numbers are saved.

**Files:** `plays/rules.ts` (on a branch only), `results/demo_base.json`, `results/demo_head.json`, `results/demo_comment.md` (committed on main, on purpose).

**Cut:** no

**Prompt:**

```
Follow @docs/spec.md sections 6 and 11, and @.cursor/rules/project.mdc.

Goal: the demo.

1. Tell me how to make a branch called loosen-icp and change one line: MIN_EMPLOYEES from 50 to 10 (or remove the country check, my choice). Nothing else changes.
2. Before I push, run the offline scorer locally for base and head and show me the comment. Do not guess numbers.
3. I open the pull request myself. When CI is red, I download the artifact. Copy demo_base.json, demo_head.json and demo_comment.md into results/ on main and commit them on purpose.
4. Do not merge the demo pull request.

When you finish, read the verdict line out to me and explain each number in it. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** the demo pull request has a red X, and `results/demo_comment.md` on main matches its comment.

**Understand it:**

- Which events turned into false alerts, and why?
- Why change only one line?
- Why keep the demo pull request open and unmerged?

### 5.2 - README with honest limits

**Goal:** A README a stranger can follow, where every number links to a committed file, and the limits are said plainly.

**Files:** `README.md`.

**Cut:** no. Never cut the limits section.

**Prompt:**

```
Follow @docs/spec.md sections 0, 6 and 10, and @.cursor/rules/project.mdc.

Goal: rewrite README.md.

Order: the one-paragraph pitch (spec 0), the demo verdict line with a link to results/demo_comment.md, how it works (a short diagram), what runs where (offline gate vs live job, exactly as spec 6 rule 3), how to run it locally in PowerShell, cost (from docs/cost.md), and "Honest limits".

Honest limits must say: the 30 events are synthetic and hand-made; it shows the method, not accuracy on real data; the offline gate uses saved company facts; the live job runs only with a label; the credit cap is not an all-in ceiling; the email path is proven or not proven (from docs/cost.md); and the set is small.

Every number must link to the committed file it came from. No number without a source.

When you finish, list every number in the README with its source file. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** every number in `README.md` appears in a file under `results/` or `docs/`, and the "Honest limits" section exists.

**Understand it:**

- Why put the limits in the README and not hide them?
- How do you explain "offline gate" to a non-engineer in one line?
- Which limit would a Deepline engineer ask about first?

### 5.3 - recording plan and an unsent post

**Goal:** A 20 to 40 second shot list for the screen recording, and one post draft, saved locally, not published.

**Files:** `writeup/recording_plan.md`, `writeup/post_draft.md`.

**Cut:** no. Publishing is out of scope until you approve it. The agent must not post.

**Prompt:**

```
Follow @docs/spec.md sections 6 and 11, and @.cursor/rules/project.mdc.

Goal: two files under writeup/.

recording_plan.md: a shot list of 20 to 40 seconds total, each shot with its seconds:
1. The one-line change in rules.ts in VS Code.
2. The pull request opening.
3. The check running, then the red X.
4. The comment table with the verdict line.
5. Optional: deepline plays check passing, so Deepline is on screen.
Plus tips: a large font, a cropped window, no secrets or emails on screen, and no notifications.

post_draft.md: start the file with "Not posted. Waiting for the owner." Lead with the failure that got caught, using only the numbers in results/demo_comment.md. Name Deepline once in the "what I built" line. Describe exactly what runs where (spec 6 rule 3). Lowercase, casual, no em dashes, no emojis, no hype words.

Do not post. Do not upload anything.

When you finish, point me at the files and explain the first line of the post. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** both files exist, `post_draft.md` starts with "Not posted. Waiting for the owner.", and every number in it is in `results/demo_comment.md`.

**Understand it:**

- Why does the post start with the failure that got caught?
- Which claim would be untrue if you wrote "every PR reruns the play on Deepline"?
- Why is "not posted" still a finished task?

### 5.4 - final clean pass

**Goal:** A fresh clone runs, no secrets are in git history, and the repo stands on its own.

**Files:** whatever needs fixing.

**Cut:** no

**Prompt:**

```
Follow @docs/spec.md sections 6 and 9, and @.cursor/rules/project.mdc.

Goal: check the repo like a stranger.

1. Clone the repo into a new folder, follow the README in PowerShell, and run pytest and the offline scorer. Fix anything the README missed.
2. Search the whole git history for secrets: git log -p | Select-String -Pattern "DEEPLINE_API_KEY=.+" and any key-looking strings. Report what you find. Do not rewrite history without asking me.
3. Check no file links to or names another repo of mine.
4. Check fixtures still pass check_synthetic.
5. Check every number in README.md and writeup/ has a source file.

When you finish, give me a short pass/fail list. Answer the Understand it questions. Append a few lines to @docs/LEARNING.md. Commit with a short lowercase message, no prefix and no emoji.
```

**Done when:** the fresh-clone `pytest` passes, the secret search finds nothing, and every line on the list is a pass.

**Understand it:**

- Why test from a fresh clone and not your working folder?
- What would you do if a key was found in history?
- What is the one sentence you would say about this project in an interview?
