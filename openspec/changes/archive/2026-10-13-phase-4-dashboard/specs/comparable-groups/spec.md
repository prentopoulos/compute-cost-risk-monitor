## MODIFIED Requirements

### Requirement: Region groups
For a snapshot, a region group SHALL be the normalized rows sharing a GPU variant, GPU count,
region and rental type. Each group SHALL report:
- its key;
- the snapshot's run ID, start time and data label;
- every member, with its size (or offer ID), USD/GPU-hour and observation key;
- each member's published price, currency and price unit as stored with its observation;
- each member's provenance: the run ID, and the raw response's file path, sequence number and
  SHA-256;
- the member count;
- the rule set's exclusions text.

A group with one observation SHALL be labelled `single list price`. Excluded rows SHALL never
appear in a group.

#### Scenario: Several sizes in one group
- **WHEN** a snapshot holds two normalized `on_demand` rows in one region for different sizes with the same variant and GPU count
- **THEN** one region group lists both sizes with their USD/GPU-hour and member count 2

#### Scenario: Single list price
- **WHEN** a region group holds one observation
- **THEN** it is labelled `single list price`

#### Scenario: Different counts never share a group
- **WHEN** a 1-GPU and a 2-GPU size of the same variant are listed in one region
- **THEN** they fall in two region groups

#### Scenario: Only succeeded snapshots
- **WHEN** a partial run holds normalized rows
- **THEN** no group is built from it

#### Scenario: Member carries its source price and provenance
- **WHEN** a 2-GPU size is stored at 7.0 USD per "1 Hour" from raw response sequence 0 of its run
- **THEN** its member reports price 7.0, currency USD, unit "1 Hour", USD/GPU-hour 3.5, and that response's run ID, file path, sequence number and SHA-256
