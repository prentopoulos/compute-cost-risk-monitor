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
  date for Azure; GPU VRAM and country code for marketplace offers;
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

#### Scenario: Marketplace missing fields are its own
- **WHEN** a compared marketplace offer has no VRAM and no country code
- **THEN** the marketplace report counts one missing `gpu_vram_gb` and one missing `country_code`, and names no Azure field
