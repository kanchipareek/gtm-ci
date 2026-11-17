# gtm-ci

CI for a GTM automation built on Deepline. This repo automates Deepline's own golden-set eval method in pull request CI. Every pull request that changes the Play gets scored on a fixed set of synthetic job-change cases with known answers, before and after the change. The check is blocked if false alerts go up overall, if false alerts go up for any trap type, or if any single case flips from pass to fail.

The test set uses the golden-dataset columns from Deepline's review skill: `case_id`, `split`, `input_*`, `expected_*`, `grading_notes`, and `notes`.

**Status: in progress.** This repository is scaffolding only. There is no Play, scorer, or workflow yet, and there are no results or cost numbers.

The spec is [`docs/spec.md`](docs/spec.md). The ordered work plan is [`TASKS.md`](TASKS.md). After each task, short notes go in [`docs/LEARNING.md`](docs/LEARNING.md). A prior-art note is in [`docs/prior_art.md`](docs/prior_art.md).

The advisor-seat rule follows an idea already used in [mhimed-crustdata/champion-job-change-tracker](https://github.com/mhimed-crustdata/champion-job-change-tracker), which filters advisor seats, board seats, and same-company moves.

## Run

Use Python 3.11 on Windows PowerShell.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
pytest
```

Copy `.env.example` to `.env.deepline` and paste your Deepline key on your machine. `.env.deepline` is not committed.

## Honest limits (will be filled in on day 5)

- Every person in the test set is made up. No real person's data is used.
- The test set will be small (30 cases). It can show the method. It cannot prove accuracy on real data.
- This project does not send email, does not write to any CRM, and does not publish or deploy a Play.
