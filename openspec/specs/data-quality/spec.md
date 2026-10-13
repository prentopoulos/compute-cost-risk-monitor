# data-quality Specification

## Purpose
The counts-only quality report for each source's latest snapshot (freshness, rows by
reason, run-record counts, duplicates, missing fields, thin and single-price groups,
history) and the quality command that prints it.
## Requirements
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
prices.

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

### Requirement: Quality command
`uv run python -m compute_cost_risk_monitor.quality [--db PATH] [--as-of TIME]` SHALL print the
report for each source, counts only. It SHALL refuse, with exit code 2, a missing database, an
`--as-of` time without a time zone, or a database whose rule set is not stored yet.

#### Scenario: Before normalizing
- **WHEN** the command runs on a database that holds a run but no rule set
- **THEN** it exits with code 2 and says to run normalize first

#### Scenario: Report printed
- **WHEN** the command runs after normalize, with `--as-of` one day after the snapshot
- **THEN** it prints one report per source, the Azure one `not stale`, and a source without runs as having no snapshot

