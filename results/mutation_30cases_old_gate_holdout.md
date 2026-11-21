## Mutation score

Fixtures: `fixtures/events.jsonl`. Each mutation is one edit to `plays/rules.ts`. Caught means the offline gate would have blocked the pull request.

| split | caught | applied | not applied |
| --- | --- | --- | --- |
| discovery | 0 | 0 | 0 |
| holdout | 10 | 19 | 0 |
| all | 10 | 19 | 0 |

| id | split | mutation | outcome | cases that moved |
| --- | --- | --- | --- | --- |
| h01 | holdout | min employees loosened to 45 | caught | e13 no alert (company_too_small) -> alert (icp_fit) |
| h02 | holdout | max employees doubled | survived | none |
| h03 | holdout | Australia added to allowed countries | survived | none |
| h04 | holdout | CA dropped from allowed countries | caught | e05 alert (icp_fit) -> no alert (wrong_country), e09 alert (icp_fit) -> no alert (wrong_country) |
| h05 | holdout | event age window 150 days | caught | e28 no alert (stale_event) -> alert (icp_fit) |
| h06 | holdout | working student dropped from junior words | survived | none |
| h07 | holdout | student dropped from junior words | survived | none |
| h08 | holdout | head of dropped from senior words | caught | e02 alert (icp_fit) -> no alert (ambiguous_title), e07 alert (icp_fit) -> no alert (ambiguous_title), e10 alert (icp_fit) -> no alert (ambiguous_title), e15 no alert (wrong_country) -> no alert (ambiguous_title), e30 alert (icp_fit) -> no alert (ambiguous_title) |
| h09 | holdout | growth dropped from function words | caught | e02 alert (icp_fit) -> no alert (ambiguous_title), e11 alert (icp_fit) -> no alert (ambiguous_title), e12 no alert (duplicate_person) -> no alert (ambiguous_title) |
| h10 | holdout | operations dropped from function words | survived | none |
| h11 | holdout | yahoo dropped from free-mail domains | survived | none |
| h12 | holdout | cro no longer senior on its own | survived | none |
| h13 | holdout | min employees boundary flipped to exclusive | caught | e03 alert (icp_fit) -> no alert (company_too_small) |
| h14 | holdout | max employees boundary flipped to exclusive | caught | e04 alert (icp_fit) -> no alert (company_too_big) |
| h15 | holdout | event age boundary flipped to exclusive | caught | e08 alert (icp_fit) -> no alert (stale_event) |
| h16 | holdout | same-company check never fires | caught | e25 no alert (same_company) -> alert (icp_fit) |
| h17 | holdout | country read from the event hint, not the company | survived | none |
| h18 | holdout | junior check skipped | caught | e21 no alert (junior_title) -> alert (icp_fit), e22 no alert (junior_title) -> alert (icp_fit) |
| h19 | holdout | null employee count not treated as not found | survived | e17 no alert (company_not_found) -> no alert (company_too_small) |
