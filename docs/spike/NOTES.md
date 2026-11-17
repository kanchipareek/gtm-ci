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
