## Context

Phase 4 of PROJECT.md §6. Phase 3 delivered normalization under `groups-v1`, region groups,
cross-region summaries, marketplace groups, history and a counts-only quality report, all as pure
functions over stored rows (Phase 3 D6: Phase 3 computes group outputs; Phase 4 only displays
them). Phase 1's acceptance row for Phase 4: Streamlit filters by comparable group; every figure
shows its group key, snapshot time, exclusions and data label; a data-quality panel shows missing,
duplicate, stale, thin and unmapped counts; usage telemetry is off. Evidence: AppTest flows on
synthetic data, plus a local manual check.

The Phase 4 grilling ran one round on 2026-10-12:
- An informed-answerer subagent researched 20 questions and found 6 more.
- The main agent re-checked the settled answers' sources: Streamlit 1.65's `config.py`
  (`server.address`, `browser.gatherUsageStats`, `client.toolbarMode`,
  `client.disableDataExport`, the config-file order), its server's default bind address, the
  startup banner's IP lookups in `web/bootstrap.py`, pytest-socket's `allow_hosts` handling,
  `tests/smoke/test_stack.py`, `db.connect` and the synthetic fixtures.
- The owner accepted every recommendation ("all recommended").

Measured facts this design relies on (2026-10-12, local read-only commands, counts only):
- **Live data:** one live snapshot (`20261012T151909Z-5473f1`), normalized: 1,238 compared rows,
  929 region groups (684 single list price), 51 cross-region summaries (11 thin), 17 variants,
  54 regions, GPU counts 1, 2, 4 and 8, two compared rental types.
- **Precision:** stored VM-hour prices carry 1 to 6 decimal places (rows by places: 1:122,
  2:197, 3:396, 4:35, 5:111, 6:377). Rounding USD/GPU-hour moves more than 0.5% of the value in
  141 compared rows at 2 decimals, 2 rows at 3 and none at 4.
- **Speed:** opening the live database takes 0.06 s, `region_groups` 0.02 s, `summaries` 0.02 s
  and `quality.build` for both sources 0.12 s.
- **Locks (DuckDB 1.5.6 on this PC):** while one process holds a read-only connection, a writer
  in another process fails ("being used by another process"); a second read-only process
  succeeds. While a writer is open, a reader in another process fails. In one process, a second
  connection to the same file with a different configuration fails. Opening a missing file
  read-only fails and creates nothing. `register()` works on a read-only connection.
- **Streamlit 1.65.0 defaults:** `browser.gatherUsageStats` is true; `server.address` is unset,
  so the server binds 0.0.0.0 (turned into "::") and is reachable from the LAN; with the address
  unset, the startup banner looks up the internal IP (a UDP connect to 8.8.8.8) and, when
  headless, the external IP (checkip.amazonaws.com). Config files are read from
  `~/.streamlit`, then `$CWD/.streamlit`, then the script's folder, later files winning. The owner
  has no global `config.toml`.
- **Charts:** `st.scatter_chart` cannot layer rule marks. Altair 6.3.0 is locked through
  Streamlit (`altair>=5.0.0,<7`, excluding 5.4.0 and 5.4.1) and ships `py.typed`. AppTest exposes
  charts only as an unknown element, so chart tests check the Vega-Lite spec.
- **Tests:** AppTest needs a loopback socket on Windows. A test module marked
  `allow_hosts(["127.0.0.1"])` runs AppTest under the global socket block, and a connection to
  another host is still refused. Coverage counts a script run by AppTest. `streamlit.exe` in
  `.venv/Scripts` is uv's native launcher, so the `&` in the folder name does not break it.

## Goals / Non-Goals

**Goals:**
- A GPU buyer can pick one comparable group and see every listed size in it, with its
  USD/GPU-hour, its published VM-hour price and where each number came from.
- No figure appears without its group key, snapshot time, data label and exclusions, and the page
  says plainly whether it shows published Azure list prices or invented synthetic prices.
