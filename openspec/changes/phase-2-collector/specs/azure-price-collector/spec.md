## ADDED Requirements

### Requirement: Read-only fixed request
The collector SHALL send only HTTP GET requests to `https://prices.azure.com/api/retail/prices`.
The first request SHALL carry exactly these parameters:
- `api-version=2023-01-01-preview`
- `currencyCode='USD'`
- `meterRegion='primary'`
- `$filter=serviceName eq 'Virtual Machines' and contains(armSkuName, 'Standard_N')`

Later pages SHALL be fetched from each response's `NextPageLink`, exactly as given, only when the
link uses scheme `https`, host `prices.azure.com`, port 443 or none, and path `/api/retail/prices`.
Redirects SHALL NOT be followed. The collector SHALL send no credentials, cookies or
`Accept-Encoding` other than `identity`.

#### Scenario: First request is the fixed request
- **WHEN** a live run starts
- **THEN** its first request is a GET to the endpoint with exactly the four parameters above, and a User-Agent naming the project and its version

#### Scenario: Next page link on another host refused
- **WHEN** a page's `NextPageLink` points at a host other than `prices.azure.com`, at another path, or uses `http`
- **THEN** no request is sent to it and the run stops with status `partial` and stop reason `invalid_next_link`

#### Scenario: Repeated next page link stops the run
- **WHEN** a page's `NextPageLink` equals a link already fetched in the run
- **THEN** the run stops with status `partial` and stop reason `repeated_next_link`

#### Scenario: Redirect not followed
- **WHEN** the API answers with a 3xx redirect
- **THEN** the redirect target is not requested and the response is recorded as a failed request

### Requirement: Pacing, retries and limits
The collector SHALL start requests at least 1 second apart. After any HTTP 429 it SHALL wait at least 2
seconds between requests for the rest of the run. Each request SHALL time out after 30 seconds. A
page SHALL be attempted at most 5 times. Retries SHALL happen only after HTTP 429, HTTP 5xx, a
timeout or connection error, or a 200 response whose body is not a valid page. The wait before a
retry SHALL be:
- the `Retry-After` header's value (seconds or HTTP date), capped at 300 seconds, when present;
- after a 429 without it, Azure's `x-ms-ratelimit-retailprices-retry-after` header, also
  capped, when present;
- 60 seconds after a 429 with neither;
- otherwise 2, 4, 8 and 16 seconds for the four retries.

Any other status SHALL stop the run without a retry. A run SHALL stop after 200 pages or 30 minutes.
An empty final page right after a full page of 1,000 items SHALL be fetched once more, after 60
seconds, before it is accepted.

#### Scenario: Requests are paced
- **WHEN** a run fetches three pages with no errors
- **THEN** each request starts at least 1 second after the previous one

#### Scenario: Throttled request retried after Retry-After
- **WHEN** a page returns 429 with `Retry-After: 7`, then 200
- **THEN** the collector waits 7 seconds before the retry, both attempts are recorded, and later requests in the run start at least 2 seconds apart

#### Scenario: Azure's own retry header honoured only for throttling
- **WHEN** a page returns 429 with `x-ms-ratelimit-retailprices-retry-after: 45` and no `Retry-After`, or returns 503 with that header
- **THEN** the collector waits 45 seconds after the 429, but the usual 2 seconds after the 503

#### Scenario: Retries exhausted
- **WHEN** a page returns 503 five times
- **THEN** the run stops with stop reason `retries_exhausted` and records all five attempts

#### Scenario: Client error not retried
- **WHEN** a page returns 400
- **THEN** it is not retried and the run stops with stop reason `http_400`

#### Scenario: Page cap reached
- **WHEN** the API keeps returning a next page after 200 pages
- **THEN** no 201st page is requested and the run stops with status `partial` and stop reason `page_cap`

#### Scenario: Suspicious empty page fetched again
- **WHEN** a page with 1,000 items is followed by a page with no items and no next link
- **THEN** that page is requested once more after 60 seconds before the run completes

### Requirement: Raw responses kept before parsing
Every request attempt SHALL be kept on disk before its body is parsed. The body file SHALL be
`data/raw/azure-retail/YYYY/MM/DD/<run_id>-<seq>.json.gz`, using the run's UTC start date. It SHALL
hold the exact response bytes, gzip-compressed at level 9 with modification time 0. A sidecar
`<run_id>-<seq>.meta.json` SHALL be written after the body file. Each file SHALL be written once
(temporary file, then rename) and never overwritten. The sidecar SHALL record:
- sidecar version, source, run ID, sequence, page number, attempt number, data label and code
  version;
- method, request URL as sent, and User-Agent;
- UTC request and receive times, and elapsed milliseconds;
- HTTP status and reason;
- every response header except `Set-Cookie`, names lower-cased;
- uncompressed byte length, SHA-256 of the uncompressed bytes, compressed byte length, and the
  file name relative to `data/raw`;
- any error.

