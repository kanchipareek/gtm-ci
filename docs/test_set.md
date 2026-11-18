# Test set

The accepted golden set is `fixtures/events.jsonl`. `fixtures/events.csv` is the same 30 rows in Sheet shape. The owner reviewed `data/fixtures_draft.jsonl` on 18 Nov 2026 and accepted every `expected_alert`, `expected_reason`, `trap`, and the 20/10 split. Those labels were written by reading spec section 5.B. They were not produced by running `plays/rules.ts`, and the offline runner was not run on this file when it was copied in.

The `DRAFT.` prefix is gone from `notes`, because spec 5.C says that prefix lasts only until the set is accepted. The answers themselves are the draft answers.

Calls the owner confirmed:

- e16, a blank company country, is `wrong_country`.
- 50 employees (e03), 5000 employees (e04), and 120 days (e08) still alert.
- 121 days (e28) does not.
- e30, "Head of Internal Sales", is senior, so it alerts.
- e26, "Advisor" at a 4-person company, is `ambiguous_title`.

This is a small hand-made set. It shows the method. It does not prove the tracker is accurate on real data. The Play runner never reads `expected_*`, `grading_notes`, `notes`, `trap`, or `split`. e11 and e12 share person `p11`, both sit in development, and e11 comes first. The duplicate reason only holds when those two are scored in one run in that order.

## Cases

| case_id | split | trap | what it tests | expected_alert | expected_reason |
| --- | --- | --- | --- | --- | --- |
| e01 | development | clean_alert | Champion, senior revenue title, 300 people, US, 32 days | true | icp_fit |
| e02 | holdout | clean_alert | Champion, "Head of Growth", 1200 people, US | true | icp_fit |
| e03 | development | boundary_exactly_50 | Exactly 50 employees, the minimum, still inside | true | icp_fit |
| e04 | holdout | boundary_exactly_5000 | Exactly 5000 employees, the maximum, still inside | true | icp_fit |
| e05 | development | clean_alert_canada | "Chief Revenue Officer", Canada is allowed | true | icp_fit |
| e06 | development | email_not_found_still_alerts | No email found. Email is not part of the decision | true | icp_fit |
| e07 | development | email_risky_catch_all | Email status is risky. Still an ICP fit | true | icp_fit |
| e08 | holdout | boundary_exactly_120_days | Start date exactly 120 days before the event | true | icp_fit |
| e09 | development | clean_alert_gtm | "Senior Director, GTM Operations", 95 people, Canada | true | icp_fit |
| e10 | development | clean_alert | Champion, "Head of Marketing", 2600 people, US | true | icp_fit |
| e11 | development | duplicate_first_seen | First row for person p11. Must run before e12 | true | icp_fit |
| e12 | development | duplicate_person | Same person as e11, already alerted in this run | false | duplicate_person |
| e13 | holdout | too_small_49 | 49 employees, one under the line | false | company_too_small |
| e14 | development | too_big | 12000 employees, over the maximum | false | company_too_big |
| e15 | development | wrong_country | Company country DE, not US, CA, or GB | false | wrong_country |
| e16 | development | missing_country | Company country is blank. Not in the allowed list | false | wrong_country |
| e17 | development | company_not_found_dead_domain | Domain is present, company snapshot is null | false | company_not_found |
| e18 | development | fake_title_ninja | "Revenue Ninja": function word, no senior word | false | ambiguous_title |
| e19 | holdout | fake_title_growth_hacker | "Growth Hacker in Residence": function word, no senior word | false | ambiguous_title |
| e20 | development | fake_title_head_of_vibes | "Head of Vibes": senior word, no function word | false | ambiguous_title |
| e21 | development | intern | "Sales Intern" | false | junior_title |
| e22 | holdout | working_student | "Working Student, Sales Ops". Junior is checked first | false | junior_title |
| e23 | development | freelancer_no_domain | Empty domain. Nothing to look up | false | missing_domain |
| e24 | holdout | free_mail_domain | Only domain is gmail.com. No email is stored | false | missing_domain |
| e25 | development | promotion_same_company | Title change inside the same company | false | same_company |
| e26 | holdout | advisor_side_role | "Advisor" at a 4-person company. Title is checked first | false | ambiguous_title |
| e27 | development | stale_200_days | Started 200 days before the event | false | stale_event |
| e28 | holdout | stale_121_days | 121 days, one over the line | false | stale_event |
| e29 | development | not_a_champion | Never a champion. Everything else would fit | false | not_champion |
| e30 | holdout | word_match_trap_internal | "Head of Internal Sales". "Internal" is not "intern" | true | icp_fit |

## Counts by reason

The order is the check order in spec 5.B. `icp_fit` is the alert that remains when every check passes.

| reason | count | development | holdout | case_ids |
| --- | --- | --- | --- | --- |
| not_champion | 1 | 1 | 0 | e29 |
| missing_domain | 2 | 1 | 1 | e23, e24 |
| same_company | 1 | 1 | 0 | e25 |
| duplicate_person | 1 | 1 | 0 | e12 |
| stale_event | 2 | 1 | 1 | e27, e28 |
| junior_title | 2 | 1 | 1 | e21, e22 |
| ambiguous_title | 4 | 2 | 2 | e18, e19, e20, e26 |
| company_not_found | 1 | 1 | 0 | e17 |
| company_too_small | 1 | 0 | 1 | e13 |
| company_too_big | 1 | 1 | 0 | e14 |
| wrong_country | 2 | 2 | 0 | e15, e16 |
| icp_fit | 12 | 8 | 4 | e01, e02, e03, e04, e05, e06, e07, e08, e09, e10, e11, e30 |
| total | 30 | 20 | 10 | e01 to e30 |

## Counts by split

The runner scores all 30 in one pass. `split` is for reporting, and later for tuning on development and accepting on holdout.

| split | cases | should alert | should not alert |
| --- | --- | --- | --- |
| development | 20 | 8 | 12 |
| holdout | 10 | 4 | 6 |
| all | 30 | 12 | 18 |

Holdout is e02, e04, e08, e13, e19, e22, e24, e26, e28, e30. Development is the other 20, including the e11 and e12 pair.
