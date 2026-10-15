# Compute Cost & Risk Monitor AI operations

PROJECT.md owns scope, decisions and operator gates. OpenSpec owns requirements and tasks.
This record maps AI capabilities to their current evidence; link existing artifacts rather
than maintaining duplicate specifications. Read
[the AI-ops skill](.agents/skills/compute-cost-risk-monitor-ai-ops/SKILL.md) for the affected procedure.

## Capability map

The only planned AI capability is the market-brief drafter: one hosted model call that writes
the brief's prose from numbers the deterministic code has already computed and checked
(PROJECT.md §5). The owner put it in Phase 8 scope in the Phase 8 grilling (2026-10-14). No AI
code exists yet, so nothing below is enabled.

| Capability | Status | Reason / evidence or task | Recheck when |
|---|---|---|---|
| Hosted or local model inference | deferred | Phase 8: one Claude API call (`claude-opus-5-5`) per brief draft, started by hand. Not built yet | The Phase 8 drafter task, or any provider or model change |
| Prompts and structured output | deferred | Phase 8: one versioned prompt. The draft is prose with placeholders from a closed list of fact IDs; code fills every number and a validator rejects the draft otherwise | Prompt, placeholder list, validator or model changes |
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
| System bundle and last known-good version | TBD: Phase 8 run record (model ID, prompt version and hash, fact-set hash, SDK version, git commit) |
| Evaluation plan, held-out cases and evaluator | TBD: Phase 8 fixture responses for the normal case and every rejection case, the deterministic validator, and the independent brief check |
| Offline deterministic check command | `uv run --frozen python scripts/gate.py` |
| Authorized provider-evaluation command and budget | TBD: the Phase 8 drafter command, started by hand; budget under the PROJECT.md §6 spend gate |
| Run records / metrics / alerts | TBD: a JSON record beside each brief (Phase 8). No alerts: runs are manual |
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

No AI runtime evaluation has been established by installing this kit. Record actual candidate
and baseline versions, case counts, commands, pass/fail/not_run/stale outcomes and limitations
as implementation proceeds. A deferred capability needs fresh evidence before it is enabled.
