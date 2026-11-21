# Mutation testing the test set

The offline gate is only as good as the 30 cases behind it. A green check means "no case got worse". It does not say whether a case exists that *could* get worse. So this tests the test set: break `plays/rules.ts` on purpose, one small edit at a time, and see if the gate blocks the change.

```
python -m scorer.mutate
```

Offline, 0 credits, about 20 seconds. The list is [`ci/mutations.json`](../ci/mutations.json). Each mutation is one find and replace in `plays/rules.ts` (for example `MIN_EMPLOYEES = 50` to `49`). For each one, `scorer/mutate.py` copies `plays/`, applies the edit, scores the copy, and runs the same `scorer.compare` the pull request gate runs. Caught means the gate would have blocked that pull request. Survived means it would have merged.

## Two lists, written before any new case

- **discovery** (m01 to m25): run first, and used to find holes.
- **holdout** (h01 to h19): written at the same time, before any case was added, and not used to design cases. Its v1 result was saved without being read until the new cases were in.

Same idea as a development and holdout split. If patching the holes you found also closes holes you did not look at, the test set got better. If it only closes the ones you looked at, you taught to the test.

## Results

| stage | cases | gate | discovery caught | holdout caught | source |
| --- | --- | --- | --- | --- | --- |
| 1. as built | 30 | alerts only | 18 / 25 | 10 / 19 | [discovery](../results/mutation_30cases_old_gate_discovery.md), [holdout](../results/mutation_30cases_old_gate_holdout.md) |
| 2. add cost gate | 30 | alerts + paid lookups | 19 / 25 | 10 / 19 | [results](../results/mutation_30cases_cost_gate.md) |
| 3. add e31 to e36 | 36 | alerts + paid lookups | 25 / 25 | 11 / 19 | [results](../results/mutation.md) |

Discovery went to 25 of 25. Holdout moved by one, from 10 to 11 (h02, max employees doubled, is now caught by e31). **Patching the holes i could see barely touched the holes i could not.** That is the finding.

## What the discovery holes were

| mutation | why the gate missed it | fix |
| --- | --- | --- |
| m04 max employees 5000 to 5001 | only 5000 (inside) and 12000 were tested, nothing just outside | e31, 5001 people |
| m07 India allowed | only DE and blank country were tested | e32, India HQ |
| m13 intern dropped | e21 "Sales Intern" has no senior word, so it falls to `ambiguous_title` anyway. The junior rule was never tested on its own | e33, "Intern, Office of the Chief Revenue Officer" |
| m14 trainee dropped | no trainee case | e34, "Sales Director Trainee" |
| m15 apprentice dropped | no apprentice case | e35, "Apprentice to the Head of Growth" |
| m21 gmail dropped | e24 is still rejected later (null company), so no alert changes | cost gate, see below |
| m22 proton.me dropped | no proton.me case, and the same backstop as m21 | e36 plus the cost gate |

## The cost gate

m21 cannot be caught by any alert test. Drop gmail.com from the free-mail list and the row is still rejected, just later: in a live run the lookup would search gmail.com, most likely get Google back, and reject it as too big. Not run live, so that part is a guess. The alert is right. The bill is not. The Play only pays for `leadmagic_search_companies` when the first `decide` call returns `company_not_found` ([`plays/champion-tracker.play.ts`](../plays/champion-tracker.play.ts)), so a rule change that moves a free reject behind that call spends credits on every such row.

`scripts/offline_run.ts` now makes the same two `decide` calls as the Play and marks `would_lookup` on each row. `scorer/score.py` counts `paid_lookups`. `ci/thresholds.json` has `paid_lookups_max_increase: 0`, so a pull request that sends more rows to the paid lookup is blocked with "Blocked: paid company lookups went X -> Y", even when every alert is still right. Today's rules send 19 of the 36 cases to the lookup ([`results/mutation.md`](../results/mutation.md) base run, also printed by `python -m scorer --mode offline`).

## Holes still open (holdout, 8 of 19)

Left open on purpose. Patching them now would turn the holdout into a second discovery list and the next score would mean nothing.

| mutation | why it survives |
| --- | --- |
| h03 Australia allowed | no AU case. Same hole class as m07: the set tests one wrong country, not "every other country" |
| h06 "working student" dropped | **cannot be caught.** "student" is also in the list and matches the same titles. This is an equivalent mutant, so the real holdout ceiling is 18, and the score is 11 of 18 |
| h07 "student" dropped | e22 "Working Student, Sales Ops" is still caught by "working student". No plain "Student" title |
| h10 "operations" dropped | every operations title in the set also has revenue, sales or gtm in it |
| h11 yahoo dropped | no yahoo.com case, so the cost gate has nothing to count |
| h12 "cro" no longer senior alone | e05 spells out "Chief Revenue Officer". No title says just "CRO" |
| h17 country read from `country_hint` instead of the company | **every case has `country_hint` equal to the company country.** The rule comment says it uses the snapshot, not the hint, and nothing tests that. This is the one that matters most: under this mutation a German company with a GB `country_hint` would alert, and the gate would stay green |
| h19 null employees not treated as not found | e17 moves from `company_not_found` to `company_too_small`, still no alert. Reasons are shown but not gated, by design (spec 5.D) |

## Limits

- The mutations are hand-written, and by the same person who wrote the cases. A mutation tool that generates edits from the syntax tree would be less biased.
- 44 mutations on one 223-line rules file. The score is a coverage signal for this rules file, not a general accuracy number.
- The mutation run is a command, not a CI step. It is not yet run on every pull request.
- All six new cases are "should not alert". The set is now 12 alerts and 24 no-alerts.
