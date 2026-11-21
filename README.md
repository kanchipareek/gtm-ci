# gtm-ci

CI for GTM workflows, built on [Deepline](https://code.deepline.com).

GTM teams now keep their automations in git. Deepline stores each workflow as a `*.play.ts` file, and its official GitHub workflow runs `deepline plays check`, which proves the Play is valid code. It does not tell you if the output got worse. Loosen one targeting rule and the Play still runs; you find out when the wrong people get messaged. Deepline's review skill describes scoring a Play against a labelled golden set by hand, in a Sheet. This repo automates that method in pull request CI: old rules vs new rules on the same cases, a before and after table on the pull request, and a failed check if false alerts go up overall, for any trap type, if any case flips from pass to fail, or if the change makes the Play pay for more lookups. Then it tests the test set itself.

**Demo:** [pull request 2](https://github.com/kanchipareek/gtm-ci/pull/2) changes `MIN_EMPLOYEES` from 50 to 1. The check goes red: "Blocked: false alerts went 0 -> 1" ([comment](results/demo_comment.md)). Case e13, a 49-person company, became the false alert.

## What is in here

| piece | what it does | evidence |
| --- | --- | --- |
| the Play | champion job-change tracker on Deepline. Rules in [`plays/rules.ts`](plays/rules.ts), one paid call (`leadmagic_search_companies`), only when the free checks pass | [`plays/champion-tracker.play.ts`](plays/champion-tracker.play.ts) |
| golden set | 36 synthetic job changes with written answers, each built around one trap (49 employees, "Head of Vibes", "Internal" vs "intern", 121 days old...) | [`docs/test_set.md`](docs/test_set.md) |
| offline gate | every pull request, 0 credits. Scores base and head rules, posts one comment, fails on regressions | [`.github/workflows/gtm-ci.yml`](.github/workflows/gtm-ci.yml) |
| cost gate | fails a pull request that sends more rows to the paid lookup, even if every alert is still right | [`docs/mutation.md`](docs/mutation.md#the-cost-gate) |
| mutation score | breaks the rules on purpose, 44 ways, to find cases the test set is missing. Runs on every pull request and warns when a test set change lets a rule break through | [`docs/mutation.md`](docs/mutation.md) |
| live eval | the real Play on Deepline, only with the `live-eval` label, credit cap 10 | [`ci/thresholds.json`](ci/thresholds.json) |
| real cases | 10 real public job changes run live | [`results/real_run.md`](results/real_run.md) |
| drift watch | every Monday, re-runs 5 saved companies live and opens an issue if their data changed | [`.github/workflows/drift-watch.yml`](.github/workflows/drift-watch.yml) |

## How the gate works

```
pull request
   |
   +-- offline-gate (every PR, 0 credits)
   |     base/plays/rules.ts --+
   |                           +--> head scorer + head fixtures --> compare --> one PR comment
   |     head/plays/rules.ts --+                                      |
   |                                                                  +--> red if worse
   |     guard: fixtures/ or thresholds changed without the test-set-change label --> red
   |
   +-- plays-check (deepline plays check, free)
   |
   +-- live-eval (only with the live-eval label, same-repo only, cap 10 credits)
         runs the real Play on 5 saved companies, adds a "Live run" section to the comment
```

- **The gate is offline.** Every pull request scores `plays/rules.ts` on saved company facts. The real Play only runs on Deepline when someone adds the `live-eval` label. `rules.ts` is imported by both the Play and the offline runner, so the gate tests the same decision code the Play runs, including its two-step lookup gate.
- **A pull request cannot grade itself.** Base and head rules are both scored with the head scorer and head fixtures, and [`scorer/guard.py`](scorer/guard.py) fails the job if the answer key or thresholds changed without a reviewer's `test-set-change` label.
- **Thresholds** ([`ci/thresholds.json`](ci/thresholds.json)): false alerts +0, missed alerts +0, false alerts per trap +0, pass to fail 0, paid lookups +0.

## Testing the test set

A green check means no case got worse. It does not mean a case exists that *could* get worse. So [`scorer/mutate.py`](scorer/mutate.py) breaks `rules.ts` one edit at a time (`MIN_EMPLOYEES` 50 to 49, India added to the country list, "intern" dropped...) and checks whether the gate blocks each one.

The mutations were split before any new case was written: 25 **discovery** mutations used to find holes, and 19 **holdout** mutations that were not used to design cases.

| stage | cases | discovery caught | holdout caught |
| --- | --- | --- | --- |
| as built | 30 | 18 / 25 | 10 / 19 |
| plus cost gate | 30 | 19 / 25 | 10 / 19 |
| plus 6 new cases | 36 | 25 / 25 | 11 / 19 |

Sources: [`results/mutation_30cases_old_gate_discovery.md`](results/mutation_30cases_old_gate_discovery.md), [`results/mutation_30cases_old_gate_holdout.md`](results/mutation_30cases_old_gate_holdout.md), [`results/mutation_30cases_cost_gate.md`](results/mutation_30cases_cost_gate.md), [`results/mutation.md`](results/mutation.md).

Patching every hole I could see took discovery to 25 of 25 and moved holdout by one. The test set got better at the test I looked at, not in general. One holdout mutant cannot be caught at all ("working student" is covered by "student"), so the honest holdout score is 11 of 18. The worst open hole: every case has a `country_hint` equal to the company's country, so a change that read the hint instead of the company would pass. The 8 open holes are listed in [`docs/mutation.md`](docs/mutation.md#holes-still-open-holdout-8-of-19) and left open so the holdout still means something.

**On every pull request** the comment gets a "Test set strength" section: the same 44 breaks, run on the base test set and the head test set. The `test-set-change` label lets a reviewer approve a change to the answers; this section shows what that change costs, for example "this test set change stops catching: m07 (India added to allowed countries)". Shown, not gated.

Two discovery holes could not be caught by any alert test. Dropping gmail.com from the free-mail list still rejects the row, just after a paid company lookup. That is why the cost gate exists.

## Real job changes, live

10 real public job changes from the last 3 months (company press releases), run through the real Play on Deepline on 20 Nov 2026. Names are not in the repo. [`results/real_run.md`](results/real_run.md):

| correct alerts | false alerts | missed alerts | correct no alerts | credits |
| --- | --- | --- | --- | --- |
| 5 | 0 | 0 | 5 | 1.2 |

The two that could have flipped did not: Ampcontrol (LinkedIn band 11 to 50) came back at 22 employees and was rejected as too small, and Buildots (Tel Aviv HQ, US and UK offices) came back as IL and was rejected on country. Rules were not changed for this run.

## Drift watch

[`drift-watch.yml`](.github/workflows/drift-watch.yml) runs every Monday at 03:30 UTC (and by hand). It runs the Play live on 5 saved companies ([`fixtures/live_companies.json`](fixtures/live_companies.json)), cap 2 credits, and opens or updates one issue, "company data drift", listing company, field, old value, new value and where the old value came from. It closes the issue when nothing differs. An empty lookup is not counted as a change.

The first run (20 Nov, 0 credits, from the 7-day cache, [`docs/spend.md`](docs/spend.md)) opened [issue 4](https://github.com/kanchipareek/gtm-ci/issues/4): HubSpot and Twilio headcounts did not match. **That was my bug, not drift.** Those two snapshots came from public filings (9016 and 5625), and the live value is a LinkedIn count (13083 and 7816). The issue showed it because it lists where each saved value came from. On 21 Nov both snapshots were replaced with the LeadMagic values from the 19 Nov run ([`docs/cache/run2_run_output.json`](docs/cache/run2_run_output.json)), and the old value and the reason are kept in each `snapshot_source`. Against that run, drift is now 0, so the next issue means a company actually changed. Figma's snapshot is still a filing count, and its lookup comes back empty, so it is never compared. The issue lists the snapshot source for exactly this reason.

## Cost

Every live run is in [`docs/spend.md`](docs/spend.md), with credits from `deepline billing usage --run-id`, not estimates. Total so far: 1.8 of 25 free credits.

- Offline gate: 0 credits per pull request.
- One company lookup: 0.15 credits per result ([`docs/tools.md`](docs/tools.md)).
- Cache: a repeat run within 7 days paid 0 credits ([`docs/cost.md`](docs/cost.md)).
- Cap: `--max-credits 0.01` refused a 1.46-credit call and spent 0 ([`docs/cost.md`](docs/cost.md#credit-cap-19-nov-2026)).

## Run it locally (Windows PowerShell)

Needs Python 3.11 and Node 22.

```powershell
git clone https://github.com/kanchipareek/gtm-ci.git
cd gtm-ci
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
npm ci
pytest
python -m scorer --mode offline --label head
python -m scorer.mutate
```

`pytest`, the offline score and the mutation run cost 0 credits and need no key. A live run needs the Deepline CLI, a key in `.env.deepline` (copy `.env.example`, never committed), and asks before it spends:

```powershell
python -m scorer --mode live --fixtures fixtures/live_companies.json --max-credits 2
```

## Honest limits

- **The golden set is synthetic and hand-made.** 36 cases, written by me. It shows the method, not accuracy on real data. The mutation score shows how much it is missing: 11 of 18 catchable holdout mutations.
- **The offline gate uses saved company facts.** It tests the decision code and the lookup gate, not LeadMagic's answers.
- **The live job runs only with a label.** Not every pull request runs the Play on Deepline.
- **The credit cap is not an all-in ceiling.** It refuses a call whose projected charge goes over. Admitted work and compute can still bill ([`docs/cost.md`](docs/cost.md#credit-cap-19-nov-2026)).
- **Email is mock.** Live email finding is built but not proven in this repo ([`docs/cost.md`](docs/cost.md)). "Emails found" counts mock emails.
- **The 10 real cases are a curated sample, not an accuracy rate.** Hand-picked (5 should alert, 5 should not, each "no" failing a different rule) and hand-labelled by me. Two of them (r09, r10) are rejected before the lookup, so they never reach LeadMagic.
- **The live company set is 5 big companies.** 3 of the 5 are over 5000 people and Figma comes back empty, so the live run mostly proves the plumbing and the bill, not the size boundary. Figma's lookup comes back empty and its snapshot is a filing count, so Figma is never compared. HubSpot and Twilio started as filing counts; that mistake is what the first drift issue caught.
- **The demo bug was planted on purpose.**
- **The mutations are hand-written** by the same person who wrote the cases, and only cover `rules.ts`. The per-PR strength section is shown, not gated.

## Not in scope

No sending email, no CRM writes, no publishing or deploying the Play, no monitors.

## More

[`docs/test_set.md`](docs/test_set.md), [`docs/trap_sources.md`](docs/trap_sources.md) (the real complaint behind each trap), [`docs/mutation.md`](docs/mutation.md), [`docs/cost.md`](docs/cost.md), [`docs/spend.md`](docs/spend.md), [`docs/prior_art.md`](docs/prior_art.md).
