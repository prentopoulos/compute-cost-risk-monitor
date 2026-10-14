## ADDED Requirements

### Requirement: Desk theme
The committed `src/compute_cost_risk_monitor/.streamlit/config.toml` SHALL set one dark theme:
- `theme.base = "dark"`, with explicit `backgroundColor`, `secondaryBackgroundColor`,
  `textColor`, `primaryColor` (the steel-blue accent), `borderColor`, `redColor`, `greenColor`,
  `orangeColor` (the amber for data labels and the stale warning) and chart colours;
- `codeTextColor` set to the muted grey and `codeBackgroundColor` to `secondaryBackgroundColor`,
  so inline code, such as a size name on Data quality, is neutral (Streamlit colours inline code
  green by default);
- no `[theme.light]` or `[theme.dark]` section, no `fontFaces`, and no
  `server.enableStaticServing`. Streamlit's bundled fonts are used and no font is fetched from
  elsewhere;
- `textColor`, `redColor`, `greenColor`, `primaryColor` and `orangeColor` each at a contrast of at
  least 4.5:1 against `backgroundColor`, `secondaryBackgroundColor` and the entered-column shade
  the dashboard uses in the scenario grid;
- `borderColor` at a contrast of at least 3:1 against both background colours.

The page SHALL:
- show no ticker, bid/ask label, animated or flashing value, or "live" badge;
- colour red only for an added cost and green only for a saving, each always with its sign;
- use amber only for data labels and the stale warning, and the accent only for the current or
  selected state (the active tab, the chosen unit, a toggle that is on, keyboard focus) and the
  entered grid column. Prices, price changes, statistics and zero changes stay neutral;
- show every state message (refused input, failed check, not normalized, no snapshot, in use,
  open errors) as a plain status word in text colour with its message, never in a coloured
  alert box. The mixed-labels warning may use amber;
- take chart colours from the same values as the theme;
- inject no custom CSS. Styler colours, font weights and borders on a table drawn with
  `st.table` are allowed;
- show no explanatory sentences, hints or "(optional)" markers. Labels are terse, with units
  written as USD/GPU-h, USD/VM-h, VM-h, h and VMs, and explanations live in the Sources section.

#### Scenario: Dark theme committed
- **WHEN** the committed config is parsed
- **THEN** the theme base is dark, its colours are set, and it has no light or dark section, no font faces and no static serving

#### Scenario: Contrast floor
- **WHEN** the contrast of the text, red, green, accent and amber colours is computed against both background colours and the entered-column shade, and of the border colour against both background colours
- **THEN** each text ratio is at least 4.5:1 and the border ratio at least 3:1

#### Scenario: Colour only for meaning
- **WHEN** the grid shows +14,400 and −28,800 cells
- **THEN** the first is red with its plus sign, the second green with its minus sign, and no price or price-change cell is coloured

#### Scenario: Tags are neutral
- **WHEN** the committed config is parsed
- **THEN** inline code text is the muted grey on the panel colour, not the green that marks a saving

#### Scenario: No alert boxes
- **WHEN** an input is refused, the check fails, or the snapshot is not normalized
- **THEN** the page shows a status word and the message in text colour, and no warning, error or success element

#### Scenario: No injected CSS
- **WHEN** the dashboard's source is inspected
- **THEN** it writes no `<style>` element and loads no stylesheet

#### Scenario: No helper sentences on the page
- **WHEN** the Workload cost tab is drawn for the demo with its Sources section closed
- **THEN** none of the workload introduction, the budget hint, the headroom sentence, the several-sizes note or the lowest-listed note appears, and each is in Sources

### Requirement: Status line and key figures
Every tab SHALL sit under one status line, its parts separated by "·":

`COMPUTE COST & RISK MONITOR · <data label> · AS OF <d MON yyyy HH:MM> UTC`

