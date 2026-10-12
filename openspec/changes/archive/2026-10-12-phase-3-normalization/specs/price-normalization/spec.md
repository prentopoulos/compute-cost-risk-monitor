## ADDED Requirements

### Requirement: GPU size map from Microsoft Learn
The package SHALL ship map version `gpu-map-v1` as a CSV built only from Microsoft Learn VM size
pages. Each row SHALL record:
- the ARM size name;
- the GPU variant label;
- form factor, when Learn names one;
- per-GPU memory in GB;
- GPU count, as a whole number or a fraction;
- a `learn.microsoft.com` source URL;
- notes with the retrieval date.

A size SHALL be mapped only when its exact ARM size name appears on the cited page. The map SHALL
carry the credit "Contains material from Microsoft Learn, licensed CC BY 4.0". Loading SHALL fail
on a missing column, a duplicate size, a URL outside `learn.microsoft.com`, or a GPU count or
memory that is not greater than zero.

#### Scenario: Map loads
- **WHEN** the packaged map is loaded
- **THEN** every row has a variant label, a GPU count greater than zero and a Learn URL, and no size appears twice

#### Scenario: Fractional count parsed
- **WHEN** a map row gives GPU count `1/4`
- **THEN** it loads as 0.25 and the size is treated as fractional

#### Scenario: Invalid map refused
- **WHEN** a map file has a duplicate size, a non-Learn URL, or GPU count 0
- **THEN** loading raises an error naming the row, and nothing is written

#### Scenario: Labels follow the variant rule
- **WHEN** the map is loaded
- **THEN** every label has the form `<model>[ <form factor>] <memory>GB` (optionally followed by `confidential`), and the label's memory equals the row's per-GPU memory

### Requirement: Frozen rule set
Rule version `groups-v1` SHALL be a constant in code that holds every parameter the
normalization and group rules read:
- compared rental types;
- exclusion order;
- government-region prefixes;
- Windows product suffixes;
- hourly unit;
- retirements, with dates and URLs;
- stale and thin thresholds;
- the absence count for "not listed";
- the exclusions text;
- the map version.

Normalizing SHALL store the rule set in `rule_set` when absent. When a stored rule set or map row
with the same version differs from the code, normalizing SHALL refuse and write nothing.

#### Scenario: First run stores the rules and map
- **WHEN** normalize runs on a database with no rule set
- **THEN** `rule_set` holds `groups-v1` with the code's parameters and `gpu_sku_map` holds every `gpu-map-v1` row

#### Scenario: Changed rules refused
- **WHEN** the stored `groups-v1` parameters differ from the code's, or a stored `gpu-map-v1` row differs from the CSV
- **THEN** normalize exits with code 2, names the difference, and writes no rows

### Requirement: Every observation normalized or excluded
For each price observation, normalizing SHALL write exactly one `normalized_price` row per rule
version.

An Azure observation SHALL be excluded with the first matching reason in this order:
- `rental_type_not_compared`: rental type other than `on_demand` or `spot`;
- `government_cloud`: region starts with `usgov` or `usdod`;
- `windows`: the product name's last word is `Windows` or `Win`;
- `unit_not_hourly`: price unit other than `1 Hour`;
- `unmapped_sku`: size not in the map;
- `fractional_gpu`: mapped GPU count not a whole number;
- `retired_size`: Learn retirement date on or before the snapshot's UTC start date, using a
  region's own date where Learn extends the retirement for that region.

Otherwise the row SHALL be normalized with USD/GPU-hour = price ÷ mapped GPU count, plus the GPU
variant label, GPU count and map reference. Every row SHALL carry the rule set's exclusions text.
An excluded row SHALL have no USD/GPU-hour, and SHALL name the map reference and GPU fields when
the size is mapped. Values SHALL never be filled in to make a row pass.

#### Scenario: Normal Linux pay-as-you-go row
- **WHEN** a Linux `on_demand` observation of a mapped 8-GPU size in a commercial region has price 80
- **THEN** its row has USD/GPU-hour 10, GPU count 8, the size's variant label and no excluded reason

#### Scenario: Exclusion order
- **WHEN** a Windows `dev_test` observation of an unmapped size is normalized
- **THEN** its single row has reason `rental_type_not_compared`

