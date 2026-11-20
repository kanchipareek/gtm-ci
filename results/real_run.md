# real_run

- mode: live
- plays: plays
- git sha: 762a28020b3ca83590f0940d8e33dc1f41df012b
- date: 2026-11-20
- events: 10

| metric | value |
| --- | --- |
| correct alerts | 5 |
| false alerts | 0 |
| missed alerts | 0 |
| correct no alerts | 5 |
| emails found | 5 |
| credits | 1.2 |

By split. The gate uses the full set, which is the all row.

| split | correct alerts | false alerts | missed alerts | correct no alerts | emails found |
| --- | --- | --- | --- | --- | --- |
| development | 5 | 0 | 0 | 5 | 5 |
| holdout | 0 | 0 | 0 | 0 | 0 |
| all | 5 | 0 | 0 | 5 | 5 |

wrong reason (shown, not gated): 0
false alert case ids: none
missed alert case ids: none
join errors: missing 0, duplicate 0, extra 0

LeadMagic snapshots. Stand-ins were not sent. Rules were not changed.

| case_id | employees | country | reason | expected reason |
| --- | --- | --- | --- | --- |
| r01 | 727 | US | icp_fit | icp_fit |
| r02 | 766 | US | icp_fit | icp_fit |
| r03 | 597 | US | icp_fit | icp_fit |
| r04 | 239 | US | icp_fit | icp_fit |
| r05 | 305 | US | icp_fit | icp_fit |
| r06 | 22 | US | company_too_small | company_too_small |
| r07 | 453 | IL | wrong_country | wrong_country |
| r08 | 697862 | IE | company_too_big | company_too_big |
| r09 |  |  | ambiguous_title | ambiguous_title |
| r10 |  |  | same_company | same_company |

Disagreeing snapshots: none

run id: play/champion-tracker/run/20261120t134154-056-fa345bd1-caller-7d749c8cae455b7f77261b7c49d4bc64a0f9f41bd9d6157aa6e448d29bb70705
