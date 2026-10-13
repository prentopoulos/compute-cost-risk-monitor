## MODIFIED Requirements

### Requirement: Price changes
A price change SHALL be the same key observed in two consecutive snapshots with different
prices. The key SHALL be the item key for Azure, and the continuity key for marketplace offers:
machine ID, GPU name, GPU count, region and rental type. Each change SHALL report:
- both observations;
- both prices in the source's unit;
- both USD/GPU-hour values, when both rows are normalized;
- the comparable group of the later row, when it is normalized.

Equal prices SHALL NOT be a change. A key missing from one of the two snapshots SHALL NOT be a
change, so a listing that returns after an absence at a different price is not reported as one.

#### Scenario: Azure price change
- **WHEN** an item key has price 10 in one snapshot and 12 in the next
- **THEN** one change is reported, linking both observations, with prices 10 and 12

#### Scenario: Unchanged price
- **WHEN** an item key has the same price in consecutive snapshots
- **THEN** no change is reported

#### Scenario: Re-listed offer is a continuing offer
- **WHEN** machine M-01's offer S-1 at 2.0 is replaced in the next snapshot by offer S-9 with the same GPU, count, region and rental type at 2.2
- **THEN** one change from 2.0 to 2.2 is reported, with no new offer and no absence

#### Scenario: Return at a new price is not a change
- **WHEN** an item key has price 10 in snapshot 1, is missing from snapshot 2 and has price 12 in snapshot 3
- **THEN** no change is reported between snapshots 2 and 3, and the listing is neither absent nor `not listed` as of snapshot 3

### Requirement: Absences and not listed
A listing SHALL be absent from a snapshot when it was present in the previous one and is missing
from this one. The listing key SHALL be (size, region, rental type, OS) for Azure, and the
continuity key for marketplace offers.
- After one absence, it SHALL be reported as `absent once (unconfirmed)`.
- After absence from 2 or more consecutive snapshots, it SHALL be reported as `not listed`,
  dated at the first absent snapshot.
- A listing that reappears SHALL stop being absent.

No price SHALL be filled in for an absent listing.

#### Scenario: Absent once
- **WHEN** a listing is present in snapshot 1 and missing from snapshot 2, the latest
- **THEN** it is reported `absent once (unconfirmed)` and not as `not listed`

#### Scenario: Not listed after two absences
- **WHEN** a listing is present in snapshot 1 and missing from snapshots 2 and 3
- **THEN** it is reported `not listed`, dated at snapshot 2's start time

#### Scenario: Reappearance clears the absence
- **WHEN** a listing is present in snapshot 1, missing from 2 and present in 3
- **THEN** it is neither absent nor `not listed` as of snapshot 3

#### Scenario: Meter re-key is not a delisting
- **WHEN** an Azure size keeps its region, rental type and OS but its item key changes between snapshots
- **THEN** the listing is not absent

#### Scenario: Still not listed after three absences
- **WHEN** a listing is present in snapshot 1 and missing from snapshots 2, 3 and 4
- **THEN** it is reported `not listed` as of snapshot 4, still dated at snapshot 2's start time
