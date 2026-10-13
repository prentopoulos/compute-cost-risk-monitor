# Phase 6 tests review (traceability, coverage, live regression, build safety, market review)

- **Scope:** OpenSpec change `phase-6-tests` on branch `phase-6-tests`, at commit 76230c9 plus
  the code-review fixes (§ Code review). It covers tests for units, calculations, missing data and stale offers; the coverage threshold;
  Hypothesis; and four fixes found on the way.
- **Reviewer:** the main agent (Claude). This is a read-through and evidence record, not the
  code review: `/code-review` runs on PR #11.
- **Evidence:**
  - **Gate:** green with both coverage steps (all nine checks pass).
  - **Tests:** 718, at 100.0% branch coverage overall.
  - **Dependency audit:** `uv audit --locked --preview-features audit-command` found "no known
    vulnerabilities and no adverse project statuses in 69 packages".
  - **Live regression:** a scratch script on a read-only connection, counts and pass/fail only.
    No live price, cost or exposure figure appears in this document.
  - **Environment:** Windows 11, Python 3.13.16, uv 0.13.0, Hypothesis 6.169.0, coverage 7.16.2.
- **Recheck when:** a core module changes, a rule, map or scenario version is added, the
  coverage threshold is changed, Hypothesis changes major version, or a second live snapshot
  exists.

## Coverage before and after (design D3)

| | Tests | Statements (missed) | Branches (partial) | Total |
|---|---|---|---|---|
| Before, main at a79f0e0 | 649 | 2,830 (37) | 764 (21) | 98.4% |
| After the code-review fixes | 718 | 2,857 (0) | 762 (0) | 100.0% |

- **Total minimum:** pytest fails below 99.0% (`fail_under`, precision 1). The only exclusion is
  `if __name__ == "__main__":`. No `# pragma: no cover` exists.
- **Core coverage:** the gate step holds `azure_retail`, `normalize`, `checks`, `gpu_map`,
  `rules`, `groups`, `history`, `quality`, `calculator`, `scenarios` and `workload_check` at
  100% (1,392 statements and 416 branches). The gate deletes old coverage data before the tests
  step, and the step fails, naming the module, if a core module is renamed or missing.
- **Both steps fail when they should:** a run of `tests/unit/test_calculator.py` alone fails
  the minimum ("Required test coverage of 99.0% not reached. Total coverage: 10.95%"). The core
  step then exits 2 on an unrun module (`history.py` 0.0%).

## Traceability (design D2)

Tests are in `tests/unit/` unless named otherwise. **New** marks a Phase 6 test.

### Units

| Requirement or scenario | Tests |
|---|---|
| price-normalization "Every observation normalized or excluded": USD/GPU-hour = price ÷ GPU count; `unit_not_hourly` | `test_normalize::test_known_answers` (normal 8-GPU, normal Spot, not hourly, fractional); `test_synthetic::test_normalize_known_answers` |
| … the unit must be exactly `1 Hour` (MODIFIED) | **New:** `test_known_answers[unit in lower case]`, `[unit in the plural]`, `[hundred hours]` |
| … the first matching reason wins past the first (MODIFIED) | **New:** `test_known_answers[government before Windows and unit]`, `[Windows before unit]`, `[unit before unmapped]`, `[unit before retired]` |
| price-normalization "Independent checks": multiply back within 1e-9 | `test_checks::test_honest_rows_pass`, `test_tampered_price_caught`; **New:** `test_properties::test_usd_per_gpu_hour_times_gpus_gives_back_the_price` |
| azure-price-collector "Item key, repeats and price units": a non-hourly unit is flagged, not dropped | `test_azure_retail::test_item_known_answers`; **New:** `test_ingest::test_stored_row_with_a_non_hourly_unit_is_flagged` |
| price-data-schema: USD only; a reservation keeps its term unit | `test_schema::test_non_usd_currency_rejected`, `test_reservation_with_term_unit_accepted` |
| workload-calculator "Workload inputs": hours from 0.01 to 8,784 (MODIFIED) | `test_calculator::test_fractional_and_maximum_hours_accepted`, `test_impossible_hours_refused` (now with 0.009 and 5e-324); `test_app::test_impossible_hours_refused` |
| End to end: a `1/Day` row is excluded every time and never converted | **New:** `tests/e2e/test_known_answers.py::test_units_and_usd_per_gpu_hour` |

