## MODIFIED Requirements

### Requirement: Workload inputs
A workload SHALL be:
- total GPUs, an integer that is a whole multiple of the selected group's GPUs per VM, from one
  VM up to 100,000 GPUs;
- hours for the period, a finite number from 0.01 to 8,784;
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
- **WHEN** hours are 0, below 0.01, negative, NaN or above 8,784, or storage is negative or infinite
- **THEN** the workload is refused with a message naming the input, and no figure is computed

#### Scenario: Hours too small to price
- **WHEN** hours are 5e-324, the smallest positive float
- **THEN** the workload is refused with "Hours must be at least 0.01 and at most 8,784.", because a budget's headroom over them would overflow

### Requirement: Budget headroom
Given a budget B in USD, from 0.01 to 10,000,000,000, and a valid workload, the headroom
SHALL be c = B ÷ (GPUs × hours), the rise in USD per GPU-hour that would use up B. It SHALL also be
given as % of the starting price, and worded "A rise of USD c per GPU-hour (p% of starting price)
would use up USD B over G GPUs × H h. Storage unchanged. Scenario calculation, not a forecast". An
empty budget SHALL give no figure, 0 SHALL be refused, and a budget below 0.01 SHALL be refused.

#### Scenario: Known headroom
- **WHEN** the budget is USD 11,520 for 32 GPUs over 720 hours
- **THEN** the headroom is USD 0.50 per GPU-hour

#### Scenario: Zero budget
- **WHEN** the budget is 0
- **THEN** it is refused with "enter an amount above zero" and no figure is shown

#### Scenario: Budget below a cent
- **WHEN** the budget is USD 5e-324
- **THEN** it is refused with "Budget must be at least USD 0.01.", because its headroom would underflow to zero
