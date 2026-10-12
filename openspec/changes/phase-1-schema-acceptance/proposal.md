## Why

PROJECT.md Phase 1: requirements, data schema and acceptance criteria; architecture diagrams in
Figma. Phases 2–7 need a fixed, tested place to store prices with provenance, written acceptance
criteria to build against, and a picture of the system. Grilling also changed the data source.
Vast.ai's terms (version 2026-09-01) forbid the planned collection without a written agreement,
and so does every other GPU marketplace checked, so the owner chose the Azure Retail Prices API
(published list prices). PROJECT.md, AGENTS.md, the OpenSpec config and the skills are reframed
to match.

## What Changes

- Add an executable DuckDB schema, `compute_cost_risk_monitor/schema/001_initial.sql`, plus a
  typed `db` module. `connect()` pins the session time zone to UTC, and `create_schema()` applies
  numbered SQL files and records `schema_version`.
- The schema has:
  - a source-neutral core: `collection_run`, `raw_response`, `price_observation`
  - per-source detail: `azure_retail_price`, plus `marketplace_offer` for labelled synthetic data
  - versioning: `rule_set` and `gpu_sku_map`
  - a derived table, `normalized_price`
- Constraints reject duplicate (source, item, retrieval time) rows, non-finite or non-positive
  prices, missing provenance, unknown data labels and rental types, and synthetic marketplace
  rows in non-synthetic runs.
- Add pytest coverage on labelled synthetic fixtures, including deliberately failing inserts.
- Add `pytz` as a runtime dependency (DuckDB needs it to return TIMESTAMPTZ values) and
  `types-pytz` as a dev dependency.
- Write the Phase 2–7 acceptance criteria as a table in this change's design.
- Draw three diagrams in one FigJam file on the owner's Pro seat: C4 system context, C4
  container and the schema ERD. Export them as SVG to `docs/architecture/`.
- Ignore `data/` in Git.
- Reframe PROJECT.md §1, §2, §3, §4, §5 and §6, AGENTS.md, `openspec/config.yaml`, and the
  next-phase, build-safety and market-review skills from "Vast.ai marketplace asking prices" to
  "published Azure list prices, plus labelled synthetic marketplace data".

## Non-goals

- No HTTP client, collector code or call to any provider; no account, API key, `.env` or
  `.env.example` (Phase 2, behind the live-data ⛔ gate).
- No normalization, SKU-to-GPU mapping content, grouping, duplicate flagging, staleness or
  quality logic beyond schema constraints (Phase 3).
- No Streamlit page, calculator or scenarios (Phases 4–5).
- No scheduling; no real source data in Git; no publishing.
- No contact with Vast.ai or any provider.

## Capabilities

### New Capabilities

- `price-data-schema`: the stored data model. It covers tables, keys and constraints, data
  labels, UTC time handling, schema and rule versioning, and the connection helper that later
  phases use.

### Modified Capabilities

None. The Phase 0 capabilities (`dev-environment`, `quality-gate`, `hosted-ci`) are unchanged;
adding a runtime dependency does not change their requirements.

## Impact

- New: `src/compute_cost_risk_monitor/db.py`, `src/compute_cost_risk_monitor/schema/001_initial.sql`,
  `tests/unit/test_schema.py`, `tests/fixtures/synthetic/`, `docs/architecture/*.svg`.
- Edited: `pyproject.toml`, `uv.lock` (pytz, types-pytz), `.gitignore` (data/), PROJECT.md,
  AGENTS.md, `openspec/config.yaml`, three skills, HANDOFF.md.
- Figma: one new FigJam file in the owner's drafts (owner-approved, 2026-10-11).
- ⛔ gates touched: none acted on. The live-data gate gets a recorded finding, and the source
  change stays unresolved until the operator confirms Azure's terms and pacing in Phase 2.