### Calculations

| Requirement or scenario | Tests |
|---|---|
| workload-calculator "Workload cost" and "Scenario figures and exposure", including 32 × 720 × $0.50 = $11,520 | `test_calculator::test_known_cost_without_and_with_storage`, `test_project_example_whatever_the_starting_price`, `test_known_scenario_rows`; **New:** `e2e::test_workload_on_the_third_snapshot` |
| … cost is linear; exposure = scenario cost − base cost, with the change's sign | **New:** `test_properties::test_cost_is_linear_in_gpus_and_hours`, `test_exposure_is_the_cost_difference_and_follows_the_change` |
| workload-calculator "Spot to pay-as-you-go fallback" | `test_calculator::test_fallback_*`; **New:** `test_workload_view::test_spot_size_missing_from_its_pay_as_you_go_group_is_not_computed`, `e2e::test_spot_workload_and_fallback` |
| workload-calculator "Budget headroom": budget from 0.01 (MODIFIED) | `test_calculator::test_known_headroom`, `test_budget_inputs` (now with 5e-324 and 0.01) |
| workload-calculator "Independent check of workload figures" | `test_workload_check` (every tamper test), including **new** `test_custom_change_of_an_unknown_kind_is_a_failed_definition`, a refused row with a note and a missing headroom % |
| … valid input never fails the check | `test_workload_view::test_extreme_custom_changes_pass_on_many_prices` (the 400-price sweep, kept); **New:** `test_properties::test_calculator_and_independent_check_agree` |
| price-normalization "Independent checks": a check does not lean on the schema | **New:** `test_checks::test_row_with_neither_reason_nor_price_caught`, `test_compared_row_without_a_variant_caught` (on a copy of the table without its CHECKs) |
| comparable-groups: lowest listed and statistics; ties | `test_groups::test_cross_region_summaries`, `test_ties_go_to_the_first_name`; **New:** `test_properties::test_lowest_and_statistics_do_not_depend_on_row_order` |

### Missing data

| Requirement or scenario | Tests |
|---|---|
| price-data-schema "Missing values stay missing"; collector "Missing field rejected, never filled in" | `test_ingest::test_missing_values_stay_null`, `test_azure_retail::test_optional_fields_stay_missing`, `test_schema::test_unmapped_observation_keeps_nulls` |
| snapshot-history "Absences and not listed": still not listed after three absences (MODIFIED) | `test_history::test_absent_once_then_not_listed`; **New:** `test_still_not_listed_after_three_absences`, `e2e::test_history_as_of_the_third_snapshot` |
| snapshot-history "Price changes": a return at a new price is not a change (MODIFIED) | **New:** `test_history::test_return_at_a_new_price_is_not_a_change`; the e2e fixture's item D |
| data-quality "Quality report": a run without a summary gives unknown counts (MODIFIED, fix) | **New:** `test_quality::test_run_without_a_summary_counts_are_unknown`, `test_dashboard::test_panel_shows_unknown_counts_without_a_run_summary` |
| data-quality: no snapshot, not normalized | `test_quality::test_no_snapshot_is_not_zero_prices`, `test_snapshot_not_yet_normalized_is_flagged`; **New:** `test_app::test_withheld_snapshot_lists_no_groups_and_flags_the_panel` |
| dashboard "Read-only access and database states" | `test_app` states; **New:** `test_file_that_is_not_a_database_is_named`, `test_read_error_is_shown_not_raised`, `test_choice_naming_no_group_draws_nothing`; `test_dashboard::test_database_error_on_open_named` |
| synthetic-marketplace "Synthetic command checks every file first" (ADDED, fix) | **New:** `test_synthetic::test_refused_file_creates_no_database`, `test_refusal_said_once`, `test_unreadable_file_refused_before_the_database`, `test_database_that_cannot_open_refused`; `test_synthetic_azure::test_refused_file_leaves_an_existing_database_unchanged` |
| A failed write leaves nothing | **New:** `test_synthetic::test_failed_write_rolls_back_the_whole_run`, `test_synthetic_azure::test_failed_write_rolls_back_the_whole_azure_run`, `test_schema::test_failed_migration_rolls_back`; `test_ingest::test_failed_write_leaves_nothing_behind` |
| Calculator "not computed", never filled in | `test_workload_check::test_missing_fallback_must_not_be_filled_in`, `test_workload_view::test_missing_published_price_fails_the_check` |

