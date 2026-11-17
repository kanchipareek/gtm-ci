# Spike notes

Written from the JSON files in this folder. The workspace display name in `command_context.active_organization.org_name` was replaced with `removed` before commit. Run ids are unchanged.

The installed CLI was `deepline` 0.3.537 (`deepline --version`). Spec section 3 was checked against 0.3.535.

## Where the run id is

`docs/spike/run_id.json` field `runId`. The CLI wrote this file when the server accepted the run, before the result was printed.

The same id is in the finished output at `run.id` in `docs/spike/run_output.json` and in `docs/spike/run_get.json`. Billing names it `run.run_id` in `docs/spike/billing_usage.json`.

`play/hello-company/run/20261117t081507-848-56853e24-caller-861f90f9670f5684e9c9329c87f23ccccc4f988137d7433a4127a2942e911047`

## Where the status is

`run.status` in `docs/spike/run_output.json` and `docs/spike/run_get.json`. The value is `completed`.

`steps[0].status` is `unknown`. That is not the run status. `deepline runs get` also has `runStatus.focusStep.status`, and that value is `completed` for the `echo` step.

`run_output.json` has a notice whose text says the run is active. The status field still says `completed`.

## Where the returned object is

`result` in `docs/spike/run_output.json` and `docs/spike/run_get.json`.

```json
{
  "echo": {
    "checked_at": "2026-11-17T08:15:14.856Z",
    "domain": "example.com"
  },
  "ok": true
}
```

`resultState` is `available`. `datasets` is `[]`. This spike did not return rows.

`diagnostics.result` is a different object. It has `_metadata` beside `ok` and `echo`. `diagnostics.outputs.echo.value` and `diagnostics.outputs.ok.value` are the two fields split apart.

## What billing usage said

From `docs/spike/billing_usage.json`, `run.spent_credits` is 0, `run.rough_usd_spent` is 0, and `run.event_count` is 1.

`recent.entries` has one event. `provider` is `compute`, `credits` is 0, `charge_state` is `free`, and `charge_finality` is `final`.

`docs/spike/run_get.json` field `credits.kind` is `none`. The `plays run` file has no top-level `credits` field.

`diagnostics.billing` inside the run overview says `totalCredits` 0 and `computeEvents` 0. That event count does not match the one billing event above. The spend line uses `billing usage` `run.spent_credits`.

## Q1

`deepline plays run --json --full` wrote one JSON object. `kind` is `run_overview` and `schemaVersion` is 1.

- Run id: `run.id`
- Status: `run.status`
- Returned object: `result`

The CLI help text does not name `result`. `--full` includes it. Spec Q1 should record these three paths. It should not treat `steps[0].status` or the notice text as the run status, and it should not treat `diagnostics.result` as the returned object.

## Q2

`deepline plays check`, `deepline plays run --dry-run`, and the real `deepline plays run` all finished in Windows PowerShell with exit code 0.

`--run-id-file` also wrote `docs/spike/run_id.json.submission.json`. That file is the bundle the CLI uploaded, not the result. It is not kept.

PowerShell `>` on this laptop writes UTF-16 LE. `docs/spike/run_output.json` started with the bytes `FF FE`. Fix: read that file as Unicode and write it back as UTF-8 with no byte-order mark. The later `runs get` and `billing usage` files were written the same way, with .NET `UTF8Encoding` and no mark, instead of `>`.

This task did not reinstall the CLI, so it does not answer whether a fresh install needs `--allow-scripts=esbuild`.

## What the spec should change

- F5 says `plays check --json` includes `outputSchema`. On 0.3.537 that key was absent. The payload had `valid`, `inputSchema`, and `recognized.outputs` (`ok` and `echo`, with no nested fields). The help text still lists `outputSchema`.
- Q1 should record `run.id`, `run.status`, and `result`, from the files above.
- The spec's checked CLI version is 0.3.535. This run used 0.3.537.

