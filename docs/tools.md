# Tools

Checked on **Tue 17 Nov 2026** with `deepline` **0.3.537** (`deepline --version`). CI pins 0.3.535.

No tool was run. The commands were `deepline search`, `deepline describe`, and `deepline billing usage`. Prices and field names below are copied from `describe` output.

## Billing check

`deepline billing usage --json` before the searches, and again after every `search` and `describe` in this task:

| | before | after |
|---|---|---|
| balance | 25 | 25 |
| month spent | 0 | 0 |
| last 30 days | 0 | 0 |
| temporary holds | 0 | 0 |
| recent events | 1 | 1 |

The one recent event is still the hello-world spike's compute event, 0 credits. Search and describe added no event and spent no credits. `plan.usd_per_credit` was 0.1.

## Search

Command: `deepline search "company enrichment by domain employee count country"`

113 matches. The first 20:

| tool id | credits on the search line | what the summary says |
|---|---|---|
| prebuilt/company-to-info | 0.96/run (observed) | domain or name to headcount and headquarters |
| prebuilt/company-to-info-batch | 0.846/row (observed) | same, for a CSV |
| free_simple_company_search | 0 (free) | filter a free company corpus |
| peopledatalabs_enrich_company | 1/result | domain or name to headcount and location |
| enrich_company | 0.98/call | domain, name, or LinkedIn URL to size and headquarters |
| prebuilt/person-to-company-info | 0.328/run (observed) | a person, then their company |
| datagma_full_enrichment | usage-based | person or company |
| limadata_enrich_company | 0.28/call | domain or LinkedIn URL to headcount and locations |
| prebuilt/person-to-company-info-batch | 0.782/row (observed) | people CSV |
| free_company_bulk_lookup | 0 (free) | up to 1,000 companies by domain |
| crustdata_v3_company_enrich | variable | domain, name, or LinkedIn URL |
| apollo_company_search | 0.48/page | search, not one-company enrich |
| edges_salesnavigator_extract_employees_count | 0.42/result | headcount from a Sales Navigator URL |
| free_company_lookup | 0 (free) | one company by domain, LinkedIn URL, or exact name |
| peopledatalabs_bulk_organization_enrichment | 1/result | many domains |
| prebuilt/company-domain-to-linkedin-employees-harvestapi | 0.0334/row (observed) | lists employees |
| edges_linkedin_extract_company_employees_insights | 0.42/result | employee breakdown |
| aviato_company_search | 0.04/call | filtered company search |
| prebuilt/company-to-employees | 0.612/run (observed) | lists employees |
| hunter_companies_find | 0.3/result | account context from a domain |

A second search, `deepline search "domain -> company employee count and headquarters country"`, put `leadmagic_search_companies` on the list at 0.15/result. It was not in the first 20. That is the tool picked below. Its price in this file is from `describe`, not from the search line.

## Three tools, from describe

`describe <id> --json` folds nested fields. Where a field name came from `describe <id> --schema-only --json` or from `--json` nested `fields`, that is said below.

### free_company_lookup

- Tool id: `free_company_lookup`
- Credits: `Free`. `credentialStatus` is `managed`. No BYOK feature on this describe.
- Required input: none of the inputs is marked required. The schema says to pass exactly one of `domain`, `linkedin_url`, or `company_name`. The Play would pass `domain`.
- Employee field: `employee_count` (integer or null), inside `matches`.
- Country field: none. The location field is `location` (string or null), inside `matches`.
- Read path from `--json`: `result.fields.matches.values` (`toolResponse.raw.matches`).

`free_company_bulk_lookup` is the same corpus for many keys. Cost `Free`, `credentialStatus` `managed`, input `domains` (not required), output `results`. Same two columns: `employee_count` and `location`. No country field.

`free_simple_company_search` describes that corpus table. Its schema text says `location` is "comma-separated: locality, region, country" (example: `san francisco, california, united states`), and `employee_count` is the "upper bound of size bucket (10, 50, 200, 500, 1000, 5000, 10000+)". That is a full country name inside one string, and a bucket, not a count that can tell 49 from 50.

### limadata_enrich_company

