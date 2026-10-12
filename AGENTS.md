# Compute Cost & Risk Monitor

Answers which comparable GPU cloud options are listed, what a workload would cost, and how
exposed a compute budget is to changing prices, using published Azure list prices from the
public Azure Retail Prices API, plus labelled synthetic marketplace-style data.

Read PROJECT.md for scope, acceptance criteria and gates.
Follow WORKFLOW.md and .agents/skills/next-phase/SKILL.md for phase/checkpoint work.
Read HANDOFF.md for recovery state. Use .agents/skills/compute-cost-risk-monitor-build-safety/SKILL.md for
architecture, dependencies, tool contracts, data, telemetry, spend or readiness.
Use .agents/skills/compute-cost-risk-monitor-market-review/SKILL.md for offer data, comparable
pricing, workload costs, budget exposure and the market brief.

## Boundaries

- Seven phases after Phase 0 (PROJECT.md §6): schema, collector, normalization and quality
  checks, Streamlit dashboard, workload costs and exposure scenarios, tests, public demo.
- One source (Azure Retail Prices API) until a second source's access, terms and comparable
  fields are verified. No GPU marketplace qualifies (terms checked 2026-10-11).
- Data is published list prices, read-only. Never create or change cloud resources.
- Tests use synthetic or recorded fixtures. Live reads, scheduled collection, paid calls and
  publishing wait for their ⛔ gates.
- An AI agent is optional and only drafts the market brief from validated numbers.

## Non-negotiables

- Secrets use the runtime secret mechanism (gitignored .env for local development); never
  print, commit or put them in outputs.
- ⛔ gates in PROJECT.md are operator-resolved. Surface and stop at the relevant gate; never
  satisfy or waive one. Local work can proceed before deferred gates.
- Never fabricate results or external-service output. Label mocked, local and live results
  accurately. Preserve failed runs.
- Label data as published Azure list prices, never a marketplace, benchmark or what customers
  pay; label synthetic data synthetic. Label exposure figures as scenario calculations, not
  forecasts.
- Deterministic code computes every price, cost and exposure figure. State cost exclusions.
- Every PR that changes code gets a code review before merge (WORKFLOW.md).

## Development

Python 3.13 with pandas, DuckDB, Streamlit and pytest, managed by uv (`uv.lock`); the OpenSpec
CLI is pinned through npm (`package-lock.json`). Bootstrap: `uv sync --locked` then
`npm ci --ignore-scripts`. Run Python and its tools only through uv (`uv run ...`): bare
`python`, `ruff` and `mypy` on the owner's PC come from other environments and differ by shell.
Architecture diagrams: a Figma draft on the owner's Pro seat, created in Phase 1.
Gate: `uv run --frozen python scripts/gate.py`. CI runs it on every PR
(`.github/workflows/ci.yml`).
Remote: https://github.com/prentopoulos/compute-cost-risk-monitor (private). Push phase
branches and open PRs at the points WORKFLOW.md sets; nothing goes straight to main, and a PR
merges only after its review and the user's go-ahead.
