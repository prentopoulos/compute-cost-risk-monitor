# Current handoff

Read PROJECT.md and current user instructions. Inspect actual Git/OpenSpec state before resuming.

## Current checkpoint

Phase 1 (requirements, data schema, acceptance criteria, Figma diagrams) is implemented on branch
`phase-1-schema`, OpenSpec change `phase-1-schema-acceptance`, draft PR #5. All tasks pass. Code
review, archive and merge remain (WORKFLOW.md § Pull requests and code review, steps 3–5).
The branch was cut from PR #4 (`chore/verbatim-skill-bytes`), which is still open. Merge #4 first,
then #5; the second diff then shows only Phase 1.

Phase 0 is Done and merged (PR #3, merge commit 0f06a80); its specs live in `openspec/specs/`.

**Data source changed in Phase 1 grilling (owner, 2026-10-11).** Vast.ai's terms (version
2026-09-01) forbid automated collection, price-comparison use and redistribution without a
written agreement. So does every GPU marketplace checked (SF Compute, RunPod, Lambda, TensorDock,
Shadeform, Prime Intellect, io.net, Akash). The owner chose not to seek permission. The v1 source
is the Azure Retail Prices API (public, no account), and the data is "published list prices for
GPU VMs from one cloud provider". Labelled synthetic marketplace-style data covers the
marketplace rules and the public demo. PROJECT.md, AGENTS.md, `openspec/config.yaml` and the
skills are reframed. No provider has been called yet.

## Implemented behavior

- Phase 0 toolchain: Python 3.13.16 via uv (`uv.lock`), OpenSpec CLI 1.6.0 via npm, the gate
  `uv run --frozen python scripts/gate.py` (after `uv sync --locked`, `npm ci --ignore-scripts`),
  CI on GitHub Actions, and Dependabot alerts and security updates.
- Phase 1 schema:
  - `src/compute_cost_risk_monitor/db.py`: `connect()` pins TimeZone=UTC; `create_schema()`
    applies numbered SQL files and records `schema_version`.
  - `schema/001_initial.sql`: nine tables (design § Schema) with constraints for the evidence
    rules. It ships in the wheel.
- `pytz` is a runtime dependency (DuckDB needs it for TIMESTAMPTZ → Python); `data/` is gitignored.
- Synthetic fixtures in `tests/fixtures/synthetic/`: an Azure-shaped page and marketplace offers,
  all invented values.
- Diagrams: [FigJam board](https://www.figma.com/board/JISCFP9eQzMq5QVg1k2V2A) on the Projects
  (Pro) team, with SVG exports in `docs/architecture/`.
- Acceptance criteria for Phases 2–7: the table in the Phase 1 design.

## Verification

- Phase 1 gate green on 2026-10-12 in Git Bash and Windows PowerShell: 64 tests, including 30
  schema tests (rejections, acceptances, and both fixtures end to end) and 27 provenance cases.
- The wheel built with `uv build` contains `schema/001_initial.sql`.
- Diagram screenshots were checked visually before export.
- Phase 0 evidence (fresh clone, deliberate defects, CI runs, audit) is in the Phase 0 archive
  and PR #3.

## Findings for later phases

- Azure reservation rows report `retailPrice` as the total for the term while
  `unitOfMeasure` says "1 Hour". Phase 2 must not store them in a way that reads as an hourly
  price: record the term next to the unit, or keep them out of `price_observation`. They are
  never compared (design D11).
- Live-data ⛔ gate for Azure (Phase 2): the operator confirms the Microsoft API terms and the
  pacing (≤ 1 request/s, back off on 429) before the first live read. No key is needed.
- Publishing live Azure figures is not expressly permitted by Microsoft's terms; the Phase 7
  demo uses synthetic data unless the publishing gate approves derived figures.
- DuckDB connections must go through `db.connect`; elsewhere TIMESTAMPTZ comes back in local time.
- npm's Windows `.cmd` shims (`npx`) break on the `&` in this folder name; run Node CLIs as
  `node node_modules/<pkg>/<bin>.js`.
- The global OpenSpec CLI sends PostHog telemetry unless `OPENSPEC_TELEMETRY=0`; the gate sets it.
- Phase 2: pytest-socket network blocking and a secret scanner. Phase 3: `gpu_sku_map` content
  from Microsoft Learn (CC BY 4.0, credited). Phase 4: Streamlit `gatherUsageStats = false`.
- CME's compute futures page still said "later this year, pending regulatory review" on
  2026-10-12; recheck before reframing PROJECT §1 in Phase 7.

## Next action

Phase 1 PR #5: run `/code-review` and record the market-review read-through, resolve findings,
archive the change (`chore:`, phase Done), rerun validation and the gate, push and mark ready.
Merge #4 then #5 only on the owner's go-ahead. Then Phase 2 grilling (Azure collector, including
the live-data gate).