## Task 1.5 — champion-tracker on two companies

Written from `docs/spike/play_run_output.json`, `docs/spike/play_billing_usage.json`, and `docs/spike/play_receipts.json`. The workspace display name in `command_context.active_organization.org_name` was replaced with `removed` before commit. Run ids are unchanged.

### Where the rows are

`result.rows` in `docs/spike/play_run_output.json`. There are 2 rows. `resultState` is `available`. `datasets` is `[]`.

`run.status` is `completed`. The run id is `run.id`. The same id is `runId` in `docs/spike/play_run_id.json` and `run.run_id` in `docs/spike/play_billing_usage.json`.

`play/champion-tracker/run/20261117t105954-708-32e63239-caller-d74d48a6682a88a979ff4c5d5dceea2cd705eac4d0150a4ae1d579e73d16ea6e`

### What the company tool returned

Tool id `leadmagic_search_companies`. The Play's rows do not keep the provider object. The field names are in the receipt log, `docs/spike/play_receipts.json`. That log repeats each receipt. There are two job ids:

- `shopify.com`: `ctx-tool-57039683a8a91df8e7f6a13eb5635666`
- `asana.com`: `ctx-tool-ce3960eced80a99744b034e88d183213`

On the company row, the employee field is `linkedin_employee_count` and the country field is `hq_country_code`. Those are the names in `docs/tools.md`. `plays/rules.ts` was not changed.

| domain | linkedin_employee_count | hq_country_code |
|---|---|---|
| asana.com | 4400 | US |
| shopify.com | 29663 | CA |

The receipt stores that row at `toolResponse.rawV2.companies` and in `listDatasets.companies.preview`. `listDatasets.companies.sourceLabel` is `toolResponse.raw.companies`. `listExtractorPaths` is `result.data.companies`.

The Play does not read the receipt. It reads `fields.companies.values` on the `deepline.tools.execute` result, then `linkedin_employee_count` and `hq_country_code`. That path worked. `result.rows` has the same employees and country codes as the table above.

Also on the row, and not used by the rules: `hq_country` is the full name (`United States`, `Canada`). `employee_min`, `employee_max`, and `employee_range` are a bucket. For Shopify, `employee_max` is 0 and `employee_range` is `10001+`, while `linkedin_employee_count` is 29663.

### Two lookups

`run.work.providerRequests` in `play_run_output.json` is 2. `diagnostics.progress` says `executed` 2 and `reused` 0.

`play_billing_usage.json` field `run.spent_credits` is 0.3. `run.rough_usd_spent` is 0.03. `run.event_count` is 3. `recent.entries` has 2 events, and `recent.total` is 2.

The leadmagic event is one line: `credits` 0.3, `batch_count` 2, `pricing_model` `per_result`, `charge_state` `posted`. `metadata.chargeGroupIds` lists both job ids above. Each receipt's `billing.credits_charged` is 0.15. The compute event is `credits` 0 and `charge_state` `free`.

That is two lookups posted as one reconciled line of 0.3. The rows do not match: Asana is 4400 people in US, Shopify is 29663 people in CA.

`diagnostics.billing` inside the run overview says `totalCredits` 0. The spend line uses `billing usage` `run.spent_credits`.

### What the rows decided

`l01` Asana: `alert` true, `reason` `icp_fit`, `company.employees` 4400, `company.country` US.

`l02` Shopify: `alert` false, `reason` `company_too_big`, `company.employees` 29663, `company.country` CA.

The mock emails were copied onto the rows. No email tool ran.

### PowerShell

`>` wrote UTF-16 LE. `docs/spike/play_run_output.json` started with the bytes `FF FE`. It was read as Unicode and written back as UTF-8 with no byte-order mark. Billing and the receipt log were written with .NET `UTF8Encoding` and no mark, instead of `>`.

`--run-id-file` also wrote `docs/spike/play_run_id.json.submission.json`. That file is the uploaded bundle, not the result. It is not kept.
