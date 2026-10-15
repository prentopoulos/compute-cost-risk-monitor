---
name: compute-cost-risk-monitor-ai-ops
description: Operate Compute Cost & Risk Monitor ML, LLM, RAG and agent systems. Use when changing model or prompt behavior, evaluation, retrieval, training data, runtime state, provider routing, monitoring or release recovery.
---

# Compute Cost & Risk Monitor AI operations

Read [PROJECT.md](../../../PROJECT.md), the affected OpenSpec tasks, and
[AI_OPS.md](../../../AI_OPS.md). Follow
[build-safety](../compute-cost-risk-monitor-build-safety/SKILL.md) for the shared engineering baseline.
This skill adds operational procedures; PROJECT owns scope and authorization, OpenSpec owns
requirements/tasks, and AI_OPS maps capabilities to evidence. Reuse these records.

## 1. Select the changed boundary

Classify the slice using AI_OPS: ML training/serving, LLM calls, RAG, tools, state, code
execution, multi-user access, or external tool servers. Record enabled, deferred or unknown
with a reason and recheck trigger. A coding assistant helping build an ordinary app does
not make that app an AI system. Load only the relevant references:

| Trigger | Reference |
|---|---|
| Code/model/prompt/tool/config/data/environment release or rollback | [System versions](references/system-versions.md) |
| Behavior change, model comparison, quality gate or experiment | [Evaluation](references/evaluation.md) |
| Retrieval, ingestion, cache, gateway, streaming or prompt experiment | [LLM and RAG operations](references/llm-rag.md) |
| Tool actions, approval, checkpoint/replay, concurrency, sandbox or MCP | [Agent runtime](references/agent-runtime.md) |
| Training data/features, retraining, model registry, drift or fairness | [ML lifecycle](references/ml-lifecycle.md) |
| Run records, cost, latency, alerts, incident or recovery | [Operations](references/operations.md) |

## 2. Establish evidence before changing behavior

Identify the current system version, baseline cases, success criteria and affected controls.
For a behavior change, freeze cases and thresholds before tuning. Include the negative path
at the actual enforcing boundary. Existing valid evidence may be reused with its revision.
Missing information becomes an explicit gap, not a pass or invented default.

## 3. Implement within the selected scope

Build the smallest applicable control with the existing stack. Local files, JSONL and a
single check command can suffice. Course tools and sample numbers are examples, not mandatory
dependencies or thresholds. Verify installed APIs or official documentation before adopting
version-specific code. Keep deterministic checks offline; separately identify authorized
provider evaluations and their aggregate budget.

Preserve standing authorization. Add an approval interruption only where the project's
action policy requires it, with a concrete action ready for review. Unknown capabilities
block only the dependent exposure or release, not unrelated local implementation.

## 4. Verify and record

Run affected checks, retain failures, compare the same cases against the baseline and
record scope, system version, evaluator version, sample counts and uncertainty. Each
required check is pass, fail, not_run or stale. An absent capability can be not_applicable
with evidence and a recheck trigger. Any hard-control failure rejects promotion; missing
required evidence holds it.

Use existing equivalent records; otherwise adapt [EVAL_PLAN.md](assets/EVAL_PLAN.md),
[RELEASE_RECORD.md](assets/RELEASE_RECORD.md) or [RUNBOOK.md](assets/RUNBOOK.md) when needed.
These are forms to fill, not passed checks. Keep raw sensitive data in protected storage.

Done when changed boundaries have implementation/test evidence, failed or untested cases
are explicit, AI_OPS evidence pointers are current, and HANDOFF names the next action.
Do not label a documentation update, synthetic fixture or local smoke test production-ready.

[Sources and course qualifications](references/SOURCES.md) explain the adapted material.
