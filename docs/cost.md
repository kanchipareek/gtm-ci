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

Two of the reused answers are about 46.3 hours old on run 1 (`resultAgeMs` 166836173 and 166833456). That matches the 17 Nov Asana and Shopify lookups in `docs/spend.md`. The other two are about 3.6 hours old (`resultAgeMs` 13139299 and 13141211). This spend log has no run at that time. The 17 Nov billing file shows balance 24.7 and month spent 0.3. Run 1's billing file shows balance 24.4 and month spent 0.6. The 0.3 in between is not a line here, and there is no run id for it in this repo.

Figma was called live on both runs. The row came back with null employees and a null country, and an empty answer is not reused. The live retry is still 0 credits in the billing file. Compute on both runs is `charge_state` `free`.

`staleAfterSeconds` was not changed.

## Credit cap, 19 Nov 2026

One live run of `plays/champion-tracker.play.ts` on the five companies in `fixtures/live_companies.json`, with `--max-credits 0.01` and no `--refresh-cache`. Run id `play/champion-tracker/run/20261119t100646-806-3d0ffe24-caller-1c164779dbf631ea1e84e5df6b745c50b093f2f3a29156d75909337d77f8830e`. The overview in `docs/cap/run_output.json` has `run.status` `failed`, `resultState` `not_returned`, and `errorDetails.reported[0].code` `RUN_BILLING_CAP_EXCEEDED`. The message says the run is capped at 0.01 credits, 0 already spent, 0.01 remaining, and this call needs 1.46. There is no `result.rows`. `docs/cap/billing_usage.json` has `run.spent_credits` 0. Its one line is compute, `status` `error`, `charge_state` `failed`, credits 0. There is no LeadMagic line. `--max-credits` refuses a tool call whose projected charge would go over the cap. Work that was already admitted stays billable, and compute stays billable, so the cap is not a ceiling on the whole run (spec F10). On this run the message says nothing had been spent yet, and the posted bill is 0, while the compute line is still on the usage file. The 1.46 in the message is the projected charge of the refused call. `docs/tools.md` lists `leadmagic_search_companies` at 0.15 credits per result. The cap check used the 1.46 figure from this run.
