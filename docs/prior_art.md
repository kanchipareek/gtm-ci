# Prior art check for gtm-ci

Checked on 17 Nov 2026 (IST). Sources: GitHub repo search and code search, Deepline docs and skills pages, n8n docs, Clay blog, X search, general web search.
Star counts and dates are from the GitHub API on that day. Most repos below have 0 to 3 stars, so none of them is famous. That matters: the idea is out there, but no widely used public project owns this exact shape yet.

## Short verdict

Nobody has built exactly this: a Deepline Play, gated on every pull request, against a public labelled set of job-change traps, with a before and after table and a 0 credit offline gate.

But the general idea is NOT new, and the README and post must not pretend it is:

1. "Golden set plus a CI gate that fails when a sales or GTM task gets worse" already exists in at least 4 small public repos (gtm-evals, prospectr, gtm-agent-testing, ai-workflow-regression-gate).
2. Deepline itself already documents the method. Its own `deepline-plays-improve` / `deepline-plays-review` skill describes golden datasets, frozen evaluation, deterministic graders and "regressions relative to the current accepted run". What it does not have is an automatic pull request gate. It runs live (spends credits), uses Google Sheets for review, is agent-supervised, and says its eval tabs are a "planned extension".
3. Clay publicly calls what its own GTM team does "GTM CI/CD". Their version is A/B tests, agent-proposed fixes and pull requests, not a labelled test set gate.
4. An open-source champion job-change tracker that already ignores advisor seats, board seats and same-company moves exists (Crustdata), with unit tests in CI.
5. Job-change benchmarks exist, but they score data vendors (is the new employer right?), not your own alert logic.

What is genuinely new (as far as I could find):
- Running the gate on a Deepline Play at all. Only 1 public GitHub workflow file mentions "deepline" (`crushed-taro/deepline`, which I did not open and is likely unrelated). Deepline's own Action only runs `deepline plays check`.
- A public, labelled set of job-change DECISION traps (advisor role, duplicate, intern, promotion, stale event, wrong size or country, parked domain), each linked to a real complaint.
- Gating on false alerts per trap type, with base vs head scored on the head's test set, and a rule that a pull request cannot edit its own answers.

## Closest findings

| # | What | Link | Stars / date | How close | What gtm-ci does that it doesn't |
|---|---|---|---|---|---|
| 1 | Deepline's own `deepline-plays-improve` / `deepline-plays-review` skill. Golden dataset format `case_id, split, input_*, expected_*`, deterministic graders, "regressions relative to the current accepted run", development and holdout splits. | https://deepline.com/skills/deepline-plays-review and https://skillbundle.dev/site/code.deepline.com/deepline-plays-improve | Deepline docs, read 17 Nov 2026 | Partial overlap. Same method, same product. | Automatic on every PR, fails the merge, posts a before and after table, 0 credit offline gate, public test set. Theirs is a manual, agent-run, live, Sheets-based loop, and its eval tab writer is "planned". |
| 2 | Deepline "Deploy with GitHub Actions" guide. PRs run `deepline plays check`, merge runs `deepline plays deploy`. | https://deepline.com/docs/sdk-v2/github-deployments | Deepline docs | Adjacent. This is the gap. | Checks output quality, not just that the code is valid. |
| 3 | usmanqamar19/gtm-evals. Prompt eval harness for 4 sales tasks (email intent, lead qualification, objection, MEDDIC), 40 hand-written examples each, offline mock model, CI job fails if accuracy drops below 0.85. | https://github.com/usmanqamar19/gtm-evals | 0 stars, created 4 Sep 2026 | Partial overlap. Closest in shape: golden set, offline, CI gate, GTM framing. | Not Deepline, not job changes, no enrichment, gates on a fixed accuracy number, not base vs head. No PR comment table. Scores LLM prompts, not a rules-plus-data workflow. |
| 4 | rohitguta2432/prospectr. Outbound agent (ICP score, email verify, pitch) with a 10-lead golden set with trap cases and a CI-style gate that exits non-zero. | https://github.com/rohitguta2432/prospectr | 0 stars, created 7 Jun 2026 | Partial overlap. | Not Deepline, no job changes, 10 cases, no before and after, no real failure sources. |
| 5 | derrtaderr/gtm-agent-testing. Evals for GTM agents: rules plus LLM rubric, golden "trajectories" replayed and diffed, GitHub Action that blocks on eval or regression. | https://github.com/derrtaderr/gtm-agent-testing | 0 stars, created 7 Sep 2026 | Partial overlap. | Focused on agent outputs like cold emails and "autonomy". No job-change data, no Deepline, no labelled trap set. |
| 6 | mhimed-crustdata/champion-job-change-tracker. Open-source champion tracker with Slack alerts. Rules already ignore advisor seats, board seats, angel investments and same-company moves, dedupes alerts. Unit tests in a GitHub workflow. | https://github.com/mhimed-crustdata/champion-job-change-tracker | 0 stars, created 18 Oct 2026 | Partial overlap on the Play itself. Also proves the advisor and promotion traps are known. | It has unit tests, not a scored labelled set, and no base vs head gate on false alerts. Not Deepline. |
| 7 | Clay, "In an agentic GTM era, sales plays will ship like software". Clay's GTM team runs what it calls "GTM CI/CD": versioned workflows, PRs, agent audits, A/B tests. | https://www.clay.com/blog/gtm-self-learning-loops | Clay blog, date not confirmed | Adjacent. Same thesis as Chirag's "treat gtm systems as software". | Clay's is internal and based on live reply rates. gtm-ci is a public, offline, labelled test gate anyone can fork. |
| 8 | n8n Evaluations. Built-in test datasets, Evaluation node, metrics, compare runs. | https://docs.n8n.io/build/integrate-ai/test-and-improve-ai-workflows/understand-why-to-test | n8n docs | Adjacent. A real product feature for workflow regression tests. | Runs inside the n8n UI, not as a PR gate. Not GTM-specific. |

