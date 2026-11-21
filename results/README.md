# Results

This folder is scorer output. `results/*` is gitignored. `results/README.md` is the exception, so this note can be committed.

A result file is committed only on purpose:

- One recorded live run: `results/live_<date>.json` and `results/live_<date>.md`.
- The demo pull request scores: `results/demo_base.json`, `results/demo_head.json`, and `results/demo_comment.md`.
- The real job-change run: `results/real_run.json` and `results/real_run.md`.
- The mutation score: `results/mutation.*` (36 cases, current) and `results/mutation_30cases_*` (the 30-case set before the fix). See `docs/mutation.md`.

Every other run stays local. `results/head.json` and `results/head.md` from a local offline score are not committed.
