## MODIFIED Requirements

### Requirement: Every observation normalized or excluded
For each price observation, normalizing SHALL write exactly one `normalized_price` row per rule
version.

An Azure observation SHALL be excluded with the first matching reason in this order:
- `rental_type_not_compared`: rental type other than `on_demand` or `spot`;
- `government_cloud`: region starts with `usgov` or `usdod`;
- `windows`: the product name's last word is `Windows` or `Win`;
- `unit_not_hourly`: price unit other than exactly `1 Hour`, compared as stored, with no change
  of case or plural;
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

#### Scenario: Unit must be exactly 1 Hour
- **WHEN** Linux `on_demand` observations of a mapped size in a commercial region have price units `1 Hour`, `1 hour`, `1 Hours` and `100 Hours`
- **THEN** the first is normalized and the other three are excluded as `unit_not_hourly`, with no USD/GPU-hour

#### Scenario: First matching reason wins past the first
- **WHEN** an `on_demand` observation of a mapped size in a commercial region has a product name ending `Windows` and price unit `1/Day`
- **THEN** its single row has reason `windows`, not `unit_not_hourly`
