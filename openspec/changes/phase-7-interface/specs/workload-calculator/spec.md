## ADDED Requirements

### Requirement: Scenario ladder ladder-v1
The scenario ladder set `ladder-v1` SHALL be frozen in code, in the same module as
`scenarios-v1`. It holds eight steps, in this order:
- seven percentages of the starting price: −50, −25, −10, +10, +25, +50 and +100;
- one absolute change of +0.50 USD per GPU-hour.

A changed step SHALL need a new set version, never an edit in place.

For a valid workload, the ladder SHALL have:
- **rows:** one per step. Then, for a Spot starting member, a "Spot → pay-as-you-go" row priced
  from the same size's pay-as-you-go listing in the same region, marked as crossing rental types.
  Then, when a custom move is entered, a "Custom" row priced like the custom scenario. This is
  the order of the `scenarios-v1` rows;
- **columns:** 8, 16, 32, 64 and 128 GPUs, plus the entered GPU count when it is not one of
  them, in ascending order. The column for the entered count is marked as entered, whether or not
  it is one of the defined counts. A defined column whose GPU count is not a whole multiple of the
  group's GPUs per VM SHALL be left out;
- **cells:** each cell SHALL be column GPUs × hours entered × (scenario − starting USD/GPU-hour),
  signed and computed from unrounded values. A percentage step's change is starting price × step
  ÷ 100, and a USD step's change is its magnitude exactly. Cells are stated for the hours
  entered, never as a month. Storage is unchanged and not in the cells.

A row whose scenario price would be zero or below SHALL be refused ("not computed: the price
would be zero or below") and carry no cells. A fallback row with no pay-as-you-go listing SHALL
read "not computed: no pay-as-you-go listing for this size in this region" and carry no cells. No
row SHALL be floored or filled in.

For a Spot starting member, a row whose scenario price is above the same size's pay-as-you-go
list price in the same region SHALL be marked, and the above-pay-as-you-go note SHALL accompany
the ladder. No row SHALL be capped or refused for this reason.

The ladder SHALL carry `ladder-v1`, "Scenario calculation, not a forecast" and "Round
sensitivities chosen by judgement, not calibrated to history (one snapshot) or to any model".

#### Scenario: Set contents
- **WHEN** `ladder-v1` is read
- **THEN** it holds exactly the seven percentage steps and the +0.50 USD/GPU-hour step above, in that order

#### Scenario: Frozen set
- **WHEN** code tries to change a step of `ladder-v1`
- **THEN** the change fails

#### Scenario: Known cells
- **WHEN** a workload of 32 GPUs for 720 hours starts at 2.5 USD/GPU-hour
- **THEN** the 32-GPU cells are 14,400 at +25%, −28,800 at −50%, 57,600 at +100% and 11,520 at +0.50 USD, and the 8-GPU cell at +10% is 1,440

#### Scenario: Entered count added
- **WHEN** a workload of 24 GPUs is entered in a group with 8 GPUs per VM
- **THEN** the columns are 8, 16, 24, 32, 64 and 128 GPUs, with 24 marked as entered

#### Scenario: Matches scenarios-v1
- **WHEN** the ladder and `scenarios-v1` are computed for the same workload
- **THEN** the entered column's −25%, +25%, +100% and +0.50 USD cells equal the `decline-25`, `increase-25`, `spike-100` and `example-050` exposures

#### Scenario: Custom row refused
- **WHEN** a custom change of −0.50 USD/GPU-hour is entered for a starting price of 0.40
- **THEN** the Custom row reads "not computed: the price would be zero or below" and has no cells

#### Scenario: Fallback row
- **WHEN** a Spot size at 1.0 USD/GPU-hour is listed on pay-as-you-go at 4.0 in the same region, for 8 GPUs and 10 hours
- **THEN** the "Spot → pay-as-you-go" row's 8-GPU cell is 240, and the row is marked as crossing rental types

#### Scenario: Spot row above pay-as-you-go
- **WHEN** a Spot size at 60% of its pay-as-you-go price is laddered
- **THEN** only the +100% row (120% of pay-as-you-go) is marked among the percentage rows, it keeps its computed cells, and the above-pay-as-you-go note accompanies the ladder

## MODIFIED Requirements

### Requirement: Independent check of workload figures
A check module that imports no calculator code SHALL re-derive every workload figure from
plain values. Its inputs are:
- GPUs, hours and the storage entered;
- the member the page picked, with its item key, VM-hour price and GPUs per VM;
- the pay-as-you-go member's VM-hour price;
- the budget;
- `scenarios-v1`'s and `ladder-v1`'s definitions.

It SHALL use the calculator's two pricing formulas: a percentage multiplies the starting
price, and a USD scenario's change is its magnitude exactly. Tolerances SHALL be a relative
1e-9 of each figure's own scale (GPU-hours times the larger of the starting and scenario
prices); a storage amount added to a cost SHALL widen a tolerance only by that sum's
rounding. It SHALL check that:
- the figures were priced from the member the page picked;
- VM-hour price ÷ GPUs per VM equals the starting USD/GPU-hour;
- VM-hour price × VMs × hours equals compute cost;
- the storage shown equals the storage entered, and total = compute + storage;
- each scenario price matches its kind and magnitude;
- exposure equals both GPUs × hours × change and scenario cost − starting cost;
- each row's effect matches the sign of its exposure, and a refused row reads "not computed";
- a row is refused exactly when its price is zero or below, either way within rounding of
  zero;
