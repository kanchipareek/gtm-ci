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
