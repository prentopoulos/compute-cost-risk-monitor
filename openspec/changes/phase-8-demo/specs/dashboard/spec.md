## MODIFIED Requirements

### Requirement: Figure captions and framing line
The status line ("Status line and key figures") SHALL name the data and its time on every tab;
it replaces the framing line.

Every tab that shows a workload figure SHALL title its scenario grid
"SCENARIO GRID · Δ cost, USD · <hours> h · NOT A FORECAST". The title labels every scenario
figure on that tab, the Headroom key figure included. Directly under the grid, a footer SHALL
start with the exclusions tag line: "EXCL. " followed by every item of the group's exclusions
text, in its stored order, joined by " · ". The items are the text after "Excludes ", split at
", ", without the final full stop. The tag line states the exclusions for every workload figure
on that tab. Only when they apply, the footer then adds, each on its own line with its mark
first:
- "Total includes USD X storage entered by you.";
- "* Crosses rental types (Spot → pay-as-you-go): same size, same region.", for the fallback row
  labelled "Spot → PAYG *";
- "† Above this size's pay-as-you-go list price (USD x/GPU-h): the arithmetic, not what Azure
  would bill.", for rows and a headroom marked "†";
- each not-computed reason: "Not computed: no pay-as-you-go listing for this size in this
  region." (on the "*" line) or "Not computed: the price would be zero or below." (for the
  Custom row).

The Comparable groups tab SHALL show the exclusions tag line once, in the footer style, under
its first price table; it states the exclusions for every price and statistic on that tab.

Comparisons SHALL carry terse tags on the page, as muted text at body size, joined by " · "
(not inline code, which Streamlit draws at 0.75em, below 12 px): `crosses regions` on the
cross-region summary,
and `single list price`, `thin`, `lowest listed per region`, `synthetic` and `machine_duplicate`
where they apply.

A "Sources" section, closed by default, under the tab's last table (at full width, or in the
Workload cost column), and never
hidden by a failed state, SHALL hold, for the figures on its tab:
- the group key (both keys for the fallback row, or the regions crossed), the snapshot's start
  time in UTC and run ID, and the data label code;
- `ladder-v1` and `scenarios-v1`, with the judgement note "Round sensitivities chosen by
  judgement, not calibrated to history (one snapshot) or to any model";
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
  deallocated still bills for its disks.";
- the full above-pay-as-you-go note when a row or the headroom is marked;
- the headroom sentence when a budget is entered;
- the explanatory notes: the several-sizes note, the lowest-listed note, that the median is a
  statistic and not a listed price, the group-browser note and the budget note;
- the source records: item key, run ID, data label, raw-response file path, sequence number and
  SHA-256.

The as-of time SHALL be read from the clock once per page run by the app entry point and passed
in; tests SHALL inject it.

#### Scenario: Footer under the grid
- **WHEN** the scenario grid is shown with no storage, no Spot row and no marked row
- **THEN** the grid title ends "NOT A FORECAST", and the footer reads only the exclusions tag line, which on the demo is "EXCL. disks and storage · egress · public IPs · licences · taxes · negotiated discounts · reservations and savings plans · Spot eviction risk · capacity and quota"

#### Scenario: Storage clause
- **WHEN** USD 5,000 of storage is entered
- **THEN** the footer adds "Total includes USD 5,000.00 storage entered by you."

#### Scenario: Fallback captioned as crossing
- **WHEN** the Spot to pay-as-you-go row is shown
- **THEN** its label is "Spot → PAYG *", the footer holds "* Crosses rental types (Spot → pay-as-you-go): same size, same region.", and Sources names both group keys

#### Scenario: Sources hold the provenance
- **WHEN** the Sources section of the Workload cost tab is opened for a Spot group with no storage entered
- **THEN** it holds the group key, snapshot time, run ID, data label code, `ladder-v1`, `scenarios-v1`, the judgement note, "Storage not included.", the billing assumptions line and the Spot line

#### Scenario: Every figure captioned
- **WHEN** any group, summary or chart is shown
- **THEN** the status line holds its data label and AS OF time, the footer style holds the exclusions tag line, and its Sources section holds the group key or "crosses regions", the snapshot time and the run ID

#### Scenario: Synthetic framing
- **WHEN** the latest snapshot is labelled `synthetic`
- **THEN** the status line says, in amber, "SYNTHETIC DATA — NOT AZURE LIST PRICES"

#### Scenario: Stale as of an injected time
- **WHEN** the latest snapshot started 8 days before the injected as-of time
- **THEN** the status line adds "STALE — OLDER THAN 7 DAYS AS OF" that time

#### Scenario: Workload figures captioned
- **WHEN** the scenario grid and COST table are shown for a Spot group with no storage entered
- **THEN** the grid title ends "NOT A FORECAST", the footer holds the exclusions tag line, and Sources holds the group key, snapshot time and run ID, data label, "Storage not included.", the billing assumptions line, the Spot line, `ladder-v1` and `scenarios-v1`

### Requirement: Display formatting
The dashboard SHALL display:
- USD/GPU-h and statistics to 4 decimal places;
- the published price at its full stored precision;
- USD amounts to 2 decimal places with thousands separators, except grid cells, which are whole
  USD, rounded half up, with a sign and thousands separators. A non-zero cell that would round to
  0 shows 3 significant digits in positional notation, never in exponent form;
- percentages to 1 decimal place;
- times in UTC;
- "n/a" in a grid cell that is not computed, and "—" for an empty input, a value not entered, or
  a key figure withheld before the check.

It SHALL format values only for display and never compute from rounded values.

#### Scenario: Four decimals for USD/GPU-hour
- **WHEN** a member's USD/GPU-hour is 12.291267
- **THEN** it is displayed as 12.2913, and the stored value is unchanged

