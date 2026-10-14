## ADDED Requirements

### Requirement: Desk theme
The committed `src/compute_cost_risk_monitor/.streamlit/config.toml` SHALL set one dark theme:
- `theme.base = "dark"`, with explicit `backgroundColor`, `secondaryBackgroundColor`,
  `textColor`, `primaryColor`, `redColor`, `greenColor` and chart colours;
- no `[theme.light]` or `[theme.dark]` section, no `fontFaces`, and no
  `server.enableStaticServing`. Streamlit's bundled fonts are used and no font is fetched from
  elsewhere;
- `textColor`, `redColor` and `greenColor` each at a contrast of at least 4.5:1 against
  `backgroundColor` and against `secondaryBackgroundColor`.

The page SHALL:
- show no ticker, bid/ask label, animated or flashing value, or "live" badge;
- colour red only for additional expense and green only for lower expense, each always with its
  sign and effect words. Prices, price changes, statistics and "no change" stay neutral;
- take chart colours from the same values as the theme;
- inject no custom CSS.

#### Scenario: Dark theme committed
- **WHEN** the committed config is parsed
- **THEN** the theme base is dark, its colours are set, and it has no light or dark section, no font faces and no static serving

#### Scenario: Contrast floor
- **WHEN** the contrast of the text, red and green colours is computed against both background colours
- **THEN** each ratio is at least 4.5:1

#### Scenario: Colour only for a scenario's effect
- **WHEN** the ladder shows +14,400.00 and −28,800.00 cells
- **THEN** the first is red with its plus sign, the second green with its minus sign, and no price or price-change cell is coloured

#### Scenario: No injected CSS
- **WHEN** the dashboard's source is inspected
- **THEN** it writes no `<style>` element and loads no stylesheet

### Requirement: Answer strips
The Workload cost tab SHALL show, only after the independent check passes, one line above its
other figures:

"Total USD X for the hours entered (G GPUs = V VMs × H h) · starting USD p/GPU-hour, \<size\> ·
largest additional expense: \<scenario name\> +USD y · scenarios-v1 · Scenario calculation, not
a forecast"

Here X is the total, p the starting USD/GPU-hour, \<size\> the starting member, and y the
largest exposure among the computed `scenarios-v1` rows, named by that row. The custom and
fallback rows are not in this maximum. With a refused input or a failed check there is no strip.

The Comparable groups tab SHALL show one line above the region-group table:

"\<group key\> · lowest listed USD p/GPU-hour (\<size or offer ID\>) · members N · \<labels\> ·
snapshot \<UTC\> · run \<ID\> · \<data label\>"

Both strips show only figures already computed and checked, formatted as in "Display
formatting", and refer to their panel's notes.

#### Scenario: Strip on the demo
- **WHEN** the synthetic demo is open on an H100 ×8 pay-as-you-go group with 32 GPUs and 720 hours
- **THEN** the strip shows the total, 32 GPUs = 4 VMs × 720 h, the starting price and size, and names the `scenarios-v1` row with the largest exposure

#### Scenario: No strip before the check
- **WHEN** the input is refused or the independent check fails
- **THEN** no strip and no price is shown

#### Scenario: Group strip
- **WHEN** a region group with two members is chosen
- **THEN** the strip shows its key, the lower member's USD/GPU-hour and size, "members 2", the snapshot time, run ID and data label

## MODIFIED Requirements

### Requirement: Figure captions and framing line
Every table and chart that shows a price or statistic SHALL carry a one-line caption with:
- its group key, or "crosses regions" with the variant, GPU count and rental type, or "crosses
  rental types (Spot → pay-as-you-go)" with both group keys;
- the snapshot's start time in UTC and run ID;
- the data label;
- the numbers of the notes that apply to it.

The full exclusions text SHALL appear as a numbered note directly under the panel that holds the
figure. A panel is one titled section of a tab: a subheader and the figures under it, up to the
next subheader. Notes SHALL be always visible, never in an expander, tooltip or other hidden
element, and in text no smaller or fainter than a caption. Each note's text SHALL appear once per
panel, and every figure in the panel that needs it SHALL refer to its number.

Every workload cost, ladder, scenario and headroom figure SHALL also refer to notes holding:
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

