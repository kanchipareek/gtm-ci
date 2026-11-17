# Review checklist for fixtures_draft.jsonl (and fixtures_draft.csv)

DRAFT. Nothing here is final until you tick it. About 20 minutes.

The 30 cases now use Deepline's golden-dataset columns from the review skill: `case_id`, `split`, `input_*`, `expected_*`, `grading_notes`, `notes`, plus a separate `trap` field that the Play runner never reads. JSONL is the working file. The CSV is a Sheet-shaped mirror with the same columns and answers.

## Before you start
- [ ] Read the ICP rule at the top of `data/failure_sources.md`.
- [ ] Skim spec section 5.C so the new column names are familiar.

## Check the answers by hand
- [ ] Go through all 30 rows. For each, cover `expected_alert` and `expected_reason` and say the answer out loud from the rule. Then check.
- [ ] 12 alert, 18 do not. Every reason from spec 5.B has at least one case.
- [ ] e11 comes before e12 in the file, and both have `split=development`. The duplicate only works in that order, in the same run.

## Decide these 4 calls
- [ ] Missing country (e16): is it `wrong_country`? I said yes.
- [ ] Boundaries: 50 people alerts (e03), 5000 alerts (e04), 120 days alerts (e08), 121 days does not (e28). Agree?
- [ ] Whole-word matching: "Head of Internal Sales" (e30) is senior, not junior. Agree? If yes, `rules.ts` must match whole words.
- [ ] Advisor at a 4-person startup (e26) gives `ambiguous_title`, not `company_too_small`, because titles are checked first. Fine?

## Development / holdout split
- [ ] 20 development, 10 holdout. The runner still scores all 30 in one pass. Holdout is the acceptance slice, not a second isolated run.
- [ ] Holdout cases are e02, e04, e08, e13, e19, e22, e24, e26, e28, e30 (4 should-alert, 6 should-not). Agree, or say which ones to swap?
- [ ] Types with two or more cases appear in both splits where possible. The duplicate pair stays in development. The two country cases stay in development until the missing-country call is decided. Advisor is in holdout on purpose.

## Synthetic data
- [ ] Every `input_full_name` ends in "Testcase".
- [ ] Every email is `synthetic.<person_id>@<domain>.example`, or null.
- [ ] Every `input_new_domain` ends in `.example`, is empty, or is gmail.com.
- [ ] e23 and e24 have `input_mock_email` null. Your 2.1 validator must allow a null email when `input_mock_email_status` is `not_found`.

## Notes, grading_notes, and trap
- [ ] Each row's `notes` starts with `DRAFT.` and includes the trap name, source ids, and a one-line why. The Play runner must never read `notes`, `grading_notes`, `trap`, `split`, or `expected_*`.
- [ ] `trap` is a separate field used only by the scorer for per-trap slices and the per-trap false-alert gate.
- [ ] `grading_notes` describe how to score the row, not a new expected answer.

## Sources
- [ ] Open the 5 best quotes yourself before you use any in the README or a post.
- [ ] S15 (Reddit) is a search excerpt. Open the thread and confirm the comment before using it.
- [ ] Label vendor sources as vendor wherever you quote them.

## When done
- [ ] After you accept the answers and the split, task 2.2 copies these files to `fixtures/events.jsonl` and `fixtures/events.csv`.
- [ ] Add the counts table (including split) to `docs/test_set.md`.
