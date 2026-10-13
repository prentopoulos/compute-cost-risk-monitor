## ADDED Requirements

### Requirement: Workload cost view
The page SHALL have a fourth lazy tab, "Workload cost", after "Comparable groups". It SHALL use
the region group chosen by the sidebar filters and show:
- the starting member, with a size choice when the group has several members;
- the workload inputs: GPUs (minimum and step equal to GPUs per VM, default 32, with the VM
  count shown), hours (default 720, with help text "720 h = 30 days; Microsoft's pricing
  calculator uses 730 h for a month") and an optional storage amount;
- the custom scenario inputs and an optional budget for headroom;
- a cost breakdown (compute, storage, total), the scenario table and a bar chart of exposure per
  computed scenario row with a rule at zero.

The view SHALL behave as follows:
- **Inputs:** they SHALL be keyed and keep their values when the user switches tabs. The size
  choice SHALL be remembered per group, starting at the group's lowest listed member.
- **Marketplace source:** when "Synthetic marketplace" is the selected source, the tab SHALL
  show only a note that the calculator uses Azure list-price groups and that the marketplace
  data exercises the data-quality rules.
- **Other states:** with no snapshot, a snapshot that is not normalized, or no groups, the tab
  SHALL show the same states as the "Comparable groups" tab and no figure.
- **Invalid input:** the tab SHALL show the validator's message and no figure.
- **Failed check:** when the independent check fails, the tab SHALL show "The independent check
  failed: <checks>. No figures are shown." and no figure.

The starting price SHALL appear only with the checked figures, under the cost table's caption,
so no price is ever shown with a refused input or a failed check.

#### Scenario: Known workload on the demo
- **WHEN** the synthetic demo is open on an H100 ×8 pay-as-you-go group with 32 GPUs and 720 hours
- **THEN** the tab shows 4 VMs, the compute cost, and the PROJECT example row with exposure USD 11,520.00 labelled "Scenario calculation, not a forecast"

#### Scenario: Inputs kept across tabs
- **WHEN** the user enters 16 GPUs, opens "Group browser" and returns to "Workload cost"
- **THEN** the GPU input still holds 16

#### Scenario: No price before the check
- **WHEN** the budget entered is 0, or the independent check fails
- **THEN** the tab shows the message and no price, not even the starting price

#### Scenario: Marketplace source
- **WHEN** the synthetic marketplace source is selected
- **THEN** the tab shows the note and no workload figure

#### Scenario: Not normalized
- **WHEN** the latest snapshot is not normalized
- **THEN** the tab withholds its figures, as the group views do

#### Scenario: Fallback not computed on the demo
- **WHEN** the demo's uksouth H100 ×8 Spot group is chosen
- **THEN** the fallback row reads "not computed: no pay-as-you-go listing for this size in this region"

## MODIFIED Requirements

### Requirement: Figure captions and framing line
Every table and chart that shows a price or statistic SHALL carry a caption with:
- its group key, or "crosses regions" with the variant, GPU count and rental type, or "crosses
  rental types (Spot → pay-as-you-go)" with both group keys;
- the snapshot's start time in UTC and run ID;
- the data label;
- the full exclusions text.

Every workload cost, scenario and headroom figure SHALL also carry:
- the storage line: "Storage: USD X entered by you for this period, not an Azure list price and
  not checked against Azure disk prices. The total adds it; every other exclusion still applies."
  when storage is entered, and "Storage not included." otherwise;
- the billing assumptions line: "Assumes each VM is allocated for exactly the hours entered.
  Azure bills full minutes while a VM is allocated, including Stopped (allocated); only Stopped
  (deallocated) ends compute billing. Every VM has an OS disk, billed as storage and not in the
  GPU price; add it under storage.";
- for a Spot group, the Spot line: "Spot: Azure can evict these VMs at any time with 30 seconds'
  notice and gives no SLA, and the Spot price is variable. This figure assumes every hour entered
  runs at this listed Spot price; evicted hours may not be delivered, and an evicted VM that is
  deallocated still bills for its disks.".

Every exposure and headroom figure SHALL also carry "Scenario calculation, not a forecast". Every
scenario figure SHALL also carry the scenario set version and "Round sensitivities chosen by
judgement, not calibrated to history (one snapshot) or to any model".

The page SHALL show a framing line under its title "Compute Cost & Risk Monitor":
- for a `live` or `recorded` snapshot: "Published Azure retail list prices for GPU VMs ·
  <label> · snapshot <UTC> · local analysis only";
- for a `synthetic` snapshot: "Synthetic data: invented prices for demonstration, not Azure list
  prices · snapshot <UTC>";
- when the snapshot is stale: "STALE (older than 7 days as of <UTC>)" added.

The as-of time SHALL be read from the clock once per page run by the app entry point and passed
in; tests SHALL inject it.

#### Scenario: Every figure captioned
- **WHEN** any group, summary or chart is shown
- **THEN** its caption holds the group key or "crosses regions", the snapshot time and run ID, the data label and the exclusions text

#### Scenario: Synthetic framing
- **WHEN** the latest snapshot is labelled `synthetic`
- **THEN** the framing line says the prices are invented and are not Azure list prices

#### Scenario: Stale as of an injected time
- **WHEN** the latest snapshot started 8 days before the injected as-of time
- **THEN** the framing line shows STALE with that as-of time

#### Scenario: Workload figures captioned
- **WHEN** the cost breakdown, scenario table or exposure chart is shown for a Spot group with no storage entered
- **THEN** its caption holds the group key, snapshot time and run ID, data label, exclusions text, "Storage not included.", the billing assumptions line and the Spot line, and the scenario table and chart also hold `scenarios-v1`, "Scenario calculation, not a forecast" and the judgement note

#### Scenario: Fallback captioned as crossing
- **WHEN** the Spot to pay-as-you-go fallback row is shown
- **THEN** its caption says "crosses rental types (Spot → pay-as-you-go)" and names both group keys

### Requirement: Display formatting
The dashboard SHALL display USD/GPU-hour and statistics with 4 decimal places, the published
price at its full stored precision, USD amounts with 2 decimal places and thousands separators,
percentages with 1 decimal place, and times in UTC. It SHALL format values only for display and
never compute from rounded values.

#### Scenario: Four decimals for USD/GPU-hour
- **WHEN** a member's USD/GPU-hour is 12.291267
- **THEN** it is displayed as 12.2913, and the stored value is unchanged

#### Scenario: USD amounts and percentages
- **WHEN** an exposure is 11520 and a change is 33.3333% of the starting price
- **THEN** they are displayed as 11,520.00 and 33.3%, and the computed values are unchanged
