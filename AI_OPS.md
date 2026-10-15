# Compute Cost & Risk Monitor AI operations

PROJECT.md owns scope, decisions and operator gates. OpenSpec owns requirements and tasks.
This record maps AI capabilities to their current evidence; link existing artifacts rather
than maintaining duplicate specifications. Read
[the AI-ops skill](.agents/skills/compute-cost-risk-monitor-ai-ops/SKILL.md) for the affected procedure.

## Capability map

The only planned AI capability is the market-brief drafter: one hosted model call that writes
the brief's prose from numbers the deterministic code has already computed and checked
(PROJECT.md §5). The owner put it in Phase 8 scope in the Phase 8 grilling (2026-10-14). It is
built (`src/compute_cost_risk_monitor/drafter.py`) and tested offline; its first real run is
Phase 8 task 4.4, started by the owner.

| Capability | Status | Reason / evidence or task | Recheck when |
|---|---|---|---|
| Hosted or local model inference | enabled | `drafter.py`: one Claude API request (`claude-opus-5-5`, effort low, 4,000 tokens) per attempt, at most two, started by hand with `brief --draft`; no fallback model, no SDK retries. Tests: `tests/unit/test_drafter.py`, `tests/unit/test_brief_command.py` | Any provider, model, effort or token change |
| Prompts and structured output | enabled | `drafter.SYSTEM_PROMPT` (`prompt v2` since the first run, SHA-256 in every run record); JSON-schema output with one string per section; placeholders from the fact set's closed list; the validator and the independent brief check (`brief_check.py`) | Prompt, placeholder list, banned words, validator or model changes |
| RAG / document ingestion | not applicable | The drafter receives one fact set built by code; nothing is retrieved or indexed | A document source or retrieval step is proposed |
| Semantic or response caching | not applicable | One call per draft, no cache | Repeated or batched drafting is proposed |
| Model training / feature pipelines | not applicable | No model is trained or tuned | Any training or fine-tuning is proposed |
| Tool actions / external adapters | not applicable | The model gets no tools. The only external adapter is the Azure Retail Prices collector, which uses no AI | The model is given a tool, or a new adapter is added |
| Persistent state / replay | not applicable | Each draft is one stateless request; run records are files | Multi-turn drafting or resumable runs are proposed |
| Multiple users / tenants | not applicable | Single-user local tool (PROJECT.md §2) | A second user, host or shared service is proposed |
| Generated code execution | not applicable | No code execution | A code-execution tool is proposed |
| MCP / external tool servers | not applicable | The product runs no MCP server. Design-time MCP tools used to build it (Figma, 21st.dev) are not part of the product | The product exposes or calls an MCP server |

## Evidence locations

| Record | Location / current status |
|---|---|
| System bundle and last known-good version | `run-record.json` beside each brief: model, model used, SDK version, prompt version and SHA-256, fact-set SHA-256, git commit. Last known-good: provider run 2, 2026-10-15 (`docs/brief/run-record.json`) |
| Evaluation plan, held-out cases and evaluator | Fixed cases in `tests/fixtures/synthetic/drafter_replies.json` (one valid reply and one per rejection rule), the deterministic validator (`drafter.rejections`) and the independent brief check; no LLM judge |
| Offline deterministic check command | `uv run --frozen python scripts/gate.py` |
| Authorized provider-evaluation command and budget | `uv run --locked python -m compute_cost_risk_monitor.brief --db data/synthetic.duckdb --as-of 2026-10-12T09:00:00Z --out docs/brief --draft`, started by hand; USD 5, up to USD 10 in total (PROJECT.md §6) |
| Run records / metrics / alerts | `run-record.json` beside each brief: each attempt's request ID, stop reason, usage, outcome and reasons, and the estimated cost. No alerts: runs are manual |
| Release evidence and stop/recovery runbook | TBD: the Phase 8 review record in `docs/reviews/`. Stopping is not running the command; the template brief is the fallback |
| Operational owner and maintenance/recheck cadence | The owner. Rechecked when a trigger above fires |

## Current operational limits

Decided in the Phase 8 grilling (owner, 2026-10-14); enforced by the Phase 8 code once built,
and by the provider console:

- one call per draft, at most 4,000 output tokens, low effort, at most one retry after a
  rejected draft, then the template brief;
- synthetic figures only; never in CI, tests, the dashboard or a schedule;
- spend under the PROJECT.md §6 spend gate: USD 5, up to USD 10 in total, an organisation spend
  limit of USD 10 in the provider console and automatic top-up off;
- the API key in the user environment or a gitignored `.env`, never in the repo.

The provider keeps API inputs and outputs for up to 30 days and does not train on them
(Phase 8 grilling research, 2026-10-14). Only synthetic figures are sent.

## Latest scoped evidence

- **Offline, 2026-10-15 (pass):** 24 drafter tests and the brief command's `--draft` tests
  pass with a fake sender and synthetic replies, no key and no network. `drafter.py` and
  `brief.py` are at 100% branch coverage; the gate is green.
- **Provider run 1, 2026-10-15 (fail, kept):** `prompt v1`, two requests, about USD 0.09;
  both drafts rejected for digits (likely GPU and size names), so the template was used
  (commit 0730db0). Fixed by design D46 (`prompt v2`).
- **Provider run 2, 2026-10-15 (pass):** `prompt v2`, one request, 6,119 input and 1,082
  output tokens, about USD 0.05; the draft was accepted and passed the independent check
  (105 numbers and 13 times re-derived). Last known-good: this run's record in
  `docs/brief/run-record.json`. Spend so far about USD 0.14 of the USD 10 cap.
