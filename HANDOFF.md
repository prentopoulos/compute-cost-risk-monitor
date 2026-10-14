# Current handoff

Read PROJECT.md and current user instructions. Inspect actual Git/OpenSpec state before resuming.

## Current checkpoint

Phase 7 (front-office interface: dark desk theme, answer-first layout and a scenario ladder) is
Done. It was delivered through PR #13 from branch `phase-7-interface` and archived as
`openspec/changes/archive/2026-10-14-phase-7-interface` (design D1–D50). Specs changed in
`openspec/specs/`:
- `dashboard`: ADDED "Desk theme" and "Status line and key figures". MODIFIED "Local-only
  configuration" (Streamlit's menu hidden), "Dataset and source choice", "Figure captions and
  framing line" (status line, one footer, Sources), "Workload cost view", "Comparable-group
  filters" (region names), "Region-group view", "Cross-region summary view", "Group browser" and
  "Display formatting".
- `workload-calculator`: ADDED "Scenario ladder ladder-v1". MODIFIED "Independent check of
  workload figures" (every ladder cell re-derived), "Budget headroom" (the input is labelled
  "Contingency, USD") and "Spot price above pay-as-you-go" (the note names the "Spot → PAYG *"
  row).

The design rounds, both critiques, the manual check, the market review and the code review are in
`docs/reviews/2026-10-14-phase-7-interface.md`, with four synthetic screenshots. `DESIGN.md` at
the root records the design system derived from the build; `config.toml` holds the theme values
and PROJECT.md §5 outranks it.

The approved Figma mock v3 is https://www.figma.com/design/aODgN8zO3eCm9bmN8sOSCK?node-id=7-2 (file
"Compute Cost & Risk Monitor · Interface (Phase 7)", the owner's Projects team), with its state
frames. It holds synthetic figures only.