#### Scenario: Government region
- **WHEN** a Linux `spot` observation of a mapped size is in region `usgovvirginia`
- **THEN** it is excluded as `government_cloud`

#### Scenario: Windows by product name
- **WHEN** Linux and Windows `on_demand` observations of one mapped size have product names ending `Series` and `Win`
- **THEN** the first is normalized and the second is excluded as `windows`

#### Scenario: Unmapped size kept with its reason
- **WHEN** a Linux `on_demand` observation names a size absent from the map
- **THEN** its row has reason `unmapped_sku`, no USD/GPU-hour and no map reference

#### Scenario: Fractional size
- **WHEN** a Linux `spot` observation names a size mapped at 1/2 GPU
- **THEN** its row has reason `fractional_gpu`, keeps GPU count 0.5 and the map reference, and has no USD/GPU-hour

#### Scenario: Retired by snapshot date
- **WHEN** a mapped whole-GPU size retired on 2026-09-30 is observed in snapshots started on 2026-09-29 and 2026-10-12
- **THEN** the first is normalized and the second is excluded as `retired_size`

#### Scenario: Regional extension
- **WHEN** a mapped NVv3 size is observed in `uaenorth` and in `westeurope` in a snapshot started on 2026-10-12, with the series retired on 2026-09-30 and UAE North extended to 2027-01-31
- **THEN** the `uaenorth` row is normalized and the `westeurope` row is excluded as `retired_size`

#### Scenario: Non-primary rows never arrive
- **WHEN** a page item has `isPrimaryMeterRegion` false
- **THEN** ingest rejects it as `not_primary_meter` and no `normalized_price` row exists for it

#### Scenario: Idempotent
- **WHEN** normalize runs twice on the same database
- **THEN** the second run writes no rows and reports zero new rows

### Requirement: Independent checks
A checks module that does not import normalization code SHALL validate the stored rows, reading
only the database and the stored rule set:
- USD/GPU-hour × GPU count SHALL equal the observation's price within a relative tolerance of
  1e-9;
- each observation SHALL have exactly one row per rule version;
- an excluded row SHALL have a reason and no USD/GPU-hour, and a normalized row SHALL have no
  reason;
- each Azure row SHALL use the map row for its observation's own size, or name no map row when
  the size is not mapped, and its GPU count and variant SHALL equal that row's;
- each row's reason SHALL equal the first matching reason re-derived from the stored rules, and
  SHALL belong to its source;
- a normalized row SHALL have a compared rental type, a whole GPU count and an hourly unit;
- normalized plus excluded rows SHALL equal the observations, and per run SHALL equal the run
  summary's stored count.

The normalize command SHALL run the checks and exit non-zero when any fails.

#### Scenario: Multiply-back holds
- **WHEN** the checks run after a normalize on known-answer fixtures
- **THEN** every check passes and the report lists each check with its row count

#### Scenario: Tampered row caught
- **WHEN** a stored normalized row's USD/GPU-hour is changed so it no longer multiplies back
- **THEN** the multiply-back check fails, names the row, and the command exits non-zero

#### Scenario: Wrong map row caught
- **WHEN** a stored row for an H100 size names another size's map row and GPU fields, so its figure still multiplies back
- **THEN** the map check fails and names the observation's size

#### Scenario: Wrong reason caught
- **WHEN** a retired size is stored as compared, or a row in a government region is stored with reason `windows`
- **THEN** the re-derived reason check fails and names the reason the rules give

#### Scenario: Missing row caught
- **WHEN** an observation has no row under `groups-v1`
- **THEN** the one-row-per-observation check fails

### Requirement: Normalize command
`uv run python -m compute_cost_risk_monitor.normalize [--db PATH]` SHALL:
- normalize every observation in the database that lacks a `groups-v1` row, in one transaction;
- run the checks;
- print counts only: new rows, rows by status and reason, distinct unmapped sizes, and check
  results.

It SHALL never print prices or USD/GPU-hour values. The default database SHALL be
`data/monitor.duckdb`, anchored to the repository.

#### Scenario: Counts only
- **WHEN** the command runs on a fixture database
- **THEN** its output holds the counts by reason and the check results, and none of the fixture's price values

#### Scenario: Nothing written on failure
- **WHEN** an error occurs part-way through normalizing
- **THEN** the transaction rolls back and no `normalized_price`, `rule_set` or `gpu_sku_map` row from the run remains
