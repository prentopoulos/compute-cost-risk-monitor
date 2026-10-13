# dashboard Specification

## Purpose
The local Streamlit dashboard: one database and source at a time, read-only;
comparable-group filters; region-group, cross-region, marketplace and group-browser
views; the workload calculator and labelled exposure scenarios; captions with key,
snapshot, label and exclusions; the data-quality panel; and the local-only configuration.
## Requirements
### Requirement: Local-only configuration
The repository SHALL commit `src/compute_cost_risk_monitor/.streamlit/config.toml`, beside the
app script, so Streamlit applies it whatever folder the dashboard is launched from, with:
- `browser.gatherUsageStats = false`;
- `server.address = "127.0.0.1"`;
- `client.toolbarMode = "viewer"`.

The dashboard SHALL be launched with `uv run streamlit run src/compute_cost_risk_monitor/app.py`.

#### Scenario: Telemetry off and bound to localhost
- **WHEN** the committed config beside the app script is parsed
- **THEN** usage statistics are off, the server address is 127.0.0.1 and the toolbar mode is `viewer`

#### Scenario: Applies from any folder
- **WHEN** Streamlit lists the config files it reads for the app script
- **THEN** the committed config is among them, whatever the working folder

### Requirement: Dataset and source choice
The dashboard SHALL offer, in the sidebar, only the known databases that exist:
`data/monitor.duckdb` as "Live Azure list prices (local only)" and `data/synthetic.duckdb` as
"Synthetic (invented prices)". It SHALL default to `data/monitor.duckdb` when that file exists.
Tests SHALL be able to supply other paths. One page SHALL show one database and one source
(`azure-retail` or `synthetic-marketplace`) at a time, and never combine figures from two.

The data label shown with every figure SHALL be the snapshot's recorded `collection_run`
label, never one inferred from the file. When one source's succeeded snapshots carry more than
one label, the page SHALL warn that the source mixes labels.

#### Scenario: Only existing databases offered
- **WHEN** only `data/synthetic.duckdb` exists
- **THEN** the dataset choice offers only "Synthetic (invented prices)" and selects it

#### Scenario: Live database is the default
- **WHEN** both databases exist
- **THEN** the dashboard opens `data/monitor.duckdb`

#### Scenario: Label comes from the run
- **WHEN** the selected database's latest `azure-retail` snapshot is labelled `synthetic`
- **THEN** every figure for it is labelled `synthetic`

#### Scenario: Mixed labels warned
- **WHEN** one source has a succeeded `live` run and a succeeded `synthetic` run
- **THEN** the page shows a warning that the source mixes labels

### Requirement: Read-only access and database states
The dashboard SHALL open the selected database read-only, once per page run, and close it before
the run ends. It SHALL never cache a connection and never write. It SHALL show, instead of
figures:
- no database: a message naming the command that creates one;
- a database file with no tables yet: a message naming the commands that store a run;
- no stored rule set: "run normalize first";
- a source with no succeeded run: "no snapshot", never zero prices;
- a database that another process holds open for writing: "in use, rerun when it finishes";
- a file DuckDB cannot open for any other reason: the error itself.

Commands shown on the page SHALL quote the database path, so they can be pasted as they are.

When the latest snapshot has observations without a row under the rule set, the page SHALL show
a `NOT NORMALIZED` banner with that count and the normalize command, and SHALL withhold the group
views for that snapshot.

#### Scenario: No database
- **WHEN** neither database exists
- **THEN** the page names the collect and synthetic commands and shows no figure

#### Scenario: No rule set
- **WHEN** the database holds a snapshot but no stored rule set
- **THEN** the page says to run normalize first and shows no figure

#### Scenario: No snapshot
- **WHEN** the selected source has no succeeded run
- **THEN** the page says "no snapshot" for it

#### Scenario: Not normalized
- **WHEN** the latest snapshot has observations and no normalized rows
- **THEN** the page shows the `NOT NORMALIZED` banner with the count and shows no group view

#### Scenario: Database without tables
- **WHEN** the selected database file exists but holds no tables
- **THEN** the page names the commands that store a run and shows no figure

#### Scenario: Unreadable file is not called in use
- **WHEN** the selected file is not a DuckDB database
- **THEN** the page shows the open error, not the "in use" message

#### Scenario: Connection closed after the run
- **WHEN** a page run finishes
- **THEN** a new writing connection to the same database opens

### Requirement: Comparable-group filters
The dashboard SHALL filter by comparable group with cascading choices: GPU variant, then GPU
count, then rental type, then region. Each choice SHALL offer only values for which a region
group exists in the latest snapshot, given the choices above it. Choices SHALL be sorted by
their natural order (variant and region by name, GPU count numerically).

#### Scenario: Only existing groups offered
- **WHEN** a snapshot holds region groups for ("A100 PCIe 80GB", 1, `on_demand`, eastus) and ("H100 NVL 94GB", 2, `spot`, westeurope)
- **THEN** after choosing "A100 PCIe 80GB", the GPU count choice offers only 1 and the rental type choice offers only `on_demand`

