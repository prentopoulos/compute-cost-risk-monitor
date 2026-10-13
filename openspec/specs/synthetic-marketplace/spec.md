# synthetic-marketplace Specification

## Purpose
Labelled synthetic marketplace snapshots: the file format, ingest as `synthetic` runs
into their own database, and how their offers are normalized. They exercise the
marketplace-only rules; the provider is fictional.
## Requirements
### Requirement: Synthetic snapshot files
A synthetic marketplace snapshot SHALL be a JSON file holding:
- `"_label": "synthetic"`;
- a fictional provider name;
- an `observed_at` UTC time;
- a list of offers, each with offer ID, machine ID, listed GPU name, GPU count, VRAM, country
  code, region, rental type and USD per offer-hour.

A file without the synthetic label, or with a duplicate offer ID, SHALL be refused before
anything is written.

#### Scenario: Unlabelled file refused
- **WHEN** a snapshot file lacks `"_label": "synthetic"`
- **THEN** ingest raises an error and writes nothing

#### Scenario: Duplicate offer ID refused
- **WHEN** a snapshot file lists offer S-1 twice
- **THEN** ingest raises an error and writes nothing

### Requirement: Synthetic runs
Each snapshot file SHALL be ingested, in one transaction, as one `synthetic-marketplace` run
labelled `synthetic` and `succeeded`, started at the file's `observed_at`. It SHALL write:
- one raw response recording the file's repository-relative path, SHA-256 and byte length;
- one price observation and one `marketplace_offer` row per offer, keyed by offer ID and timed at
  `observed_at`;
- a run summary whose counts equal the offers stored.

Synthetic runs SHALL go to `data/synthetic.duckdb` by default and never to `data/monitor.duckdb`.
Ingesting a run that is already stored SHALL be refused.

#### Scenario: Snapshot stored as synthetic
- **WHEN** a valid snapshot file with 6 offers is ingested into an empty database
- **THEN** one run labelled `synthetic` with 6 observations exists, and each observation traces to a raw response whose SHA-256 matches the file

#### Scenario: Default database is separate
- **WHEN** synthetic ingest runs without a database path
- **THEN** it writes to `data/synthetic.duckdb`, and refuses the path `data/monitor.duckdb`

### Requirement: Marketplace normalization
A marketplace observation SHALL be excluded as `rental_type_not_compared` when its rental type is
not `on_demand` or `spot`. It SHALL be excluded as `unmapped_gpu_name` when its listed GPU name is
not in the synthetic name map, or its VRAM differs from the mapped variant's. Otherwise its
USD/GPU-hour SHALL be the offer price ÷ GPU count, with the mapped variant label and GPU count,
and no `gpu_sku_map` reference.

#### Scenario: Two-GPU offer
- **WHEN** an `on_demand` offer for 2 × "H100 SXM" (80 GB) costs 4.0 per hour
- **THEN** its row has USD/GPU-hour 2.0, GPU count 2 and the name map's variant label

#### Scenario: Unknown GPU name
- **WHEN** an offer lists GPU name "Mystery 9000"
- **THEN** its row is excluded as `unmapped_gpu_name`

#### Scenario: VRAM mismatch
- **WHEN** an offer lists "A100" with 40 GB but the name map gives that name 80 GB
- **THEN** its row is excluded as `unmapped_gpu_name`

