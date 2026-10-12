# Current handoff

Read PROJECT.md and current user instructions. Inspect actual Git/OpenSpec state before resuming.

## Current checkpoint

Phase 2 (Azure Retail Prices collector) is Done. It was delivered through PR #7 from branch
`phase-2-collector` and archived as
`openspec/changes/archive/2026-10-12-phase-2-collector`. Its specs live in
`openspec/specs/azure-price-collector`, with updates to `price-data-schema` and
`quality-gate`. After the merge, no OpenSpec change is active.

Earlier phases are Done and merged: Phase 1 (PR #5) and Phase 0 (PR #3).

Each phase starts in a fresh session (WORKFLOW.md § Fresh session per phase). Everything the
next phase needs is in this file, PROJECT.md, OpenSpec and Git.

PROJECT.md §5–6 are the constitution (version 2.1.0, unchanged in Phase 2). Copies in AGENTS.md
and `openspec/config.yaml` are kept in step by `tests/repo/test_constitution.py`.

**Live-data gate resolved for Azure (owner, 2026-10-12).** The scope, recorded in PROJECT.md §6:
- unauthenticated GET of the Retail Prices API only, with the GPU filter;
- runs the owner starts by hand, at most one a day;
- at most 1 request/s, backing off on 429;
- local storage and analysis only, with no redistribution.

The scheduling, spend and publishing gates are untouched.

## Implemented behavior (Phase 2)

- **Command:**
  - `uv run python -m compute_cost_risk_monitor.collect` fetches one run labelled `live` into
    `data/raw/azure-retail/YYYY/MM/DD/`, then ingests it into `data/monitor.duckdb`.
  - Both paths are anchored to the repo, not the working directory.
  - `--ingest-run RUN_ID` loads kept files without the network. It refuses a run that may still
    be fetching (no end manifest, less than 35 minutes since its start).
  - A live fetch within 24 hours of the last one that sent requests is refused.
  - Output is counts only, never prices.
  - In this environment's bash, uv lives at
    `/c/Users/Peter/AppData/Local/Microsoft/WinGet/Packages/astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe/uv.exe`.
- **Request:** `api-version=2023-01-01-preview`, `currencyCode='USD'`, `meterRegion='primary'`,
  and `$filter=serviceName eq 'Virtual Machines' and contains(armSkuName, 'Standard_N')`.
  - A client-side check keeps NC, ND, NG and NV sizes.
  - Next links are pinned to the API: printable ASCII only, https, the API's host and path.
- **Pacing:**
  - requests ≥ 1 s apart, ≥ 2 s after a 429;
  - waits follow Retry-After, or Azure's `x-ms-ratelimit-retailprices-retry-after` after a 429,
    capped at 300 s;
  - otherwise 60 s after a 429 and 2/4/8/16 s backoff;
  - 5 attempts per page; caps of 200 pages, 30 minutes and 64 MiB per body;
  - an empty first page, or an empty page after a full one, is fetched once more.
- **Raw files:** each file is written once.
  - Gzip bodies (level 9, mtime 0) plus JSON sidecars, and start and end manifests.
  - The end manifest records the stop reason and the number of requests.
  - Any unexpected error ends a run with stop reason `error`.
- **Row rules (`azure_retail.py`):**
  - scope, then rejection reasons counted per reason, then rental type and flags;
  - item key = Phase 1 D15 + `armSkuName`;
  - reservations get the unit "<term> term".
- **Ingest:** one transaction, from the files only.
  - Bodies are verified against their SHA-256 first.
  - First copy wins; later copies go to `observation_repeat`.
  - Status is `succeeded` only when paging completed; otherwise `partial` or `failed`.
- **Schema v2:** `002_run_records.sql` adds `collection_run_summary` (with the accounting
  identity), `collection_run_tally` and `observation_repeat`. Run rows are write-once.
- **Gate:** detect-secrets scans against `.secrets.baseline`. pytest runs with sockets blocked;
  only the Streamlit smoke test may connect, and only to 127.0.0.1.
- **Diagrams:** the FigJam container view and the ERD (schema v2) are updated, and the SVGs in
  `docs/architecture/` are re-exported.

## Data collected so far

- **First live run:** `20261012T151909Z-5473f1`, started by the owner on 2026-10-12. It
  succeeded.
  - 15 pages and 14,593 rows: 14,347 stored, 246 out of scope (NP FPGA and NM MA35D), 0 repeats,
    0 rejected, no 429s.
  - 100 GPU sizes in 60 regions.
  - By rental type: on_demand 3,285, spot 3,048, dev_test 3,803, reservation 2,387, other (Low
    Priority) 1,824.
  - The data is local in `data/` (gitignored). Counts only are recorded anywhere in Git.
- **Live-run observations (design Open Questions):**
  - next links keep the fixed parameters;
  - there is no standard Retry-After, but `x-ms-ratelimit-remaining-retailprices-requests: 9`
    and `x-ms-ratelimit-retailprices-retry-after: 60` appear on every response;
  - reservation terms include 5 Years;
  - 8,014 rows are Windows products.

## Verification

- **Gate:** green at e0a51d3 in Windows PowerShell; 298 tests pass. Branch coverage is 100% for
  the row rules, raw store and fetch loop, and about 99% overall.
- **CI:** hosted CI (Linux) passed on the branch pushes. There the real-page test skips because
  no data is kept.
- **Audit:** `uv audit` found no known vulnerabilities in 67 packages.
- **Live run:** a script independent of ingest re-hashed all 15 kept bodies and matched every
  count in DuckDB.
- **Code review:** `/code-review` on PR #7 found 14 defects, all fixed with tests (design D28).
- **Read-through:** the market-review and build-safety read-through is in
  `docs/reviews/2026-10-12-phase-2-collector.md`.
- **Deliberate failures checked:**
  - a planted fake AWS key fails the gate;
  - the Streamlit test fails without its loopback marker;
  - Windows-style sidecar paths could escape the raw root until fixed.

## Findings for later phases

- **Phase 3:**
  - Exclude Windows rows and Low Priority (`other`) rows from comparisons (Phase 1 D11).
  - Offset paging (`$skip`) can miss rows silently when the catalogue changes mid-run, so infer
    "not listed" only from repeated absence across succeeded snapshots.
  - Build `gpu_sku_map` from Microsoft Learn (CC BY 4.0); the live run has 100 distinct GPU
    `armSkuName` values to map.
  - Fractional NV sizes are left out of v1 (Phase 1 D12).
- **DuckDB 1.5.6 limits:** a `collection_run` row cannot be updated once referenced, and
  migrations cannot add CHECKs or constrained columns (Phase 1 D23 was wrong). Changing a
  version-1 CHECK list means rebuilding into a new database file.
- **D27 (owner-confirmed on PR #7, 2026-10-12):** `--ingest-run` restores a run under its own ID and label.
  `recorded` is for a new run built from kept responses (as in `test_real_page.py`).
- **Local quirks:**
  - In the Phase 2 session, pytest could not use `%LOCALAPPDATA%\Temp\pytest-of-Peter`
    ("access denied"). Gate runs there used `PYTEST_ADDOPTS=--basetemp=tmp/pytest` (`tmp/` is
    gitignored and must exist). If you see the same error, delete that folder.
  - npm's Windows `.cmd` shims break on the `&` in the folder name; run Node CLIs as
    `node node_modules/<pkg>/<bin>.js`.
- **Carried over:**
  - Phase 7 stays synthetic unless the publishing gate approves derived live figures.
  - Phase 4 sets Streamlit `gatherUsageStats = false`.
  - Recheck CME futures before Phase 7.
  - Dependabot alert #1 (`braces`, dev-only, no fix) stays open.
  - detect-secrets scans files only: scan Git history before the repo goes public.

## Next action

Start Phase 3 in a fresh session: the owner clears the context and runs `/next-phase`. Then
grill Phase 3 (normalization to USD/GPU-hour, `gpu_sku_map` v1, comparable groups, duplicate and
quality checks), using the Phase 1 acceptance row and the findings above. Collecting more live
data is the owner's choice: one manual run a day at most.
