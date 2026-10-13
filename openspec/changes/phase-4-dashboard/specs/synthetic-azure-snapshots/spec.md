## ADDED Requirements

### Requirement: Synthetic Azure snapshot files
A synthetic Azure snapshot SHALL be a JSON file shaped like one Azure Retail Prices API page
(`Items`, with `NextPageLink` null) that also holds `"_label": "synthetic"` and an `observed_at`
time with a time zone. Its prices SHALL be invented; its size names MAY be real Azure names so
the packaged GPU map applies. A file without the synthetic label, without a valid `observed_at`,
or without a non-empty `Items` list SHALL be refused before anything is written.

The committed file `tests/fixtures/synthetic/azure_demo.json` SHALL cover at least:
- a region group with several sizes and one with a single list price;
- a thin cross-region summary and one with at least 5 regions;
- a Spot price equal to the pay-as-you-go price of the same size;
- an unmapped size and a Windows row.

#### Scenario: Unlabelled file refused
- **WHEN** an Azure-shaped file lacks `"_label": "synthetic"`
- **THEN** ingest raises an error and writes nothing

#### Scenario: Demo file covers the dashboard cases
- **WHEN** `azure_demo.json` is ingested and normalized into an empty database
- **THEN** its snapshot has a multi-size region group, a single-price group, a thin and a non-thin summary, a Spot row equal to its pay-as-you-go price, a row excluded as `unmapped_sku` and a row excluded as `windows`

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
