# workload-calculator Specification

## Purpose
Workload cost and labelled budget-exposure scenarios for one listed size in one comparable
group: whole-VM workload inputs, cost with an optional entered storage amount, the frozen
`scenarios-v1` set and a custom change, the Spot to pay-as-you-go fallback, budget headroom,
and an independent check that every figure must pass before it is shown. Scenario
calculations, never forecasts.
## Requirements
### Requirement: Workload inputs
A workload SHALL be:
- total GPUs, an integer that is a whole multiple of the selected group's GPUs per VM, from one
  VM up to 100,000 GPUs;
- hours for the period, a finite number above 0 and at most 8,784;
- optionally, a storage amount in USD for the period, finite, from 0 to 10,000,000.

The validator SHALL refuse a non-multiple GPU count and name the two nearest valid counts, and
SHALL refuse zero, negative, out-of-range and non-finite inputs, with a message saying which input
is wrong. It SHALL never round an input. The VM count SHALL be GPUs ÷ GPUs per VM.

#### Scenario: Whole VMs
- **WHEN** a workload asks for 32 GPUs in a group with 8 GPUs per VM
- **THEN** it is accepted as 4 VMs

#### Scenario: Not a whole number of VMs
- **WHEN** a workload asks for 30 GPUs in a group with 8 GPUs per VM
- **THEN** it is refused with a message naming 24 and 32 as the nearest valid counts

#### Scenario: Impossible inputs refused
- **WHEN** hours are 0, negative, NaN or above 8,784, or storage is negative or infinite
- **THEN** the workload is refused with a message naming the input, and no figure is computed

### Requirement: Starting price
The starting price SHALL be the stored, unrounded USD/GPU-hour of one member of one region group
of an Azure-shaped snapshot (live, recorded or synthetic). It SHALL be the member the user picks,
or the group's lowest listed member (by USD/GPU-hour, then size name) when none is picked. It
SHALL carry its group key, size, published VM-hour price with currency and unit, item key, run ID,
snapshot start time and data label. No entered price and no cross-region statistic SHALL be used.

#### Scenario: Lowest member by default
- **WHEN** a group has two sizes at 0.5 and 0.6 USD/GPU-hour and none is picked
- **THEN** the starting price is 0.5, with that size's provenance

#### Scenario: Picked member
- **WHEN** the user picks the 0.6 USD/GPU-hour size
- **THEN** every figure uses 0.6 and names that size

### Requirement: Workload cost
Compute cost SHALL be GPUs × hours × starting USD/GPU-hour, computed from unrounded values. The
total SHALL be compute cost plus the storage amount when one is entered, and compute cost alone
otherwise. Every cost figure SHALL be stated "for the hours entered" and never converted to a
month.

#### Scenario: Known answer without storage
- **WHEN** a workload of 8 GPUs for 100 hours uses a starting price of 2.5 USD/GPU-hour and no storage
- **THEN** compute cost and total are both USD 2,000

#### Scenario: Known answer with storage
- **WHEN** the same workload enters USD 150 of storage
- **THEN** compute cost is USD 2,000 and the total is USD 2,150

### Requirement: Scenario set scenarios-v1
The scenario set `scenarios-v1` SHALL be frozen in code. Each scenario has an ID, a name, a kind
(a percentage of the starting price or an absolute USD/GPU-hour change), a magnitude and a
one-line narrative:
- `decline-25`, "Decline −25%", −25%;
- `increase-25`, "Increase +25%", +25%;
- `example-050`, "PROJECT example +$0.50/GPU-hour", +0.50 USD/GPU-hour;
- `spike-100`, "Spike +100% (price doubles)", +100%, whose narrative names arXiv 2603.21690 only
  as motivation.

A changed scenario SHALL need a new set version, never an edit in place. Every scenario figure
SHALL carry the set's version, "Scenario calculation, not a forecast" and "Round sensitivities
chosen by judgement, not calibrated to history (one snapshot) or to any model".

#### Scenario: Set contents
- **WHEN** `scenarios-v1` is read
- **THEN** it holds exactly the four scenarios above, including a decline and a spike, each with a narrative

#### Scenario: Frozen set
- **WHEN** code tries to change a scenario of `scenarios-v1`
- **THEN** the change fails

### Requirement: Scenario figures and exposure
For each scenario, the scenario price SHALL be the starting price × (1 + magnitude ÷ 100) for a
percentage, or the starting price + magnitude for a USD change. Each row SHALL report:
- the change in USD/GPU-hour and as % of the starting price;
- the scenario USD/GPU-hour;
- the scenario cost: GPUs × hours × scenario USD/GPU-hour, plus any entered storage, unchanged;
- the exposure: GPUs × hours × (scenario − starting USD/GPU-hour), signed;
- the effect: "additional expense" when positive, "lower expense" when negative and "no change"
  at zero.