### Requirement: Region-group view
For the chosen variant, GPU count, rental type and region, the dashboard SHALL show the region
group's members, one row each, with:
- size name (or offer ID);
- USD/GPU-hour;
- the published price per VM-hour as stored, with its currency and unit;
- retrieval time in UTC.

A "Source records" expander SHALL list, per member, the item key, run ID, data label,
raw-response file path, sequence number and SHA-256. A group of one member SHALL show the
`single list price` label. A group of several members SHALL be captioned that its sizes share
GPU variant and count but differ in vCPUs, RAM and local disk. A Spot price equal to the
pay-as-you-go price of the same size SHALL be shown as listed, with no warning.

#### Scenario: Every member listed
- **WHEN** a region group holds two sizes
- **THEN** the table shows both sizes with their USD/GPU-hour, VM-hour price, currency, unit and retrieval time, and the several-sizes caption

#### Scenario: Single list price
- **WHEN** a region group holds one size
- **THEN** the view shows the `single list price` label

#### Scenario: Provenance shown
- **WHEN** the Source records expander is opened for a group
- **THEN** each member's item key, run ID, data label, raw-response file, sequence number and SHA-256 are listed

### Requirement: Cross-region summary view
For the chosen variant, GPU count and rental type of an Azure snapshot, the dashboard SHALL show
the cross-region summary: one row per region with the region, its lowest listed size and that
size's USD/GPU-hour, and the region count, minimum, median and maximum. It SHALL show the labels
`lowest listed per region` and `crosses regions`, and `thin` when present. Its caption SHALL say
that each region contributes its lowest listed size, the cheapest configuration listed there,
and that the median is a statistic, not a listed price.

One chart SHALL plot each contributing region as a point at its lowest listed USD/GPU-hour, with
rule marks at the minimum, median and maximum, and no line joining points. A region without a
listing SHALL be absent from the chart, never filled in.

#### Scenario: Known-answer summary shown
- **WHEN** five regions' lowest members have USD/GPU-hour 1, 2, 3, 4 and 10
- **THEN** the view shows 5 regions, minimum 1, median 3 and maximum 10, without the `thin` label

#### Scenario: Thin summary labelled
- **WHEN** a summary covers 4 regions
- **THEN** the view shows the `thin` label

#### Scenario: Chart plots only listed regions
- **WHEN** a summary covers 3 regions
- **THEN** the chart's point layer holds exactly 3 points, and its rule layer marks the minimum, median and maximum

### Requirement: Marketplace group view
For the `synthetic-marketplace` source, the dashboard SHALL show the chosen group's offers with
offer ID, machine ID, USD/GPU-hour, the offer price with currency and unit, and retrieval time.
Offers flagged `machine_duplicate` SHALL be marked. The view SHALL show the distinct-machine
count, minimum, median and maximum of the machine prices, the `synthetic` label, and `thin`
when present.

#### Scenario: Machine duplicate marked
- **WHEN** a marketplace group holds two offers from machine M-01
- **THEN** the higher offer is marked `machine_duplicate` and the machine count counts M-01 once

### Requirement: Group browser
The dashboard SHALL list every region group of the latest snapshot for the chosen source, with
a toggle that narrows the list to the chosen GPU variant, showing each group's key, its member
count (for marketplace groups, its distinct machines and its offers) and labels
(`single list price`, `thin`, `synthetic`). It SHALL show no price, statistic or price-ordered ranking, SHALL sort
groups by key in its field order (variant, GPU count, region, rental type), and SHALL be captioned with the snapshot's start time in UTC, run ID and data
label.

#### Scenario: No prices in the browser
- **WHEN** the group browser is shown for a snapshot
- **THEN** it holds group keys, member counts and labels, and no column holds a price or statistic

#### Scenario: Narrowed to the chosen variant
- **WHEN** the toggle is on and "A100 PCIe 80GB" is the chosen variant
- **THEN** the browser lists only that variant's groups

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

### Requirement: Data-quality panel
For each source in the selected database, the dashboard SHALL show a data-quality panel built from
the quality report as of the injected time, holding counts only:
- missing: missing optional fields among compared rows, and observations not normalized;
- duplicate: repeats and `shared_meter_key` flags for Azure, `machine_duplicate` offers for the
  marketplace;
- stale: the stale flag with the as-of time;
- thin: thin summaries or groups;
- unmapped: the unmapped size names and the count of rows excluded as unmapped.

It SHALL also show, as secondary counts, rows by reason, rejected, out-of-scope rows,
`os_ambiguous` rows, single-price groups, changes, `absent once (unconfirmed)` and `not listed`.
Each panel SHALL be captioned with its snapshot's start time in UTC, run ID, data label and the
as-of time. A source with no succeeded run SHALL show "no snapshot".

#### Scenario: Panel counts match the report
- **WHEN** the panel is shown for a normalized synthetic Azure snapshot with one unmapped size
- **THEN** its counts equal the quality report's, and it names the unmapped size

#### Scenario: No snapshot in the panel
- **WHEN** the selected database holds no marketplace run
- **THEN** the marketplace panel shows "no snapshot"

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

