## Context

Phase 2 of PROJECT.md §6. Phase 1 delivered schema version 1, the UTC connection helper and the
Phase 2–7 acceptance table. No provider has been called and no database file exists.

The Phase 2 grilling ran one round on 2026-10-12:
- An informed-answerer subagent researched 13 questions and found 7 more.
- The main agent re-checked its sources: DuckDB probes, Microsoft's API page and API terms, and
  PyPI.
- The owner accepted every recommendation ("Recommended for all is fine"). The decision list
  below records who decided each item.

Measured facts this design relies on (2026-10-12, DuckDB 1.5.6, re-run by the main agent):
- Once a `raw_response` row references a `collection_run` row, any UPDATE of that run fails:
  "Violates foreign key constraint because key … is still referenced". A control table with
  the same keys updates fine. Adding the two-column CHECK at `001_initial.sql:30`, which
  includes the key column `source`, reproduces the failure.
- These all fail:
  - `ALTER TABLE … ADD COLUMN … CHECK` ("Adding columns with constraints not yet supported");
  - `ADD CONSTRAINT` ("No support for that ALTER TABLE option yet");
  - dropping a referenced table.
- A new table with foreign keys into version-1 tables can be created.
- Facts from Microsoft's Retail Prices page (updated 2026-01-06):
  - `api-version=2023-01-01-preview` is the only version with savings-plan prices, and its
    filter values are case-sensitive.
  - `meterRegion='primary'` limits results to primary meters, and is supported from 2021-10-01.
  - At most 1,000 records come per page, with a `NextPageLink` that pages by `$skip`.
  - The filterable fields include `armSkuName`, `meterName`, `serviceName` and `priceType`, but
    not `isPrimaryMeterRegion`.
  - Microsoft's example uses `contains(meterName, 'Spot')`.
  - No rate limit is documented.
- Microsoft's reservation example (E64 v4, 1 Year) has `retailPrice` 25007 and `unitOfMeasure`
  "1 Hour". That is about $2.85 an hour over 8,760 hours, so the price is for the whole term.
- On Windows, asyncio's proactor creates an AF_INET socket pair, so pytest-socket's
  `--disable-socket` breaks the Streamlit AppTest smoke test (measured by the answerer).

## Goals / Non-Goals

**Goals:**
- A collector that reads only published prices from one fixed request. It keeps every attempt's
  exact bytes before parsing, and stores observations whose provenance and counts can be checked
  independently.
- Run records that are honest about partial and failed runs, and that tolerate a crash: files
  are written first, and the database is written once from the files.
- Offline contract tests on synthetic pages, with network access blocked in tests, then one live
  run started by the owner.

**Non-Goals:** as in the proposal.

## Decisions

