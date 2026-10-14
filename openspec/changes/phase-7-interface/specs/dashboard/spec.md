## ADDED Requirements

### Requirement: Desk theme
The committed `src/compute_cost_risk_monitor/.streamlit/config.toml` SHALL set one dark theme:
- `theme.base = "dark"`, with explicit `backgroundColor`, `secondaryBackgroundColor`,
  `textColor`, `primaryColor` (the steel-blue accent), `redColor`, `greenColor`, `orangeColor`
  (the amber for the data label and stale warning) and chart colours;
- no `[theme.light]` or `[theme.dark]` section, no `fontFaces`, and no
  `server.enableStaticServing`. Streamlit's bundled fonts are used and no font is fetched from
  elsewhere;
- `textColor`, `redColor`, `greenColor` and `orangeColor` each at a contrast of at least 4.5:1
  against `backgroundColor` and against `secondaryBackgroundColor`.

The page SHALL:
- show no ticker, bid/ask label, animated or flashing value, or "live" badge;
- colour red only for an added cost and green only for a saving, each always with its sign;
- use amber only for the data label and the stale warning, and the accent only for the active tab
  and the entered ladder column. Prices, price changes, statistics and zero changes stay neutral;
- take chart colours from the same values as the theme;
- inject no custom CSS;
- show no explanatory sentences, hints or "(optional)" markers. Labels are terse, with units, and
  explanations live in the Sources section.

#### Scenario: Dark theme committed
- **WHEN** the committed config is parsed
- **THEN** the theme base is dark, its colours are set, and it has no light or dark section, no font faces and no static serving

#### Scenario: Contrast floor
- **WHEN** the contrast of the text, red, green and amber colours is computed against both background colours
- **THEN** each ratio is at least 4.5:1

#### Scenario: Colour only for meaning
- **WHEN** the ladder shows +14,400 and −28,800 cells
- **THEN** the first is red with its plus sign, the second green with its minus sign, and no price or price-change cell is coloured

#### Scenario: No injected CSS
- **WHEN** the dashboard's source is inspected
- **THEN** it writes no `<style>` element and loads no stylesheet

#### Scenario: No helper sentences on the page
- **WHEN** the Workload cost tab is drawn for the demo with its Sources section closed
- **THEN** none of the workload introduction, the budget hint, the several-sizes note or the lowest-listed note appears, and each is in Sources

### Requirement: Status line and key figures
Every tab SHALL sit under one status line:

`COMPUTE COST & RISK MONITOR · <data label> · AS OF <d MON yyyy HH:MM> UTC`

