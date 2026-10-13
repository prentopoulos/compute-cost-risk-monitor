# Current handoff

Read PROJECT.md and current user instructions. Inspect actual Git/OpenSpec state before resuming.

## Current checkpoint

Phase 5 (workload cost calculator and labelled budget-exposure scenarios) is Done. It was
delivered through PR #10 from branch `phase-5-calculator` and archived as
`openspec/changes/archive/2026-10-13-phase-5-calculator`. New spec in `openspec/specs/`:
`workload-calculator`. Modified:
- `dashboard`: the "Workload cost view", workload captions and display formatting;
- `synthetic-azure-snapshots`: the demo file covers a Spot size with no pay-as-you-go listing.

After the merge, no OpenSpec change is active.

Earlier phases are Done and merged: Phase 4 (PR #9), Phase 3 (PR #8), Phase 2 (PR #7), Phase 1
(PR #5) and Phase 0 (PR #3).

Each phase starts in a fresh session (WORKFLOW.md § Fresh session per phase). Everything the
next phase needs is in this file, PROJECT.md, OpenSpec and Git.

PROJECT.md §5–6 are the constitution (version 2.1.0, unchanged in Phase 5). Copies in AGENTS.md
and `openspec/config.yaml` are kept in step by `tests/repo/test_constitution.py`.

**Live-data gate resolved for Azure (owner, 2026-10-12).** The scope, recorded in PROJECT.md §6:
- unauthenticated GET of the Retail Prices API only, with the GPU filter;
- runs the owner starts by hand, at most one a day;
- at most 1 request/s, backing off on 429;
- local storage and analysis only, with no redistribution.

Owner's reading, 2026-10-12 (Phase 4 grilling): the dashboard's CSV download and copy controls
stay on; a file saved on this PC is local storage, and sharing it would still be redistribution.
Phase 5 fetches nothing new: storage is an amount the user enters, because disk prices are
outside the GPU filter. The scheduling, spend and publishing gates are untouched.

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
- **Synthetic data (Phases 3–5):** `uv run python -m compute_cost_risk_monitor.synthetic FILE ...
  [--db PATH]` stores labelled synthetic snapshots as `synthetic` runs. It tells marketplace
  files (`offers`) from Azure-shaped ones (`Items`), defaults to `data/synthetic.duckdb` and
  refuses `data/monitor.duckdb`. The demo database:
  `... synthetic tests/fixtures/synthetic/azure_demo.json tests/fixtures/synthetic/marketplace/snapshot-1.json
  ...snapshot-2.json ...snapshot-3.json`, then `normalize --db data/synthetic.duckdb`. After the
  demo file changes, rebuild from an empty file: move the old `data/synthetic.duckdb` aside first.
- **Dashboard (Phases 4–5):** `uv run streamlit run src/compute_cost_risk_monitor/app.py`.
  - The config beside the script applies from any folder: 127.0.0.1 only, no usage statistics,
    no Deploy button.
  - It offers the databases that exist, live first. Labels come from each run.
  - Tabs: Comparable groups, Workload cost, Group browser, Data quality.
  - Each page run holds a read-only lock while it reads (under a second on the live data). A
    collect or normalize started in that moment fails rather than waits: rerun it.

## Implemented behavior (Phase 5)

Owner decisions are D1–D12 in the archived design. D13–D28 are settled with their basis. D29
records the code review.

- **Scenario set (`scenarios.py`):** data only, frozen as `scenarios-v1`:
  - Decline −25%, Increase +25%, PROJECT example +$0.50/GPU-hour and Spike +100%;
  - each with a narrative; the spike names arXiv 2603.21690 only as motivation;
  - the labels "Scenario calculation, not a forecast" and the judgement note.
- **Calculator (`calculator.py`):** pure, with no Streamlit and no database.
  - Validates whole-VM GPU counts (naming the nearest valid counts), hours (0 to 8,784), an
    optional storage amount, a custom change and a budget. Nothing is rounded.
  - Starts from one member of the chosen region group, the lowest listed by default
    (`groups.price_order`, the one rule for "lowest listed").
  - Cost = GPUs × hours × USD/GPU-hour, plus storage when entered.
  - Scenario rows with signed exposure and effect. A price at or below zero is refused, never
    floored.
  - For Spot: the "Spot to pay-as-you-go fallback" from the same size in the same region, or
    "not computed"; a note on any Spot row above that size's pay-as-you-go price.
  - Budget headroom: the rise per GPU-hour that would use up a budget.
- **Independent check (`workload_check.py`):** imports no calculator code. It re-derives every
  figure, effect and note from the VM-hour prices of the member the page picked and the scenario
  definitions, at tolerances scaled to each figure. The page shows no figure unless it passes.
- **Tab ("Workload cost", `app.py` and `dashboard.py`):**
  - inputs keyed with `persist_state="session"`, so they survive tab and group changes;
  - a size choice per group;
  - a cost breakdown, a scenario table (outcome columns first) and an exposure bar chart;
  - headroom text;
  - captions carrying the group key, snapshot, label, exclusions, storage line, billing
    assumptions, Spot line, `scenarios-v1` and the forecast label;
  - the fallback's caption names both keys and the pay-as-you-go item key, or "(not listed in
    this snapshot)".
- **States:** the marketplace source shows a note, and a snapshot that is missing, not
  normalized or groupless shows its state. No price appears before validation and the check.
- **Demo data:** `azure_demo.json` gained an invented uksouth Spot H100 ×8 item with no
  pay-as-you-go listing, so the demo shows "not computed".
- **Diagrams:** the FigJam container view marks the calculator built (a component in the
  dashboard tab), and `docs/architecture/c4-container.svg` is re-exported. The ERD is unchanged.

## Data collected so far

- **One live snapshot:** `20261012T151909Z-5473f1` (owner, 2026-10-12), succeeded. It has 14,347
  stored rows covering 100 GPU sizes in 60 regions.
- **Normalized under `groups-v1`:** 1,238 compared rows.
  - 929 region groups, 684 of them single list price; 456 are Spot, and every Spot size is
    listed on pay-as-you-go in its region.
  - 51 cross-region summaries, 11 of them thin.
  - 49 sizes are not in the map.
- **`data/synthetic.duckdb`:** the synthetic demo database, rebuilt 2026-10-13 from the updated
  demo file. It is disposable. The pre-Phase 5 copy is `tmp/synthetic.pre-phase5.duckdb`, also
  disposable.
- All data is local in `data/` (gitignored). `data/monitor.pre-phase3.duckdb` is a pre-Phase 3
  copy the owner may delete. Only counts appear anywhere in Git.

## Verification

- **Gate:** green on the branch, with branch coverage at 98%. `uv audit` found no known
  vulnerabilities in 67 packages. The exact test count is in the PR.
- **CI:** hosted CI ran on the branch pushes.
- **Review record:** `docs/reviews/2026-10-13-phase-5-calculator.md`.
  - Manual check in Chrome on synthetic data.
  - Live check, counts only: every one of the 1,238 live members as the starting price, alone
    and with a custom change and budget. All 2,476 results pass the independent check, and the
    PROJECT example is exactly 11,520 in all of them. The real tab renders for all 33 variant ×
    rental type combinations.
  - Market-review and build-safety read-through. The BCBS d450 checklist is in the design.
- **Code review:** `/code-review` on PR #10 found 14 issues, and all were fixed with tests (D29).

## Findings for later phases

- **Phase 6 (tests):**
  - Set the coverage threshold deferred in Phase 0. Branch coverage is about 98%; `app.py` is
    the lowest file.
  - The extreme-input test sweeps 400 invented prices. Property-based testing (Hypothesis)
    would be a new dev dependency, so it needs a decision.
  - Close the brief's gaps: units, calculations, missing data and stale offers.
- **Phase 7 (demo):**
  - "PROJECT example +$0.50/GPU-hour" reads oddly to a public audience. Renaming it needs a
    `scenarios-v2` and an owner call.
  - Screenshots of the tables need a visible Chrome window: in a hidden window the data grid's
    canvas does not paint.
  - In the FigJam container view, the label "Dashboard reads synthetic (read-only)" overlaps
    "Creates tables" (from Phase 4). Fix it with the Phase 7 diagram update.
  - Custom theme and branding were deferred (Phase 4 D6). `azure_demo.json` is the likely
    public demo dataset, subject to the publishing gate.
- **Map v2:** add the H100 `noIB`/`flex`/`isrf` sizes, MI300X `ND96is` and 20 RTX PRO 6000 sizes
  only when Learn names them exactly. A new version, never an edit.
- **History:** only one live snapshot exists. Changes, "not listed" and any history-based
  scenario need owner-started runs, at most one a day.
- **DuckDB 1.5.6 limits:**
  - A referenced row cannot be updated.
  - Migrations cannot add CHECKs or constrained columns.
  - A writer and a reader in different processes exclude each other.
- **Streamlit 1.65 quirks:**
  - A table drawn in a hidden tab opens with collapsed columns, hence lazy tabs.
  - AppTest keeps no tab state between runs, so tests set `session_state["view"]`.
  - AppTest needs a loopback socket on Windows, so its tests are marked `allow_hosts(["127.0.0.1"])`.
  - `persist_state="page"` resets a remounted widget to its default under AppTest; use
    `"session"`.
  - A keyed `number_input` keeps its value when its min or step changes, and resets only when
    the value falls outside the new bounds.
- **Local quirks:**
  - Gate runs use `PYTEST_ADDOPTS=--basetemp=tmp/pytest`; `tmp/` is gitignored and must exist.
  - npm's `.cmd` shims break on the `&` in the folder name; run Node CLIs as
    `node node_modules/<pkg>/<bin>.js`.
  - Commands shown to the owner must quote paths.
  - The Chrome extension's screenshots time out intermittently on the Streamlit page. Reading
    the page text, or the data grid's accessible cells through JavaScript, works.
  - The dashboard reopens on the live database after a restart. Switch to synthetic first, and
    confirm it before reading figures.
  - Some multi-line bash heredocs fail to parse in the agent's shell tool; writing to a scratch
    file and appending with Python works.
  - Figma's `download_assets` exports a node as SVG straight to a URL. Strip its full-page
    background `<rect>` to match earlier exports.
  - Cloning a FigJam connector shared its label with the original; build new connectors fresh.
- **Carried over:**
  - Phase 7 stays synthetic unless the publishing gate approves derived live figures.
  - Recheck CME futures before Phase 7.
  - Dependabot alert #1 (`braces`, dev-only, no fix) stays open.
  - detect-secrets scans files only: scan Git history before the repo goes public.
  - A refused synthetic command can leave an empty `data/synthetic.duckdb`. The dashboard
    explains it, but the command could check its files before creating the database.

## Next action

Start Phase 6 (tests for units, calculations, missing data and stale offers, and the coverage
threshold deferred in Phase 0) in a fresh session: the owner clears the context and runs
`/next-phase`. Then grill Phase 6 using the Phase 1 acceptance row and the findings above.
Collecting more live data is the owner's choice: one manual run a day at most, followed by
normalize.