## Other things found (less close)

- ohjeffkuston/ai-workflow-regression-gate. Baseline vs candidate fixtures for AI and n8n workflows, PASS / REVIEW / BLOCK, offline. 0 stars, Jul 2026. Generic, not GTM. https://github.com/ohjeffkuston/ai-workflow-regression-gate
- zarif3624/n8n-enterprise-workflows. Pull request CI replays changed policies against target-branch and current fixtures and summarizes deltas, including a sales lead routing workflow. Closest to the "base vs head" mechanic, but not job changes and not Deepline. https://github.com/zarif3624/n8n-enterprise-workflows
- divyanaras/gtm-agent-evals. LangGraph cold outreach agent with a LangSmith eval on 6 companies. 0 stars. https://github.com/divyanaras/gtm-agent-evals
- ShivaniSeth5/llm-lead-scorer. ICP lead scorer with a 10-lead frozen golden set. 0 stars. https://github.com/ShivaniSeth5/llm-lead-scorer
- amathziah/leadflow. Lead platform with deterministic ICP checks, 20 labelled cases (5 adversarial), CI workflow. https://github.com/amathziah/leadflow
- ShubhamGarje99/lead-qualifier-agent. Lead enrichment and scoring with 20 labelled synthetic leads. https://github.com/ShubhamGarje99/lead-qualifier-agent
- itsyusufahmed/gtm-models-eval. 243 companies with labels, 12-model judge panel for "is this really an AI company". https://github.com/itsyusufahmed/gtm-models-eval
- automatewithuday/agentic-outbound-plays. 5 outbound workflows on Deepline including champion job changes, spend caps, `--selftest`. No eval set, no CI workflow found. https://github.com/automatewithuday/agentic-outbound-plays
- getaero-io/gtm-eng-skills (81 stars). Appears to be Deepline's own org. Skills for enrichment, job change detection. Its `clay-to-deepline` skill mentions "parity validation". No PR eval gate found. https://github.com/getaero-io/gtm-eng-skills
- Generic eval-in-CI tools, none GTM-specific: DeepEval regression testing in CI (https://deepeval.com/guides/guides-regression-testing-in-cicd), ruchit07/llm-eval-runner GitHub Action (https://github.com/ruchit07/llm-eval-runner), promptfoo, Braintrust. A "golden set regression gate" is a named pattern (https://www.frontierengg.com/learn/patterns/evaluation-feedback/golden-set-regression-gate).

## Public job-change datasets and benchmarks

These exist, but they test vendors' data accuracy, not your alert rules:
- B2BDataBenchmarks live profile benchmark. 250 real people who changed jobs, graded against employer announcements, set v2026-11-03.1. https://www.b2bdatabenchmarks.com/benchmarks/live
- Theokovalev/revenuebench. Kit to score contact-data vendors on your own labelled CSV, including a `still` job (left vs stayed). 3 stars. https://github.com/Theokovalev/revenuebench
- Champions blog, "Job Change Data Accuracy: How to Test a Vendor". Recommends a frozen set of 25 to 50 confirmed moves, precision first because false alerts waste rep time. Vendor content. https://getchampions.io/blog/job-change-data-accuracy/
- getaob.com job change tools roundup. Suggests "keep the list as a standing regression set". Vendor-ish content. https://getaob.com/job-change-tracking-tools

I found no public labelled set of job-change decision traps (advisor seat, promotion, duplicate, intern and so on) with expected alert / no-alert answers.

## Not found / limits of this check

- X search found no post of anyone shipping evals or CI for a Deepline Play. Closest was a how-to on building a champion tracker from a warehouse (@henryhund, 21 Oct 2026, 293 likes): https://x.com/henryhund/status/2112929408080400587
- No Product Hunt or Hacker News launch of "tests for GTM workflows" turned up in web search. I did not browse those sites directly.
- GitHub code search only covers default branches of public repos. Private company repos (where this might already exist internally) can't be checked.
- The GitHub connector returned only the first result per query, so I used the public search API for lists. A few searches hit rate limits and were not retried.

## Positioning so it stays non-generic

1. Do not say "nobody tests GTM automations" or "first CI for GTM". It is false (see above) and a founder will know.
2. Say this instead: "Deepline's docs already describe golden-set evals for Plays. They run by hand, live, in a Sheet. I made that same method automatic in pull request CI: every pull request is scored on a labelled set of job-change traps, offline for 0 credits, and blocked if false alerts go up, if false alerts go up for any trap type, or if any single case flips from pass to fail."
3. The fixtures now use Deepline's own golden-set columns: `case_id`, `split` (development / holdout), `input_*`, `expected_*`, `grading_notes`, `notes`, plus a scorer-only `trap` field. That reads as the missing CI half of their own loop, not a rival tool.
4. Make the trap set the headline asset. A public labelled set of job-change decision traps, each linked to a real complaint, is the part I could not find already published.
5. Gate on a pass-to-fail flip for any single case and on per-trap false alerts, not just the total. That is a detail the other public repos above do not do.
6. Credit `mhimed-crustdata/champion-job-change-tracker` in the README for the advisor-seat rule idea. Honest credit makes the rest more believable.