### Stale

| Requirement or scenario | Tests |
|---|---|
| data-quality "Fresh snapshot", "Stale snapshot" | `test_quality::test_fresh_and_stale` |
| … exactly 7 days is not stale (MODIFIED) | **New:** `test_quality::test_exactly_seven_days_is_not_stale`, `test_command_prints_the_as_of_time_in_utc`, `e2e::test_stale_as_of[+7 days, +7 days 1 s]` |
| … from the latest succeeded run (MODIFIED) | **New:** `test_quality::test_staleness_comes_from_the_latest_succeeded_run[partial, failed]` |
| … a snapshot dated after the as-of time (MODIFIED, owner D10) | **New:** `test_quality::test_snapshot_dated_after_the_as_of_time_is_not_stale` |
| data-quality "Quality command": as-of printed in UTC (MODIFIED, fix) | **New:** `test_quality::test_command_prints_the_as_of_time_in_utc` |
| dashboard: stale framing as of an injected time | `test_app::test_stale_framing_as_of_an_injected_time`, `test_dashboard::test_framing_lines` |

## Defects found and fixed (design D7)

1. **Synthetic command (D9):** it opened the database before checking any file, so a refused
   file left an empty database (12,288 bytes, no tables), and the message read "refused: …:
   refused: …". Now every file is checked first. Commit 26178b7.
2. **Quality command (D15):** it printed `--as-of` with the offset as given. It now prints UTC.
   Commit 1ccb74d.
3. **Missing run summary:** a run without its summary row reported "out of scope 0, repeats 0",
   filling in counts the records lack. It now reports them as `unknown (no run summary)` in the
   report and the dashboard panel. Commit 8b53b8f.
4. **Hours and budget bounds (D23, found by Hypothesis):** the validators accepted hours and
   budgets down to 5e-324.
   - **What happened:** the headroom overflowed or underflowed, and the independent check
     withheld every figure for a valid input. It failed safe. The page displays two decimals,
     but whether it keeps more digits a user types is not verified.
   - **Fix:** both must now be at least 0.01. Commit 050db8e.
   - **Evidence:** with those bounds, 10,000 random examples passed, as did two `explore` runs
     of 2,000 examples per property and the fixed `gate` profile.

Five more fixes came from the code review (§ Code review). No frozen version or methodology
definition needed a change.

## Property tests (design D4, D11)

- **The five properties:** `tests/unit/test_properties.py`, under the `gate` profile
  (derandomized, no example database, no deadline, 200 examples). `tests/repo/test_dependencies.py`
  loads `tests/conftest.py` in a fresh interpreter with and without `CI`, and gets `gate`
  each time. An unregistered `HYPOTHESIS_PROFILE` stops the run with one message.
- **One tolerance fix, in the test:** a storage amount adds rounding at its own scale to the
  difference of two costs. The product's check already allows for it (`_slack`), and the
  property now does too.

## Live regression, counts only (design D12)

Scratch script, read-only connection to `data/monitor.duckdb`, run 2026-10-13. The only live
snapshot is `20261012T151909Z-5473f1`.
- **Checks:** all seven independent normalization checks pass (multiply back 1,238; one row per
  observation 14,347; totals reconcile 1).
- **Quality report:** the same counts as Phase 5. 14,347 observations, 1,238 normalized, 929
  region groups (684 single list price), 51 cross-region summaries (11 thin), 49 sizes not in
  the map, out of scope 246. Not stale as of the run. No previous snapshot, so no changes or
  absences.
