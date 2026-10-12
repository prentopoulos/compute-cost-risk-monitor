# Phase 3 normalization review (market review and build safety)

- **Scope:** OpenSpec change `phase-3-normalization` at commit 8553cd2, plus the first
  normalization of the live snapshot `20261012T151909Z-5473f1` under `groups-v1` and
  `gpu-map-v1`.
- **Reviewer:** the main agent (Claude). This is a read-through, not the code review, which
  `/code-review` does on PR #8.
- **Evidence:**
  - the gate, and known-answer tests on synthetic fixtures;
  - the independent checker (`checks.py`) on the live rows;
  - a recount of every exclusion reason by a script that shares no code with the package
    (it parses the map CSV itself and types the retirement dates by hand);
  - plausibility counts from the stored rows.

  Counts only: no price, USD/GPU-hour or statistic appears in this document.
- **Recheck when:** the map, the rule set, the OS rule, the retirement list or the group
  statistics change, or a new snapshot shows reason counts that move sharply.

## Market review (compute-cost-risk-monitor-market-review)

| Check | Outcome | Evidence |
|---|---|---|
| Prices finite, positive, USD, original unit kept beside USD/GPU-hour | Pass | Schema CHECKs. USD/GPU-hour exists only in `normalized_price`. The observation keeps its price and unit, and only "1 Hour" rows are compared |
| USD/GPU-hour × GPU count reproduces the hourly price | Pass | `multiply_back` passes on all 1,238 compared rows (rel. tol. 1e-9). An independent SQL recompute finds 0 mismatches |
| Every figure carries group key, snapshot time and exclusions | Pass | Region groups and summaries carry their key, snapshot run and start time, and the rule set's exclusions text (checked true for all 929 groups and 51 summaries). Cross-region summaries are labelled `crosses regions` and `lowest listed per region` |
| Comparable groups only | Pass | Group key = variant, GPU count, region, rental type (D3, D6). Different counts never share a group (test). Excluded rows never enter a group (test) |
| Every price accounted for | Pass | 14,347 observations → 14,347 rows: 1,238 compared; 8,014 rental type not compared; 311 government cloud; 3,009 Windows; 775 unmapped; 666 fractional; 334 retired. The independent recount matches every count |
| Missing stays missing | Pass | Unmapped rows have no GPU fields or map reference. The checker fails a row that gains them. 49 sizes are named as not in the map |
| No duplicate (item, retrieval time); a re-listing is not a new offer | Pass | Primary keys. The live run has 0 repeats and 0 `shared_meter_key`. On the synthetic snapshots, machine duplicates are flagged and counted once, and a re-listing continues as the same offer |
| Stale and thin flagged, never averaged in | Pass | The quality report is `not stale` as of the snapshot day. 11 of 51 summaries are `thin` (< 5 regions), and 684 of 929 region groups are `single list price`. Medians state their count |
| "Not listed" never inferred from one absence | Pass | Two absences in a row are required (D7). Partial and failed runs never count (tests). One live snapshot exists, so there is no history yet |
| Labels and framing | Pass | Output says "list price", "lowest listed" and "synthetic". No code or document calls the data a market price, index, benchmark or what customers pay |
| Results name inputs and versions | Pass | Rows carry `groups-v1` and `gpu-map-v1`. Both are stored as frozen rows, and changed ones are refused. Each map row cites its Learn URL and retrieval date |

Plausibility on the live compared rows (counts only):
- **Shape:** 629 pay-as-you-go and 609 Spot rows, covering 34 sizes, 17 variants and 54 regions.
- **Spot against pay-as-you-go:** of the 609 size-region pairs that have both, Spot is lower in
  561, equal in 48 and never higher. Every Spot row has a pay-as-you-go twin.
- **Groups with several sizes:** 245 region groups hold more than one size. In 64 of them the
  highest member is over 1.5× the lowest, because sizes with the same GPUs differ in vCPUs, RAM
  and local disk (for example the RTX PRO 6000 `ds` and `lds` lines, and the T4 sizes).