Earlier phases are Done and merged: Phase 6 (PR #11), Phase 5 (PR #10), Phase 4 (PR #9), Phase 3
(PR #8), Phase 2 (PR #7), Phase 1 (PR #5) and Phase 0 (PR #3). PR #12 added the design-skill
routing (`.agents/skills/next-phase/design-skills.md`).

Each phase starts in a fresh session (WORKFLOW.md § Fresh session per phase). Everything the
next phase needs is in this file, PROJECT.md, OpenSpec and Git.

PROJECT.md §5–6 are the constitution (version 2.1.0, unchanged in Phase 7). Copies in AGENTS.md
and `openspec/config.yaml` are kept in step by `tests/repo/test_constitution.py`.

**Live-data gate resolved for Azure (owner, 2026-10-12).** The scope, recorded in PROJECT.md §6:
- unauthenticated GET of the Retail Prices API only, with the GPU filter;
- runs the owner starts by hand, at most one a day;
- at most 1 request/s, backing off on 429;
- local storage and analysis only, with no redistribution.

Owner's reading, 2026-10-12 (Phase 4 grilling): the dashboard's CSV download and copy controls
stay on; a file saved on this PC is local storage, and sharing it would still be redistribution.
Phase 7 fetched nothing new. Live figures never left this PC: Figma, screenshots, Git and the PR
hold synthetic figures only. The scheduling, spend and publishing gates are untouched.

## Commands

In this environment's bash, uv lives at
`/c/Users/Peter/AppData/Local/Microsoft/WinGet/Packages/astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe/uv.exe`.
Every command prints counts, names and keys only, never prices.

- **Gate:** `uv run --frozen python scripts/gate.py`. It runs nine checks:
  - pytest fails below 99.0% total branch coverage;
  - "core coverage" fails unless the eleven calculation and data modules are at 100%: azure_retail,
    normalize, checks, gpu_map, rules, groups, history, quality, calculator, scenarios and
    workload_check.
- **Property tests:** they run in the gate under the fixed `gate` profile (`tests/conftest.py`).
  For a longer random search by hand: `HYPOTHESIS_PROFILE=explore uv run pytest
  tests/unit/test_properties.py`.
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
  [--as-of TIME]` prints the counts-only report for each source's latest snapshot. Any
  `--as-of` offset is converted to UTC.
- **Synthetic data (Phases 3–6):** `uv run python -m compute_cost_risk_monitor.synthetic FILE ...
  [--db PATH]` stores labelled synthetic snapshots as `synthetic` runs.
  - It tells marketplace files (`offers`) from Azure-shaped ones (`Items`), defaults to
    `data/synthetic.duckdb` and refuses `data/monitor.duckdb`.
  - It checks every file before it opens the database, so a refused file writes nothing.
  - The demo database: `... synthetic tests/fixtures/synthetic/azure_demo.json
    tests/fixtures/synthetic/marketplace/snapshot-1.json ...snapshot-2.json ...snapshot-3.json`,
    then `normalize --db data/synthetic.duckdb`. After the demo file changes, rebuild from an
    empty file: move the old `data/synthetic.duckdb` aside first.
- **Dashboard (Phases 4–7):** `uv run streamlit run src/compute_cost_risk_monitor/app.py`.
  - The config beside the script applies from any folder: 127.0.0.1 only, no usage statistics,
    one dark theme, and Streamlit's menu hidden (no Deploy button and no theme switch).
  - It offers the databases that exist, live first: "Azure list prices (local only)" and
    "Synthetic demo". Labels come from each run.
  - Tabs: Workload cost (first), Comparable groups, Group browser, Data quality. Only the open
    tab is drawn.
  - Each page run holds a read-only lock while it reads (under a second on the live data). A
    collect or normalize started in that moment fails rather than waits: rerun it.

## Implemented behavior (Phase 7)

Owner decisions are D1–D15, D27–D29, D31–D39, D47 and D49 in the archived design; the rest are
settled with their basis. D50 records the code review.

- **Layout (mock v3):**
  - one status line on every tab: the title, the data label in amber, AS OF in UTC, and STALE;
  - key figures ("Cost, USD", "USD/GPU-h · PAYG|SPOT", "VMs", "GPUs × h", "Headroom,
    USD/GPU-h"), shown as "—" until the independent check passes;
  - one row of inputs, the %/USD unit switch above the Custom input;
  - then one 960 px column: the scenario grid, a muted footer with one clause per line, the COST
    table and a closed Sources section that holds every explanation.
- **Scenario grid:** `ladder-v1` (−50% to +100% and +0.50 USD/GPU-h) by 8–128 GPUs plus the
  entered count, whole USD rounded half up, red "+" and green "−", the entered column shaded and
  bold, a "Spot → PAYG *" row for Spot starts and "†" for rows above the pay-as-you-go list
  price. `workload_check` re-derives every cell without importing the calculator.
- **States:** plain status words (REFUSED, CHECK FAILED, WITHHELD, NO SNAPSHOT, NO GROUPS, IN
  USE, CANNOT READ) with their messages, never alert boxes.
- **Contingency:** the headroom input is "Contingency, USD", money set aside for price rises
  (D49). The calculation is unchanged.
- **Region names:** the stored location name from the shown snapshot's run, in the filter, the
  cross-region table, its chart and the Group browser; Sources keep the code.
- **Tests:** 784, up from 718, at 100.0% branch coverage; the core modules at 100%.
- **Diagrams:** unchanged; Phase 7 changed no component, data flow or schema. Phase 8 updates
  them.

## Data collected so far

- **One live snapshot:** `20261012T151909Z-5473f1` (owner, 2026-10-12), succeeded. It has 14,347
  stored rows covering 100 GPU sizes in 60 regions. It turns stale after 2026-10-19 15:19 UTC.
- **Normalized under `groups-v1`:** 1,238 compared rows.
  - 929 region groups, 684 of them single list price; 456 are Spot, and every Spot size is
    listed on pay-as-you-go in its region.
  - 51 cross-region summaries, 11 of them thin.
  - 49 sizes are not in the map.
- **`data/synthetic.duckdb`:** the synthetic demo database, rebuilt 2026-10-13 and unchanged by
  Phase 7. `tmp/synthetic.pre-phase5.duckdb` is a disposable older copy.
- All data is local in `data/` (gitignored). `data/monitor.pre-phase3.duckdb` is a pre-Phase 3
  copy the owner may delete. Only counts appear anywhere in Git.

## Verification

- **Gate:** green on the branch with both coverage steps. 784 tests pass, at 100.0% branch
  coverage, with the core modules at 100%. `uv audit` found no known vulnerabilities in 69
  packages; the phase added no dependency.
- **CI:** hosted CI ran on the branch pushes.
- **Review record:** `docs/reviews/2026-10-14-phase-7-interface.md`:
  - mock critique 25/40 and build critique 27/40, with every finding and what was done;
  - the manual check at 1920×1080 and 1440×900, synthetic only;
  - the market-review read-through: every shown figure matches an independent recomputation,
    and the PROJECT example is exactly 11,520.
- **Code review:** `/code-review` on PR #13 found 15 issues: 13 fixed with tests, and 2 partly
  fixed and partly answered in design D50.

## Findings for later phases

- **Phase 8 (demo):**
  - The dashboard opens on the live database when it exists. Switch to "Synthetic demo" before
    the first frame of any recording, and confirm the amber SYNTHETIC label.
  - `azure_demo.json` is the likely public demo dataset, subject to the publishing gate.
  - The methodology document can cite the Phase 6 traceability table, the end-to-end fixture's
    worked answers and `DESIGN.md`.
  - In the FigJam container view, the label "Dashboard reads synthetic (read-only)" overlaps
    "Creates tables" (from Phase 4). Fix it with the Phase 8 diagram update.
  - Some 21st.dev code copies could be saved for Phase 8's public page, where React or HTML
    code could actually run (Phase 7 D15). The account is free tier: 2 free code copies a day.
  - Hours start at 0.01 (Phase 6 D23). If the owner prefers one billed minute (1/60 h), that is
    a small `workload-calculator` change.
- **Recorded in the Phase 7 critiques, not fixed:**
  - Group browser and Data quality got the theme only (D2): Data quality keeps large headings,
    raw field names, "Stale: no (latest snapshot older than 7 days…)" and size names as 10.5 px
    inline code.
  - A Group browser row cannot load its group, and the grid cannot be exported.
  - The 2 px zero rule measures 2.46:1 (decorative).
  - A tiny custom move can print a grid cell in exponent form ("+6e-09").
  - "AS OF" is the snapshot time in the status line and the check time in the STALE clause
    (owner-approved wording, D9, D28).
  - The owner rejected adding the region to the price label (it repeats the sidebar).
  - D17's separate impeccable polish pass was folded into the critique fixes.
- **Not yet tested:**
  - changes, absences and "not listed" on real data, which need more owner-started live
    snapshots;
  - the Phase 7 page on the live database by eye (AppTest and the synthetic viewer cover it);
  - mutation testing (Phase 6 D5).
- **Map v2:** add the H100 `noIB`/`flex`/`isrf` sizes, MI300X `ND96is` and 20 RTX PRO 6000 sizes
  only when Learn names them exactly. A new version, never an edit.
- **History:** only one live snapshot exists. Changes, "not listed" and any history-based
  scenario need owner-started runs, at most one a day.
- **DuckDB 1.5.6 limits:**
  - A referenced row cannot be updated.
  - Migrations cannot add CHECKs or constrained columns.
  - A writer and a reader in different processes exclude each other.
  - The schema's CHECKs block some states the independent checks test for. Tests copy the
    table without constraints to reach them.
- **Streamlit 1.65 quirks:**
  - A table drawn in a hidden tab opens with collapsed columns, hence lazy tabs.
  - AppTest keeps no tab state between runs, so tests set `session_state["view"]`.
  - AppTest needs a loopback socket on Windows, so its tests are marked `allow_hosts(["127.0.0.1"])`.
  - `persist_state="session"` keeps a widget's value through runs that do not draw it (tabs,
    or an early return such as IN USE); `"page"` resets a remounted widget under AppTest.
  - A keyed `number_input` keeps its value when its min or step changes, and resets only when
    the value falls outside the new bounds.
  - Inline code is fixed at 0.75em (10.5 px at the 14 px base), and `codeTextColor` defaults to
    the theme's green; the theme sets it to the muted grey, and tags are plain muted text.
  - `st.table` sizes to the Styler's cell `min-width`s; `width="content"` keeps a narrow table
    narrow inside a wider `st.container(width=...)`.
  - Streamlit paints `primaryColor` on radios, toggles and focus rings as well as the active tab.
- **Hypothesis 6.169 and coverage 7.16 quirks:**
  - Hypothesis writes caches to `.hypothesis/` even with no example database, so the folder is
    gitignored.
  - Under `CI`, Hypothesis loads its own `ci` profile unless one is loaded explicitly, which
    `tests/conftest.py` does.
  - Coverage rounds the total to `precision` before comparing, but 100 must be exactly 100.
- **Local quirks:**
  - Gate runs use `PYTEST_ADDOPTS=--basetemp=tmp/pytest`; `tmp/` is gitignored and must exist.
    With that setting, `tmp_path` sits inside the repo, so a test needing "not a Git repository"
    sets `GIT_DIR`.
  - npm's `.cmd` shims break on the `&` in the folder name; run Node CLIs as
    `node node_modules/<pkg>/<bin>.js`, with `OPENSPEC_TELEMETRY=0` for the OpenSpec CLI.
  - `openspec archive` refuses a MODIFIED requirement that drops a main-spec scenario: keep each
    scenario's name with updated WHEN/THEN.
  - Commands shown to the owner must quote paths.
  - The Chrome extension's screenshots and zoom time out intermittently on the Streamlit page.
    Measure with JavaScript instead (bounding boxes, computed styles, canvas pixels for the data
    grid), and check 1440×900 in an iframe of that size. For screenshots, use a scratch launcher
    that offers `data/synthetic.duckdb` only.
  - The harness may stop a background viewer when memory runs low; restart it only when the
    owner says so.
  - Some multi-line bash heredocs fail to parse in the agent's shell tool, and `\b` inside a
    heredoc'd Python string can arrive as a backspace. Write to a scratch file, or use the Edit
    tool.
  - Figma's `download_assets` exports a node as SVG straight to a URL. Strip its full-page
    background `<rect>` to match earlier exports.
  - Cloning a FigJam connector shared its label with the original; build new connectors fresh.
- **Carried over:**
  - Phase 8 stays synthetic unless the publishing gate approves derived live figures.
  - Recheck CME futures before Phase 8.
  - Dependabot alert #1 (`braces`, dev-only, no fix) stays open.
  - detect-secrets scans files only: scan Git history before the repo goes public.
  - Untracked `.agents/skills/openspec-*` and `source-command-opsx-*` folders appeared on
    2026-10-13 outside any phase, and an untracked `.codex/config.toml` on 2026-10-14. None is
    committed; the owner decides whether to keep them.

## Next action

Phase 8 (public demo, methodology document, market brief, two-minute walkthrough, updated
diagrams) starts in a fresh session with `/next-phase`. It is grilled with the Phase 1 acceptance
row "7 Demo and brief" and the Phase 8 findings above. Any visible change gets a quick Figma
mock with synthetic figures for the owner's approval first. The publishing gate (§6) stays the
owner's. Collecting more live data is the owner's choice: one manual run a day at most, followed
by normalize.
