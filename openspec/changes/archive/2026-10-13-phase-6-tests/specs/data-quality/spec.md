## MODIFIED Requirements

### Requirement: Quality report
For each source with stored data, a quality report SHALL describe the latest snapshot, as of an
injected time. It SHALL hold counts only, never prices:
- run ID, label and start time;
- `stale`, when the latest snapshot started more than 7 days before the as-of time;
- observations, normalized rows and excluded rows by reason under the rule version, and a
  `NOT NORMALIZED` flag with the count of observations that have no row yet;
- distinct unmapped sizes, with their names;
- rejected rows by reason, out-of-scope rows and repeats, from the run records;
- duplicates: repeats and `shared_meter_key` flags for Azure, `machine_duplicate` offers for
  marketplace;
- missing optional fields among normalized rows: location, product name and effective start
  date for Azure; country code for marketplace offers (an offer without VRAM is never
  compared, so VRAM is not counted);
- `os_ambiguous` rows;
- region groups labelled `single list price`;
- thin summaries or groups;
- changes, `absent once (unconfirmed)` listings and `not listed` listings since the previous
  snapshot.

A source with no succeeded run SHALL be reported as having no snapshot, never as having zero
prices. When the latest snapshot's run has no summary row, its out-of-scope, repeat and
rejected totals, and any tallied count with no tally row, SHALL be reported as unknown, never
as zero; tally rows that exist are still reported.

#### Scenario: Fresh snapshot
- **WHEN** the latest snapshot started 2 days before the as-of time
- **THEN** the report is not stale

#### Scenario: Stale snapshot
- **WHEN** the latest snapshot started 8 days before the as-of time
- **THEN** the report is marked `stale`

#### Scenario: Counts reconcile
- **WHEN** a report is built after normalizing a known-answer fixture
- **THEN** normalized plus excluded rows equal the snapshot's observations, and the reason counts match the fixture's known answers

#### Scenario: Not normalized yet
- **WHEN** the latest snapshot was stored after the last normalize
- **THEN** the report flags `NOT NORMALIZED` with the count of observations lacking a row, instead of showing empty groups as if nothing were comparable

#### Scenario: No snapshot
- **WHEN** a source has only a failed run
- **THEN** the report says it has no snapshot and gives no row counts as if they were zero prices

#### Scenario: Counts only
- **WHEN** a report is rendered as text
- **THEN** it contains none of the fixture's price values

#### Scenario: Marketplace missing fields are its own
- **WHEN** a compared marketplace offer has no country code
- **THEN** the marketplace report counts one missing `country_code`, and names no Azure field

#### Scenario: Exactly seven days is not stale
- **WHEN** the latest snapshot started exactly 7 days before the as-of time
- **THEN** the report is not stale, and one second later it is

#### Scenario: Staleness comes from the latest succeeded run
- **WHEN** a source's newest run is partial or failed and its latest succeeded run started 8 days before the as-of time
- **THEN** the report describes the succeeded run and is marked `stale`

#### Scenario: Snapshot dated after the as-of time
- **WHEN** the latest snapshot started after the as-of time
- **THEN** the report is not stale and carries no other flag for it

#### Scenario: Run without a summary
- **WHEN** the latest snapshot's run has no `collection_run_summary` row
- **THEN** the report and the dashboard panel give its out-of-scope, repeat and rejected totals and its `shared_meter_key` count as `unknown (no run summary)`, not 0, while a tally row that exists, such as `rejected missing_field: 2`, is still shown

### Requirement: Quality command
`uv run python -m compute_cost_risk_monitor.quality [--db PATH] [--as-of TIME]` SHALL print the
report for each source, counts only. It SHALL refuse, with exit code 2, a missing database, an
`--as-of` time without a time zone, or a database whose rule set is not stored yet. It SHALL
convert an `--as-of` time with any offset to UTC before building and printing the report.

#### Scenario: Before normalizing
- **WHEN** the command runs on a database that holds a run but no rule set
- **THEN** it exits with code 2 and says to run normalize first

#### Scenario: Report printed
- **WHEN** the command runs after normalize, with `--as-of` one day after the snapshot
- **THEN** it prints one report per source, the Azure one `not stale`, and a source without runs as having no snapshot

#### Scenario: As-of time printed in UTC
- **WHEN** the command runs with `--as-of 2026-10-13T10:00:00-04:00`
- **THEN** the report gives the as-of time as 2026-10-13T14:00:00+00:00 and judges staleness at that instant