- the fallback matches the pay-as-you-go VM-hour price;
- the above-pay-as-you-go note appears exactly on Spot rows above that price, and on no other
  row;
- GPUs × hours × headroom equals the budget;
- the ladder's rows are exactly `ladder-v1`'s steps, then the fallback row for a Spot start,
  then the Custom row when a custom move is entered;
- the ladder's columns are exactly the defined GPU counts that are whole multiples of GPUs per
  VM, plus the entered count;
- each ladder cell equals (column GPUs ÷ GPUs per VM) × hours × (scenario − starting VM-hour
  price), and a refused ladder row carries no cells exactly when its price is zero or below or
  its pay-as-you-go listing is missing;
- the ladder's above-pay-as-you-go marks are exactly on Spot rows priced above that price;
- every figure is finite.

Figures SHALL be shown only when every check passes.

#### Scenario: Correct result passes
- **WHEN** the calculator's result for a known workload is checked
- **THEN** every check passes

#### Scenario: Tampered figure caught
- **WHEN** one exposure in a result is changed by one cent
- **THEN** the check fails and names that row

#### Scenario: Tampered ladder cell caught
- **WHEN** one ladder cell is changed by one cent
- **THEN** the check fails and names that row and column

#### Scenario: Ladder column dropped or added
- **WHEN** a ladder column is missing, or holds a count that is not a whole multiple of GPUs per VM
- **THEN** the check fails on the ladder's columns

#### Scenario: Large storage hides no cent
- **WHEN** USD 10,000,000 of storage is entered and one row's cost and exposure are each changed by one cent
- **THEN** the check fails and names that row's cost and exposure

#### Scenario: Valid extreme change passes
- **WHEN** a custom change of −99.99999% is applied across many starting prices
- **THEN** every result passes the check

#### Scenario: Result from another member caught
- **WHEN** the figures were priced from a different size than the one the page picked
- **THEN** the check fails on the starting member

#### Scenario: Independent of the calculator
- **WHEN** the check module's imports are inspected
- **THEN** it imports nothing from `calculator.py`

### Requirement: Budget headroom
Given a budget B in USD, from 0.01 to 10,000,000,000, and a valid workload, the headroom
SHALL be c = B ÷ (GPUs × hours), the rise in USD per GPU-hour that would use up B. It SHALL also be
given as % of the starting price, and worded "A rise of USD c per GPU-hour (p% of starting price)
would use up USD B over G GPUs × H h. Storage unchanged. Scenario calculation, not a forecast".
The page shows the figure as its "Headroom, USD/GPU-h" key figure and the sentence in its Sources
section. An empty budget SHALL give no figure, 0 SHALL be refused, and a budget below 0.01 SHALL
be refused.

#### Scenario: Known headroom
- **WHEN** the budget is USD 11,520 for 32 GPUs over 720 hours
- **THEN** the headroom is USD 0.50 per GPU-hour

#### Scenario: Zero budget
- **WHEN** the budget is 0
- **THEN** it is refused with "enter an amount above zero" and no figure is shown

#### Scenario: Budget below a cent
- **WHEN** the budget is USD 5e-324
- **THEN** it is refused with "Budget must be at least USD 0.01.", because its headroom would underflow to zero
