# Current handoff

Read PROJECT.md and current user instructions. Inspect actual Git/OpenSpec state before resuming.

## Current checkpoint

Phase 7 (front-office interface) is planned and specified, with no code yet:
- The owner added the phase on 2026-10-13, ahead of the demo, which is now Phase 8.
- Branch `phase-7-interface`, with a draft PR.
- OpenSpec change `openspec/changes/phase-7-interface`: proposal, design D1–D32, tasks and delta
  specs for `dashboard` and `workload-calculator`.
- The grilling is done: the owner accepted every recommendation on 2026-10-13.
- The owner rejected the first design brief as cluttered, asked for research on front-office
  screens, corrected one quick mock, and approved the second on 2026-10-14:
  https://www.figma.com/design/aODgN8zO3eCm9bmN8sOSCK?node-id=5-2 (Figma file "Compute Cost &
  Risk Monitor · Interface (Phase 7)", Projects team).
  - It has terse labels, no helper text and one status line, then key figures, inputs, one
    scenario grid with a compliance footer, and a cost table beside a closed Sources section.
  - Design D6–D10 and D14 were revised to it, and D27–D32 added.
- A design-eval critique of v2 scored 25/40 (0 P0, 4 P1, 1 P2; local snapshot in
  `.impeccable/critique/`). The owner chose the fixes. They became mock v3
  (https://www.figma.com/design/aODgN8zO3eCm9bmN8sOSCK?node-id=7-2) and its state frames:
  - refused input (8:2), check failed (8:115), Spot without a pay-as-you-go listing (8:228),
    and storage and budget entered (8:519);
  - live (8:799) and stale (8:806) headers.
  A second grilling round settled the rest, and the owner approved v3 on 2026-10-14
  (D33–D46). Where v3 and D34–D38 differ (custom unit switch, "n/a" cells, the † mark,
  footnote wording), the decisions govern.
- The scenario ladder `ladder-v1` and its independent check are built (tasks 2.1–2.2, commit
  dc43f41). The page does not show them yet.
- Tasks 1.1–1.4 and 2.1–2.2 are done. The next tasks are 3.1–3.6: the theme, sidebar, status
  line, plain status words, the Workload tab, Sources, and the Comparable groups key figures,
  all built to v3.

Phase 6 (tests for units, calculations, missing data and stale offers) is Done. It was delivered
through PR #11 from branch `phase-6-tests` and archived as
`openspec/changes/archive/2026-10-13-phase-6-tests`. Specs changed in `openspec/specs/`:
- `quality-gate`: the coverage minimums, and the dashboard tests' loopback exception;
- `dev-environment`: Hypothesis in the dev group;
- `data-quality`: the 7-day boundary, the latest succeeded run, a future-dated snapshot, unknown
  counts without a run summary, the as-of time in UTC;
- `snapshot-history`: not listed after three or more absences; a return at a new price is not a
  change;
- `price-normalization`: the exact `1 Hour` unit and exclusion order;
- `workload-calculator`: hours and budget at least 0.01;
- `synthetic-marketplace`: ADDED "Synthetic command checks every file first".

Earlier phases are Done and merged: Phase 5 (PR #10), Phase 4 (PR #9), Phase 3 (PR #8), Phase 2
(PR #7), Phase 1 (PR #5) and Phase 0 (PR #3).

Each phase starts in a fresh session (WORKFLOW.md § Fresh session per phase). Everything the
next phase needs is in this file, PROJECT.md, OpenSpec and Git.

PROJECT.md §5–6 are the constitution (version 2.1.0, unchanged in Phase 6). Copies in AGENTS.md
and `openspec/config.yaml` are kept in step by `tests/repo/test_constitution.py`.

**Live-data gate resolved for Azure (owner, 2026-10-12).** The scope, recorded in PROJECT.md §6:
- unauthenticated GET of the Retail Prices API only, with the GPU filter;
- runs the owner starts by hand, at most one a day;
- at most 1 request/s, backing off on 429;
- local storage and analysis only, with no redistribution.

Owner's reading, 2026-10-12 (Phase 4 grilling): the dashboard's CSV download and copy controls
stay on; a file saved on this PC is local storage, and sharing it would still be redistribution.
Phase 6 fetched nothing new; its live regression read the stored snapshot read-only. The
scheduling, spend and publishing gates are untouched.

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
- **Dashboard (Phases 4–5):** `uv run streamlit run src/compute_cost_risk_monitor/app.py`.
  - The config beside the script applies from any folder: 127.0.0.1 only, no usage statistics,
    no Deploy button.
  - It offers the databases that exist, live first. Labels come from each run.
  - Tabs: Comparable groups, Workload cost, Group browser, Data quality.
  - Each page run holds a read-only lock while it reads (under a second on the live data). A
    collect or normalize started in that moment fails rather than waits: rerun it.

## Implemented behavior (Phase 6)

Owner decisions are D1–D10 in the archived design. D11–D22 are settled with their basis. D23
records a fix made under D7, and D24 the code review. Earlier phases' behaviour is
in their archived designs and the main specs.

- **Tests:** 718 tests, up from 649, at 100.0% branch coverage, up from 98.4%. They cover:
  - units: the exact "1 Hour" match and exclusion order past the first reason;
  - calculations: every failure branch of both independent checks;
  - missing data: not listed after three absences, a return at a new price, a run without a
    summary, the dashboard's error states, rollback paths;
  - stale: exactly 7 days, the latest succeeded run, a snapshot dated after the as-of time.
- **End to end:** `tests/e2e/test_known_answers.py` runs three dated synthetic Azure-shaped
  snapshots (`tests/fixtures/synthetic/azure_history/`) through ingest, normalize, the checks,
  the quality report, groups, history, the calculator and the workload check. It asserts the
  answers worked out by hand in the fixtures README.
- **Property tests:** `tests/unit/test_properties.py`, with Hypothesis (dev only). They check:
  - the calculator and the independent check agree;
  - the multiply-back;
  - cost is linear;
  - exposure is the cost difference, with the change's sign;
  - order independence.
- **Fixes:**
  - the synthetic command checks files before it opens the database;
  - the quality command prints its as-of time in UTC;
  - a missing run summary's counts read `unknown (no run summary)`;
  - hours and budgets must be at least 0.01, because Hypothesis found that 5e-324 made the
    headroom overflow or underflow (D23).
- **Code-review fixes (D24):**
  - every count a missing run summary leaves unproven reads unknown;
  - the synthetic command refuses two files with one observation time, an out-of-range time
    and an unusable `--db` folder before writing;
  - the gate's core coverage step cannot pass on stale data or a missing module;
  - the Hypothesis profile is tested with `CI` set, and a mistyped profile name gives one
    message.
- **Diagrams:** unchanged; Phase 6 changed no component, data flow or schema.

## Data collected so far

- **One live snapshot:** `20261012T151909Z-5473f1` (owner, 2026-10-12), succeeded. It has 14,347
  stored rows covering 100 GPU sizes in 60 regions. It turns stale after 2026-10-19 15:19 UTC.
- **Normalized under `groups-v1`:** 1,238 compared rows.
  - 929 region groups, 684 of them single list price; 456 are Spot, and every Spot size is
    listed on pay-as-you-go in its region.
  - 51 cross-region summaries, 11 of them thin.
  - 49 sizes are not in the map.
- **`data/synthetic.duckdb`:** the synthetic demo database, rebuilt 2026-10-13. It is
  disposable, and Phase 6 did not change it. The Phase 6 history fixtures are for tests only and
  are not in it. `tmp/synthetic.pre-phase5.duckdb` is a disposable older copy.
- All data is local in `data/` (gitignored). `data/monitor.pre-phase3.duckdb` is a pre-Phase 3
  copy the owner may delete. Only counts appear anywhere in Git.

## Verification

- **Gate:** green on the branch with both coverage steps. 718 tests pass, at 100.0% branch
  coverage, with the core modules at 100%. `uv audit` found no known vulnerabilities in 69
  packages.
- **CI:** hosted CI ran on the branch pushes.
- **Review record:** `docs/reviews/2026-10-13-phase-6-tests.md`. It holds:
  - the traceability table (area → requirement → tests) and coverage before and after;
  - the defects fixed;
  - the live regression, counts only: all seven checks pass; 2,476 of 2,476 member runs pass
    the workload check, with the PROJECT example exactly 11,520; 111,420 property cases on live
    prices pass; order independence holds in 929 of 929 groups;
  - the build-safety and market-review read-throughs.
- **Code review:** `/code-review` on PR #11 found 14 issues: 11 fixed with tests, and 3 answered on the PR and in design D24.

## Findings for later phases

- **Phase 8 (demo; it was Phase 7 until 2026-10-13):**
  - "PROJECT example +$0.50/GPU-hour" reads oddly to a public audience. Renaming it needs a
    `scenarios-v2` and an owner call. Phase 7 D8 deferred it to the start of Phase 8, with the
    demo copy.
  - Screenshots of the tables need a visible Chrome window: in a hidden window the data grid's
    canvas does not paint.
  - In the FigJam container view, the label "Dashboard reads synthetic (read-only)" overlaps
    "Creates tables" (from Phase 4). Fix it with the Phase 8 diagram update.
  - Phase 7 builds the custom theme (deferred by Phase 4 D6). `azure_demo.json` is the likely
    public demo dataset, subject to the publishing gate.
  - Design skills (2026-10-13): `.agents/skills/next-phase/design-skills.md` routes UI work to
    impeccable, ui-ux-pro-max, the tasteskill, 21st.dev and design-eval, with their limits
    here. The 21st.dev plugin is installed and the key is in the user environment. The account
    is free tier: AI generation off, free searches, and 2 free code copies a day.
  - Some 21st.dev code copies could be saved for Phase 8's public page, where React or HTML
    code could actually run (Phase 7 D15).
  - The methodology document can cite the Phase 6 traceability table and the end-to-end
    fixture's worked answers.
  - Hours now start at 0.01 (D23). If the owner prefers one billed minute (1/60 h), that is a
    small `workload-calculator` change.
- **Not yet tested:**
  - changes, absences and "not listed" on real data, which need more owner-started live
    snapshots;
  - no manual browser check of Phase 6's two changed texts, which AppTest covers;
  - mutation testing was not run (Phase 6 D5).
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
  - `persist_state="page"` resets a remounted widget to its default under AppTest; use
    `"session"`.
  - A keyed `number_input` keeps its value when its min or step changes, and resets only when
    the value falls outside the new bounds.
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
  - Commands shown to the owner must quote paths.
  - The Chrome extension's screenshots time out intermittently on the Streamlit page. Reading
    the page text, or the data grid's accessible cells through JavaScript, works.
  - The dashboard reopens on the live database after a restart. Switch to synthetic first, and
    confirm it before reading figures.
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
    2026-10-13 outside any phase. They are not committed; the owner decides whether to keep
    them.

## Next action

Continue Phase 7 on branch `phase-7-interface` at task 3.1 and build to mock v3 (Figma node
7:2 and its state frames) and design D33–D46. Load the Figma skills first if you need to read
the mock, and re-authenticate Figma if its connection dropped. Then do the verification in
section 4 and the records and review in section 5. After Phase 7 merges, Phase 8 (public demo, methodology
document, market brief, two-minute walkthrough, updated diagrams) starts in a fresh session. It
is grilled with the Phase 1 acceptance row "7 Demo and brief" and the Phase 8 findings above. The
publishing gate (§6) stays the owner's. Collecting more live data is the owner's choice: one
manual run a day at most, followed by normalize.