Every exposure, ladder and headroom figure SHALL also carry "Scenario calculation, not a
forecast" on its caption line. Every scenario and ladder figure SHALL also carry its set version
on its caption line, and refer to a note holding "Round sensitivities chosen by judgement, not
calibrated to history (one snapshot) or to any model". When the above-pay-as-you-go note applies,
it SHALL be a numbered note under the panel, and the rows it applies to SHALL name its number.

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
- **THEN** its caption line holds the group key or "crosses regions", the snapshot time and run ID, the data label and its note numbers, and the exclusions text appears in a numbered note directly under its panel

#### Scenario: Notes always visible
- **WHEN** any tab with a price, cost or exposure figure is drawn
- **THEN** every note its figures refer to is on the page outside any expander, and each note's text appears once in its panel

#### Scenario: Synthetic framing
- **WHEN** the latest snapshot is labelled `synthetic`
- **THEN** the framing line says the prices are invented and are not Azure list prices

#### Scenario: Stale as of an injected time
- **WHEN** the latest snapshot started 8 days before the injected as-of time
- **THEN** the framing line shows STALE with that as-of time

#### Scenario: Workload figures captioned
- **WHEN** the ladder, cost breakdown, scenario table or exposure chart is shown for a Spot group with no storage entered
- **THEN** each caption line holds the group key, snapshot time and run ID, data label and note numbers; the panel's notes hold the exclusions text, "Storage not included.", the billing assumptions line and the Spot line; and the ladder, scenario table and chart also carry their set version and "Scenario calculation, not a forecast" on the caption line, with the judgement note among the notes

#### Scenario: Fallback captioned as crossing
- **WHEN** the Spot to pay-as-you-go fallback row is shown
- **THEN** its caption says "crosses rental types (Spot → pay-as-you-go)" and names both group keys

### Requirement: Workload cost view
The page SHALL open on its first lazy tab, "Workload cost", followed by "Comparable groups",
"Group browser" and "Data quality". The tab SHALL use the region group chosen by the sidebar
filters and show:
- the starting member, with a size choice when the group has several members;
- the workload inputs: GPUs (minimum and step equal to GPUs per VM, default 32, with the VM
  count shown), hours (default 720, with help text "720 h = 30 days; Microsoft's pricing
  calculator uses 730 h for a month") and an optional storage amount;
- the custom scenario inputs and an optional budget for headroom;
- after the independent check passes: the answer strip, the scenario ladder, a cost breakdown
  (compute, storage, total), the scenario table, a bar chart of exposure per computed scenario
  row with a rule at zero, and the budget headroom.

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
- **Ladder:** it SHALL be drawn as a plain table of `ladder-v1` steps by GPU counts, with the
  entered column marked and the above-pay-as-you-go rows naming their note.

The starting price SHALL appear only with the checked figures, after the independent check
passes, so no price is ever shown with a refused input or a failed check.

#### Scenario: Opens on Workload cost
- **WHEN** the page is first drawn
- **THEN** "Workload cost" is the first tab and the one shown

#### Scenario: Known workload on the demo
- **WHEN** the synthetic demo is open on an H100 ×8 pay-as-you-go group with 32 GPUs and 720 hours
- **THEN** the tab shows 4 VMs, the compute cost, and the PROJECT example row with exposure USD 11,520.00 labelled "Scenario calculation, not a forecast"

#### Scenario: Ladder on the demo
- **WHEN** the same workload is shown
- **THEN** the ladder's 32-GPU column, marked as entered, has a +25% cell equal to the `increase-25` exposure and a +100% cell equal to the `spike-100` exposure

#### Scenario: Inputs kept across tabs
- **WHEN** the user enters 16 GPUs, opens "Group browser" and returns to "Workload cost"
- **THEN** the GPU input still holds 16

#### Scenario: No price before the check
- **WHEN** the budget entered is 0, or the independent check fails
- **THEN** the tab shows the message and no price, not even the starting price, and no strip or ladder

#### Scenario: Marketplace source
- **WHEN** the synthetic marketplace source is selected
- **THEN** the tab shows the note and no workload figure

#### Scenario: Not normalized
- **WHEN** the latest snapshot is not normalized
- **THEN** the tab withholds its figures, as the group views do

#### Scenario: Fallback not computed on the demo
- **WHEN** the demo's uksouth H100 ×8 Spot group is chosen
- **THEN** the fallback row reads "not computed: no pay-as-you-go listing for this size in this region"
