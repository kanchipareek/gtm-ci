## Mutation score

Fixtures: `fixtures/events.jsonl`. Each mutation is one edit to `plays/rules.ts`. Caught means the offline gate would have blocked the pull request.

| split | caught | applied | not applied |
| --- | --- | --- | --- |
| discovery | 18 | 25 | 0 |
| holdout | 0 | 0 | 0 |
| all | 18 | 25 | 0 |

| id | split | mutation | outcome | cases that moved |
| --- | --- | --- | --- | --- |
| m01 | discovery | min employees loosened to 1 | caught | e13 no alert (company_too_small) -> alert (icp_fit) |
| m02 | discovery | min employees off by one, looser | caught | e13 no alert (company_too_small) -> alert (icp_fit) |
| m03 | discovery | min employees off by one, stricter | caught | e03 alert (icp_fit) -> no alert (company_too_small) |
| m04 | discovery | max employees off by one, looser | survived | none |
| m05 | discovery | max employees off by one, stricter | caught | e04 alert (icp_fit) -> no alert (company_too_big) |
| m06 | discovery | max employees removed in practice | caught | e14 no alert (company_too_big) -> alert (icp_fit) |
| m07 | discovery | India added to allowed countries | survived | none |
| m08 | discovery | Germany added to allowed countries | caught | e15 no alert (wrong_country) -> alert (icp_fit) |
| m09 | discovery | GB dropped from allowed countries | caught | e04 alert (icp_fit) -> no alert (wrong_country), e07 alert (icp_fit) -> no alert (wrong_country), e30 alert (icp_fit) -> no alert (wrong_country) |
| m10 | discovery | event age off by one, looser | caught | e28 no alert (stale_event) -> alert (icp_fit) |
| m11 | discovery | event age off by one, stricter | caught | e08 alert (icp_fit) -> no alert (stale_event) |
| m12 | discovery | event age window a year | caught | e27 no alert (stale_event) -> alert (icp_fit), e28 no alert (stale_event) -> alert (icp_fit) |
| m13 | discovery | intern dropped from junior words | survived | e21 no alert (junior_title) -> no alert (ambiguous_title) |
| m14 | discovery | trainee dropped from junior words | survived | none |
| m15 | discovery | apprentice dropped from junior words | survived | none |
| m16 | discovery | director dropped from senior words | caught | e03 alert (icp_fit) -> no alert (ambiguous_title), e06 alert (icp_fit) -> no alert (ambiguous_title), e09 alert (icp_fit) -> no alert (ambiguous_title), e16 no alert (wrong_country) -> no alert (ambiguous_title) |
| m17 | discovery | chief dropped from senior words | caught | e05 alert (icp_fit) -> no alert (ambiguous_title) |
| m18 | discovery | vp dropped from senior words | caught | e01 alert (icp_fit) -> no alert (ambiguous_title), e04 alert (icp_fit) -> no alert (ambiguous_title), e08 alert (icp_fit) -> no alert (ambiguous_title), e11 alert (icp_fit) -> no alert (ambiguous_title), e12 no alert (duplicate_person) -> no alert (ambiguous_title), e13 no alert (company_too_small) -> no alert (ambiguous_title), e14 no alert (company_too_big) -> no alert (ambiguous_title), e17 no alert (company_not_found) -> no alert (ambiguous_title) |
| m19 | discovery | marketing dropped from function words | caught | e04 alert (icp_fit) -> no alert (ambiguous_title), e10 alert (icp_fit) -> no alert (ambiguous_title), e16 no alert (wrong_country) -> no alert (ambiguous_title) |
| m20 | discovery | revenue dropped from function words | caught | e05 alert (icp_fit) -> no alert (ambiguous_title) |
| m21 | discovery | gmail dropped from free-mail domains | survived | e24 no alert (missing_domain) -> no alert (company_not_found) |
| m22 | discovery | proton.me dropped from free-mail domains | survived | none |
| m23 | discovery | seniority word alone counts as senior | caught | e20 no alert (ambiguous_title) -> alert (icp_fit) |
| m24 | discovery | duplicate check never remembers anyone | caught | e12 no alert (duplicate_person) -> alert (icp_fit) |
| m25 | discovery | champion check skipped | caught | e29 no alert (not_champion) -> alert (icp_fit) |
