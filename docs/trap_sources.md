# Trap sources: why each case is in the test set

Collected 17 Nov 2026.

Every quote below was read on the page linked, except where it says "search excerpt". Quotes are copied as written. Nothing is made up. If a trap has no real source, it says "no source found".

## How to read this

- **Complaint** means a real user or practitioner describing a problem they hit.
- **Vendor** means the company selling a tool (or a blog selling one). Useful, but they have a reason to talk up the problem. Label it that way if you quote it.
- The fixture file links to these by id (S01, S02, ...).

## The ICP rule the answers follow

This is `plays/rules.ts`. Checked in this order. The first one that fails is the reason.

1. Was a champion (`not_champion`)
2. Has a real company domain, not empty and not free mail like gmail.com (`missing_domain`)
3. Actually moved to a different company, not a title change at the same one (`same_company`)
4. Not already alerted in this run (`duplicate_person`)
5. Started 120 days or less before the event (`stale_event`)
6. Title is not junior: intern, student, trainee, apprentice, working student (`junior_title`)
7. Title is senior AND has a function word: needs one of vp, vice president, head of, director, chief, cro, revops lead, plus one of revenue, sales, growth, gtm, operations, marketing (`ambiguous_title`)
8. Company lookup found the company (`company_not_found`)
9. 50 people or more (`company_too_small`)
10. 5000 people or fewer (`company_too_big`)
11. Country is US, CA or GB (`wrong_country`)
12. Otherwise alert (`icp_fit`)

Two calls the rules make: a missing country counts as `wrong_country`, and word checks match whole words only (so "Internal" is not "intern").

## Sources

