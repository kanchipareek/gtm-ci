# Learning notes

This is a running notebook. After each task in `TASKS.md`, append a few lines in plain language: what was built, why, and how it connects to the piece before it. Do not paste code. Do not invent results. Do not rewrite older notes.

Answer that task's "Understand it" questions in a sentence or two. Those are the things to be able to say out loud in an interview.

## Template

Copy this heading for each task. Leave the older notes above it alone.

### Task <id> — <short name>

- Built:
- Why:
- Connects to:
- I can explain:

## Notes

### Starter kit — skeleton only

- Built: the spec, the task list, the Cursor rules, this notebook, a smoke test, and the Python project file. No Play, no scorer, no workflow yet.
- Why: the project gets built one task at a time, with tests after each change, so every piece is understood before the next one.
- Connects to: `docs/spec.md` is the source of truth. Its section 3 lists the Deepline facts checked on 17 Nov 2026 with links. Section 4 lists what is still unknown, and which task answers it. Task 1.1 is a spike that proves one real run works before anything else is built.
- I can explain: nothing runs yet, so there is no score and no cost to talk about.

### Task 1.1 — one real play run

- Built: a tiny Play that echoes a domain through one step, and the saved JSON from one real cloud run.
- Why: the scorer has to read the path Deepline actually uses. A guessed path would look for fields that are not in the file.
- Connects to: the starter kit left the output shape unknown. `docs/spike/NOTES.md` now says the returned object is `result`, the run id is `run.id`, and the status is `run.status`. The spend line for this run is in `docs/spend.md`.
- I can explain: `plays check` only validates the file. `--dry-run` only prints the plan. A real run is one cloud execution of that Play, and it can spend credits. The run id is saved as soon as the server accepts the run, so a dropped connection still leaves an id to fetch. `unknown` is the right credit number when usage is missing, because a missing bill is not proof the run was free. This run's billing file did report a number, so the spend line uses that number.

### Task 1.2 — company lookup tool

- Built: `docs/tools.md` names `leadmagic_search_companies`, its 0.15 credit managed price, and the fields `linkedin_employee_count` and `hq_country_code`, copied from `describe`. Spec section 8 now has the lookup sum. An email tool id is noted and was not called.
- Why: the Play needs a real tool id, and the credit number has to come from that tool's describe output. The free lookup was cheaper and did not have a country field.
- Connects to: task 1.1 proved one cloud run. This task did not run a tool. Search and describe left the balance at 25. The next Play task calls this tool id. The offline gate still uses saved company facts.
- I can explain: price the tool with `describe`, because that response is the contract for this id: the credit line and the field names. The pricing page only gives a range across many tools. The two fields the size and country rules need are `linkedin_employee_count` and `hq_country_code`. The sum we use is 0.15 × 5 companies × 5 runs = 3.75 credits, because the spec's live set is 5 companies. The prompt's 10-company product is 7.5 credits and is not the plan. A tool is one operation. A Play is the TypeScript file that calls tools and then applies our rules. Managed means Deepline's provider access, billed at the credit line on `describe`. BYOK means connecting your own provider account so the call runs there; `describe` did not give that mode a second credit price, so the budget uses the managed price.

### Task 1.3 — the rules file

- Built: the decision rules in `plays/rules.ts` (constants, title class, decide, brief) and `scripts/offline_run.ts`, which reads a golden jsonl file and prints one result row per event. A pytest runs that on three synthetic events: one alert, one company that is too small, and one duplicate person.
- Why: the Play and the offline gate have to execute the same decision. The rules file imports nothing from Deepline, so tsx can load it offline and the run spends nothing. The runner maps `case_id` and `input_*` only. It does not read `expected_*`, `grading_notes`, `notes`, `trap`, or `split`.
- Connects to: the company snapshot stands in for the lookup from task 1.2. Section 5.A says the Play will call these same functions. The scorer, later, joins these rows to the labels by `case_id`.
- I can explain: the first failing check wins. An advisor at a 4-person company is `ambiguous_title`, not `company_too_small`, because the title is checked before the size. Swap those two checks and the reason changes. The brief is one fixed sentence, so it never calls a model, never spends credits, and the same event always gets the same words. If the runner could see `expected_*`, it could copy the answer key. The gate would go green for a Play that never applied the rules. A blank company country is `wrong_country`, because section 5.B has no separate missing-country reason. 50 employees and 120 days are still inside the limits. 49 and 121 are not.

### Task 1.4 — the Play file

- Built: `plays/champion-tracker.play.ts` and `plays/deepline.json`. The Play loops over events, skips empty and free-mail domains, looks up the others with `leadmagic_search_companies`, reads the mock email off the event, then calls `decide` and `writeBrief`. `plays check` reported `valid: true`. `--dry-run` printed a plan and did not start a run. pytest still passed. No live run.
- Why: this is the file Deepline will execute. The rules stay in `rules.ts`, which this file imports from the same folder. The manifest tells Deepline which files are Plays and that there are no monitors.
- Connects to: task 1.2 named the tool, the fields, and 0.15 credits per result. Task 1.3 wrote the decision. The Play is the only place a credit can be spent, and only on the company call. Live email throws, because task 4.5 is cut and a synthetic person must not reach an email tool.
- I can explain: the line that can cost money is `deepline.tools.execute` for `leadmagic_search_companies`. The input is only `company_domain`, so the described call is one company at 0.15 credits, not a page of results. `staleAfterSeconds: 604800` is the line that stops the same domain being paid for again for 7 days. The call id is the static string `company`. A templated id failed `plays check`; the domain in the input is what separates one lookup from another. Live email throws `live email is only allowed in task 4.5` before any lookup, so that request spends nothing. `deepline.json` says every `*.play.ts` under `plays/` is a Play, and the monitors list is empty.