| # | Decision | Who / basis |
|---|---|---|
| D1 | Live-data ⛔ gate for Azure resolved, with this scope: unauthenticated GET of the Retail Prices API only, with the Phase 2 GPU filter; manual runs started by the owner, at most one a day; ≤ 1 request/s, backing off on 429; local storage and analysis only; no redistribution (publishing keeps its own gate). Recorded in PROJECT.md §6 | **owner** (Gate) |
| D2 | Phase 2 is Done only after one successful `live` run. Later runs are ones the owner starts by hand, which leaves the scheduling gate untouched | **owner** (Scope) |
| D3 | Breadth: every N-series GPU family (NC, ND, NG, NV; NVIDIA and AMD; whole and fractional), all regions, all price types, USD, primary meters. The server filter is `contains(armSkuName, 'Standard_N')`, and a client-side family check is authoritative. Other N sizes (such as NP FPGA) are counted out of scope. Phase 3 decides what is compared | **owner** (Scope, Methodology) |
| D4 | Reservation rows are stored with rental type `reservation` and price unit "<term> term". Azure's "1 Hour" is kept verbatim in `azure_retail_price.unit_of_measure` | **owner** (Methodology, One-way door) |
| D5 | Rental-type mapping in rule order, as in the `azure-price-collector` spec. Savings plans stay nested JSON, so v1 has no `savings_plan` observations | **owner** (Methodology) |
| D6 | Item key = Phase 1 D15's key plus `armSkuName`. Stored items that differ only by `armSkuName` are flagged `shared_meter_key` | **owner** (Methodology). Source: Microsoft Q&A 539767 (two sizes, one meter ID) |
| D7 | A snapshot is one `succeeded` run, timed by its `started_at`. Runs are `partial` (≥ 1 page parsed) or `failed` (none) when paging stops early. Everything is kept, and "not listed" is never inferred from them. Rule-breaking rows are skipped and counted per reason, and their bytes stay in the raw files | **owner** (Methodology) |
| D8 | Repeats: keep the first copy, and record later copies in `observation_repeat` with price and field match | **owner** (Methodology, One-way door) |
| D9 | Schema 001 stays frozen. Run records are written once at run end, in one transaction (on Ctrl-C too). Migration 002 adds insert-only tables. Phase 1's D23 is corrected (Risks below). Changing a CHECK list later means rebuilding into a new database file | **owner** (One-way door, Conflict) |
| D10 | Fetch writes files and ingest reads them; `--ingest-run <run_id>` exposes ingest. Labels say how a run's bytes were obtained: `live` (fetched from the API by that run), `recorded` (a new run built from responses kept from an earlier fetch), `synthetic` (invented) | **owner** (Scope, Methodology). Refinement in D27 |
| D11 | Sidecar contents and write rules as in the `azure-price-collector` spec ("Raw responses kept before parsing") | **owner** (One-way door) |
| D12 | Timebox: one session of about 3 h. Cut in this order if it overruns: (1) the `--ingest-run` command; (2) diagram polish beyond marking components built; (3) the live run moves to a follow-up session and the phase stays In progress. Never cut contract tests, raw-byte retention, network blocking, the secret scanner or run records | **owner** (Scope, Value trade-off) |
| D13 | `retrieved_at` = the `received_at` of the response the row came from | recorded. PROJECT.md §3 |
| D14 | HTTP with the standard library (`urllib.request`), behind an injected fetcher. There is no new runtime dependency, urllib sends `Accept-Encoding: identity` so the stored bytes are the entity bytes, and redirects are disabled | default. httpx's last stable release is 0.28.1 (2024-12-06), with a breaking 1.0 pending (PyPI, 2026-10-12). Revisit if HTTP/2, async or concurrency is needed |
| D15 | pytest-socket 0.8.1 (MIT, released 2026-08-19, pytest ≥ 7): `--disable-socket --allow-unix-socket`. Only the Streamlit smoke test is marked to allow sockets | recorded (Phase 0 D23) and fact (PyPI) |
| D16 | detect-secrets 1.5.0 (Apache-2.0) as a dev dependency, run by the gate over `git ls-files` against `.secrets.baseline`, with network verification off. Not gitleaks: installing a binary would be an Authority call. A Git-history scan stays due before the repo goes public | default. PyPI (2026-10-12); Phase 0 D18 |
| D17 | Request parameters, paging, pacing, retries and limits as in the `azure-price-collector` spec | fact (Microsoft's page), recorded (D1 pacing) and default (the numbers). Measured 429s or page counts on the first live run would change the numbers |
| D18 | Command: `uv run python -m compute_cost_risk_monitor.collect`. A fetch is always `live`. No console script before Phase 7 | default |
| D19 | Update the FigJam container view (collector and raw files built) and the ERD (version 2 tables), and re-export the SVGs | recorded. PROJECT.md §4; Phase 1 D5 |
| D20 | Offset paging can miss rows when the catalogue changes mid-run. HANDOFF records this for Phase 3, which decides how "not listed" is inferred | default. Phase 1 put "not listed" in Phase 3 |
| D21 | The pyproject description is reworded to the Azure list-price framing | recorded. Constitution §5 |
| D22 | No `.env.example`: Azure needs no key | recorded. Phase 0 D20 |
| D23 | After the first live run, a test runs against one real page kept under `data/` (gitignored). It skips when the file is absent | recorded. Phase 1 D4 and Risks |
| D24 | Layout: the run's folder is `data/raw/azure-retail/YYYY/MM/DD/` from the run's UTC start date, so one run's files sit together. Run ID `YYYYMMDDTHHMMSSZ-<6 hex>`. Response ID `<run_id>-<seq:04d>`. Start manifest `<run_id>.run.json` (label, start time, code and dependency versions, request parameters) and end manifest `<run_id>.end.json` (finish time, stop reason), each written once | default. Needed for D9's crash recovery; files stay under D3's layout |
| D25 | The command refuses a live fetch within 24 hours of the previous live run's start, read from start manifests on disk. There is no override | default. Enforces D1's "at most one a day"; the owner can relax it later |
| D26 | Flags in `collection_run_tally` (kind `flagged`): `rental_type_ambiguous`, `unknown_price_type`, `shared_meter_key`, `unit_not_hourly`, `next_link_missing_params` (a next link that lacks one of the fixed parameters), `orphan_body_file` (a body without a sidecar) | default. These answer the first live run's open questions (below) |
| D28 | Code review of PR #7 (2026-10-12) found 14 defects, all fixed with tests:<br>- Any unexpected error now ends a run with stop reason `error` and an end manifest.<br>- A failed error-body read is retryable.<br>- Next links with stray characters are refused.<br>- An empty first page is fetched again, then stops as `empty_first_page`.<br>- Numbers too large for a float, and `\|` inside key fields, are rejected as `invalid_value`.<br>- Non-ASCII Retry-After digits are ignored.<br>- Unreadable or misdirected raw files raise named integrity errors.<br>- Sidecars sort by `seq`.<br>- The finish time is monotonic.<br>- Default paths are anchored to the repo.<br>- The 24-hour guard ignores runs that sent no request (refines D25).<br>- `--ingest-run` waits out a run that may still be fetching.<br>- The secret scan runs in batches. | main agent. Source: `/code-review` findings on PR #7 |
| D27 | Refinement of D10's example: restoring a run with `--ingest-run`, after a crash or into a new database, keeps the run's own ID, label and start time. The alternative, re-labelling it as a new `recorded` run, would give a rebuilt snapshot the rebuild's time and corrupt the stale flag. `recorded` is used when a new run is built from kept responses, as D23's test does | main agent, to confirm in PR review. Source: D7 (snapshot timed by its start) |

### Module layout

Pure rules sit apart from I/O. Normalization does not exist yet, and nothing here computes
USD/GPU-hour.

```text
compute_cost_risk_monitor/
  azure_retail.py  pure: fixed request, next-link check, item classification, rental type,
                   item key, price unit
  raw_store.py     files: write-once bodies, sidecars and manifests; read back and verify
  fetch.py         urllib fetcher (no redirects, identity encoding, timeout, size cap) and the
                   paced fetch loop, with injected fetcher, clock and sleep
  ingest.py        files → one DuckDB transaction: run, summary, tallies, responses,
                   observations, Azure detail, repeats
  collect.py       command-line entry point (python -m compute_cost_risk_monitor.collect)
  schema/002_run_records.sql
```

Data flow: API → `fetch.py` → `raw_store.py` (bytes on disk) → `ingest.py` (reads the files back,
verifies them, parses) → DuckDB. The fetch loop parses JSON only to find the next link and item
count, after the bytes are on disk.

### Schema version 2

```text
collection_run_summary(run_id PK, (run_id, source) → collection_run, requests, pages_parsed,
    failed_requests, throttled, items_seen, observations_stored, repeats, out_of_scope,
    rejected, stop_reason)
    counts ≥ 0; pages_parsed + failed_requests = requests; throttled ≤ failed_requests;
    items_seen = observations_stored + repeats + out_of_scope + rejected
collection_run_tally((run_id, kind, reason) PK, (run_id, source) → collection_run,
    kind IN ('rejected', 'flagged'), reason, occurrences > 0)
observation_repeat((response_id, item_index) PK, (response_id, source) → raw_response,
    item_key, first_retrieved_at, (source, item_key, first_retrieved_at) → price_observation,
    same_price, same_fields)
```

`stop_reason` and `reason` are free text, not CHECK lists, because a CHECK list cannot be
extended later (D9). The `kind` list is the exception: it has two values and is not expected to
change.

### Non-negotiables check

| PROJECT.md §5 rule or §6 gate | How this design keeps it |
|---|---|
| Secrets never printed or committed | The API needs no key, there is no `.env`, and the sidecar keeps no cookies. detect-secrets joins the gate (D16) |
| Never fabricate; label results; preserve failed runs | Every attempt is kept, including failures. `partial` and `failed` runs are stored (D7). Labels come from how the bytes were obtained (D10, D27). Contract tests are synthetic and say so. The live run's outcome is recorded as observed |
| Operator resolves ⛔ gates | The live-data gate was resolved by the owner (D1). The scheduling, spend and publishing gates are not touched, and the first live run is started by the owner (D2) |
| Call the data published Azure list prices | No figures are presented in this phase. The command prints counts, never prices. Documents keep the list-price framing (D21) |
| Deterministic code computes every figure | No figures are computed beyond counts. There is no AI |
| Compare only within comparable groups; state exclusions | No comparisons or costs in this phase. Rental type and the item key carry the group's parts forward (D5, D6) |
| Collector only reads published prices | Only GET to one endpoint, with next links pinned to it, no redirects and no credentials. No other host is called (`azure-price-collector` spec) |
| Use a source within its terms and rate limits; missing stays missing | ≤ 1 request/s, slower after a 429, `Retry-After` honoured, page and time caps, and at most one run a day (D1, D17, D25). A GPU-only filter keeps the request to the minimum data. Rejected rows are counted, never filled in (D7) |
| ⛔ Before reading live data | Resolved 2026-10-12 by the owner with the D1 scope. A second source stays gated |
| ⛔ Unattended collection / spend / publishing | Not touched. No scheduler, no paid service, and no real data in Git or anywhere public |

No exception to any rule is needed.

## Risks / Trade-offs

- [Phase 1's D23 said a migration could extend the CHECK lists; it cannot] → corrected here.
  Version-1 lists (labels, statuses, rental types, sources) can change only by rebuilding into a
  new database file. Version 2 avoids new CHECK lists except `kind`.
- [A run row cannot be updated, so a run is invisible in the database until it ends] → raw files
  and manifests are written as the run goes, and `--ingest-run` restores a run that never reached
  the database.
- [`contains()` on `armSkuName` is undocumented] → the client-side family check is
  authoritative. If the server ignores the filter, rows are counted out of scope and the page cap
  stops the run as `partial`. The first live run shows which happened.
- [`NextPageLink` may drop `api-version`, `currencyCode` or `meterRegion`] → links are followed
  verbatim. The `next_link_missing_params` flag records any drop, and per-row checks reject
  non-USD and non-primary rows. Savings-plan JSON could go missing on later pages if
  `api-version` drops; the first live run checks.
- [Offset paging over a changing catalogue can repeat or miss rows] → repeats are recorded (D8).
  Misses are undetectable within a run, so Phase 3 decides "not listed" (D20).
- [Throttling once returned an empty page with no next link (Microsoft Q&A 1312424, 2023)] →
  an empty page after a full one is fetched again after 60 s before it is accepted.
- [The reservation price is the whole-term price by inference, not by Microsoft's statement] →
  the unit names the term and reservations are never compared (Phase 1 D11).
- [urllib's timeout applies per socket operation, not to the whole response] → there is a 64 MiB
  body cap, and the 30-minute run cap bounds the total.
- [detect-secrets has had no release since 2024-05 and scans files, not history] → a history
  scan is due before going public. Swap the scanner if it stops working on Python 3.13.

## Migration Plan

New modules, migration 002 and tests. Existing databases: none exist yet. `create_schema`
applies version 2 on top of version 1. To roll back, revert the merge commit and delete
`data/monitor.duckdb`. The raw files stay valid for a later ingest.

## Open Questions

Answered by the first live run, `20261012T151909Z-5473f1`, started by the owner on
2026-10-12 at commit 73b35ac. Counts only, checked against the kept files by a script
independent of ingest:

- **Server filter:** `contains(armSkuName, 'Standard_N')` filters on the server. Of 14,593
  rows, 246 were out of scope: NP FPGA sizes and `Standard_NM16ads_MA35D` (an AMD media
  accelerator), whose `armSkuName` carries two trailing spaces. No in-scope name had stray
  whitespace.
- **Pages and status:** 15 pages (14 × 1,000 + 593), all HTTP 200. The run succeeded.
  14,347 rows were stored, with 0 repeats and 0 rejected.
- **Rows by rental type:** on_demand 3,285, spot 3,048, dev_test 3,803, reservation 2,387,
  other (Low Priority) 1,824. That covers 100 GPU sizes in 60 regions.
- **Next links:** they kept all four fixed parameters, so `next_link_missing_params` stayed 0.
- **Throttling:** no 429 occurred, and no standard `Retry-After` header was sent. Every
  response carried `x-ms-ratelimit-remaining-retailprices-requests: 9` and
  `x-ms-ratelimit-retailprices-retry-after: 60`. The fetch loop now honours the latter after
  a 429 (spec "Pacing, retries and limits"). The meaning of the remaining-requests count is
  not documented, and it did not fall during the run.
- **Flags:** no `shared_meter_key`, `rental_type_ambiguous`, `unknown_price_type` or
  `unit_not_hourly` flags. Every unit was "1 Hour".
- **Reservation terms:** 1 Year, 3 Years and **5 Years**, stored as "<term> term".
- **Other fields:** savings-plan arrays were on 1,262 stored rows. Every row had an
  `effectiveStartDate`.
- **Retrieval times:** each observation's retrieval time equals its response's receive
  time.
