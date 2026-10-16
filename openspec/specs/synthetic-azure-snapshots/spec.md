# synthetic-azure-snapshots Specification

## Purpose
Labelled synthetic Azure-shaped snapshot files with invented prices, stored as
`azure-retail` runs labelled `synthetic` through the live row rules, kept out of the
live database. They feed the dashboard demo, its tests and screenshots.
## Requirements
### Requirement: Synthetic Azure snapshot files
A synthetic Azure snapshot SHALL be a JSON file shaped like one Azure Retail Prices API page
(`Items`, with `NextPageLink` null) that also holds `"_label": "synthetic"` and an `observed_at`
time with a time zone. Its prices SHALL be invented; its size names MAY be real Azure names so
the packaged GPU map applies. A file without the synthetic label, without a valid `observed_at`,
or without a non-empty `Items` list SHALL be refused before anything is written, and so SHALL a
file none of whose items passes the row rules.

The committed file `tests/fixtures/synthetic/azure_demo.json` SHALL cover at least:
- a region group with several sizes and one with a single list price;
- a thin cross-region summary and one with at least 5 regions;
- a Spot price equal to the pay-as-you-go price of the same size;
- a Spot size with no pay-as-you-go listing in its region;
- an unmapped size and a Windows row.

#### Scenario: Unlabelled file refused
- **WHEN** an Azure-shaped file lacks `"_label": "synthetic"`
- **THEN** ingest raises an error and writes nothing

#### Scenario: Nothing stored is refused
- **WHEN** every item in a synthetic Azure file is out of scope or rejected
- **THEN** ingest raises an error and stores no run

#### Scenario: Demo file covers the dashboard cases
- **WHEN** `azure_demo.json` is ingested and normalized into an empty database
- **THEN** its snapshot has a multi-size region group, a single-price group, a thin and a non-thin summary, a Spot row equal to its pay-as-you-go price, a Spot row whose size has no pay-as-you-go listing in its region, a row excluded as `unmapped_sku` and a row excluded as `windows`

### Requirement: Synthetic Azure runs
Each synthetic Azure snapshot file SHALL be ingested, in one transaction, as one `azure-retail`
run labelled `synthetic` and `succeeded`, started at the file's `observed_at`. Its items SHALL
pass the same row rules as live ingest (scope, rejection, repeats and flags). It SHALL write:
- one raw response recording the file's repository-relative path, SHA-256 and byte length, with
  a `file:` request URL;
- one price observation and one `azure_retail_price` row per stored item, timed at
  `observed_at`;
- a run summary and tallies whose counts equal what was stored, rejected and flagged.

The existing synthetic command SHALL accept these files beside marketplace snapshot files,
telling them apart by shape. Synthetic Azure runs SHALL go to `data/synthetic.duckdb` by default
and never to `data/monitor.duckdb`. Ingesting a run that is already stored SHALL be refused.

#### Scenario: Snapshot stored as a synthetic Azure run
- **WHEN** a valid synthetic Azure file is ingested into an empty database
- **THEN** one `azure-retail` run labelled `synthetic` exists, its observations trace to a raw response whose SHA-256 matches the file, and its summary counts equal the stored rows

#### Scenario: Same row rules as live ingest
- **WHEN** a synthetic Azure file holds a non-primary meter item
- **THEN** the item is rejected as `not_primary_meter` and counted in the run's tallies

#### Scenario: Live database refused
- **WHEN** the synthetic command is given `data/monitor.duckdb`
- **THEN** it refuses with exit code 2 and writes nothing

### Requirement: Synthetic demo history
The repository SHALL commit two more synthetic Azure snapshot files, observed at 2026-09-28
09:00 UTC and 2026-10-05 09:00 UTC, that come before `azure_demo.json` (2026-10-12 09:00 UTC)
and leave it unchanged. Ingested and normalized in date order into one database, the three
SHALL hold at least:
- one price change between 2026-10-05 and 2026-10-12: the US East H100 ×8 pay-as-you-go listing
  (`Standard_ND96isr_H100_v5`) goes from 88 to 96 USD per VM-hour;
- one listing present on 2026-09-28 and 2026-10-05 and missing on 2026-10-12, which is
  "absent once (unconfirmed)";
- one listing present only on 2026-09-28, which is "not listed" since 2026-10-05;
- no Spot price above the same size's pay-as-you-go price in its region, in any snapshot.

Every item outside these cases SHALL match `azure_demo.json`. The fixtures README SHALL list each
case and its known answers, worked out by hand before the test is written. `azure_history`
SHALL stay the end-to-end test fixture.

#### Scenario: Demo history known answers
- **WHEN** the three demo snapshots are ingested and normalized in date order into an empty database
- **THEN** the history as of the 2026-10-12 snapshot shows the US East H100 ×8 pay-as-you-go change from 11.0000 to 12.0000 USD/GPU-h, one listing absent once and one not listed since 2026-10-05, and every count equals the fixtures README

#### Scenario: Latest snapshot unchanged
- **WHEN** the dashboard reads the demo database
- **THEN** its latest snapshot is the 2026-10-12 run built from the unchanged `azure_demo.json`, so the "Demo file covers the dashboard cases" checks still hold

#### Scenario: No Spot above pay-as-you-go
- **WHEN** any of the three demo snapshots is normalized
- **THEN** no Spot USD/GPU-hour is above the same size's pay-as-you-go USD/GPU-hour in the same region

