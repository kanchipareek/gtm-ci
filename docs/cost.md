# Cost

Live email finding is built but not proven in this repo.

## Cache test, 19 Nov 2026

Two live runs of the unpublished file `plays/champion-tracker.play.ts` on `fixtures/live_companies.json`. Cap 10. No `--refresh-cache`. Run 1 started at 09:20 UTC. Run 2 started at 09:28 UTC.

The numbers below are copied from `run.spent_credits` and from the LeadMagic and compute lines in the billing files. They are not estimates.

| | run 1 | run 2 |
|---|---|---|
| `run.spent_credits` | 0 | 0 |
| LeadMagic line, credits | 0 | 0 |
| compute line, credits | 0 | 0 |

Run 1: `docs/cache/run1_billing_usage.json`. Run 2: `docs/cache/run2_billing_usage.json`.

The cache worked for a successful answer. An unpublished local file counts as the same Play across separate CLI runs.

Each billing file has one LeadMagic line, `status` `no_result`, `outcome` `miss`, `charge_state` `free`, credits 0. That line is the Figma lookup. The run logs show the other four lookups as `execution_source` `cache` and `sends` 0, and run 2 reused the same four receipt keys as run 1. Those logs are in `docs/cache/run1_run_output.json` and `docs/cache/run2_run_output.json`.

Two of the reused answers are about 46.3 hours old on run 1 (`resultAgeMs` 166836173 and 166833456). That matches the 17 Nov Asana and Shopify lookups in `docs/spend.md`. The other two are about 3.6 hours old (`resultAgeMs` 13139299 and 13141211). That age lines up with the GitHub Actions live run in `docs/spend.md`. `deepline runs list` shows it started at 2026-11-19T05:41:36.665Z. The 17 Nov billing file shows balance 24.7 and month spent 0.3. Run 1's billing file shows balance 24.4 and month spent 0.6. The 0.3 in between is that Actions run. `deepline billing usage --run-id` for `play/champion-tracker/run/20261119t054133-501-e3431d39-caller-8c1a12447d2410d4837cfb885dd4fa8fa16c6d548142c5269a0c7256b027fd2c` says `run.spent_credits` 0.3.

Figma was called live on both runs. The row came back with null employees and a null country, and an empty answer is not reused. The live retry is still 0 credits in the billing file. Compute on both runs is `charge_state` `free`.

`staleAfterSeconds` was not changed.

## Credit cap, 19 Nov 2026

One live run of `plays/champion-tracker.play.ts` on the five companies in `fixtures/live_companies.json`, with `--max-credits 0.01` and no `--refresh-cache`. Run id `play/champion-tracker/run/20261119t100646-806-3d0ffe24-caller-1c164779dbf631ea1e84e5df6b745c50b093f2f3a29156d75909337d77f8830e`. The overview in `docs/cap/run_output.json` has `run.status` `failed`, `resultState` `not_returned`, and `errorDetails.reported[0].code` `RUN_BILLING_CAP_EXCEEDED`. The message says the run is capped at 0.01 credits, 0 already spent, 0.01 remaining, and this call needs 1.46. There is no `result.rows`. `docs/cap/billing_usage.json` has `run.spent_credits` 0. Its one line is compute, `status` `error`, `charge_state` `failed`, credits 0. There is no LeadMagic line. `--max-credits` refuses a tool call whose projected charge would go over the cap. Work that was already admitted stays billable, and compute stays billable, so the cap is not a ceiling on the whole run (spec F10). On this run the message says nothing had been spent yet, and the posted bill is 0, while the compute line is still on the usage file. The 1.46 in the message is the projected charge of the refused call. `docs/tools.md` lists `leadmagic_search_companies` at 0.15 credits per result. The cap check used the 1.46 figure from this run.

## Recorded live run, 19 Nov 2026

No new Deepline call. This is the second cache-test run. The scorer read `docs/cache/run2_run_output.json`, the run id in `docs/cache/run2_run_id.json`, and `run.spent_credits` in `docs/cache/run2_billing_usage.json`. It wrote `results/live_2026-11-19.json` and `results/live_2026-11-19.md`.

The numbers below are copied from that result file and from the billing file. They are not estimates.

| | value |
|---|---|
| run id | `play/champion-tracker/run/20261119t092809-247-9b8e1402-caller-34a7e53d73eb1a75a116767bc27df45dc9f37e8f1044e084c8884c5f7df5942d` |
| credits, whole run | 0 |
| companies | 5 |
| credits per company | 0 |
| drift count | 4 |
| compute time | not shown |

Credits per company is the whole-run bill divided by the 5 companies in `fixtures/live_companies.json`: 0 / 5 = 0.

Drift is 4 fields. The scorer compared `result.rows` with the saved snapshots: c03 employees, c04 employees, c04 country, c05 employees. c01 and c02 match. c04 came back with a null employee count and a null country, so both fields differ.

Compute time is not shown. The compute line on this run is `charge_state` `free`, credits 0, and `provider_units` 6. That line has no duration field. This recorded run is the 5-company live set.

This run id is already in `docs/spend.md` (cache test run 2, 0 credits). It is not entered again. A second line would count one run twice.

The spend lines add up to 0.6 credits. The account started with 25 free credits. 0.6 of those 25 are written in the log. This run's billing file shows balance 24.4 and month spent 0.6. 25 minus 0.6 is 24.4, which matches that balance. The 0.3 that used to sit between the log and the month total is the GitHub Actions run now in `docs/spend.md`.

Rough sum, not a quote: 1,000 contacts at this run's 0 credits per company is 0 credits. That repeats this bill. Four lookups were cache hits, and the live Figma call is 0 credits on the bill. It is not the price of 1,000 fresh lookups.

A second rough sum, not a quote, uses the described price in `docs/tools.md`: 0.15 credits per result. 1,000 × 0.15 = 150 credits. At $0.10 per credit (`plan.usd_per_credit` 0.1, [`tools.md`](tools.md)) that is $15. This run did not pay 0.15 per company. The sum leaves out cache, misses, email, and compute.
