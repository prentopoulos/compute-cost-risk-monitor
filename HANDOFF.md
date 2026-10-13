# Current handoff

Read PROJECT.md and current user instructions. Inspect actual Git/OpenSpec state before resuming.

## Current checkpoint

**Phase 4 (Streamlit dashboard) is in progress** on branch `phase-4-dashboard`, OpenSpec change
`openspec/changes/phase-4-dashboard`. Grilling finished on 2026-10-12: the owner accepted every
recommendation (design D1–D8 are owner decisions, D9–D30 settled with their basis). The next
step is the first open task in `tasks.md`. The sections below describe Phase 3 and stay true.

Phase 3 (normalization, comparable groups, history and quality checks) is Done. It was delivered
through PR #8 from branch `phase-3-normalization` and archived as
`openspec/changes/archive/2026-10-12-phase-3-normalization`. Its specs live in
`openspec/specs/` as `price-normalization`, `comparable-groups`, `snapshot-history`,
`data-quality` and `synthetic-marketplace`. After the merge, no OpenSpec change is active.

Earlier phases are Done and merged: Phase 2 (PR #7), Phase 1 (PR #5) and Phase 0 (PR #3).

Each phase starts in a fresh session (WORKFLOW.md § Fresh session per phase). Everything the
next phase needs is in this file, PROJECT.md, OpenSpec and Git.

PROJECT.md §5–6 are the constitution (version 2.1.0, unchanged in Phase 3). Copies in AGENTS.md
and `openspec/config.yaml` are kept in step by `tests/repo/test_constitution.py`.

**Live-data gate resolved for Azure (owner, 2026-10-12).** The scope, recorded in PROJECT.md §6:
- unauthenticated GET of the Retail Prices API only, with the GPU filter;
- runs the owner starts by hand, at most one a day;
- at most 1 request/s, backing off on 429;
- local storage and analysis only, with no redistribution.

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
  - Exit codes: 0 when the checks pass, 1 when a check fails, 2 when refused (a changed frozen
    row, a bad map file, or a database that cannot be opened); a refusal writes nothing.
  - **Run it after every collect**; the quality report flags a snapshot that is not normalized
    yet.
- **Quality (Phase 3):** `uv run python -m compute_cost_risk_monitor.quality [--db PATH]
  [--as-of TIME]` prints the counts-only report for each source's latest snapshot.
- **Synthetic marketplace (Phase 3):** `uv run python -m compute_cost_risk_monitor.synthetic FILE
  ... [--db PATH]` stores labelled synthetic snapshots as `synthetic` runs. It defaults to
  `data/synthetic.duckdb` and refuses `data/monitor.duckdb`. Then run normalize and quality with
  `--db data/synthetic.duckdb`.

## Implemented behavior (Phase 3)

Owner decisions are D1–D11 in the archived design; D12–D25 are settled with their basis. D24
(regional retirement extensions) was flagged for review on PR #8, which the owner approved for
merge on 2026-10-12 without comment on it.

- **GPU map `gpu-map-v1`:** `src/compute_cost_risk_monitor/reference/gpu_sku_map_v1.csv`.
  - 51 sizes (35 whole-GPU, 16 fractional), hand-built from Microsoft Learn size pages, with a
    URL and retrieval date on every row and the CC BY 4.0 credit.
  - A size is mapped only if Learn names it exactly (D9). Labels follow Learn's wording, e.g.
    "H100 NVLink 80GB" or "H100 NVL 94GB confidential" (D3).
- **Rule set `groups-v1`** (`rules.py`), stored once and refused if changed:
  - compared rental types: on_demand and spot;
  - exclusion order: rental type, government cloud (`usgov`/`usdod`), Windows (last
    product-name word `Windows`/`Win`), unit not hourly, unmapped, fractional, retired;
  - retirements are by snapshot date, with Learn's regional extensions: NCv3 in Jio India West
    until 2027-06-30 and NVv3 in UAE North until 2027-01-31 (D24);
  - thresholds: stale after 7 days, thin below 5 regions or 5 machines, "not listed" after 2
    absences;
  - the exclusions text and the synthetic marketplace GPU names.
- **Normalization:** USD/GPU-hour = price ÷ mapped GPU count. Excluded rows keep their reason and
  their map reference when mapped.
- **Independent checks (`checks.py`, imports no normalization code):**
  - multiply-back and one row per observation;
  - reasons are valid per source, and each one is re-derived from the stored rules;
  - GPU fields match the map row for the observation's own size;
  - compared rows follow the rules, and totals match the run records.
- **Groups (`groups.py`):**
  - region groups (variant, count, region, rental type), labelled `single list price` when they
    hold one price;
  - cross-region summaries from each region's lowest listed member: region count, min, median and
    max, labelled `thin` below 5 regions;
  - marketplace groups take one price per machine and flag the others `machine_duplicate`.
- **History (`history.py`):**
  - changes between consecutive succeeded snapshots, keyed by item for Azure and by machine
    continuity for the marketplace;
  - "absent once (unconfirmed)", then "not listed" after two absences.
- **Quality (`quality.py`):**
  - the stale flag, a `NOT NORMALIZED` flag, and rows by reason;
  - unmapped size names, run-record counts, duplicates and missing fields;
  - `os_ambiguous`, single-price and thin counts, changes and absences.
- **Diagrams:** the FigJam container view marks normalization as built and adds the synthetic
  database; `docs/architecture/c4-container.svg` is re-exported. The ERD is unchanged (no schema
  change, D10).

## Data collected so far

- **One live snapshot:** `20261012T151909Z-5473f1` (owner, 2026-10-12), succeeded.
  - 14,347 stored rows, covering 100 GPU sizes in 60 regions.
  - By rental type: on_demand 3,285, spot 3,048, dev_test 3,803, reservation 2,387 and other
    (Low Priority) 1,824.
  - 7,878 stored rows are Windows, including all 3,803 Dev/Test rows.
- **Normalized under `groups-v1` (2026-10-12):**
  - 1,238 compared: 629 pay-as-you-go and 609 Spot, covering 34 sizes, 17 variants and 54
    regions.
  - Excluded:

    | Reason | Rows |
    |---|---|
    | rental type not compared | 8,014 |
    | Windows | 3,009 |
    | unmapped | 775 |
    | fractional | 666 |
    | retired | 334 |
    | government cloud | 311 |

  - 49 sizes are not in the map.
  - 929 region groups, of which 684 hold a single list price. 51 cross-region summaries, of which
    11 are thin.
- The data is local in `data/` (gitignored). `data/monitor.pre-phase3.duckdb` is a copy taken
  before the first normalize; the owner may delete it. Only counts appear anywhere in Git.

## Verification

- **Gate:** green in Git Bash and Windows PowerShell; 422 tests pass, about 98% branch coverage.
  `uv audit` found no known vulnerabilities in 67 packages.
- **CI:** hosted CI passed on the branch pushes.
- **Live normalize:**
  - all seven independent checks pass on the 14,347 rows;
  - a script sharing no package code recounted every exclusion reason and matched;
  - an SQL recompute of multiply-back found 0 mismatches.
- **Code review:** `/code-review` on PR #8 found 15 issues. 12 were fixed with tests, and 3 were
  answered without code change (design D25).
- **Read-through:** the market-review and build-safety read-through is in
  `docs/reviews/2026-10-12-phase-3-normalization.md`.

## Findings for later phases

- **Phase 4 (dashboard):**
  - Show every member of a multi-size region group with its size name. In 64 of 245 multi-size
    groups the highest member is over 1.5× the lowest, because of vCPU, RAM and disk differences.
  - Say that "lowest listed per region" picks the cheapest configuration.
  - 48 Spot rows equal their pay-as-you-go price; they are published that way, so show them as
    listed, not as errors.
  - Show the `NOT NORMALIZED`, stale, thin and single-price labels.
  - Set Streamlit `gatherUsageStats = false`.
- **Map v2:** add the H100 `noIB`/`flex`/`isrf` sizes, MI300X `ND96is` and 20 RTX PRO 6000 sizes
  only when Learn names them exactly. A new version, never an edit.
- **History:** only one live snapshot exists. Changes and "not listed" need owner-started runs, at
  most one a day.
- **DuckDB 1.5.6 limits:** a referenced row (for example a run, rule set or map row) cannot be
  updated, and migrations cannot add CHECKs or constrained columns. Changing a version-1 CHECK
  list means rebuilding into a new database file.
- **Local quirks:**
  - pytest could not use `%LOCALAPPDATA%\Temp\pytest-of-Peter` ("access denied"). Gate runs used
    `PYTEST_ADDOPTS=--basetemp=tmp/pytest` (`tmp/` is gitignored and must exist).
  - npm's Windows `.cmd` shims break on the `&` in the folder name; run Node CLIs as
    `node node_modules/<pkg>/<bin>.js`.
  - Figma's `use_figma` returns at most 20 KB, so a large SVG export needs chunking. Phase 3 sent
    it LZW-compressed in 17 chunks, rebuilt it from the session transcript, and verified it
    against Figma's length and checksum.
- **Carried over:**
  - Phase 7 stays synthetic unless the publishing gate approves derived live figures.
  - Recheck CME futures before Phase 7.
  - Dependabot alert #1 (`braces`, dev-only, no fix) stays open.
  - detect-secrets scans files only: scan Git history before the repo goes public.

## Next action

Start Phase 4 (Streamlit dashboard with comparable-group filters and the data-quality panel) in
a fresh session: the owner clears the context and runs `/next-phase`. Then grill Phase 4 using
the Phase 1 acceptance row and the findings above. Collecting more live data is the owner's
choice: one manual run a day at most, followed by normalize.
