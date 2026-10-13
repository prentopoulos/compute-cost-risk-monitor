# Phase 4 dashboard review (manual check, market review and build safety)

- **Scope:** OpenSpec change `phase-4-dashboard` at commit ba67bf6, plus the code-review fixes
  at 7890d65 (§ Code review): the Streamlit dashboard
  (`app.py`, `dashboard.py`), the local-only Streamlit config, group members with their source
  price and provenance, read-only connections, and the synthetic Azure demo snapshot and loader.
- **Reviewer:** the main agent (Claude). This is a read-through plus the manual check, not the
  code review, which `/code-review` does on PR #9.
- **Evidence:**
  - the gate, the view-model unit tests and the AppTest flows on synthetic file databases;
  - a manual check in Chrome against `data/synthetic.duckdb`, through the real `app.main`;
  - the real `app.py` launched headless, to read its bind address and startup banner;
  - the real page run through AppTest on the live local database, printing counts, keys and
    pass or fail only.

  Counts only: no live price, USD/GPU-hour or statistic appears in this document. The three
  screenshots in `2026-10-12-phase-4-screenshots/` show the synthetic demo data (invented
  prices), never live figures (design D20).
- **Recheck when:** the page gains a view, a figure or an export path; the Streamlit version or
  `.streamlit/config.toml` changes; or the publishing gate is resolved.

## Manual check (task 5.1, 2026-10-12)

Synthetic data, in Chrome (`data/synthetic.duckdb`: the Azure demo snapshot and the three
marketplace snapshots, normalized; all seven independent checks pass on its 45 rows):

| Flow | Outcome |
|---|---|
| Framing line says "Synthetic data: invented prices for demonstration, not Azure list prices" with the snapshot time | Pass |
| Filters cascade over existing groups only (A100 → 1 GPU → pay-as-you-go; H100 → 8 GPUs → pay-as-you-go or Spot) | Pass |
| Region group: size, USD/GPU-hour, published price, currency, unit, retrieval time; `single list price` label; caption with key, snapshot, run, label and exclusions; Source records expander | Pass |
| Across regions: 5 regions with their lowest listed size, region count, min, median, max; `thin` on the one-region A100 summary; chart with points and min, median and max rules | Pass after fix |
| Group browser: keys, member counts and labels, no price column; the toggle narrows to the chosen variant | Pass |
| Data quality: both sources, the five checks, unmapped size named, captions with as-of time; marketplace STALE (its latest snapshot is 2026-10-03) | Pass after fix |
| No Deploy button; only the viewer menu | Pass |

Found and fixed in the check (commit ba67bf6):
- Tables drawn inside a hidden tab opened with collapsed columns. The tabs are now lazy, so only
  the open tab is drawn; re-checked in Chrome.
- The chart legend cut off "median (a statistic, not a listed price)", and the minimum rule had
  the points' colour. The legend now sits below the chart, the median rule is orange, min and max
  are grey, and axis ticks drop trailing zeros.
- The marketplace panel showed an Azure-only "sizes not in the map" count; it now reports only
  its `unmapped_gpu_name` rows.

The real entry point, launched headless from the repository root: the server listens on
`127.0.0.1:8501` only (netstat), the banner prints one local URL and no network or external
URL, so no IP lookup ran, and the health endpoint answers 200. The page was not opened in a
browser, because it defaults to the live database.

Live local data, through AppTest with the default databases (counts and pass or fail only):
- first page run 0.75 s; no exception; the live database is the default;
- the framing line says "Published Azure retail list prices for GPU VMs · live … local analysis
  only"; no mixed-label warning and no `NOT NORMALIZED` banner;
- all 17 variants render with every table and chart captioned with the `live` label;
- the group browser lists 929 groups with no price column;
- the panel's rows by reason equal the Phase 3 counts in HANDOFF (1,238 compared; 8,014 rental
  type not compared; 3,009 Windows; 775 unmapped; 666 fractional; 334 retired; 311 government
  cloud), with 49 sizes not in the map and 11 thin summaries.

Not checked: the live page in a browser (by design, D20), and a screen reader or a narrow
window.

## Market review (compute-cost-risk-monitor-market-review)

