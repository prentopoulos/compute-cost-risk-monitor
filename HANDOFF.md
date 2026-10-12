# Current handoff

Read PROJECT.md and current user instructions. Inspect actual Git/OpenSpec state before resuming.

## Current checkpoint

Phase 1 (requirements, data schema, acceptance criteria, Figma diagrams) is Done and merged
(PR #5, merge commit cfeb41b), after PR #4 stored the verbatim skill copies byte for byte (merge
commit 91ca8a0). Both branches are deleted. The change is archived as
`openspec/changes/archive/2026-10-12-phase-1-schema-acceptance`, and its spec lives in
`openspec/specs/price-data-schema`. No OpenSpec change is active.

Phase 0 is Done and merged (PR #3, merge commit 0f06a80); its specs live in `openspec/specs/`.

From Phase 2 on, each phase starts in a fresh session (WORKFLOW.md § Fresh session per phase).
Everything the next phase needs is in this file, PROJECT.md, OpenSpec and Git.

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

- Phase 1 gate green on 2026-10-12 in Git Bash and Windows PowerShell. After the review fixes
  there are 83 tests: 49 schema and runner tests (rejections, acceptances, both fixtures end to
  end) and 27 provenance cases.
- Code review (`/code-review` on PR #5) found 10 issues; all are fixed with tests. The
  owner asked for more spacing in the diagrams, so they were regenerated with wider layout spacing
  and padded sections. Moving nodes through the plugin API leaves stale connector routes.
- The wheel built with `uv build` contains `schema/001_initial.sql`.
- After both merges, main has the same file tree as the reviewed PR #5 head (69f4433), whose CI
  run passed the gate and `uv audit`.
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
- Dependabot alert #1 (high, GHSA-vfj7-8cjw-p6xm): `braces` 3.0.3 can exhaust the stack on
  deeply nested brace patterns. It is a development-only dependency of the OpenSpec CLI
  (fast-glob → micromatch → braces), and no fixed release existed on 2026-10-12. OpenSpec only
  sees this repo's own paths, never outside input. The alert stays open until a fix ships or
  the owner dismisses it. `uv audit` finds nothing in the Python packages.

## Next action

Start Phase 2 in a fresh session: the owner clears the context and runs `/next-phase`. Then
grill Phase 2, the Azure Retail Prices collector, including the live-data ⛔ gate (the owner
confirms Microsoft's API terms and the pacing) and how to store reservation rows.