The sidecar SHALL NOT contain cookies, absolute paths, the host name or IP address, or environment
variables. A request that failed without a body SHALL be kept as an empty body. Each run SHALL also
keep a start manifest `<run_id>.run.json` and, when the run ends, an end manifest
`<run_id>.end.json`.

#### Scenario: Body kept byte for byte
- **WHEN** a page's bytes are kept and read back
- **THEN** the decompressed bytes equal the bytes received, and their SHA-256 and length match the sidecar

#### Scenario: Same bytes give the same file
- **WHEN** the same response bytes are kept twice under different names
- **THEN** both compressed files are identical

#### Scenario: Existing file never overwritten
- **WHEN** a body, sidecar or manifest is written to a path that already exists
- **THEN** the write fails and the existing file is unchanged

#### Scenario: Failed request kept
- **WHEN** a request times out without a response
- **THEN** an empty body file and a sidecar with no HTTP status and the error are kept

#### Scenario: Sidecar leaves out private details
- **WHEN** a response carries a `Set-Cookie` header
- **THEN** the sidecar omits it and holds no absolute path

### Requirement: Rows in scope and rows rejected
Each item SHALL be classified in this order, and counted in exactly one of:
- **rejected**: the item is not an object, or its `armSkuName` is missing;
- **out of scope**: `armSkuName` does not start with `Standard_NC`, `Standard_ND`, `Standard_NG` or
  `Standard_NV`;
- **rejected**: a required field is missing or of the wrong type (`meterId`, `skuId`,
  `armRegionName`, `type`, `retailPrice`, `unitOfMeasure`, `currencyCode`, `isPrimaryMeterRegion`,
  `tierMinimumUnits`, `meterName`, `skuName`), the currency is not USD, the meter is not primary,
  `retailPrice` is not finite or not greater than zero, an optional field has the wrong type, or a
  reservation has no term;
- **repeat**: an earlier item in the run has the same item key;
- **stored**: otherwise.

Rejected items SHALL be counted per reason. Out-of-scope and rejected items SHALL stay only in the
raw files. No value SHALL be filled in, defaulted or coerced to make an item pass.

#### Scenario: Non-GPU size out of scope
- **WHEN** a page holds an item with `armSkuName` `Standard_NP20s`
- **THEN** it is counted as out of scope and no observation is stored for it

#### Scenario: Zero price rejected with its reason
- **WHEN** an in-scope item has `retailPrice` 0
- **THEN** it is counted as rejected with reason `non_positive_price` and not stored

#### Scenario: Non-primary or non-USD rejected
- **WHEN** an in-scope item has `isPrimaryMeterRegion` false, or `currencyCode` `EUR`
- **THEN** it is rejected with reason `not_primary_meter` or `non_usd_currency`

#### Scenario: Missing field rejected, never filled in
- **WHEN** an in-scope item lacks `meterId`
- **THEN** it is rejected with reason `missing_field`, and nothing is stored with a placeholder ID

### Requirement: Rental type mapping
Each stored item's rental type SHALL be assigned by the first rule that matches:
1. `type` `Reservation` → `reservation`.
2. `type` `DevTestConsumption` → `dev_test`.
3. `type` `Consumption`:
   - `meterName` and `skuName` both end in ` Spot` → `spot`;
   - both end in ` Low Priority` → `other`;
   - neither ends in either → `on_demand`;
   - they disagree → `other`, counted under flag `rental_type_ambiguous`.
4. Any other `type` → `other`, counted under flag `unknown_price_type`, with Azure's type kept in
   `price_type`.

Savings-plan prices SHALL stay as JSON on their Consumption row and SHALL NOT become separate
observations.

#### Scenario: Spot on a DevTest row
- **WHEN** a `DevTestConsumption` item has `meterName` `F16s Spot`
- **THEN** its rental type is `dev_test`

#### Scenario: Spot and pay-as-you-go
- **WHEN** two `Consumption` items are named `NC40ads H100 v5 Spot` and `NC40ads H100 v5`
- **THEN** their rental types are `spot` and `on_demand`

#### Scenario: Names disagree
- **WHEN** a `Consumption` item's `meterName` ends in ` Spot` and its `skuName` does not
- **THEN** its rental type is `other` and the run's `rental_type_ambiguous` flag count rises by one

#### Scenario: Savings plan kept on its row
- **WHEN** a `Consumption` item carries a `savingsPlan` array
- **THEN** one `on_demand` observation is stored, and its detail row holds the array as JSON

### Requirement: Item key, repeats and price units
A stored item's key SHALL join, with `|`:
- `meterId`, `skuId`, `armRegionName` and `type`;
- `reservationTerm` (empty when absent);
- `tierMinimumUnits` as a decimal;
- `currencyCode` and `armSkuName`.

An item whose key was already stored in the run SHALL NOT be stored again. It SHALL be recorded as
a repeat, noting the response and item position it came from, the first observation it repeats,
and whether its price and all its fields matched. Stored items whose keys differ only by
`armSkuName` SHALL be counted under flag `shared_meter_key`.

