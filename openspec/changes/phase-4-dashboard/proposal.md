## Why

PROJECT.md Phase 4: a Streamlit dashboard with comparable-group filters and the data-quality
panel. Phase 3 computes region groups, cross-region summaries, marketplace groups and a
counts-only quality report, but they can only be read as command-line counts. A GPU buyer
cannot yet see the listed prices of one comparable group, with the labels and exclusions that
say what the figures are and are not.

The Phase 4 grilling (2026-10-12, one round) settled the scope. The owner accepted every
recommendation ("all recommended"). Design D1–D8 are owner decisions; D9 onwards are settled
with their basis.

## What Changes

- **Dashboard.** A local Streamlit app, `uv run streamlit run src/compute_cost_risk_monitor/app.py`,
  that reads one database at a time, read-only, and only displays what Phase 3 code computes:
  - a sidebar choice between the databases that exist (`data/monitor.duckdb`, live Azure;
    `data/synthetic.duckdb`, synthetic), defaulting to live, and a choice of source;
  - cascading comparable-group filters (variant → GPU count → rental type → region) that offer
    only groups that exist in the latest snapshot;
  - a region-group table listing every member size with its USD/GPU-hour, its published
    VM-hour price, currency and unit, and its retrieval time, plus a "Source records" expander;
  - the cross-region summary for the same variant, count and rental type, with one chart: each
    region's lowest listed USD/GPU-hour as a point, with min, median and max marked;
  - a synthetic marketplace group view: offers by machine, `machine_duplicate` flagged,
    machine count and statistics;
  - a group browser listing group keys, member counts and labels, with no prices;
  - a data-quality panel per source: missing, duplicate, stale, thin and unmapped counts, the
    `NOT NORMALIZED` banner, and the secondary counts.
- **Labels on every figure.** Each table and chart is captioned with its group key (or
  "crosses regions"), snapshot time (UTC) and run ID, data label, and the exclusions text. A
  framing line says what the data is: published Azure retail list prices, or synthetic.
- **Local only.** A committed `.streamlit/config.toml` turns usage statistics off, binds the
  server to 127.0.0.1 and hides the Deploy button.
- **Region-group members carry their source price and provenance.** The Phase 3 group query
  also returns each member's published price, currency, unit, run ID and raw-response file,
  sequence number and SHA-256 (MODIFIED `comparable-groups`).
- **Synthetic Azure demo data.** A committed, labelled synthetic Azure-shaped snapshot file and a
  loader that stores it in `data/synthetic.duckdb` as an `azure-retail` run labelled
  `synthetic`, through the same row rules as live ingest. It gives AppTest flows, the manual
  check and PR screenshots a dashboard-ready dataset with invented prices.
- **Read-only connections.** `db.connect` gains a read-only mode, so the dashboard never blocks
  or writes a database.
- **Documents.** PROJECT.md records the decisions and the owner's reading of the live-data gate
  for CSV download. The package docstring is reworded to "published Azure list prices". The
  FigJam container view marks the dashboard as built, with `c4-container.svg` re-exported.
  HANDOFF.md is updated.

## Non-goals

- No workload calculator or budget-exposure scenarios (Phase 5), and no market brief (Phase 7).
- No history view and no picker for older snapshots: the dashboard shows each source's latest
  succeeded snapshot. History appears only as counts in the quality panel.
- No view that ranks or prices groups against each other. No Spot versus pay-as-you-go
  comparison (deferred to Phase 5 or 7). No comparison of synthetic data with Azure data, and no
  cross-provider comparison.
- No button that collects, normalizes or writes anything. The dashboard opens databases
  read-only.
- No schema change, no new tables or views, and no new rule set or map version.
- No hosting, deployment or publishing, and no custom theme or branding (Phase 7).
- No live Azure figure in Git, the PR or reviews: screenshots use synthetic data only.
- No new network code, live read, schedule or spending.
- No change to the constitution (PROJECT.md §5–6). Recording the owner's reading of the
  live-data gate scope is not an amendment.

## Capabilities

### New Capabilities

- `dashboard`: the local Streamlit app: dataset and source choice, database states, comparable-
  group filters, the region-group, cross-region, marketplace and group-browser views, figure
  captions and the framing line, the data-quality panel, display formatting, and the local-only
  configuration.
- `synthetic-azure-snapshots`: the labelled synthetic Azure-shaped snapshot file format and its
  ingest as `azure-retail` runs labelled `synthetic`, kept out of `data/monitor.duckdb`.

### Modified Capabilities

- `comparable-groups`: "Region groups" members also report the observation's published price,
  currency and unit, and the run ID, raw-response file path, sequence number and SHA-256 they
  trace to.
- `dev-environment`: "Locked Python dependencies" lists the dependencies actually declared:
  pytz (Phase 1 D6), pytest-socket, detect-secrets and types-pytz (Phase 2) were added without
  updating it, and Altair joins in this phase (D5, D30).

## Impact

- New:
  - Package code: `src/compute_cost_risk_monitor/dashboard.py` (pure view model, no Streamlit
    import) and `src/compute_cost_risk_monitor/app.py` (the Streamlit script).
  - `.streamlit/config.toml`.
  - `tests/fixtures/synthetic/azure_demo.json` (synthetic, invented prices).
  - Tests: dashboard view-model unit tests, AppTest flows on synthetic databases, config and
    loader tests.
- Edited:
  - `groups.py` (member fields), `db.py` (read-only connections), `synthetic.py` (the Azure
    snapshot loader under the existing command), `__init__.py` (docstring).
  - `pyproject.toml` and `uv.lock`: Altair declared as a direct dependency. It is already locked
    at 6.3.0 through Streamlit, so no new package is installed.
  - PROJECT.md §4 and §6, HANDOFF.md, the FigJam board and `docs/architecture/c4-container.svg`.
- Local data: none written to `data/monitor.duckdb`. The synthetic loader writes
  `data/synthetic.duckdb`, which is disposable.
- ⛔ gates:
  - Live data: honoured. The dashboard reads stored rows only, binds to 127.0.0.1, and shows
    live figures locally only. The owner's reading of the built-in CSV download is recorded.
  - Scheduling, spend and publishing: untouched.
- Constitution: no amendment.
