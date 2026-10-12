## Why

PROJECT.md Phase 2: a working Azure Retail Prices collector that keeps the original responses,
so observations start accumulating. Phase 1 built the schema but nothing writes to it yet. The
owner resolved the live-data ⛔ gate for this API in the Phase 2 grilling (2026-10-12), so the
collector can be built offline and then run live by the owner.

The grilling also found two DuckDB 1.5.6 limits that Phase 1's schema did not plan for:
- A `collection_run` row cannot be updated once a `raw_response` row references it.
- A migration cannot add CHECK constraints or constrained columns.

So run records are written once, at the end of a run, and the new tables arrive as whole
tables in migration 002.

## What Changes

- New collector package code:
  - A read-only fetch loop for `GET https://prices.azure.com/api/retail/prices`, with one
    fixed set of parameters and filter covering every N-series GPU size, all regions, all
    price types, USD and primary meters. It follows `NextPageLink` and is paced, retried,
    time-limited and page-capped.
  - Raw-response retention as Phase 1 D3 set it: exact bytes gzipped, plus a sidecar with
    the request and response metadata, both written once before parsing. A run manifest is
    written at the start of a run and another at the end.
  - An ingest step that reads a run's retained files and writes the run's database records
    in one transaction. Those are the run with its final status, the run summary and
    tallies, the raw responses, the price observations with Azure detail rows, and the
    repeats.
  - Deterministic row handling:
    - a GPU-family scope check;
    - validation, with rejected rows counted by reason;
    - mapping each row to a rental type;
    - the item key (D15 plus `armSkuName`);
    - keeping the first copy of a row and recording later copies as repeats;
    - the reservation price unit taken from the term.
  - The command `uv run python -m compute_cost_risk_monitor.collect`, which fetches and
    ingests a live run. `--ingest-run <run_id>` loads a run's retained files without the
    network. Live fetches are refused within 24 hours of the previous one.
- Schema migration `002_run_records.sql` adds three insert-only tables:
  - `collection_run_summary`: typed counts, with an accounting identity and a stop reason;
  - `collection_run_tally`: per-reason counts of rejected and flagged rows;
  - `observation_repeat`: later copies of a row within a run.
- Network blocked in tests with pytest-socket. The Streamlit smoke test is the only test
  allowed sockets, which asyncio on Windows needs for an internal channel.
- A secret scanner (detect-secrets) in the gate, run against a committed `.secrets.baseline`.
- Contract tests on synthetic Azure-shaped pages, covering normal, edge and deliberately
  failing cases.
- One live run, started by the owner. After it, a local-only test against one kept real
  page, which skips when the file is absent.
- Documents:
  - PROJECT.md §6 records the live-data gate decision, and §3 defines the data labels.
  - The pyproject description is reworded to the Azure list-price framing.
  - The FigJam container diagram and ERD are updated, with their SVG exports.
  - HANDOFF.md is updated.

## Non-goals

- No SKU-to-GPU mapping content, normalization, USD/GPU-hour, comparable groups, staleness or
  "not listed" logic (Phase 3).
- No dashboard, calculator or scenarios (Phases 4–5).
- No scheduled or unattended collection. Runs are started by hand (⛔ scheduling gate stays
  unresolved).
- No second source, no account, API key or `.env`, and no call to any endpoint other than the
  Retail Prices API.
- No real source data in Git and no publishing of live figures (⛔ publishing gate).
- No console-script name, which is a Phase 7 Showcase decision.
- No change to schema 001 (forward-only, Phase 1 D21) and no change to the constitution
  (PROJECT.md §5).

## Capabilities

### New Capabilities

- `azure-price-collector`: the read-only fetch of Azure Retail Prices, raw-response retention,
  row scope and validation, rental-type mapping, item keys and repeats, run status and
  write-once run records, the ingest step, and the collect command.

### Modified Capabilities

- `price-data-schema`: schema version 2 adds the run summary, tally and repeat tables.
  Observation price units may describe a reservation term. Schema creation now applies
  versions 1 and 2.
- `quality-gate`: the gate adds a secret scan, and tests run with the network blocked.

## Impact

- New:
  - Code: `src/compute_cost_risk_monitor/` modules for Azure row handling, raw storage,
    HTTP fetch, the collect loop, ingest and the command, plus
    `schema/002_run_records.sql`.
  - Tests: `tests/unit/` collector tests, plus synthetic page fixtures.
  - `.secrets.baseline`.
- Edited:
  - Build and gate: `pyproject.toml` and `uv.lock` (pytest-socket and detect-secrets as dev
    dependencies), `scripts/gate.py` (secret scan).
  - Tests: `tests/smoke/test_stack.py` (socket marker), and `tests/unit/test_schema.py`
    (version 2 is applied too).
  - Documents: PROJECT.md §3 and §6, HANDOFF.md, the FigJam board, and the
    `docs/architecture/` SVGs.
- Runtime: no new runtime dependency; HTTP uses the standard library.
- ⛔ gates:
  - Live data (Azure): resolved by the owner on 2026-10-12, with the scope recorded in
    PROJECT.md §6. The collector honours that scope.
  - Scheduling, spend and publishing: not touched.
- Constitution: no amendment. Recording an operator decision on a gate is not one.
