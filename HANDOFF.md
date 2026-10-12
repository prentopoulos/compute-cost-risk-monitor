# Current handoff

Read PROJECT.md and current user instructions. Inspect actual Git/OpenSpec state before resuming.

## Current checkpoint

Phase 2 (Azure Retail Prices collector) is **In progress** on branch `phase-2-collector`, with
draft PR #7. The OpenSpec change is `openspec/changes/phase-2-collector`. Tasks 1.1–5.3 and 7.1
are done. Open tasks:
- 6.1: the first live run, started by the owner.
- 6.2: the local real-page test.
- 7.2: the market-review and build-safety read-through.
- 7.3: the gate in both shells, plus `uv audit`.
- 7.4: this handoff.

After that comes the code review, then archive, ready and merge (WORKFLOW.md).

Phase 1 is Done and merged (PR #5), and Phase 0 too (PR #3). Their specs live in
`openspec/specs/`.

PROJECT.md §5–6 are the constitution: version 2.1.0, unchanged by Phase 2. AGENTS.md and
`openspec/config.yaml` carry verbatim copies of §5, kept in step by
`tests/repo/test_constitution.py`.

**Live-data gate resolved for Azure (owner, 2026-10-12, Phase 2 grilling).** The scope, recorded
in PROJECT.md §6:
- unauthenticated GET of the Retail Prices API only, with the GPU filter;
- runs the owner starts by hand, at most one a day;
- at most 1 request/s, backing off on 429;
- local storage and analysis only, with no redistribution.

The scheduling, spend and publishing gates are untouched.

## Grilling decisions

Phase 2 grilling ran one round on 2026-10-12, and the owner accepted every recommendation.
Decisions D1–D27 are in the change's design. The main ones:
- **D2:** Phase 2 is Done only after one successful live run.
- **D3:** every N-series GPU family is collected (NC, ND, NG, NV), with all regions and price
  types.
- **D4:** reservations are stored with the unit "<term> term".
- **D6:** item key = Phase 1 D15's key + `armSkuName`.
- **D7:** a snapshot is one `succeeded` run.
- **D8:** later copies of a row go to `observation_repeat`.
- **D9:** run records are written once, and migration 002 adds whole tables.
- **D10:** fetch writes files, and ingest reads them.

**D27 is flagged for owner review on PR #7.** Restoring a run with `--ingest-run` keeps its own
ID and its `live` label, rather than becoming a new `recorded` run. Re-labelling would date the
snapshot to the restore and break the stale flag.

## Implemented behavior

- `azure_retail.py` holds the pure rules:
  - the fixed request;
  - the next-link checks;
  - item classification (scope, rejection reasons, rental type, flags);
  - the item key and the reservation unit.
- `raw_store.py` keeps files written once: gzip bodies (level 9, mtime 0), sidecars, and start
  and end manifests under `data/raw/azure-retail/YYYY/MM/DD/`. Read-back checks SHA-256 and
  refuses paths that escape the raw root.
- `fetch.py` has the urllib fetcher and the paced loop:
  - GET only, no redirects;
  - requests ≥ 1 s apart, ≥ 2 s after a 429;
  - Retry-After honoured, capped at 300 s;
  - 5 attempts per page;
  - caps of 200 pages and 30 minutes.
- `ingest.py` builds one run's records in one transaction, from the files only.
- `collect.py` is the command: `uv run python -m compute_cost_risk_monitor.collect` fetches and
  ingests one live run. `--ingest-run RUN_ID` loads a kept run without the network. A live fetch
  within 24 h of the last one is refused.
- `schema/002_run_records.sql` adds `collection_run_summary`, `collection_run_tally` and
  `observation_repeat`.
- The gate now runs detect-secrets against `.secrets.baseline`, and pytest runs with sockets
  blocked (pytest-socket). The Streamlit smoke test may connect to 127.0.0.1 only.
- Diagrams: the FigJam container view marks the collector and raw files built, and the ERD is
  regenerated for schema v2. The SVGs in `docs/architecture/` are re-exported.

## Verification so far

- The gate is green on Windows for every commit (latest 54f52ae), with 222 unit tests plus
  smoke and repo tests. Branch coverage is 100% for the row rules, raw store and fetch loop.
- Deliberate failures checked:
  - a planted fake AWS key fails the gate;
  - the Streamlit test fails without its loopback marker;
  - a sidecar path like `/abs/x` escaped the raw root on Windows until fixed.
- No live request has been sent yet.

## Findings for later phases

- **DuckDB 1.5.6 limits.** A `collection_run` row cannot be updated once a raw response
  references it, and migrations cannot add CHECK constraints or constrained columns. Phase 1's
  D23 was wrong about this. Version-1 CHECK lists change only by rebuilding into a new database
  file.
- **Offset paging (`$skip`)** can repeat or miss rows when the catalogue changes mid-run. Repeats
  are recorded; misses are undetectable. Phase 3 decides how "not listed" is inferred, for
  example by requiring absence from two succeeded snapshots.
- **To check on the first live run:**
  - whether `contains(armSkuName, …)` filters on the server (the out-of-scope count);
  - page counts;
  - whether next links keep the fixed parameters (`next_link_missing_params`);
  - whether 429s or Retry-After appear;
  - whether `shared_meter_key` and Low Priority rows occur.
- **Local environment quirks:**
  - pytest could not use `%LOCALAPPDATA%\Temp\pytest-of-Peter` in this session ("access
    denied"). The long scratchpad path also hit the 260-character limit. Local gate runs used
    `PYTEST_ADDOPTS=--basetemp=tmp/pytest` (`tmp/` is gitignored and must exist). If you see the
    same error, delete that folder.
  - uv was not on the session's PATH; it lives in
    `%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe`.
- **Carried from Phase 1:**
  - Publishing live Azure figures is not expressly permitted; the Phase 7 demo stays synthetic
    unless the publishing gate approves.
  - DuckDB connections go through `db.connect`.
  - Run Node CLIs as `node node_modules/<pkg>/<bin>.js` (the `&` in the folder name breaks
    `npx`).
  - Phase 3 builds the `gpu_sku_map` content from Microsoft Learn (CC BY 4.0).
  - Phase 4 sets Streamlit `gatherUsageStats = false`.
  - CME futures: recheck before Phase 7.
  - Dependabot alert #1 (`braces`, dev-only, no fix) stays open.
  - detect-secrets scans files, not history: scan Git history before the repo goes public.

## Next action

Task 6.1: the owner runs `uv run python -m compute_cost_risk_monitor.collect` once from the repo
root. Then:
1. Record the run's counts and the open questions above, without prices.
2. Do task 6.2 (keep one real page under `data/` and add the skip-if-absent test).
3. Run the read-through (7.2), the gate in both shells and `uv audit` (7.3).
4. Run `/code-review` on PR #7, then archive and mark the PR ready.