Here \<data label\> is `AZURE PUBLISHED LIST PRICES` for a `live` or `recorded` snapshot and
`SYNTHETIC DATA — NOT AZURE LIST PRICES` for a `synthetic` one, in amber for the synthetic label.
The time is the selected source's latest snapshot start. A stale snapshot adds `STALE — OLDER
THAN 7 DAYS AS OF <UTC>` in amber.

The Workload cost tab SHALL show, only after the independent check passes, one row of key
figures with terse labels:
- `COST, USD`: the total;
- `USD / GPU-HOUR`: the starting price;
- `VMS`: the VM count × the starting member's size;
- `+100%, USD`: the entered column's +100% ladder cell;
- `HEADROOM, USD / GPU-HOUR`: the budget headroom with its % of the starting price, only when a
  budget is entered.

With a refused input or a failed check there are no key figures.

The Comparable groups tab SHALL show, in the same style, the chosen group's lowest listed
USD/GPU-hour with its size or offer ID, its member count (for marketplace groups, machines and
offers) and its labels as terse tags.

Key figures show only figures already computed and checked, formatted as in "Display
formatting".

#### Scenario: Synthetic status line
- **WHEN** the latest snapshot is labelled `synthetic` and started 2026-10-12 09:00 UTC
- **THEN** the status line reads `COMPUTE COST & RISK MONITOR · SYNTHETIC DATA — NOT AZURE LIST PRICES · AS OF 12 OCT 2026 09:00 UTC`

#### Scenario: Stale as of an injected time
- **WHEN** the latest snapshot started 8 days before the injected as-of time
- **THEN** the status line adds `STALE — OLDER THAN 7 DAYS AS OF` that time

#### Scenario: Key figures on the demo
- **WHEN** the synthetic demo is open on the eastus H100 ×8 pay-as-you-go group with 32 GPUs and 720 hours
- **THEN** the key figures are `COST, USD` 276,480.00, `USD / GPU-HOUR` 12.0000, `VMS` 4 × the size, and `+100%, USD` +276,480.00

#### Scenario: No key figures before the check
- **WHEN** the input is refused or the independent check fails
- **THEN** no key figure and no price is shown

## MODIFIED Requirements

### Requirement: Figure captions and framing line
The status line ("Status line and key figures") SHALL name the data and its time on every tab;
it replaces the framing line.

Every tab that shows a workload cost or ladder figure SHALL show one footer line directly under
the ladder: "Scenario calculation, not a forecast." followed by the group's exclusions text, word
for word. This footer states the exclusions for every workload figure on that tab.

Comparisons SHALL carry terse tags on the page: `crosses regions` on the cross-region summary,
`crosses rental types (Spot → pay-as-you-go)` on the fallback ladder row, and `single list
price`, `thin`, `lowest listed per region`, `synthetic` and `machine_duplicate` where they apply.
The Comparable groups tab SHALL show the exclusions text once, in the footer style, under its
first price table; it states the exclusions for every price and statistic on that tab.

A "Sources" section, closed by default and never hidden by a failed state, SHALL hold, for the
figures on its tab:
- the group key (or the regions crossed), the snapshot's start time in UTC and run ID, and the
  data label code;
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
- the above-pay-as-you-go note when a ladder row is marked;
- the explanatory notes: the several-sizes note, the lowest-listed note, that the median is a
  statistic and not a listed price, the group-browser note and the budget note;
- the source records: item key, run ID, data label, raw-response file path, sequence number and
  SHA-256.

The as-of time SHALL be read from the clock once per page run by the app entry point and passed
in; tests SHALL inject it.

#### Scenario: Footer under the ladder
- **WHEN** the ladder is shown
- **THEN** the line under it reads "Scenario calculation, not a forecast." followed by the exclusions text

#### Scenario: Sources hold the provenance
- **WHEN** the Sources section of the Workload cost tab is opened for a Spot group with no storage entered
- **THEN** it holds the group key, snapshot time, run ID, data label code, `ladder-v1`, `scenarios-v1`, the judgement note, "Storage not included.", the billing assumptions line and the Spot line

#### Scenario: Fallback row tagged as crossing
- **WHEN** the Spot to pay-as-you-go ladder row is shown
- **THEN** it carries the `crosses rental types (Spot → pay-as-you-go)` tag, and Sources names both group keys

### Requirement: Workload cost view
The page SHALL open on its first lazy tab, "Workload cost", followed by "Comparable groups",
"Group browser" and "Data quality". The tab SHALL use the region group chosen by the sidebar
filters. It SHALL NOT repeat the chosen group as a line of text. It SHALL show, in order:
- the key figures ("Status line and key figures"), after the independent check passes;
- one row of inputs with terse labels: Size (only when the group has several members), GPUs
  (minimum and step equal to GPUs per VM, default 32), Hours (default 720), Storage USD, Custom
  move and Budget USD, with "—" as the placeholder of an empty optional input;
- after the independent check passes: the scenario ladder, its footer, then the COST table
  (USD / VM-h, VM-h and USD for compute, storage and total) beside the Sources section.

It SHALL show no `scenarios-v1` table and no exposure chart.

The view SHALL behave as follows:
- **Inputs:** they SHALL be keyed and keep their values when the user switches tabs. The size
  choice SHALL be remembered per group, starting at the group's lowest listed member.
- **Marketplace source:** when "Synthetic marketplace" is the selected source, the tab SHALL
  show only a short note that the calculator uses Azure list-price groups.
- **Other states:** with no snapshot, a snapshot that is not normalized, or no groups, the tab
  SHALL show the same states as the "Comparable groups" tab and no figure.
- **Invalid input:** the tab SHALL show the validator's message and no figure.
- **Failed check:** when the independent check fails, the tab SHALL show "The independent check
  failed: <checks>. No figures are shown." and no figure.
- **Ladder:** it SHALL be drawn as a plain table of `ladder-v1` steps, then the Custom and
  fallback rows when present, by GPU counts. The entered column is shaded and bold; refused rows
  read "not computed" with their reason, and marked rows carry their mark.

The starting price SHALL appear only with the checked figures, after the independent check
passes, so no price is ever shown with a refused input or a failed check.

#### Scenario: Opens on Workload cost
- **WHEN** the page is first drawn
- **THEN** "Workload cost" is the first tab and the one shown

#### Scenario: Known workload on the demo
- **WHEN** the synthetic demo is open on an H100 ×8 pay-as-you-go group with 32 GPUs and 720 hours
- **THEN** the key figures show 4 VMs and the cost, and the ladder's 32-GPU "+0.50 USD/GPU-h" cell is +11,520, with the "Scenario calculation, not a forecast." footer

#### Scenario: Ladder on the demo
- **WHEN** the same workload is shown
- **THEN** the ladder's entered 32-GPU column has a +25% cell equal to the `increase-25` exposure and a +100% cell equal to the `spike-100` exposure

#### Scenario: No scenario table or chart
- **WHEN** the Workload cost tab is drawn for a valid workload
- **THEN** it holds no `scenarios-v1` table and no chart

#### Scenario: Inputs kept across tabs
- **WHEN** the user enters 16 GPUs, opens "Group browser" and returns to "Workload cost"
- **THEN** the GPU input still holds 16

#### Scenario: No price before the check
- **WHEN** the budget entered is 0, or the independent check fails
- **THEN** the tab shows the message and no price, not even the starting price, and no key figures or ladder

#### Scenario: Marketplace source
- **WHEN** the synthetic marketplace source is selected
- **THEN** the tab shows the note and no workload figure

#### Scenario: Not normalized
- **WHEN** the latest snapshot is not normalized
- **THEN** the tab withholds its figures, as the group views do

#### Scenario: Fallback not computed on the demo
- **WHEN** the demo's uksouth H100 ×8 Spot group is chosen
- **THEN** the ladder's fallback row reads "not computed: no pay-as-you-go listing for this size in this region"

### Requirement: Comparable-group filters
The dashboard SHALL filter by comparable group with cascading choices: GPU variant, then GPU
count, then rental type, then region. Each choice SHALL offer only values for which a region
group exists in the latest snapshot, given the choices above it. Choices SHALL be sorted by
their natural order (variant and region by name, GPU count numerically).

Rental types SHALL be shown as "Pay-as-you-go" and "Spot". Regions SHALL be shown by the
source's stored `location` name for that region, or by the region code when no name is stored.
Nothing is shown that the source did not provide.

#### Scenario: Only existing groups offered
- **WHEN** a snapshot holds region groups for ("A100 PCIe 80GB", 1, `on_demand`, eastus) and ("H100 NVL 94GB", 2, `spot`, westeurope)
- **THEN** after choosing "A100 PCIe 80GB", the GPU count choice offers only 1 and the rental type choice offers only `on_demand`, shown as "Pay-as-you-go"

#### Scenario: Region shown by its stored name
- **WHEN** a region's rows store the `location` "US East" for eastus
- **THEN** the region choice shows "US East"

#### Scenario: Region without a stored name
- **WHEN** a region's rows store no `location`
- **THEN** the region choice shows its code

### Requirement: Region-group view
For the chosen variant, GPU count, rental type and region, the dashboard SHALL show the region
group's members, one row each, with:
- size name (or offer ID);
- USD/GPU-hour;
- the published price per VM-hour as stored, with its currency and unit;
- retrieval time in UTC.

The Sources section SHALL list, per member, the item key, run ID, data label, raw-response file
path, sequence number and SHA-256. A group of one member SHALL show the `single list price` tag.
For a group of several members, Sources SHALL say that its sizes share GPU variant and count but
differ in vCPUs, RAM and local disk. A Spot price equal to the pay-as-you-go price of the same
size SHALL be shown as listed, with no warning.

#### Scenario: Every member listed
- **WHEN** a region group holds two sizes
- **THEN** the table shows both sizes with their USD/GPU-hour, VM-hour price, currency, unit and retrieval time, and Sources holds the several-sizes note

#### Scenario: Single list price
- **WHEN** a region group holds one size
- **THEN** the view shows the `single list price` tag

#### Scenario: Provenance shown
- **WHEN** the Sources section is opened for a group
- **THEN** each member's item key, run ID, data label, raw-response file, sequence number and SHA-256 are listed

### Requirement: Cross-region summary view
For the chosen variant, GPU count and rental type of an Azure snapshot, the dashboard SHALL show
the cross-region summary: one row per region with the region, its lowest listed size and that
size's USD/GPU-hour, and the region count, minimum, median and maximum. It SHALL show the tags
`lowest listed per region` and `crosses regions`, and `thin` when present. Sources SHALL say
that each region contributes its lowest listed size, the cheapest configuration listed there,
and that the median is a statistic, not a listed price.

One chart SHALL plot each contributing region as a point at its lowest listed USD/GPU-hour, with
rule marks at the minimum, median and maximum, and no line joining points. A region without a
listing SHALL be absent from the chart, never filled in.

#### Scenario: Known-answer summary shown
- **WHEN** five regions' lowest members have USD/GPU-hour 1, 2, 3, 4 and 10
- **THEN** the view shows 5 regions, minimum 1, median 3 and maximum 10, without the `thin` tag

#### Scenario: Thin summary tagged
- **WHEN** a summary covers 4 regions
- **THEN** the view shows the `thin` tag

#### Scenario: Chart plots only listed regions
- **WHEN** a summary covers 3 regions
- **THEN** the chart's point layer holds exactly 3 points, and its rule layer marks the minimum, median and maximum

### Requirement: Group browser
The dashboard SHALL list every region group of the latest snapshot for the chosen source, with
a toggle that narrows the list to the chosen GPU variant, showing each group's key, its member
count (for marketplace groups, its distinct machines and its offers) and tags (`single list
price`, `thin`, `synthetic`). It SHALL show no price, statistic or price-ordered ranking, and
SHALL sort groups by key in its field order (variant, GPU count, region, rental type). The status
line names its data and time. Sources SHALL hold the snapshot's run ID and the note that the
browser shows no prices, so nothing is compared.

#### Scenario: No prices in the browser
- **WHEN** the group browser is shown for a snapshot
- **THEN** it holds group keys, member counts and tags, and no column holds a price or statistic

#### Scenario: Narrowed to the chosen variant
- **WHEN** the toggle is on and "A100 PCIe 80GB" is the chosen variant
- **THEN** the browser lists only that variant's groups

### Requirement: Display formatting
The dashboard SHALL display:
- USD/GPU-hour and statistics to 4 decimal places;
- the published price at its full stored precision;
- USD amounts to 2 decimal places with thousands separators, except ladder cells, which are
  whole USD with a sign and thousands separators;
- percentages to 1 decimal place;
- times in UTC.

It SHALL format values only for display and never compute from rounded values.

#### Scenario: Four decimals for USD/GPU-hour
- **WHEN** a member's USD/GPU-hour is 12.291267
- **THEN** it is displayed as 12.2913, and the stored value is unchanged

#### Scenario: USD amounts and percentages
- **WHEN** a cost is 11520 and a change is 33.3333% of the starting price
- **THEN** they are displayed as 11,520.00 and 33.3%, and the computed values are unchanged

#### Scenario: Whole USD in the ladder
- **WHEN** a ladder cell is 27648.4
- **THEN** it is displayed as +27,648, and the checked value is unchanged
