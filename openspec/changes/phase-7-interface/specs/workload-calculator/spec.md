## ADDED Requirements

### Requirement: Scenario ladder ladder-v1
The scenario ladder set `ladder-v1` SHALL be frozen in code, in the same module as
`scenarios-v1`. It holds seven steps, each a percentage of the starting price: −50, −25, −10,
+10, +25, +50 and +100. A changed step SHALL need a new set version, never an edit in place.

For a valid workload, the ladder SHALL have:
- **rows:** one per step;
- **columns:** 8, 16, 32, 64 and 128 GPUs, plus the entered GPU count when it is not one of
  them, in ascending order. The column for the entered count is marked as entered, whether or not
  it is one of the defined counts. A defined column whose GPU count is not a whole multiple of the
  group's GPUs per VM SHALL be left out.
- **cells:** each cell's exposure SHALL be column GPUs × hours entered × starting USD/GPU-hour ×
  step ÷ 100, signed and computed from unrounded values. It is stated "for the hours entered",
  never as a month. Storage is unchanged and not in the cells.

For a Spot starting member, a row whose scenario price (starting price × (1 + step ÷ 100)) is
above the same size's pay-as-you-go list price in the same region SHALL be marked, and the
above-pay-as-you-go note SHALL accompany the ladder. No row SHALL be capped or refused for this
reason.

The ladder SHALL carry `ladder-v1`, "Scenario calculation, not a forecast" and "Round
sensitivities chosen by judgement, not calibrated to history (one snapshot) or to any model".

#### Scenario: Set contents
- **WHEN** `ladder-v1` is read
- **THEN** it holds exactly the seven steps above, as percentages

#### Scenario: Frozen set
- **WHEN** code tries to change a step of `ladder-v1`
- **THEN** the change fails

#### Scenario: Known cells
- **WHEN** a workload of 32 GPUs for 720 hours starts at 2.5 USD/GPU-hour
- **THEN** the 32-GPU cells are 14,400 at +25%, −28,800 at −50% and 57,600 at +100%, and the 8-GPU cell at +10% is 1,440

#### Scenario: Entered count added
- **WHEN** a workload of 24 GPUs is entered in a group with 8 GPUs per VM
- **THEN** the columns are 8, 16, 24, 32, 64 and 128 GPUs, with 24 marked as entered

#### Scenario: Matches the scenario table
- **WHEN** the ladder and `scenarios-v1` are computed for the same workload
- **THEN** the entered column's +25% and +100% cells equal the `increase-25` and `spike-100` exposures, and its −25% cell equals `decline-25`'s

#### Scenario: Spot row above pay-as-you-go
- **WHEN** a Spot size at 60% of its pay-as-you-go price is laddered
- **THEN** only the +100% row (120% of pay-as-you-go) is marked, it keeps its computed cells, and the above-pay-as-you-go note accompanies the ladder

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
- the ladder's rows are exactly `ladder-v1`'s steps, and its columns are exactly the defined
  GPU counts that are whole multiples of GPUs per VM, plus the entered count;
- each ladder cell equals (column GPUs ÷ GPUs per VM) × VM-hour price × hours × step ÷ 100;
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
- **THEN** the check fails and names that step and column

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