#### Scenario: USD amounts and percentages
- **WHEN** a cost is 11520 and a change is 33.3333% of the starting price
- **THEN** they are displayed as 11,520.00 and 33.3%, and the computed values are unchanged

#### Scenario: Whole USD in the grid
- **WHEN** a grid cell is 27648.4
- **THEN** it is displayed as +27,648, and the checked value is unchanged

#### Scenario: Halves round up in the grid
- **WHEN** grid cells are 2.5 and 3.5
- **THEN** they are displayed as +3 and +4

#### Scenario: Not computed is not zero
- **WHEN** a grid row is refused
- **THEN** its cells show "n/a", never "0" or "—"

#### Scenario: Tiny grid change in positional form
- **WHEN** a grid cell is 0.000000006
- **THEN** it is displayed as +0.00000000600, never as "+6e-09"

### Requirement: Workload cost view
The page SHALL open on its first lazy tab, "Workload cost", followed by "Comparable groups",
"Group browser" and "Data quality". The tab SHALL use the region group chosen by the sidebar
filters. It SHALL NOT repeat the chosen group as a line of text. It SHALL show, in order:
- the key figures ("Status line and key figures");
- one row of inputs with terse labels:
  - "Size", only when the group has several members;
  - "GPUs", with minimum and step equal to GPUs per VM, default 32;
  - "Hours", default 720;
  - "Storage, USD";
  - "Custom, %" or "Custom, USD/GPU-h", with a horizontal unit switch "%" / "USD/GPU-h" above
    it in the same column;
  - "Contingency, USD": money set aside for price rises, which the headroom uses up. Not the
    total budget.

  An empty optional input shows "—" as its placeholder. As in Phase 5, each custom unit has its
  own keyed input, so switching unit never reinterprets a value;
- after the independent check passes: the scenario grid, its footer, the COST table (USD/VM-h,
  VM-h and USD for compute, storage and total), then the Sources section. Everything under the
  inputs, a status message included, sits in one column 960 px wide, as in mock v3: the grid
  about 945 px and COST about 540 px. COST shows the published USD/VM-h with every stored
  decimal and never fewer than two.

It SHALL show no `scenarios-v1` table and no exposure chart.

The view SHALL behave as follows:
- **Inputs:** they SHALL be keyed and keep their values when the user switches tabs. The size
  choice SHALL be remembered per group, starting at the group's lowest listed member.
- **Marketplace source:** when the "Marketplace" catalogue is selected, the tab SHALL show only a
  short note that the calculator uses the Azure VMs catalogue.
- **Other states:** with no snapshot, a snapshot that is not normalized, or no groups, the tab
  SHALL show the same status words as the "Comparable groups" tab and no figure. When the
  snapshot is not normalized, each tab names its own view: "The workload figures are withheld
  until this snapshot is normalized." here, and "The group views are withheld until this
  snapshot is normalized." on Comparable groups and Group browser.
- **Invalid input:** the tab SHALL show "REFUSED" and the validator's message below it, and no
  figure.
- **Failed check:** when the independent check fails, the tab SHALL show "CHECK FAILED" and "The
  independent check failed: <checks>. No figures are shown." below it, and no figure.
- **Grid:** it SHALL be drawn as a plain table of `ladder-v1` steps, then the fallback and Custom
  rows when present, by GPU counts:
  - the entered column is shaded and bold;
  - a refused row shows "n/a" in every cell, with its reason in the footer;
  - marked rows carry "†".

The starting price SHALL appear only with the checked figures, after the independent check
passes, so no price is ever shown with a refused input or a failed check.

#### Scenario: Opens on Workload cost
- **WHEN** the page is first drawn
- **THEN** "Workload cost" is the first tab and the one shown

#### Scenario: Known workload on the demo
- **WHEN** the synthetic demo is open on an H100 ×8 pay-as-you-go group with 32 GPUs and 720 hours
- **THEN** the key figures show 4 VMs and the cost, and the grid's 32-GPU "+0.50 USD/GPU-h" cell is +11,520, under a grid title ending "NOT A FORECAST"

#### Scenario: Grid on the demo
- **WHEN** the same workload is shown
- **THEN** the grid's entered 32-GPU column has a +25% cell equal to the `increase-25` exposure and a +100% cell equal to the `spike-100` exposure

#### Scenario: No scenario table or chart
- **WHEN** the Workload cost tab is drawn for a valid workload
- **THEN** it holds no `scenarios-v1` table and no chart

#### Scenario: Custom unit switch
- **WHEN** the user enters a custom move of 15 with the unit "%", switches to "USD/GPU-h", and switches back
- **THEN** the input shows 15 again under "Custom, %", and the USD input is still empty

#### Scenario: Inputs kept across tabs
- **WHEN** the user enters 16 GPUs, opens "Group browser" and returns to "Workload cost"
- **THEN** the GPU input still holds 16

#### Scenario: No price before the check
- **WHEN** the budget entered is 0, or the independent check fails
- **THEN** the tab shows the status word and the message, each key-figure label shows "—", and no price, grid or COST table is shown

#### Scenario: Marketplace source
- **WHEN** the Marketplace catalogue is selected
- **THEN** the tab shows the note and no workload figure

#### Scenario: Not normalized
- **WHEN** the latest snapshot is not normalized
- **THEN** the tab withholds its figures, as the group views do

#### Scenario: Fallback not computed on the demo
- **WHEN** the demo's uksouth H100 ×8 Spot group is chosen
- **THEN** the grid's "Spot → PAYG *" row shows "n/a" in every cell, and the footer holds "Not computed: no pay-as-you-go listing for this size in this region."
