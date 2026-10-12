# price-data-schema Specification

## Purpose
The stored data model for observed prices: tables, keys and constraints, data labels,
UTC time handling, schema and rule versioning, and the connection helper later phases use.
## Requirements
### Requirement: UTC connection helper
The package SHALL provide `compute_cost_risk_monitor.db.connect(path)`, which opens a DuckDB
connection with the session time zone set to UTC. All project code SHALL open DuckDB
connections through it.

#### Scenario: Connection reports UTC
- **WHEN** `connect(":memory:")` opens a connection on a machine whose local zone is not UTC
- **THEN** `SELECT current_setting('TimeZone')` returns `UTC`

#### Scenario: Timestamps come back in UTC
- **WHEN** a TIMESTAMPTZ value of `2026-10-11T00:00:00Z` is stored and read back through the helper's connection, both as a Python value and as a pandas column
- **THEN** both are timezone-aware UTC values equal to the stored instant

### Requirement: Versioned schema creation
`compute_cost_risk_monitor.db.create_schema(connection)` SHALL apply the package's numbered SQL
files in order. It SHALL record each applied version with its UTC time in `schema_version`, and
SHALL skip versions that are already applied.

#### Scenario: Fresh database
- **WHEN** `create_schema` runs on an empty in-memory database
- **THEN** every table in the schema exists and `schema_version` holds versions 1 and 2

#### Scenario: Re-run is a no-op
- **WHEN** `create_schema` runs a second time on the same database
- **THEN** no error is raised and `schema_version` still holds exactly one row for each version

#### Scenario: Upgrade from version 1
- **WHEN** `create_schema` runs on a database that holds only version 1
- **THEN** it applies version 2 alone and existing rows are unchanged

#### Scenario: Duplicate version numbers rejected
- **WHEN** two schema files share a version number, such as `002_a.sql` and `002_b.sql`
- **THEN** loading the files raises an error naming the version, before any SQL runs

#### Scenario: Only this database's version table counts
- **WHEN** a temporary table named `schema_version` exists on the connection
- **THEN** it does not count as an applied schema version

### Requirement: Collection runs carry a source and a provenance label
Every `collection_run` row SHALL name its source (`azure-retail` or `synthetic-marketplace`)
and exactly one data label (`synthetic`, `recorded` or `live`). A `synthetic-marketplace` run
SHALL carry the `synthetic` label. Staleness SHALL NOT be stored as a label.

#### Scenario: Unknown label rejected
- **WHEN** a run is inserted with data label `stale`
- **THEN** DuckDB rejects the insert with a constraint error

#### Scenario: Synthetic marketplace data cannot pass as live
- **WHEN** a run with source `synthetic-marketplace` is inserted with label `live`
- **THEN** DuckDB rejects the insert with a constraint error

#### Scenario: Source carries through to every observation
- **WHEN** a raw response or price observation names a source that differs from its run's source, for example a `synthetic-marketplace` observation under a live `azure-retail` run
- **THEN** DuckDB rejects the insert with a constraint error

#### Scenario: Run points at a real schema version
- **WHEN** a run records schema version 99 on a database that has only version 1
- **THEN** DuckDB rejects the insert

### Requirement: Raw responses are recorded with their fingerprint
Every `raw_response` row SHALL record its run, its sequence within the run, the file path of
the retained bytes, a 64-character SHA-256 of the uncompressed bytes, the byte length, the
request URL and the UTC request time. The pair (run, sequence) SHALL be unique. A failed
request SHALL still have a row, with its HTTP status and error.

#### Scenario: Missing fingerprint rejected
- **WHEN** a raw response row is inserted without a SHA-256
- **THEN** DuckDB rejects the insert

#### Scenario: Failed request recorded
- **WHEN** a raw response row is inserted with HTTP status 429, an error message, no item count and parse status `failed`
- **THEN** the insert succeeds

### Requirement: Price observations keep provenance and valid prices
Every `price_observation` row SHALL reference its raw response and record:
- source
- source item key (offer ID or Azure price-row key)
- retrieval time (TIMESTAMPTZ)
- rental type (`on_demand`, `spot`, `reservation`, `savings_plan`, `dev_test` or `other`)
- region
- price, finite and greater than zero
- currency `USD`
- the price unit: the source's original unit, except for a reservation priced for its whole
  term, whose unit names the term (for example `1 Year term`) so it never reads as an hourly
  price

The triple (source, item key, retrieval time) SHALL be unique.

#### Scenario: Duplicate observation rejected
- **WHEN** a second row with the same source, item key and retrieval time is inserted
- **THEN** DuckDB rejects it with a constraint error

#### Scenario: Non-positive or non-finite price rejected
- **WHEN** rows are inserted with price 0, a negative price, NaN or infinity
- **THEN** DuckDB rejects each insert

#### Scenario: Missing provenance rejected
- **WHEN** a row is inserted without a retrieval time, currency, price unit, rental type or raw response reference
- **THEN** DuckDB rejects each insert

#### Scenario: Unknown rental type rejected
- **WHEN** a row is inserted with rental type `bid`
- **THEN** DuckDB rejects the insert

#### Scenario: Reservation stored with its term as the unit
- **WHEN** an Azure reservation observation is stored with price unit `1 Year term` and its detail row keeps unit of measure `1 Hour`
- **THEN** both inserts succeed

### Requirement: Missing values stay missing
Fields that a source or mapping may not provide (for example GPU model and GPU count before a
SKU is mapped) SHALL be nullable. They SHALL never default to zero or a placeholder. A GPU count
that is present SHALL be greater than zero.

