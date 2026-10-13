# Current handoff

Read PROJECT.md and current user instructions. Inspect actual Git/OpenSpec state before resuming.

## Current checkpoint

**Phase 5 (workload cost calculator and labelled budget-exposure scenarios) is in progress** on
branch `phase-5-calculator`, OpenSpec change `openspec/changes/phase-5-calculator`. Grilling
finished on 2026-10-13: the owner accepted every recommendation in two rounds (design D1–D12 are
owner decisions, D13–D28 settled with their basis). The next step is the first open task in
`tasks.md`. The sections below describe Phase 4 and stay true.

Phase 4 (Streamlit dashboard with comparable-group filters and the data-quality panel) is Done.
It was delivered through PR #9 from branch `phase-4-dashboard` and archived as
`openspec/changes/archive/2026-10-13-phase-4-dashboard`. New specs in `openspec/specs/`:
`dashboard` and `synthetic-azure-snapshots`. Modified: `comparable-groups` (members carry their
source price and provenance), `data-quality` (marketplace missing fields) and `dev-environment`
(the declared dependencies). After the merge, no OpenSpec change is active.

Earlier phases are Done and merged: Phase 3 (PR #8), Phase 2 (PR #7), Phase 1 (PR #5) and
Phase 0 (PR #3).

Each phase starts in a fresh session (WORKFLOW.md § Fresh session per phase). Everything the
next phase needs is in this file, PROJECT.md, OpenSpec and Git.

PROJECT.md §5–6 are the constitution (version 2.1.0, unchanged in Phase 4). Copies in AGENTS.md
and `openspec/config.yaml` are kept in step by `tests/repo/test_constitution.py`.

**Live-data gate resolved for Azure (owner, 2026-10-12).** The scope, recorded in PROJECT.md §6:
- unauthenticated GET of the Retail Prices API only, with the GPU filter;
- runs the owner starts by hand, at most one a day;
- at most 1 request/s, backing off on 429;
- local storage and analysis only, with no redistribution.

Owner's reading, 2026-10-12 (Phase 4 grilling): the dashboard's CSV download and copy controls
stay on; a file saved on this PC is local storage, and sharing it would still be redistribution.
The scheduling, spend and publishing gates are untouched.

## Commands

In this environment's bash, uv lives at
`/c/Users/Peter/AppData/Local/Microsoft/WinGet/Packages/astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe/uv.exe`.
Every command prints counts, names and keys only, never prices.

- **Collect (Phase 2):** `uv run python -m compute_cost_risk_monitor.collect` fetches one `live`
  run into `data/raw/azure-retail/` and ingests it into `data/monitor.duckdb`.
  - `--ingest-run RUN_ID` restores kept files without the network.
  - A live fetch within 24 hours of the last one is refused.
- **Normalize (Phase 3):** `uv run python -m compute_cost_risk_monitor.normalize [--db PATH]`.
  - Stores `groups-v1` and `gpu-map-v1` once, then writes one `normalized_price` row for every
    observation lacking one, in one transaction, and runs the independent checks.
  - Exit codes: 0 when the checks pass, 1 when a check fails, 2 when refused.
  - **Run it after every collect**; the dashboard and the quality report flag a snapshot that is
    not normalized yet.
- **Quality (Phase 3):** `uv run python -m compute_cost_risk_monitor.quality [--db PATH]
  [--as-of TIME]` prints the counts-only report for each source's latest snapshot.
- **Synthetic data (Phases 3–4):** `uv run python -m compute_cost_risk_monitor.synthetic FILE ...
  [--db PATH]` stores labelled synthetic snapshots as `synthetic` runs. It tells marketplace
  files (`offers`) from Azure-shaped ones (`Items`), defaults to `data/synthetic.duckdb` and
  refuses `data/monitor.duckdb`. The demo database:
  `... synthetic tests/fixtures/synthetic/azure_demo.json tests/fixtures/synthetic/marketplace/snapshot-1.json
  ...snapshot-2.json ...snapshot-3.json`, then `normalize --db data/synthetic.duckdb`.
- **Dashboard (Phase 4):** `uv run streamlit run src/compute_cost_risk_monitor/app.py`.
  - The config beside the script applies from any folder: 127.0.0.1 only, no usage statistics,
    no Deploy button.
  - It offers the databases that exist, live first. Labels come from each run.
  - Each page run holds a read-only lock while it reads (under a second on the live data). A
    collect or normalize started in that moment fails rather than waits: rerun it.

## Implemented behavior (Phase 4)

Owner decisions are D1–D8 in the archived design. D9–D31 are settled with their basis. D31 records
the code review.

- **Page (`app.py`):**
  - a sidebar choice of database and source, with cascading filters that offer only existing
    groups (variant → GPU count → rental type → region);
  - a framing line, "Published Azure retail list prices … local analysis only" or "Synthetic
    data: invented prices …", plus STALE, mixed-label and `NOT NORMALIZED` notices;
  - three lazy tabs, of which only the open one is drawn:
    - **Comparable groups:** the region group, its Source records and the cross-region summary
      with its chart;
    - **Group browser:** keys, counts and labels, with no prices;
    - **Data quality:** one panel per source.
- **View model (`dashboard.py`):**
  - no Streamlit import, and it only arranges Phase 3 outputs;
  - every table and chart showing a price carries the group key (or "crosses regions"),
    snapshot time and run, data label and exclusions;
  - USD/GPU-hour is shown at 4 decimals and the published price in full;
  - states: no database, no tables, no rule set, no snapshot, not normalized, in use, and other
    open errors shown as themselves.
- **Groups:** each member now carries its published price, currency, unit, run ID, raw file,
  sequence number and SHA-256.
- **Synthetic Azure demo:** `tests/fixtures/synthetic/azure_demo.json` holds invented prices for
  real size names. It is loaded through the live row rules, and a file with no stored item is
  refused.
- **Read-only connections:** `db.connect(path, read_only=True)`.
- **Diagrams:** the FigJam container view marks the dashboard built and the calculator planned
  (Phase 5), and `docs/architecture/c4-container.svg` is re-exported. The ERD is unchanged.

## Data collected so far

- **One live snapshot:** `20261012T151909Z-5473f1` (owner, 2026-10-12), succeeded. It has 14,347
  stored rows covering 100 GPU sizes in 60 regions.
- **Normalized under `groups-v1`:** 1,238 compared rows.
  - 929 region groups, 684 of them single list price.
  - 51 cross-region summaries, 11 of them thin.
  - 49 sizes are not in the map.

  The dashboard's panel matches these counts.
- **`data/synthetic.duckdb`:** the synthetic demo database, built 2026-10-12. It is disposable and
  can be rebuilt with the commands above.
- All data is local in `data/` (gitignored). `data/monitor.pre-phase3.duckdb` is a pre-Phase 3
  copy the owner may delete. Only counts appear anywhere in Git.

## Verification

- **Gate:** green on the branch; 498 tests pass, 98% branch coverage. `uv audit` found no known
  vulnerabilities in 67 packages.
- **CI:** hosted CI passed on the branch pushes.
- **Manual check:** recorded in `docs/reviews/2026-10-12-phase-4-dashboard.md`.
  - Chrome against the synthetic database.
  - The real app launched headless from the repo root and from another folder: it listens on
    127.0.0.1 only and makes no IP lookups.
  - The live database through AppTest, with counts-only output:
    - all 17 variants render with captions;
    - the browser lists 929 groups;
    - the panel matches the Phase 3 counts.
- **Code review:** `/code-review` on PR #9 found 15 issues, and all were fixed with tests (D31).
- **Read-through:** the market-review and build-safety read-through, plus three synthetic-data
  screenshots, are in `docs/reviews/`.

## Findings for later phases

- **Phase 5 (calculator and exposure):**
  - The container view already has a planned calculator box. A Streamlit page beside the
    dashboard can reuse `dashboard.py`'s captions, labels and read-only loading.
  - A Spot versus pay-as-you-go comparison was deferred from Phase 4 (D4). It crosses rental
    types, so it needs an owner decision if wanted.
  - Use 730 h/month only where stated (Phase 1 D17). The 32 × 720 × $0.50 = $11,520 example
    must pass.
- **Phase 7 (demo):**
  - Custom theme and branding were deferred (D6).
  - `azure_demo.json` is the likely public demo dataset, subject to the publishing gate.
  - The screenshots show the Streamlit default theme.
- **Map v2:** add the H100 `noIB`/`flex`/`isrf` sizes, MI300X `ND96is` and 20 RTX PRO 6000 sizes
  only when Learn names them exactly. A new version, never an edit.
- **History:** only one live snapshot exists. Changes and "not listed" need owner-started runs,
  at most one a day.
- **DuckDB 1.5.6 limits:**
  - A referenced row cannot be updated.
  - Migrations cannot add CHECKs or constrained columns.
  - A writer and a reader in different processes exclude each other.
- **Streamlit 1.65 quirks:**
  - A table drawn in a hidden tab opens with collapsed columns, hence lazy tabs.
  - AppTest keeps no tab state between runs, so tests set `session_state["view"]`.
  - AppTest needs a loopback socket on Windows, so its tests are marked `allow_hosts(["127.0.0.1"])`.
- **Local quirks:**
  - Gate runs use `PYTEST_ADDOPTS=--basetemp=tmp/pytest`; `tmp/` is gitignored and must exist.
  - npm's `.cmd` shims break on the `&` in the folder name; run Node CLIs as
    `node node_modules/<pkg>/<bin>.js`.
  - Commands shown to the owner must quote paths.
  - The Chrome extension's screenshots time out intermittently on the Streamlit page; reading the
    page text works.
  - Figma's `download_assets` exports a node as SVG straight to a URL, so no chunking is needed.
    Strip its full-page background `<rect>` to match earlier exports.
- **Carried over:**
  - Phase 7 stays synthetic unless the publishing gate approves derived live figures.
  - Recheck CME futures before Phase 7.
  - Dependabot alert #1 (`braces`, dev-only, no fix) stays open.
  - detect-secrets scans files only: scan Git history before the repo goes public.
  - A refused synthetic command can leave an empty `data/synthetic.duckdb`. The dashboard now
    explains it, but the command could check its files before creating the database.

## Next action

Start Phase 5 (workload cost calculator and labelled budget-exposure scenarios) in a fresh
session: the owner clears the context and runs `/next-phase`. Then grill Phase 5 using the
Phase 1 acceptance row and the findings above. Collecting more live data is the owner's choice:
one manual run a day at most, followed by normalize.