| Check | Outcome | Evidence |
|---|---|---|
| Original unit kept beside USD/GPU-hour | Pass | Each member row shows the published price, currency and "1 Hour" beside USD/GPU-hour (D10); test `test_region_group_lists_every_member`, `test_eight_gpu_member_shows_its_vm_price` |
| Figures computed by deterministic Phase 3 code, not the page | Pass | `dashboard.py` only arranges `groups` and `quality` outputs and formats them; no new figure (design § Figures shown) |
| Every figure carries group key, snapshot time, label and exclusions | Pass | One caption helper per figure kind; AppTest counts one caption per table and chart (`test_every_figure_is_captioned`); live check on all 17 variants |
| Comparable groups only; crossing regions said plainly | Pass | One region group at a time. The summary is labelled `crosses regions` and `lowest listed per region`, and its caption names the cheapest-configuration effect. The browser has no prices (D4) |
| Missing stays missing | Pass | The chart plots only regions with a listing and joins no points (`test_chart_plots_only_listed_regions`). A source without a run says "no snapshot", never zero |
| Stale, thin and single-price flagged | Pass | STALE in the framing line and panel with its as-of time; `thin` and `single list price` labels shown; the median is labelled a statistic |
| Display does not change values | Pass | 4 decimals for USD/GPU-hour (0 of 1,238 live rows move over 0.5% at 4 decimals, D9); the published price shows in full ("plain"); nothing computes from a rounded value |
| Labels and framing | Pass | "Published Azure retail list prices" or "Synthetic data: invented prices"; labels come from each run (`test_live_database_is_the_default` shows a "live" file holding synthetic runs framed as synthetic) |
| Synthetic demo data is labelled and separate | Pass | `azure_demo.json` carries `"_label": "synthetic"`; it is stored as a `synthetic` run, and the loader refuses `data/monitor.duckdb` |

## Build safety (compute-cost-risk-monitor-build-safety)

Workflows read (2026-10-12), applied through the skill's project adaptation:
- `assess_threat_vectors`: assets are the live price rows and the local database. The entry
  points are the browser session on this PC and the files the page opens. The agent and prompt
  threats do not apply (no model).
- `design_pii_redaction`: no personal data is involved. The sensitive class is the live Azure
  figures, whose destinations are this PC's screen and, by the owner's reading, a CSV saved on
  this PC (D8).
- `define_release_gates`: the gate, `uv audit`, the code review and this check are the release
  evidence for the PR.

| Threat or control | Disposition | Enforcement and test |
|---|---|---|
| Telemetry leaving the PC | Usage statistics off | `src/compute_cost_risk_monitor/.streamlit/config.toml`, beside the app script, so it applies from any launch folder; `test_usage_statistics_are_off`, `test_streamlit_reads_it_from_any_folder` |
| LAN exposure of live figures | The server binds 127.0.0.1 only; with the address set, the banner makes no IP lookups | Config; `test_server_listens_on_this_pc_only`; netstat in the manual check, launched from the repo root and from `tmp/` |
| Data export | The CSV download stays on: a file on this PC is local storage, and sharing it would still be redistribution (owner, recorded in PROJECT.md §6) | Owner decision D8 |
| Writes or locks on the live database | Read-only connection per page run, closed before drawing, never cached | `db.connect(read_only=True)`; `test_read_only_connection_is_utc_and_cannot_write`, `test_database_held_by_a_writer_is_in_use`, `test_connection_closed_after_the_run` |
| Stale or unnormalized data shown as current | STALE flag with its as-of time; group views withheld while a snapshot is `NOT NORMALIZED` | `test_stale_framing_as_of_an_injected_time`, `test_not_normalized_banner_withholds_groups` |
| Synthetic data mixed with live | Labels come from runs; mixed labels warned; synthetic loaders refuse `data/monitor.duckdb` | `test_mixed_labels_warned`, `test_command_refuses_the_live_database_for_azure_files` |
| Deploy to a hosted service from the menu | Developer options hidden (`toolbarMode = "viewer"`); hosting stays behind the publishing gate | `test_developer_options_are_hidden` |
| Secrets | None involved. `**/.streamlit/secrets.toml` is gitignored; detect-secrets stays in the gate | `test_streamlit_secrets_are_ignored` |
| Supply chain | Altair declared directly at the version already locked (6.3.0); no new package. `uv audit` found no known vulnerabilities in 67 packages | `uv.lock`; `test_dependencies.py` |
| Query injection | The page passes no user text into SQL; filters choose among values read from stored groups | Code review of `app.py` and `dashboard.py` |

The scheduling, spend and publishing gates are untouched. Nothing here is hosted.

## Code review (2026-10-13)

`/code-review` on PR #9 found 15 issues; all were fixed with tests in 7890d65 (design D31). The
ones that touched this review's checks:
- the Streamlit config applied only when launched from the repo root, so a launch from another
  folder would have bound every interface and sent usage statistics. It now sits beside the app
  script; a real launch from `tmp/` listened on 127.0.0.1 only;
- a database file without tables crashed the page, and a corrupt file read as "in use"; both now
  show the right message;
- the marketplace panel showed Azure-only missing fields; the quality report now counts the
  marketplace's own (country code);
- the browser counted marketplace offers beside a `thin` label that counts machines; it now shows
  machines and offers.

After the fixes the gate is green with 498 tests and 98% branch coverage.