#### Scenario: Unmapped observation stored with nulls
- **WHEN** an observation is inserted with no GPU model and no GPU count
- **THEN** it is stored with both fields NULL

#### Scenario: Zero GPU count rejected
- **WHEN** an observation is inserted with GPU count 0
- **THEN** DuckDB rejects the insert

### Requirement: Source detail tables
`azure_retail_price` SHALL hold the Azure Retail Prices fields for an observation (retail and
unit price, unit of measure, region, effective start date, meter, product and SKU identifiers
and names, service, price type, primary-meter flag, ARM SKU name, reservation term, tier
minimum units and savings plan). `marketplace_offer` SHALL hold the synthetic marketplace
fields (offer ID, machine ID, GPU name as listed, GPU count, VRAM, country). Each detail row
SHALL reference exactly one observation.

#### Scenario: Detail row without an observation rejected
- **WHEN** an `azure_retail_price` row references an observation that does not exist
- **THEN** DuckDB rejects the insert with a foreign key error

#### Scenario: Detail row must agree with its observation
- **WHEN** an `azure_retail_price` row gives a region or retail price that differs from its observation's
- **THEN** DuckDB rejects the insert

#### Scenario: Non-finite attributes rejected
- **WHEN** a VRAM size, tier minimum or unit price is NaN or infinite, or a unit price is negative
- **THEN** DuckDB rejects the insert

### Requirement: Versioned rules, mappings and derived prices
`rule_set` SHALL store each rule version with its frozen parameters as JSON and its creation
time. `gpu_sku_map` SHALL key each mapping row by (mapping version, ARM SKU name), with a GPU
count greater than zero and a source URL. `normalized_price` SHALL key each derived row by its
observation and rule version and reference both. Its region and rental type SHALL equal the
observation's, and any SKU mapping it names SHALL exist. A normalized row SHALL store a finite,
positive USD/GPU-hour with its GPU model and count. An excluded row SHALL store the reason
instead, with no USD/GPU-hour.

#### Scenario: Derived price without a rule version rejected
- **WHEN** a `normalized_price` row references a rule version that is not in `rule_set`
- **THEN** DuckDB rejects the insert with a foreign key error

#### Scenario: Same observation under two rule versions
- **WHEN** one observation is normalized under rule versions `groups-v1` and `groups-v2`
- **THEN** both rows are stored side by side

#### Scenario: Excluded row kept with its reason
- **WHEN** an unmapped observation is recorded under a rule version with reason `unmapped SKU` and no USD/GPU-hour
- **THEN** the insert succeeds, and an excluded row that also carries a USD/GPU-hour is rejected

#### Scenario: Derived group key must match its evidence
- **WHEN** a derived row's region or rental type differs from its observation's, or it names a SKU mapping that does not exist
- **THEN** DuckDB rejects the insert

### Requirement: Run records are insert-only
Version 1 tables SHALL NOT be altered by later migrations; new structure SHALL arrive as new
tables. A `collection_run` row SHALL be written once, with its final status, because DuckDB 1.5.6
refuses to update a run row that a raw response references.

#### Scenario: Referenced run cannot be updated
- **WHEN** a `collection_run` row referenced by a `raw_response` row is updated
- **THEN** DuckDB rejects the update with a foreign key constraint error

### Requirement: Run summary
`collection_run_summary` SHALL hold one row per run, referencing the run and its source. It SHALL
store the following non-negative integer counts, plus a non-empty stop reason:
- requests sent, pages parsed, failed requests, and throttled (HTTP 429) requests;
- items seen, observations stored, repeats, out-of-scope items and rejected items.

Pages parsed plus failed requests SHALL equal requests, and throttled requests SHALL not exceed
failed requests. Items seen SHALL equal stored + repeats + out of scope + rejected.

#### Scenario: Counts that do not add up rejected
- **WHEN** a summary row has items seen 10 with stored 6, repeats 1, out of scope 1 and rejected 1
- **THEN** DuckDB rejects the insert

#### Scenario: Negative count rejected
- **WHEN** a summary row has a negative count
- **THEN** DuckDB rejects the insert

#### Scenario: Summary for an unknown run rejected
- **WHEN** a summary row names a run that does not exist, or a source that differs from its run's
- **THEN** DuckDB rejects the insert

### Requirement: Run tallies
`collection_run_tally` SHALL count a run's items per reason. Kind `rejected` holds rejection
reasons and kind `flagged` holds conditions noted on stored items or pages. Each row SHALL name its
run, kind and reason, with a count greater than zero, and (run, kind, reason) SHALL be unique.

#### Scenario: Unknown kind rejected
- **WHEN** a tally row has kind `warning`
- **THEN** DuckDB rejects the insert

#### Scenario: Zero count rejected
- **WHEN** a tally row has count 0
- **THEN** DuckDB rejects the insert

### Requirement: Repeats within a run
`observation_repeat` SHALL record each later copy of an already stored item within a run. Each
row SHALL record:
- the raw response and item position it came from;
- its item key and the observation it repeats;
- whether its price matched;
- whether all its fields matched.

(Response, item position) SHALL be unique. The response and the repeated observation SHALL exist
and share the source.

#### Scenario: Repeat of a missing observation rejected
- **WHEN** a repeat row points at an observation that does not exist
- **THEN** DuckDB rejects the insert

#### Scenario: Repeat recorded
- **WHEN** a repeat row points at an existing response and observation with price match false
- **THEN** the insert succeeds

