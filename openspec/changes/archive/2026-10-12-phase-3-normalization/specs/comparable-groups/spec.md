## ADDED Requirements

### Requirement: Region groups
For a snapshot, a region group SHALL be the normalized rows sharing a GPU variant, GPU count,
region and rental type. Each group SHALL report:
- its key;
- the snapshot's run ID and start time;
- every member, with its size (or offer ID), USD/GPU-hour and observation key;
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

### Requirement: Cross-region summary
For a snapshot, a cross-region summary SHALL cover the region groups sharing a GPU variant, GPU
count and rental type. Each region SHALL contribute its lowest member, named, with ties going to
the lexically first size. The summary SHALL report:
- region count;
- minimum, median and maximum of the contributions;
- the label `lowest listed per region`;
- the label `crosses regions`;
- the exclusions text.

It SHALL be labelled `thin` when it has fewer than 5 regions. The median of an even count SHALL be
the mean of the two middle values. No mean of all contributions SHALL be reported.

#### Scenario: Known-answer summary
- **WHEN** five regions' lowest members have USD/GPU-hour 1, 2, 3, 4 and 10
- **THEN** the summary reports 5 regions, min 1, median 3 and max 10, and is not thin

#### Scenario: Region contributes its lowest member
- **WHEN** one region's group holds sizes at 4 and 3 USD/GPU-hour
- **THEN** that region contributes 3 and names the 3-priced size

#### Scenario: Thin summary
- **WHEN** a summary covers 4 regions
- **THEN** it is labelled `thin`

#### Scenario: Even count median
- **WHEN** four regions contribute 1, 2, 3 and 4
- **THEN** the median is 2.5

### Requirement: Marketplace groups count machines
For synthetic marketplace snapshots, a group SHALL be keyed by GPU variant, GPU count, region and
rental type. Each machine SHALL contribute one price, its lowest offer, with ties going to the
lexically first offer ID. Its other offers in the group SHALL be flagged `machine_duplicate` and
left out of the statistics.

The group SHALL report:
- distinct-machine count;
- minimum, median and maximum of the machine prices;
- the label `synthetic`.

It SHALL be labelled `thin` when it has fewer than 5 distinct machines.

#### Scenario: Machine duplicate counted once
- **WHEN** machine M-01 lists two offers in one group at 2.0 and 2.2 USD/GPU-hour, and machine M-02 lists one at 2.4
- **THEN** the group counts 2 machines, uses 2.0 and 2.4, and flags the 2.2 offer `machine_duplicate`

#### Scenario: Thin marketplace group
- **WHEN** a group has offers from 4 distinct machines
- **THEN** it is labelled `thin`

#### Scenario: Synthetic label carried
- **WHEN** any marketplace group is returned
- **THEN** it carries the label `synthetic`