- Tool id: `limadata_enrich_company`
- Credits: `0.28 Deepline credits / $0.028 per call (managed by Deepline)`. `credentialStatus` is `managed`. A BYOK feature is listed: "Run it on your own provider credentials."
- Required input: neither input is marked required. Pass `domain` or `linkedin_url`.
- Employee field, from `--schema-only --json`: `employees.employee_count` (integer or null).
- Country field, from `--schema-only --json`: `locations[].country` (string or null). The schema does not say whether that string is a code or a name.
- The short `--json` output only lists `company_domain`, `company_linkedin_url`, and `company_name`. The employee and country names are in the unfolded schema.

### leadmagic_search_companies

- Tool id: `leadmagic_search_companies`
- Credits: `0.15 Deepline credits / $0.015 per result (managed by Deepline)`. `credentialStatus` is `managed`. BYOK is optional.
- `describe leadmagic_search_companies --feature byok` says: connect your own LeadMagic credentials to run this tool on your LeadMagic account; without them, Deepline's managed LeadMagic access is used. That text does not give a second credit price.
- Required input: none is marked required. `company_domain` is described as the direct one-company lookup, and it "returns one rich company row" when no broad filters or explicit limit are supplied. `domain` is an alias for `company_domain`.
- Employee field, from `--json` `outputs.companies.fields`: `linkedin_employee_count` (integer). The same object also has `employee_min` (integer), `employee_max` (integer), and `employee_range` (string).
- Country field, from the same object: `hq_country_code` (string). Also `hq_country` (string) and `location_country_code` (string or null).
- Read path from `--json`: `result.fields.companies.values` (`toolResponse.raw.companies`).

Other describes, not picked: `peopledatalabs_enrich_company` lists `employee_count` and no country field, at 1 credit per result. `hunter_companies_find` and `enrich_company` do not name employee or country fields in the output schema. `aviato_company_search` has `country` (full country name) and no employee-count field, at 0.04 credits per call.

## Pick

`leadmagic_search_companies`.

It is the cheapest described tool that names both an employee count and a country code: 0.15 credits per result, fields `linkedin_employee_count` and `hq_country_code`.
The free lookup is 0 credits, but it has no country field, and the free corpus describes `employee_count` as a size-bucket upper bound.

The Play should read `linkedin_employee_count` and `hq_country_code`.

The first live call (task 1.5) returned those names. Samples are in `docs/spike/play_receipts.json`, and the same numbers are on `result.rows` in `docs/spike/play_run_output.json`:

| domain | linkedin_employee_count | hq_country_code | hq_country |
|---|---|---|---|
| asana.com | 4400 | US | United States |
| shopify.com | 29663 | CA | Canada |

`hq_country_code` is the short code. `hq_country` is the full name. Shopify's `employee_max` in that receipt is 0 and `employee_range` is `10001+`, while `linkedin_employee_count` is 29663. The size rule uses the count.

The Play reads the execute result at `fields.companies.values`, then those two fields. That path worked: the row employees and country match the table above. The receipt envelope is a different object. It stores the row at `toolResponse.rawV2.companies`, labels the list `toolResponse.raw.companies`, and lists an extractor path `result.data.companies`.

## Estimate

One described domain lookup returns one company row, so this estimate uses one result per company. Describe does not say what a miss costs. A miss is not counted as 0.

The live set is 5 companies, run about 5 times:

0.15 × 5 companies × 5 runs = 3.75 credits.

At $0.10 per credit that is $0.375.

This is company lookups only. It does not include email, Play compute, or a second call after a cache miss. One live run of 5 companies is 0.15 × 5 = 0.75 credits of lookups, under the cap of 10.

## Email finder (not enabled)

Not called.

Search: `deepline search "find work email from full name and company domain"`.

The cheapest name-plus-domain finder on that list was described:

- Tool id: `quickenrich_employee_email_enrich`
- Credits: `0.06 Deepline credits / $0.006 per result (managed by Deepline)`. `credentialStatus` is `managed`. BYOK is listed as optional.
- Inputs: `first_name`, `last_name`, and `company_url`, or else `linkedin_url`. None is marked required. The LinkedIn input says to provide that URL, or company URL plus first and last name.
- Output field for the address: `email`, read at `result.fields.email.value`.

Live email is not enabled in this repo. The id is recorded for when it is. Synthetic people are never sent to it.
