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