- The data-quality panel makes missing, duplicate, stale, thin and unmapped data visible before
  anyone reads a price.
- The dashboard is local only: no telemetry, no LAN exposure, no writes, and no lock that blocks
  collect or normalize.

**Non-Goals:** as in the proposal.

## Decisions

| # | Decision | Who / basis |
|---|---|---|
| D1 | Scope: the acceptance row plus the Phase 3 findings. Cascading filters (variant → GPU count → rental type → region) offering only groups that exist; a region-group view listing every member with its size name; the cross-region summary for the same variant, count and rental type; a synthetic marketplace group view (machines, `machine_duplicate` flagged); a group browser (D4); a data-quality panel per source. The latest succeeded snapshot only; history appears only as the panel's counts. Non-goals as in the proposal | **owner** (Scope) |
| D2 | Timebox: one session of about 3 h. Cut in this order if it overruns: (1) chart and visual polish beyond the default theme; (2) the marketplace view, reduced to its table; (3) the raw-file path and SHA-256 in the Source records expander, keeping item key, retrieval time and run ID. Never cut: group key, snapshot time (UTC), exclusions and data label on every figure; the panel's missing, duplicate, stale, thin and unmapped counts and the `NOT NORMALIZED` banner; the published VM-hour price and its unit beside USD/GPU-hour; telemetry off and the localhost bind; AppTest flows on synthetic data and the local manual check; counts-only Git and PR | **owner** (Scope, Value trade-off, Private knowledge) |
| D3 | Datasets: one database per page. A sidebar choice lists only the known databases that exist: `data/monitor.duckdb` ("Live Azure list prices (local only)") and `data/synthetic.duckdb` ("Synthetic (invented prices)"), defaulting to live when it exists. Every figure's label comes from the snapshot's `collection_run.data_label`, never from the file. A pure path resolver lets tests supply other paths | **owner** (Showcase) |
| D4 | Views across groups: besides one region group and its cross-region summary, a group browser lists group keys with member counts and labels and no prices. No price per group across groups. A Spot versus pay-as-you-go comparison is deferred to Phase 5 or 7 | **owner** (Methodology, Showcase) |
| D5 | One chart, for the cross-region summary: a point per contributing region at its lowest listed USD/GPU-hour (region and size in the tooltip); rule marks at min, median and max, the median labelled as a statistic; no line joining points; a region without a listing is absent. Built with Altair, declared as a direct dependency (`altair>=6.3,<7`). First on the cut list (D2) | **owner** (Scope, Showcase) |
| D6 | Look and copy: Streamlit's default theme, `layout="wide"`, no custom branding before Phase 7. Title "Compute Cost & Risk Monitor". Framing line: live or recorded, "Published Azure retail list prices for GPU VMs · <label> · snapshot <UTC> · local analysis only"; synthetic, "Synthetic data: invented prices for demonstration, not Azure list prices · snapshot <UTC>"; a stale snapshot adds "STALE (older than 7 days as of <UTC>)" | **owner** (Showcase) |
| D7 | Synthetic Azure demo dataset: commit `tests/fixtures/synthetic/azure_demo.json`, labelled synthetic, with invented round prices and real size names so `gpu-map-v1` applies. It covers a multi-size group, a single-price group, a thin and a non-thin summary, a Spot row equal to its pay-as-you-go price, an unmapped size and a Windows row. A loader writes it into `data/synthetic.duckdb` as an `azure-retail` run labelled `synthetic`, following Phase 3 D22 (a `file:` request URL and the file's SHA-256), and refuses `data/monitor.duckdb` | **owner** (Scope, Showcase) |
| D8 | CSV download: the built-in CSV download and copy controls of `st.dataframe` stay on (`client.disableDataExport` unset). A CSV saved on this PC is local storage under the live-data gate's scope; Streamlit itself says the setting is not a data-protection control. Recorded in PROJECT.md §6 as the owner's reading of the gate scope | **owner** (Gate) |
| D9 | Display precision: USD/GPU-hour and statistics at 4 decimal places; the published VM-hour price at its full stored precision with "USD per 1 Hour"; times as "YYYY-MM-DD HH:MM UTC", full ISO in the Source records expander. Values are formatted only for display (`st.column_config.NumberColumn(format=...)`); nothing is computed from rounded values | fact. Precision counts in § Context; Phase 3 D19 leaves rounding to Phase 4 |
| D10 | Traceability: each member row shows size or offer ID, USD/GPU-hour, the published price with currency and unit, and retrieval time; the rental type is in the group key. A "Source records" expander lists item key (which holds meter ID and SKU ID), run ID, data label, raw-response file path, sequence number and SHA-256. `groups.py`'s `_ROWS` query, which already joins `raw_response`, returns them through new `Member` fields (MODIFIED `comparable-groups`). The dashboard runs no price query of its own | recorded. PROJECT §3 ("Every price traces to its source record"); market-review ("the original unit kept beside USD/GPU-hour"); Phase 3 D6 |
| D11 | Local only: commit `.streamlit/config.toml` at the repo root with `[browser] gatherUsageStats = false` and `[server] address = "127.0.0.1"`. Launch from the repo root, where every project command already runs. A test parses the file and checks the settings. Setting the address also skips the startup banner's IP lookups | recorded (Phase 1 acceptance row; PROJECT §6 Azure scope, "local storage and analysis only") and fact (Streamlit 1.65 source, § Context) |
| D12 | `[client] toolbarMode = "viewer"` hides the Deploy button; the developer menu's rerun and clear-cache items go with it | default. One line undoes it |
| D13 | `db.connect(path, read_only=False)`: read-only connections keep `TimeZone=UTC` and skip creating the parent folder. The dashboard checks the file exists, opens it read-only once per page run, closes it in `finally`, and never caches it. A DuckDB I/O error on open is shown as "in use, rerun when it finishes". Tests close their writing connection before AppTest opens the file | fact. Lock measurements in § Context |
| D14 | No `st.cache_data` or `st.cache_resource`. If caching is needed later, `cache_data` keyed by (path, mtime) and never a connection | fact. Timings in § Context; a cached connection would block writers (D13) |
| D15 | As-of time: the app entry point reads `datetime.now(UTC)` once per page run and passes it down; view functions take it as a parameter and tests inject a fixed time. Phase 3 D21's "command default" includes the dashboard entry point | recorded. Phase 3 D21 |
| D16 | Synthetic fixtures dated 2026-10-12 show STALE after 2026-10-19 in the manual check and screenshots. The flag is shown as computed; the data is never redated | recorded. Phase 3 D8, D21 |
| D17 | Database states: no database names the commands that create one; no rule set says "run normalize first"; a source without a succeeded run says "no snapshot", never zero; a latest snapshot with observations lacking a row shows the `NOT NORMALIZED` banner with the count and the normalize command, and its group views are withheld | recorded. `data-quality` spec ("No snapshot", `NOT NORMALIZED`); `rules.stored` raises KeyError when no rule set is stored |
| D18 | Modules: `dashboard.py`, a pure view model with no Streamlit import (dataset resolution, filter options, DataFrames, captions, framing line, chart spec, formatting); `app.py`, the Streamlit script, with `main(paths, as_of)` called under `if __name__ == "__main__"`. Launch: `uv run streamlit run src/compute_cost_risk_monitor/app.py` from the repo root | default. Mirrors the Phase 2–3 split of pure logic from I/O; changes if the owner wants a shorter command |
| D19 | Tests: the dashboard test module is marked `allow_hosts(["127.0.0.1"])`, like the smoke test. Flows use `AppTest.from_function` calling `app.main` with temporary databases and a fixed as-of time, plus one `AppTest.from_file` run of `app.py`; `run(timeout=30)`. Fixtures are file databases built with `db.connect`, `create_schema`, the synthetic loaders and normalize, then closed. The view model has plain unit tests | fact. Reproduced by the answerer (§ Context); `tests/smoke/test_stack.py` |
| D20 | PR evidence: screenshots use synthetic data only. No live dashboard screenshot or figure goes into Git, the PR or reviews. The manual check runs on synthetic data and may also run on live local data, reported as counts, group keys and pass or fail only | recorded. Phase 3 D17; PROJECT §6 (no redistribution; publishing gate) |
| D21 | No schema change; the ERD is unchanged. The FigJam container view marks the Streamlit dashboard as built and leaves the calculator planned; `c4-container.svg` is re-exported | recorded. PROJECT §4; Phase 1 D5, D20; Phase 3 D18 |
| D22 | Capabilities: new `dashboard` and `synthetic-azure-snapshots` (D7); MODIFIED `comparable-groups` "Region groups" and `dev-environment` "Locked Python dependencies" (D30). `data-quality` and `synthetic-marketplace` are unchanged | default. Spec names are internal |
| D23 | Phase 3 findings on screen: every member listed with its size name, and a multi-size group captioned that its sizes share GPU variant and count but differ in vCPUs, RAM and local disk; the cross-region caption says each region contributes its lowest listed size, the cheapest configuration listed there; Spot rows equal to pay-as-you-go are shown as listed, with no warning; the `NOT NORMALIZED`, STALE (with as-of), `thin` (with its region or machine count), `single list price` and `synthetic` labels are shown | recorded. HANDOFF Phase 4 findings; `docs/reviews/2026-10-12-phase-3-normalization.md` |
| D24 | Captions: every table and chart carries its group key (or "crosses regions" with variant, count and rental type), snapshot start time in UTC and run ID, data label and the full exclusions text, built by one helper. The framing line is extra and replaces no caption | recorded. Phase 1 acceptance row; market-review |
| D25 | Panel fields: missing = `missing_fields` plus `not_normalized`; duplicate = `repeats` and `shared_meter_key` (Azure) or `machine_duplicate` (marketplace); stale = `stale` with as-of; thin = `thin`; unmapped = `unmapped_sizes` (names) plus `unmapped_sku` or `unmapped_gpu_name` row counts. Other report counts are secondary | recorded. `quality.QualityReport`; `data-quality` spec |
| D26 | Mixed labels: each figure shows its own snapshot's label, and the page warns when one source's succeeded snapshots carry more than one label. Synthetic loaders refuse `data/monitor.duckdb` | recorded. `groups.snapshots` and `history` take every succeeded run of a source whatever its label; Phase 3 D8 |
| D27 | `__init__.py`'s docstring ("Observed GPU rental asking prices") is reworded to "published Azure list prices" | recorded. PROJECT §5 naming rule |
| D28 | Page layout: the sidebar holds the dataset choice, the source choice (`azure-retail`, `synthetic-marketplace`) and the cascading filters. The main area holds the title and framing line, then three tabs: "Comparable groups" (region group, then cross-region summary and chart for Azure, or the marketplace group view), "Group browser" and "Data quality" | default. Main agent, while writing the specs; a two-way door |
| D29 | The synthetic Azure loader sits in `synthetic.py` under the existing command, which tells file kinds apart by shape (`Items` for Azure, `offers` for marketplace). Items go through `azure_retail.classify` and the same repeat, tally and row-writing code as live ingest, shared from `ingest.py` rather than copied | default. Main agent; keeps one set of Azure row rules (Phase 1 D23) |

| D30 | `dev-environment` "Locked Python dependencies" is brought in line with `pyproject.toml`: runtime pandas, DuckDB, Streamlit, pytz and Altair; dev pytest, pytest-cov, pytest-socket, Ruff, mypy, pandas-stubs, types-pytz, commitizen and detect-secrets. A repo test compares the two | recorded. Phase 1 D6 (pytz, owner), Phase 2 D15–D16 (pytest-socket, detect-secrets), D5 here (Altair). Main agent, found while declaring Altair (task 1.3) |

### Figures shown

Phase 4 computes no new price, cost or exposure figure. It displays Phase 3's.

| Figure | Comparable-group key | Units | Exclusions |
|---|---|---|---|
| Region-group members | variant, GPU count, region, rental type, snapshot | USD per GPU per hour, beside the published USD per VM per "1 Hour" | Phase 1 D13 text, in every caption |
| Cross-region summary and chart | variant, GPU count, rental type, snapshot; crosses regions and says so ("lowest listed per region", region count, `thin`) | USD per GPU per hour | as above |
| Marketplace group | variant, GPU count, region, rental type; one price per machine | USD per GPU per hour, **synthetic** | as above, plus `synthetic` and `thin` |
| Group browser | group keys only | none: counts and labels | none needed: no price |
| Data-quality panel | per source, latest snapshot | counts | none needed: no price |

### Non-negotiables check

| PROJECT.md §5 rule or §6 gate | How this design keeps it |
|---|---|
| Secrets never printed or committed | No secrets are involved. detect-secrets stays in the gate |
| Never fabricate; label results; preserve failed runs | Every figure shows its run's recorded label (D3, D24). Synthetic Azure data is labelled in the file, refused without the label, and stored as a `synthetic` run (D7). A mix of labels in one source is warned about (D26). Failed and partial runs are never shown as snapshots |
| Operator resolves ⛔ gates | The CSV-download reading is the owner's (D8). No gate is satisfied or waived by the agent |
| Call the data published Azure list prices | The framing line and labels say "Published Azure retail list prices" or "Synthetic data: invented prices" (D6). The median is labelled a statistic (D5). The docstring is corrected (D27) |
| Deterministic code computes every figure | The dashboard only displays Phase 3 outputs and formats them (D9, D10). There is no AI |
| Compare only within comparable groups; state exclusions | One region group or one cross-region summary at a time; the summary says it crosses regions (D1, D4). The group browser carries no prices (D4). Every figure carries the exclusions text (D24) |
| Collector only reads published prices | No network code is added. The dashboard reads stored rows read-only (D13) |
| Within terms; missing stays missing | Live figures stay on this PC: localhost bind and no telemetry (D11), synthetic-only screenshots (D20). Missing regions are absent from the chart (D5); "no snapshot" is never zero (D17) |
| ⛔ live data | Honoured: no new reads; stored live rows are shown locally only. CSV download read as local storage (D8, owner) |
| ⛔ scheduling / spend / publishing | Not acted on. No schedule, no paid service, no hosting; screenshots use synthetic data |

No exception to any rule is needed.

## Risks / Trade-offs

- [The live database is the default, so a screen share could show live figures] → The framing
  line says "local analysis only", and the owner chose this default (D3). PR screenshots use
  synthetic data only (D20).
- [AppTest cannot inspect charts] → The chart spec is built by the pure view model and tested
  as data: point count, rule values and the absence of a line mark (D5, D19).
- [A dashboard left open could block collect or normalize] → It opens read-only per page run and
  closes the connection before the run ends, with no cached connection (D13, D14).
- [Synthetic fixtures turn stale after 2026-10-19] → The flag is shown as computed (D16). Tests
  inject their as-of time, so they do not age (D15).
- [Streamlit internals (config keys, AppTest) change between versions] → The lockfile pins
  Streamlit 1.65.0, and the config test fails if a setting is lost.
- [The cut list may drop the chart] → The table views and captions carry every figure the chart
  shows (D2).

## Migration Plan

New modules, a config file, a fixture and tests. No schema change. `db.connect` keeps its default
behaviour; `read_only` is a new keyword. To roll back, revert the merge commit;
`data/synthetic.duckdb` is disposable and `data/monitor.duckdb` is never written.

## Open Questions

None for the owner.