- **Spread across regions:** 8 of 51 summaries have a maximum over 2× the minimum.
- **Exclusions hold:** no compared row is in a government region, is a Windows product, or is
  from a retired series outside a Learn extension. 10 rows are compared because Learn extends
  NCv3 to Jio India West and NVv3 to UAE North (D24).
- **Dates:** no effective start date is later than the snapshot.

Findings for later phases:
- **Phase 4:** show every member of a multi-size group, with its size name. "Lowest listed per
  region" picks the cheapest configuration, often the one with the fewest vCPUs, so the dashboard
  should say so next to the summary.
- **Phase 4:** the 48 Spot rows priced the same as pay-as-you-go are published that way. Show
  them as listed; do not treat them as errors.
- **Map v2:** 49 sizes are unmapped, including the H100 `noIB`, `flex` and `isrf` sizes, MI300X
  `ND96is`, and 20 RTX PRO 6000 sizes. Add them only when Learn names them exactly.

## Build safety (compute-cost-risk-monitor-build-safety)

Workflows read (2026-10-12), each applied through the skill's project adaptation:
- `validate_architecture_spec`: conformance is checked against PROJECT §5 and the owner's
  decisions (D1–D11), not an external pattern catalog.
- `generate_eval_metrics`: "evaluation" means deterministic known-answer tests, with normal, edge
  and deliberately failing cases (its M04, domain correctness). There is no LLM judge.
- `generate_asset_metadata`: the versioned assets are the frozen rule set and map, each recorded
  with its sources and retrieval dates.
- `configure_telemetry_schema`: "tracing" is the run records plus the stored rule and map
  versions, and unknowns stay null rather than zero.

The agent, ADK, IAM, IaC and FinOps guidance does not apply: there is no model, no network code
was added, and no paid service is used.

| Threat or control | Disposition | Enforcement and test |
|---|---|---|
| New network access | None. The map was built by hand from Learn pages, and no scraper exists. The only network code is still the Azure adapter | Code review of the diff; pytest runs with sockets blocked |
| Rule or map drift (silent change of methodology) | `groups-v1` and `gpu-map-v1` are committed before the first live run and stored as rows. A stored version that differs is refused (exit code 2) | `test_changed_rule_set_refused`, `test_changed_map_refused`, `test_changed_rules_refused`, `test_command_refuses_missing_db_and_changed_rules` |
| Wrong figures from a classifier bug | An independent checker reads the stored rules and rows and re-derives multiply-back, one row per observation, reasons, map agreement, compared-row rules and totals. A failure exits non-zero | `test_checks.py`, including a deliberately lax classifier that the checker catches |
| Partial writes | Normalize and synthetic ingest each run in one transaction and roll back on error | `test_error_rolls_everything_back`, `test_duplicate_offer_refused` (nothing written) |
| Synthetic data mixed with live | Synthetic files must carry `"_label": "synthetic"`. Runs are labelled `synthetic`, the schema forces that label for marketplace sources, and the command refuses `data/monitor.duckdb` | `test_unlabelled_file_refused`, `test_command_never_writes_the_live_database` |
| Injection | SQL uses fixed table and column names with parameterized values. Map and snapshot inputs are validated before any write | `test_bad_rows_refused`, `test_bad_offers_refused`, `test_bad_files_refused` |
| Disclosure of live figures | Commands print counts, names and keys only. Git, the PR and this review hold no prices (D17) | `test_command_prints_counts_only`, `test_render_holds_no_prices` |
| Licence | Learn content is CC BY 4.0, credited in the CSV header and `reference/README.md` | Map loader test; file headers |
| Supply chain | No new dependency | `uv lock --check` in the gate |

Residual risks:
- **The OS rule depends on product-name wording.** A new suffix would make Windows rows count
  as Linux. `os_ambiguous` (0 today) and the Windows count in the quality report would show it.
  Recheck on each new snapshot.
- **Learn pages change.** Map rows and retirement dates carry their URL and retrieval date. A
  change means a new map or rule version, never an edit.
- **A local backup exists.** `data/monitor.pre-phase3.duckdb` (gitignored) is a copy taken
  before the first normalize, and can be deleted once the owner is satisfied.