### Lookup gate — a free reject skips the company call

- Built: the Play now calls `decide` once with a null company before any lookup. It calls `lookupCompany` only when that reason is `company_not_found`, then calls `decide` again with the real company. `plays/rules.ts` was not changed. `plays check` reported `valid: true`. pytest still passed. No live run.
- Why: champion, domain, same company, duplicate, age, and title are free checks, and they run before the company checks. Paying 0.15 credits for a row those checks already reject does not change the answer.
- Connects to: the paid line is still `deepline.tools.execute`. This gate sits in front of it. A null company never alerts, so the first `decide` does not add the person to `seenPersonIds`. The second call is the one that can.
- I can explain: a junior title, a free-mail domain, or a duplicate person stops before the tool. A row that survives those checks is `company_not_found` until the lookup fills in employees and country, and only then can the size and country rules run.

### Task 1.5 — first real run of the Play

- Built: one capped live run of `champion-tracker` on two synthetic people at `asana.com` and `shopify.com`, with mock email. The output, the receipt log, and the billing file are in `docs/spike/`. The spend line is 0.3 credits.
- Why: the scorer later has to read `result.rows`, and the rules have to read the fields the company tool actually returns. Describe had named them. This run is the first time those names had values.
- Connects to: task 1.4 wired the lookup and stopped in front of it for free rejects. Both events passed those checks, so both lookups ran. The field names matched `docs/tools.md`, so `rules.ts` stayed as it was. Asana (4400, US) alerted. Shopify (29663, CA) was too big. The mock emails were copied. No email tool ran.
- I can explain: the domains are real public companies because a made-up domain would not come back with a headcount and a country. The people are synthetic, surname Testcase, and `email_mode` is `mock`, so nobody is sent to an email tool. The cost is 0.3 credits, from `deepline billing usage` field `run.spent_credits` in `docs/spike/play_billing_usage.json`, and the same number is the new line in `docs/spend.md`. That is two lookups at 0.15, posted as one line with `batch_count` 2. Compute on that run was free. The cap of 5 was not hit. Spec F10 says a call whose projected charge would go over `--max-credits` is refused, and that work already admitted, plus compute, can still be billed. This run did not refuse a call, so the refusal JSON is still question Q6.

### Task 2.1 — fixture format and a validator

- Built: `scorer/fixtures.py` loads a golden JSONL file, checks each row, and can hand the Play a copy with the answer key removed. If a CSV with the same name sits beside the JSONL, the case ids and expected answers must match.
- Why: a bad line has to stop the run. The score is only true when every case is present. The synthetic checks keep real names, real emails, and registrable company domains out of the offline file. `pytest tests/test_fixtures.py` passed, 25 tests.
- Connects to: the offline runner from task 1.3 already ignores `expected_*`, `grading_notes`, `notes`, `trap`, and `split`. This loader is the Python side of that rule. Task 2.2 copies the 30 reviewed rows into `fixtures/events.jsonl` and runs these checks on them.
- I can explain: a fixture check raises on the bad row, with the line and the field, because a skipped row would shrink the set and a pull request could go green with a case missing. Reserved example domains cannot be registered, so a mock address there cannot be a real inbox and a lookup cannot hit a real company. A name like acme.com can already belong to someone. The allowed reason strings live in one tuple, `REASONS`, copied from spec 5.B. The validator imports that tuple. Later scoring code should import it too, so the two cannot disagree about what counts as a reason.

### Task 2.2 — the 30 events and their answers

- Built: the accepted golden set, 30 rows in `fixtures/events.jsonl` and the same rows in `fixtures/events.csv`, plus the case table and the counts in `docs/test_set.md`. The owner accepted the draft answers and the split. 12 should alert and 18 should not. Every reason in spec 5.B has at least one case.
- Why: the labels are the answer key for later scoring. They were written by reading the rules, before this file was given to the rule code. Copying the code's own output into `expected_*` would only prove the code agrees with itself.
- Connects to: task 2.1 loads this file and rejects a bad line, a real-looking domain, or a CSV whose labels do not match. The offline runner from task 1.3 must still ignore `expected_*`, `grading_notes`, `notes`, `trap`, and `split`. This task did not run that runner on these 30 rows.
- I can explain: the answers have to exist before the code runs, or a wrong rule would mark its own mistakes as correct. The closest call is e16. The company is a real fit except the snapshot country is blank, spec 5.B has no missing-country reason, and a blank country is not US, CA, or GB, so the reason is `wrong_country`. The owner accepted that. An email that was not found still alerts, because the check list never looks at the email. e06 is an ICP fit with status `not_found`, and `emails_found` must not count it.