Here \<data label\> is `AZURE PUBLISHED LIST PRICES` for a `live` or `recorded` snapshot and
`SYNTHETIC DATA — NOT AZURE LIST PRICES` for a `synthetic` one, in amber either way. The time is
the selected source's latest snapshot start, in text colour. A stale snapshot adds `STALE —
OLDER THAN 7 DAYS AS OF <UTC>` in amber.

The Workload cost tab SHALL show one row of key figures with terse labels:
- "Cost, USD": the total;
- "USD/GPU-h · PAYG", or "USD/GPU-h · SPOT" for a Spot group: the starting price;
- "VMs": the VM count × the starting member's short size name (its name without the
  `Standard_` prefix, with `_` shown as spaces);
- "GPUs × h": the checked GPUs and hours;
- "Headroom, USD/GPU-h": the budget headroom with its % of the starting price, only when a budget
  is entered, marked "†" when it is above the size's pay-as-you-go price.

The values appear only after the independent check passes. With a refused input or a failed
check, each label shows "—" and no value or price.

The Comparable groups tab SHALL show, in the same style, "Lowest, USD/GPU-h · PAYG" (or
"· SPOT") with the lowest listed member's USD/GPU-hour, "Size" with its size or offer ID, and
"Members" with its member count (for marketplace groups, machines and offers), plus its tags.

Key figures show only figures already computed and checked, formatted as in "Display
formatting".

#### Scenario: Synthetic status line
- **WHEN** the latest snapshot is labelled `synthetic` and started 2026-10-12 09:00 UTC
- **THEN** the status line reads `COMPUTE COST & RISK MONITOR · SYNTHETIC DATA — NOT AZURE LIST PRICES · AS OF 12 OCT 2026 09:00 UTC`, with the data label in amber

#### Scenario: Live status line
- **WHEN** the latest snapshot is labelled `live`
- **THEN** the status line's data label reads `AZURE PUBLISHED LIST PRICES`, in amber, and the word "live" appears nowhere on the page

#### Scenario: Stale as of an injected time
- **WHEN** the latest snapshot started 8 days before the injected as-of time
- **THEN** the status line adds `STALE — OLDER THAN 7 DAYS AS OF` that time

#### Scenario: Key figures on the demo
- **WHEN** the synthetic demo is open on the eastus H100 ×8 pay-as-you-go group with 32 GPUs and 720 hours
- **THEN** the key figures are "Cost, USD" 276,480.00, "USD/GPU-h · PAYG" 12.0000, "VMs" 4 × ND96isr H100 v5 and "GPUs × h" 32 × 720

#### Scenario: No values before the check
- **WHEN** the input is refused or the independent check fails
- **THEN** each key-figure label shows "—", and no price is shown

## MODIFIED Requirements

### Requirement: Local-only configuration
The repository SHALL commit `src/compute_cost_risk_monitor/.streamlit/config.toml`, beside the
app script, so Streamlit applies it whatever folder the dashboard is launched from, with:
- `browser.gatherUsageStats = false`;
- `server.address = "127.0.0.1"`;
- `client.toolbarMode = "minimal"`, so Streamlit's menu is hidden: no developer options, no
  Deploy button and no theme switch, because the scenario grid's colours are tuned for the
  dark theme.

The dashboard SHALL be launched with `uv run streamlit run src/compute_cost_risk_monitor/app.py`.

#### Scenario: Telemetry off and bound to localhost
- **WHEN** the committed config beside the app script is parsed
- **THEN** usage statistics are off, the server address is 127.0.0.1 and the toolbar mode is `minimal`

#### Scenario: Applies from any folder
- **WHEN** Streamlit lists the config files it reads for the app script
- **THEN** the committed config is among them, whatever the working folder

### Requirement: Dataset and source choice
The dashboard SHALL offer, in the sidebar, only the known databases that exist, as a dropdown
labelled "Dataset": `data/monitor.duckdb` as "Azure list prices (local only)" and
`data/synthetic.duckdb` as "Synthetic demo". It SHALL default to `data/monitor.duckdb` when that
file exists. Tests SHALL be able to supply other paths.

A dropdown labelled "Catalogue" SHALL choose the source: `azure-retail` as "Azure VMs" and
`synthetic-marketplace` as "Marketplace". Each option SHALL add " (synthetic)" when that source's
latest succeeded snapshot is labelled `synthetic`, and nothing for a `live` or `recorded` one;
the suffix is never "(live)". One page SHALL show one database and one source at a time, and
never combine figures from two.

The data label shown with every figure SHALL be the snapshot's recorded `collection_run`
label, never one inferred from the file. When one source's succeeded snapshots carry more than
one label, the page SHALL warn that the source mixes labels.

#### Scenario: Only existing databases offered
- **WHEN** only `data/synthetic.duckdb` exists
- **THEN** the dataset choice offers only "Synthetic demo" and selects it

#### Scenario: Live database is the default
- **WHEN** both databases exist
- **THEN** the dashboard opens `data/monitor.duckdb`

#### Scenario: Catalogue suffix from the run
- **WHEN** the selected database's latest `azure-retail` snapshot is labelled `synthetic`
- **THEN** the catalogue offers "Azure VMs (synthetic)", and every figure for it is labelled `synthetic`

#### Scenario: Mixed labels warned
- **WHEN** one source has a succeeded `live` run and a succeeded `synthetic` run
- **THEN** the page shows a warning that the source mixes labels

### Requirement: Figure captions and framing line
The status line ("Status line and key figures") SHALL name the data and its time on every tab;
it replaces the framing line.

Every tab that shows a workload figure SHALL show a footer directly under the scenario grid:
"Scenario calculation, not a forecast." followed by the group's exclusions text, word for word.
It states the exclusions for every workload figure on that tab, and labels every scenario figure
on it, the Headroom key figure included. Only when they apply, the footer then adds, each on its
own line with its mark first:
- "Total includes USD X storage entered by you.";
- "* Crosses rental types (Spot → pay-as-you-go): same size, same region.", for the fallback row
  labelled "Spot → PAYG *";
- "† Above this size's pay-as-you-go list price (USD x/GPU-h): the arithmetic, not what Azure
  would bill.", for rows and a headroom marked "†";
- each not-computed reason: "Not computed: no pay-as-you-go listing for this size in this
  region." (on the "*" line) or "Not computed: the price would be zero or below." (for the
  Custom row).

The Comparable groups tab SHALL show the exclusions text once, in the footer style, under its
first price table; it states the exclusions for every price and statistic on that tab.

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
- **THEN** the footer reads "Scenario calculation, not a forecast." followed by the exclusions text, and nothing else

#### Scenario: Storage clause
- **WHEN** USD 5,000 of storage is entered
- **THEN** the footer adds "Total includes USD 5,000.00 storage entered by you."

#### Scenario: Fallback row stated as crossing
- **WHEN** the Spot to pay-as-you-go row is shown
- **THEN** its label is "Spot → PAYG *", the footer holds "* Crosses rental types (Spot → pay-as-you-go): same size, same region.", and Sources names both group keys

#### Scenario: Sources hold the provenance
- **WHEN** the Sources section of the Workload cost tab is opened for a Spot group with no storage entered
- **THEN** it holds the group key, snapshot time, run ID, data label code, `ladder-v1`, `scenarios-v1`, the judgement note, "Storage not included.", the billing assumptions line and the Spot line

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
  SHALL show the same states as the "Comparable groups" tab and no figure.
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
- **THEN** the key figures show 4 VMs and the cost, and the grid's 32-GPU "+0.50 USD/GPU-h" cell is +11,520, with the "Scenario calculation, not a forecast." footer

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

### Requirement: Comparable-group filters
The dashboard SHALL filter by comparable group with cascading dropdowns labelled "GPU", "GPUs per
VM", "Pricing" and "Region", in that order. Each choice SHALL offer only values for which a
region group exists in the latest snapshot, given the choices above it. Choices SHALL be sorted
by their natural order (variant and region by name, GPU count numerically).

GPU counts SHALL be shown as numbers. Rental types SHALL be shown as "Pay-as-you-go" and "Spot";
key-figure labels and the fallback row may abbreviate pay-as-you-go to "PAYG". Regions SHALL be
shown by the source's stored `location` name for that region, or by the region code when no name
is stored. Nothing is shown that the source did not provide.

#### Scenario: Only existing groups offered
- **WHEN** a snapshot holds region groups for ("A100 PCIe 80GB", 1, `on_demand`, eastus) and ("H100 NVL 94GB", 2, `spot`, westeurope)
- **THEN** after choosing "A100 PCIe 80GB", the GPU count choice offers only 1 and the pricing choice offers only "Pay-as-you-go"

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
- USD/GPU-h;
- the published price per VM-hour as stored, with its currency and unit;
- retrieval time in UTC.

The Sources section SHALL list, per member, the item key, run ID, data label, raw-response file
path, sequence number and SHA-256. A group of one member SHALL show the `single list price` tag.
For a group of several members, Sources SHALL say that its sizes share GPU variant and count but
differ in vCPUs, RAM and local disk. A Spot price equal to the pay-as-you-go price of the same
size SHALL be shown as listed, with no warning.

#### Scenario: Every member listed
- **WHEN** a region group holds two sizes
- **THEN** the table shows both sizes with their USD/GPU-h, VM-hour price, currency, unit and retrieval time, and Sources holds the several-sizes note

#### Scenario: Single list price
- **WHEN** a region group holds one size
- **THEN** the view shows the `single list price` tag

#### Scenario: Provenance shown
- **WHEN** the Sources section is opened for a group
- **THEN** each member's item key, run ID, data label, raw-response file, sequence number and SHA-256 are listed

### Requirement: Cross-region summary view
For the chosen variant, GPU count and rental type of an Azure snapshot, the dashboard SHALL show
the cross-region summary: one row per region with the region, its lowest listed size and that
size's USD/GPU-h, and the region count, minimum, median and maximum. Regions in the table and the
chart SHALL be shown as in the filters, by stored name or else by code, and sorted by that name
ignoring case. Sources keep the region code, since it is part of the group key. It SHALL show the tags
`lowest listed per region` and `crosses regions`, and `thin` when present. Sources SHALL say
that each region contributes its lowest listed size, the cheapest configuration listed there,
and that the median is a statistic, not a listed price.

One chart SHALL plot each contributing region as a point at its lowest listed USD/GPU-h, with
rule marks at the minimum, median and maximum, and no line joining points. A region without a
listing SHALL be absent from the chart, never filled in.

#### Scenario: Known-answer summary shown
- **WHEN** five regions' lowest members have USD/GPU-hour 1, 2, 3, 4 and 10
- **THEN** the view shows 5 regions, minimum 1, median 3 and maximum 10, without the `thin` tag

#### Scenario: Regions by name
- **WHEN** the summary covers eastus, stored as "US East", and westeurope, stored as "EU West"
- **THEN** the table and the chart show "EU West" then "US East"

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
SHALL sort groups by key in its field order (variant, GPU count, region, rental type), with
each region shown and sorted by its stored name, as in the filters. The status
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
- USD/GPU-h and statistics to 4 decimal places;
- the published price at its full stored precision;
- USD amounts to 2 decimal places with thousands separators, except grid cells, which are whole
  USD with a sign and thousands separators;
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

#### Scenario: Not computed is not zero
- **WHEN** a grid row is refused
- **THEN** its cells show "n/a", never "0" or "—"