A row whose scenario price would be zero or below SHALL be refused ("not computed: the price would
be zero or below") and SHALL carry no figure; it SHALL never be floored. The user MAY add one
custom scenario, a percentage above −100 and up to 1,000 or a USD change from −1,000 to 1,000,
named "Custom: <change> (entered by you, not part of scenarios-v1)".

#### Scenario: PROJECT example
- **WHEN** a workload of 32 GPUs for 720 hours applies `example-050`
- **THEN** the exposure is USD 11,520 and the effect reads "additional expense", whatever the starting price

#### Scenario: Decline
- **WHEN** a workload of 8 GPUs for 100 hours at 2.5 USD/GPU-hour applies `decline-25`
- **THEN** the scenario price is 1.875, the change is −0.625 USD/GPU-hour (−25.0%), the scenario cost is USD 1,500 and the exposure is −USD 500, "lower expense"

#### Scenario: Price would reach zero
- **WHEN** a custom change of −0.50 USD/GPU-hour applies to a starting price of 0.40
- **THEN** that row is "not computed: the price would be zero or below" and has no exposure

### Requirement: Spot to pay-as-you-go fallback
For a Spot starting member, the scenario rows SHALL add "Spot to pay-as-you-go fallback". It uses
the pay-as-you-go member of the same snapshot with the same variant, GPU count, region and size
name, and its exposure = GPUs × hours × (pay-as-you-go − Spot USD/GPU-hour). The row SHALL be
labelled "crosses rental types (Spot → pay-as-you-go)" and name both group keys. When no such
member exists, the row SHALL read "not computed: no pay-as-you-go listing for this size in this
region" and carry no figure. The row SHALL not appear for a pay-as-you-go starting member.

#### Scenario: Fallback priced
- **WHEN** a Spot size at 1.0 USD/GPU-hour is listed on pay-as-you-go at 4.0 in the same region, for 8 GPUs and 10 hours
- **THEN** the fallback exposure is USD 240, labelled as crossing rental types with both keys

#### Scenario: Equal prices
- **WHEN** the Spot price equals the same size's pay-as-you-go price
- **THEN** the fallback exposure is 0 and reads "no change"

#### Scenario: No pay-as-you-go listing
- **WHEN** the Spot size has no pay-as-you-go listing in its region
- **THEN** the fallback row reads "not computed" and no price is filled in

### Requirement: Spot price above pay-as-you-go
When a Spot scenario price, custom price or headroom price is above the same size's pay-as-you-go
list price in the same region, the row SHALL keep its arithmetic and carry the note "Above this
size's pay-as-you-go list price (USD x/GPU-hour). With max price −1 Azure charges at most the
pay-as-you-go price; with a lower max price the VM is evicted. This row shows the scenario's
arithmetic, not what Azure would bill. See 'Spot to pay-as-you-go fallback'." No row SHALL be
capped or refused for this reason. A size with no pay-as-you-go listing SHALL get no note.

#### Scenario: Note on a crossing row
- **WHEN** a Spot size equal to its pay-as-you-go price applies `increase-25`
- **THEN** the row keeps its computed exposure and carries the note

#### Scenario: No note below pay-as-you-go
- **WHEN** a Spot size at 30% of its pay-as-you-go price applies `spike-100`
- **THEN** the row carries no note

### Requirement: Budget headroom
Given a budget B in USD, above 0 and at most 10,000,000,000, and a valid workload, the headroom
SHALL be c = B ÷ (GPUs × hours), the rise in USD per GPU-hour that would use up B. It SHALL also be
given as % of the starting price, and worded "A rise of USD c per GPU-hour (p% of starting price)
would use up USD B over G GPUs × H h. Storage unchanged. Scenario calculation, not a forecast". An
empty budget SHALL give no figure, and 0 SHALL be refused.

#### Scenario: Known headroom
- **WHEN** the budget is USD 11,520 for 32 GPUs over 720 hours
- **THEN** the headroom is USD 0.50 per GPU-hour

#### Scenario: Zero budget
- **WHEN** the budget is 0
- **THEN** it is refused with "enter an amount above zero" and no figure is shown

### Requirement: Independent check of workload figures
A check module that imports no calculator code SHALL re-derive every workload figure from
plain values. Its inputs are:
- GPUs, hours and the storage entered;
- the member the page picked, with its item key, VM-hour price and GPUs per VM;
- the pay-as-you-go member's VM-hour price;
- the budget;
- `scenarios-v1`'s definitions.

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
- every figure is finite.

Figures SHALL be shown only when every check passes.

#### Scenario: Correct result passes
- **WHEN** the calculator's result for a known workload is checked
- **THEN** every check passes

#### Scenario: Tampered figure caught
- **WHEN** one exposure in a result is changed by one cent
- **THEN** the check fails and names that row

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

