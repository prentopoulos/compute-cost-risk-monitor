## MODIFIED Requirements

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

## ADDED Requirements

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