A reservation's price unit SHALL be its term followed by `term` (for example `1 Year term`), with
Azure's `unitOfMeasure` kept verbatim in the detail row. Other items SHALL keep `unitOfMeasure` as
their price unit. A non-reservation unit other than `1 Hour` SHALL be counted under flag
`unit_not_hourly`.

#### Scenario: Repeat across pages
- **WHEN** the same item appears on page 1 and page 2 of a run, with a different price on page 2
- **THEN** one observation is stored from page 1, and a repeat row records page 2's response with price match false

#### Scenario: Reservation unit names its term
- **WHEN** a `Reservation` item has `reservationTerm` `1 Year`, `retailPrice` 25007 and `unitOfMeasure` `1 Hour`
- **THEN** its observation has rental type `reservation`, price 25007 and price unit `1 Year term`, and its detail row keeps unit of measure `1 Hour`

#### Scenario: Two sizes share a meter
- **WHEN** two stored items share every key part except `armSkuName`
- **THEN** both are stored and the run's `shared_meter_key` flag count is 1

### Requirement: Run status and write-once run records
A run's status SHALL be:
- `succeeded` when paging ended on a parsed page with no next link;
- `partial` when it stopped earlier after parsing at least one page;
- `failed` when no page was parsed.

Only `succeeded` runs are complete snapshots. A run's database records SHALL be written once, in
one transaction, after its requests end:
- the run with its final status;
- its summary and tallies;
- every raw response, including failed ones;
- its observations with Azure detail rows;
- its repeats.

Each observation's retrieval time SHALL be the receive time of the response it came from. The
summary SHALL satisfy items seen = stored + repeats + out of scope + rejected. If writing fails,
nothing of the run SHALL be written, and its files SHALL stay on disk.

#### Scenario: Complete run succeeds
- **WHEN** every page of a run is fetched and the last has no next link
- **THEN** the run is stored with status `succeeded`, a finish time, and counts that satisfy the identity

#### Scenario: Partial run kept
- **WHEN** a run's third page fails five times after two pages were parsed
- **THEN** the run is stored with status `partial`, its two pages' observations are kept, and all attempts are recorded

#### Scenario: Run with no parsed page
- **WHEN** every attempt of the first page fails
- **THEN** the run is stored with status `failed`, its attempts recorded, and no observations

#### Scenario: Interrupted run
- **WHEN** the owner presses Ctrl-C during a run
- **THEN** an end manifest with stop reason `interrupted` is written and the run is stored as `partial` or `failed`

#### Scenario: Failed write leaves nothing behind
- **WHEN** writing a run's records fails part-way
- **THEN** the database holds no row for that run and its raw files remain

### Requirement: Ingest from retained files
The ingest step SHALL build a run's records only from that run's retained files, not from memory or
the network. It SHALL check each body against its sidecar's SHA-256 and length before parsing, and
SHALL write nothing if any check fails. It SHALL take the run's data label from the start manifest.
A run with no end manifest SHALL be stored with stop reason `no_end_manifest`. Ingesting a run that
the database already holds SHALL be refused.

#### Scenario: Run restored after a crash
- **WHEN** a run's files exist without an end manifest and the run is not in the database
- **THEN** ingesting it stores the run under its own ID and label, with stop reason `no_end_manifest`

#### Scenario: Tampered body refused
- **WHEN** a kept body no longer matches its sidecar's SHA-256
- **THEN** ingest fails naming the file and writes nothing

#### Scenario: Run ingested twice
- **WHEN** a run already in the database is ingested again
- **THEN** ingest is refused and the database is unchanged

### Requirement: Collect command
`uv run python -m compute_cost_risk_monitor.collect` SHALL fetch one live run, labelled `live`, and
then ingest it. There SHALL be no option to set the data label. `--ingest-run <run_id>` SHALL
ingest a retained run without network access. The command SHALL refuse a live fetch when another
live run started less than 24 hours earlier. It SHALL print the run ID, status, stop reason and
counts, never prices. It SHALL exit 0 for a succeeded run and non-zero otherwise.

#### Scenario: Second live run within a day refused
- **WHEN** the command is run less than 24 hours after a live run started
- **THEN** no request is sent, and the command names the earlier run and exits non-zero

#### Scenario: Ingest without network
- **WHEN** `--ingest-run` names a retained run
- **THEN** the run is ingested and no request is sent

### Requirement: Collector tests stay offline
The collector's tests SHALL use synthetic fixtures, labelled `synthetic`, and an injected fetcher,
clock and sleep. They SHALL make no network call. They SHALL cover normal, edge and deliberately
failing cases. A test against a real page kept locally under `data/` SHALL skip when the file is
absent. No real Azure response SHALL be committed to Git.

#### Scenario: Multi-page synthetic run end to end
- **WHEN** a synthetic three-page run with a repeat, a 429, an out-of-scope item, a rejected item and a reservation is collected and ingested
- **THEN** the stored counts, rental types, units and repeats equal the fixture's known answers, and every observation traces to a kept body whose SHA-256 matches its raw response row

#### Scenario: Real-page test skips in CI
- **WHEN** the locally kept real page is absent
- **THEN** its test is reported as skipped, not failed
