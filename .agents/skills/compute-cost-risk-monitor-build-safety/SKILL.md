---
name: compute-cost-risk-monitor-build-safety
description: Apply relevant engineering workflows to Compute Cost & Risk Monitor architecture, dependencies, tool contracts, data handling, cost controls, telemetry and phase readiness. Use for those boundaries, not as a mandatory full audit of every edit.
---

# Compute Cost & Risk Monitor build safety

Read [PROJECT.md](../../../PROJECT.md) and the affected OpenSpec design/tasks. Follow current
scope and existing authorization. This skill grants no spending, publication or data-transfer
permission and adds no per-edit approval ritual.

The full 17-workflow Agent Builder collection is preserved under
[agent-builder](agent-builder/README.md). **First read the project adaptation below**, then the
[shared contract](agent-builder/FOUNDATION_CONTRACT.md), [baseline](agent-builder/SECURITY_BASELINE.md)
and only workflows relevant to the current boundary. Source examples are not project defaults.

## Project adaptation

- PROJECT owns scope, decisions and operator gates; OpenSpec owns requirements/design/tasks.
  Apply source questions to those records and actual code. Do not create a competing YAML
  project spec, mandatory catalog, or 17 separate result envelopes.
- Source frameworks, cloud defaults, inventory examples, sample budgets and evaluation counts
  are illustrative. Use this project's actual stack, lockfile and gate.
- Current target: a single-owner local prototype (Python, pandas, DuckDB, Streamlit) built in
  eight sessions as a portfolio demo; Phase 8 adds a public demo. Live Azure Retail Prices reads,
  scheduled collection, paid calls, a second source, the optional AI brief drafter and
  hosting are absent/deferred until their PROJECT gates, not silently implemented. No
  accounts, multiple users, sensitive personal data or instance-changing actions.
- Terms: "tools" are typed source adapters (Azure Retail Prices API first). "Evaluation" is
  deterministic pytest checks of units, comparability, cost and exposure maths on fixtures,
  plus the data-quality panel on collected data; LLM-judged cases apply only to the optional
  brief. "Model versions" are schema, comparability-rule, dependency and (if added)
  prompt/model versions. "Tracing" is collection-run records and retained raw responses.
- Gates: live source reads, scheduled collection, spend and publishing (PROJECT §6). A
  document, mock or recorded fixture closes none of them.
- The source assumes an LLM agent built on ADK and deployed to cloud. Here the product is a
  data pipeline plus dashboard: agent/ADK guidance applies only to the optional brief
  drafter, and IaC only once hosting is approved.
- Use existing artifacts for small reviews. Substantial reviews go in docs/reviews with
  scope/revision, applicability, findings, evidence, owner, next action and recheck trigger.

Read the sibling [compute-cost-risk-monitor-ai-ops](../compute-cost-risk-monitor-ai-ops/SKILL.md)
for system versioning, evaluation, retrieval, state, training and operations.

## Route the work

| Boundary | Complete workflows to read in agent-builder |
|---|---|
| Architecture, data schema and phase scope | validate_architecture_spec.md, Architecturebuild.md |
| Python dependencies, lockfile and repo layout | resolve_stack_dependencies.md, scaffold_repo_tree.md |
| Source adapters (Azure Retail Prices API; second source deferred until its access, terms and fields are verified) | select_adk_tools.md, generate_tool_schema.md |
| API keys, raw responses, dashboard inputs or new exposure | assess_threat_vectors.md, design_pii_redaction.md; map_rbac_policies.md when access roles exist (deferred until accounts exist) |
| Collection runs, raw-response retention and rule versions | configure_telemetry_schema.md, generate_asset_metadata.md |
| API rate limits, paid calls or hosting cost | apply_finops_governance.md |
| Calculation tests, data-quality checks and phase readiness | generate_eval_metrics.md, define_release_gates.md, orchestrate_ci_cd.md |
| Scheduled collection or demo hosting (deferred until their ⛔ gates) | design_iac_blueprint.md |
| AI market-brief drafter (deferred until Phase 8 and the spend gate) | standardize_system_prompt.md plus relevant tool/data workflows |

Source filenames above resolve in [agent-builder/](agent-builder/README.md).
Read [compute-cost-risk-monitor-market-review](../compute-cost-risk-monitor-market-review/SKILL.md)
for price, cost and exposure evidence.
For an explicitly comprehensive review account for all 17 workflows; for normal work record
only the relevant scope. Deferred controls must be revisited when their capability is added.

## Completion

Trace each material failure to a control, enforcement point, test and requirement. Separate
proposed, implemented, tested and externally verified. Unknown usage stays null; a mock or
local run is not a live result. Preserve failed evidence and unresolved dependencies.

[Source manifest](references/source-manifest.json) records the exact Agent Builder copies.