| id | Who | Where | Date | Type |
|---|---|---|---|---|
| S01 | Henry Schuck (@HenryLSchuck), ZoomInfo CEO | [X post](https://x.com/HenryLSchuck/status/2118390999646916613) | 5 Nov 2026 | Vendor (CEO pitching his own product) |
| S02 | "Josh M." and "Matt A.", G2 reviewers, quoted by UserGems | [UserGems blog](https://www.usergems.com/blog/usergems-reviews) | Published 9 May 2023, updated 16 Mar 2026 | Complaint, hosted by the vendor |
| S03 | Andrew McGuire (@andrewcmcguire), GTM Engineering at Navan | [X post](https://x.com/andrewcmcguire/status/2111427043254526380) | 17 Oct 2026 | Practitioner (job post) |
| S04 | Ankith H. | [Clay community](https://community.clay.com/x/general/msg_sfYLgmouwmO9/linkedin-role-updates-causing-false-job-change-sig) | 26 May 2026 | Complaint (he also sells a fix) |
| S05 | Justin R., reply in a Clay community thread | [Clay community](https://community.clay.com/x/general/msg_oYYhFhEIluWk/understanding-job-monitor-feature-in-clay-for-cust) | Thread 21 May 2025, reply date not shown | Complaint (he also offers to build it) |
| S06 | UserGems help center | [Why was a specific Job Change not found?](https://help.usergems.com/article/why-was-a-specific-job-change-not-found) | Not shown | Vendor |
| S07 | Zackrag | [dev.to test of 200 contacts](https://dev.to/zackrag/job-change-signals-tested-i-tracked-200-contacts-across-linkedin-apollo-cognism-and-clay--1m59) | 27 Aug, year not shown (text mentions early 2026) | Practitioner test. Ends by naming a tool, so may be partly promo |
| S08 | GTM Engineering Academy | [Signal-based outbound guide](https://gtmengineeracademy.com/topics/signal-based-outbound/) | Not shown | Practitioner guide |
| S09 | Verified G2 reviewer, mid-market | [G2 UserGems reviews](https://www.g2.com/products/usergems/reviews) | 1 Oct 2026 | Complaint |
| S10 | G2 reviewer ("Champion Tracking + Salesforce Integration...") | [G2 UserGems reviews](https://www.g2.com/products/usergems/reviews) | 17 Jun 2026 | Complaint |
| S11 | "Matt A.", G2 reviewer, quoted by UserGems | [UserGems blog](https://www.usergems.com/blog/usergems-reviews) | As S02 | Complaint, hosted by the vendor |
| S12 | Matthew T., mid-market, G2 | [G2 Champify reviews](https://www.g2.com/products/champify/reviews) | Not shown on page | Complaint |
| S13 | G2 reviewer | [G2 Champify reviews](https://www.g2.com/products/champify/reviews) | 5 May 2026 | Complaint |
| S14 | Verified user (incentivized review) | [TrustRadius Champify vs UserGems](https://www.trustradius.com/compare-products/champify-vs-usergems) | Not shown | Complaint |
| S15 | u/smarkman19, r/SaaS | [Reddit thread](https://www.reddit.com/r/SaaS/comments/1s3z1z1/usergems_alternative_that_wont_cost_30k/) | 26 Mar 2026 | Complaint. **Search excerpt**: the thread page loaded but Reddit did not show the comments to me. Not verified on the page |
| S16 | Aly H. | [Clay community](https://community.clay.com/x/content-and-events/msg_35tcOKa9milS/ensuring-website-accessibility-for-accurate-compan) | 22 Nov 2024 | Complaint |
| S17 | SimpleVerifier team | [Blog](https://simpleverifier.com/blog/gmail-signups-b2b-saas) | 2 Nov 2026 | Vendor |
| S18 | Reddit user (name not shown to me), r/Coldemailing | [Reddit post](https://www.reddit.com/r/Coldemailing/comments/1vfepjs/how_do_you_get_emails_that_dont_bounce_everything/) | About 3 months ago (page said "3mo ago") | Complaint |
| S19 | Siddhesh Sawant's n8n template, written up by GTM Agent Weekly | [Use case page](https://gtmagentweekly.com/use-cases/champion-job-changes-from-bounces-apollo-slack/) | Not shown (their X post about it was 6 Nov 2026) | Practitioner template |
| S20 | UserGems | [UserGems vs Sales Navigator](https://www.usergems.com/usergems-vs-linkedin-sales-navigator) | Not shown | Vendor (competitor claims) |
| S21 | Andreas W., Clay community | [Clay community](https://community.clay.com/x/general/msg_25My2Ma0CzxA/mapping-job-titles-to-seniority-levels-pre-clay-me) | 6 Oct 2024 | Practitioner question |

## Traps and their sources

### T01 Not really a champion (`not_champion`), 3 sources
- S01: "Working at a customer doesn't make them a champion. Did they advocate for us internally? Did they love the product? Were they frustrated with us?"
- S02 (Josh M.): "you might reach out to someone tagged as a former customer who was part of an entirely different team, it's not perfect!"
- S03: "Same person? Did they use and influence the product? Is the new account worth working?"
- Events: e29

### T02 No usable company domain: freelancer or free mail (`missing_domain`), 3 sources
- S06 lists "The new job is self-employed" as a case UserGems skips.
- S19: "board, advisor and freelance roles do not count as moves"
- S17 (vendor): "A personal address has no company behind its domain, so domain enrichment has nothing to work with."
- Events: e23 (self-employed, empty domain), e24 (gmail.com)

### T03 Never actually left: promotion or side role at the same company (`same_company`), 2 complaints
- S04: "Someone adds: - an advisor role - a board position - a fractional role - a side startup..etc and suddenly they get flagged as a “job change” But they never actually left your target company."
- S05: "It will indicate changes if the person has things in their Linkedin profile like volunteer work, advisory or consulting work in addition to the current job/company on record."
- Note: I found no complaint that says word for word "a promotion was counted as a job change". The same-company promotion case (e25) rests on S04 and S05 ("never actually left").
- Events: e25

### T04 Same person twice (`duplicate_person`), 4 sources
- S07: "I ended up with duplicate records on 11 of the 47 job changes I tracked."
- S08: "No dedup across signals. One account can trip three triggers in a week. Contact once, with the strongest angle, or you look like the spam you are trying to beat."
- S03: "Same person? ... Hold uncertain matches."
- S06 lists "The person has 2 profiles".
- Events: e11 (first, alerts), e12 (repeat, no alert)

### T05 Old news (`stale_event`), 4 sources
- S08: "Stale events. A new hire who started 8 months ago is not a signal. Filter on event date, not discovery date"
- S07: "Apollo: 12–35 days in most cases; occasional outliers at 60+ days" and "Contacts reached after day 21? 9% reply rate."
- S10: "The job-change data is reliable but sometimes lags by a few weeks, and the new company or title can be slightly off"
- S11 (Matt A.): "Most data is super prompt, but some data lags a few months or longer, or never appears."
- Events: e27 (200 days), e28 (121 days), e08 (exactly 120, still fresh)

### T06 Junior title: intern or student (`junior_title`), no direct complaint found
- Only a weak mention. S17 (vendor) lists people with personal emails, including "Students, job seekers and the curious. Real people, not buyers." That is about signups, not job changes.
- I searched X, Reddit, G2 and the Clay community. No one complained about a tracker alerting on an intern. It stays as a design case, not a sourced one.
- Events: e21, e22

### T07 Vague or fake title (`ambiguous_title`), partly sourced
- S15 (search excerpt): "rate limits, captchas, mismatched titles, people with multiple roles, and a bunch of false positives made it noisy enough that sales just ignored it."
- S21: "I’d love to know how they handled (or are mostly handling) the many outliers and variations without LLMs"
- Fake titles like "Revenue Ninja" or "Head of Vibes": **no source found** for a tracker alerting on one. The titles are made up for the test.
- Events: e18, e19, e20

### T08 Side advisor role (`ambiguous_title` under current rules), 4 sources
- S04 (above), S05 (above).
- S19: "board, advisor and freelance roles do not count as moves"
- S20 (vendor): "UserGems also filters out irrelevant job titles and job changes, such as: advisor, investor, member of hobby/interest groups, merger & acquisitions, etc."
- Events: e26

### T09 Company can't be found, or the site is dead (`company_not_found`), 2 sources
- S06: "our system was not able to verify that her newest company ("T-Mobile USA") is a real company, since it was not linked to the LinkedIn company page."
- S16: "I get replies that say "this website doesn't even exist anymore" or "I shut down that business a million years ago" sort of thing."
- Events: e17

### T10 Company too small (`company_too_small`), 1 direct source
- S09: "The least helpful part is that not every lead fits our ICP. When a past champion moves to a company that's too small, in the wrong industry, or without budget, we still have to filter those out before the team spends time on them."
- S10 also says "not all of them fit our ICP".
- Events: e13 (49), e03 (exactly 50, alerts)

### T11 Company too big (`company_too_big`), no source found
- Events: e14, e04 (exactly 5000, alerts)

### T12 Wrong or missing country (`wrong_country`), 1 direct source
- S12: "Sometimes a new person joining a company does not equal a warm lead especially when they are not in region"
- Missing country in the data: no source found. It is a design case.
- Events: e15 (DE), e16 (no country)

### T13 Email not found or risky, but the alert still fires (`icp_fit`), 2 sources
- S18: "the person left, the domain changed, the inbox is dead. my last batch bounced at 14%"
- S19: "a "not found" lookup is not treated as evidence of a move."
- Events: e06 (not found), e07 (risky catch-all)

### T14 General false alarms (background, not one trap)
- S14: "There were more missing job changes and false positives in UserGems, in my experience."
- S13: "Sometimes the data is inaccurate or incorrect."
- S20 (vendor, competitor claim): "from a pool of 9,000 folks, LinkedIn Sales Navigator gives you 1000+ false alarms" (the number is UserGems' own claim, not a neutral test)

## Traps found in the wild that the current rules CANNOT catch

These are real, sourced problems. They are not in the test set, because the current rules cannot decide them.

1. **Acquisition or subsidiary rename.** The champion never moved, the company was bought or renamed. Sources: S01 ("Does it exist under a different name in Salesforce? Was it acquired?"), S05 ("It also gets confused by M&A or subsidiaries."), S06 ("it's a subsidiary name that we didnt know about, there was an acquisition"), S20. The event only has company names, not an old domain, so the rules can't tell.
2. **Fractional title.** "Fractional VP Revenue Operations" has vp plus revenue, so the rules would alert. Sources: S04 ("a fractional role"), S19. A one-word rule ("fractional", "advisor", "board") would fix it.

Both are good candidates for a new rule: add it, add the case, and the gate shows the false alert going away.

## Searched, nothing usable

- X searches on job change false alerts, duplicates, interns, fake titles and Sales Navigator alerts returned mostly unrelated posts.
- Deepline Monitors, Common Room, Warmly: no complaints found about job-change accuracy.
- Reddit comment threads mostly did not load for me (only the post text). r/coldemail is banned, so that thread could not be read.