- **Workload check:** every one of the 1,238 members as the starting price, alone and with a
  −50% change and a budget. 2,476 of 2,476 pass the independent check, and the PROJECT example
  is exactly 11,520 in all 2,476.
- **Properties on live prices:** 1,238 members × 5 edge workloads × 6 changes × 3 budgets, or
  111,420 cases. All agree with the check, all are linear, and the exposure signs follow the
  change.
- **Order:** the lowest member is unchanged when members are reversed in 929 of 929 groups.

The owner ran no new live collect during the phase (D8), so changes and absences on real data
remain untested.

## Build-safety read-through

- **Dependency:**
  - Hypothesis 6.169.0 (MPL-2.0) and sortedcontainers 2.4.0 are dev only and locked with
    hashes. Nothing under `src/` imports them.
  - `uv audit`: no known vulnerabilities in 69 packages.
  - The dev-environment spec and `tests/repo/test_dependencies.py` list Hypothesis.
- **Offline:** no network code was added. Tests stay under pytest-socket. The e2e test and the
  property tests open no socket.
- **Generated files:** Hypothesis writes caches to `.hypothesis/` even with no example
  database, so the folder is ignored. After the gate, `git status --porcelain` shows only the
  pre-existing untracked `.agents/skills/openspec-*` folders, which this phase did not touch.
- **Data:** the new fixtures are labelled synthetic with invented prices and real size names. No
  live figure appears in Git, the PR or this record.
- **Gate:**
  - The new "core coverage" step runs from the locked environment (`sys.executable -m coverage`)
    and makes no network call.
  - CI runs the gate, so it inherits both steps; hosted CI on the branch is the remaining
    check.

## Market-review read-through

- **No figure changed** for any hours or budget of 0.01 or more. The calculator's formulas, the scenarios,
  rules and map are untouched. The live regression reproduces Phase 5 exactly: 2,476 of 2,476,
  and 11,520 exact.
- **Fix 4** only refuses hours or budgets below 0.01, a range where the headroom could not be
  computed. A refused input gives a message naming it, never a figure.
- **Fix 3** labels missing run records as unknown, keeping "missing observations stay missing".
- **Labels unchanged:** "published Azure list prices", "synthetic", "Scenario calculation, not
  a forecast". Every exclusion and caption line is unchanged.

## Code review

`/code-review` (high) on PR #11 found 14 issues; design D24 records each. Fixed with tests:
1. **Missing run summary:** the rejected total and a `shared_meter_key` count with no tally
   row read unknown, not 0. Tally rows that exist are still shown. Commit 1b9ab70.
2. **Synthetic command** (commit 4c26890):
   - two files in one command with the same source and observation time, including the same
     file twice, are refused before anything is written;
   - an `observed_at` that cannot convert to UTC, a `--db` whose folder cannot be made and a
     file-system error while storing are refused, not raised;
   - the raw response takes the ID its rows were built with.
3. **Gate:** the core coverage step cannot read stale data, and a missing core module fails it
   by name. Commit 9ab4c83.
4. **Hypothesis profile:** the `CI` case is tested in a subprocess, and a mistyped profile
   name gives one clear message. Commit 66cadc4.
5. **Pointers:** PROJECT.md and HANDOFF.md now cite design D1–D24.

Answered without a code change:
- **Widget minimums:** they stay at 0 while the validators start at 0.01, so the validator's
  message explains each refusal, as Phase 5 chose. D23's wording is corrected.
- **Double parsing:** each synthetic file is parsed twice, which is negligible for files of a
  few kilobytes.
- **Schema-only file:** a database error mid-write can still leave a schema-only new file. That
  is a write failure, not a refused file, and the comment says so.

## Not covered

- **Mutation testing:** not run (owner D5).
- **Manual browser check:** none. The page's flows and layout are unchanged. Its two changed
  texts, the hours refusal and the panel's "unknown", are checked by AppTest and the
  view-model tests only.
- **Real-data history:** changes, absences and "not listed" on real data need more owner-started
  live snapshots.
