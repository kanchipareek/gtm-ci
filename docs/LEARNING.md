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
