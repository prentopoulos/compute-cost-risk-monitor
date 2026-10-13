## Context

This is Phase 6 of PROJECT.md §6. Phase 1's acceptance row for it reads:
- requirement: "Close the gaps in units, calculations, missing data and stale data. Set the
  coverage threshold deferred in Phase 0";
- evidence: "Gate and CI green with the threshold".

Phase 0 D12 reported branch coverage with no minimum "until Phase 6".

The Phase 6 grilling ran one round on 2026-10-13:
- **Round 1:** an informed-answerer subagent researched 11 questions, found 3 more and audited
  the tests against every spec in the four areas.
- **Re-check:** the main agent reopened the sources behind its settled answers:
  - coverage 7.16.2 `should_fail_under` and pytest-cov 7.1.0 reading `fail_under` and `precision`
    from the coverage config;
  - the `quality-gate` spec and Phase 4 D19;
  - `quality.py`'s stale comparison and as-of printing;
  - the synthetic command's open-before-check order;
  - the dev-environment "Clean tree" scenario.

  It moved the coverage threshold from settled to an owner call: Phase 1 made it this phase's
  acceptance evidence, and its strictness costs Phase 7 hours.
- **Owner:** accepted every recommendation ("All recommended").

### Measured facts (2026-10-13, main at a79f0e0, local commands)

- **Tests:** 649 pass in about 96 s. Branch coverage is 98.386% overall: 2,830 statements with
  37 missed, and 764 branches with 21 partial. CI run 38457601984 on main matches it, with 3
  tests skipped there.
- **Files below 100%:**

  | File | Coverage | Missing |
  |---|---|---|
  | `app.py` | 95% | 94, 221, 272–273, 287, 319–321, 327–329 |
  | `synthetic.py` | 95% | 239–241, 333–335, 368–370, 385 |
  | `workload_check.py` | 97.8% | 83, 180, 200 |
  | `checks.py` | 98.1% | 97, 101 |
  | `quality.py` | 98.1% | 173→175, 296 |
  | `normalize.py` | 98.3% | 290→295, 339 |
  | `collect.py`, `db.py`, `dashboard.py`, `ingest.py`, `raw_store.py` | 97–99% | a few lines each |

  Lines 296 in `quality.py` and 339 in `normalize.py` are `if __name__ == "__main__":` bodies.
- **Coverage mechanism:**
  - coverage.py has one `fail_under`, compared after rounding to `precision` decimals, and 100
    must be exactly 100.
  - `coverage report --include=... --fail-under=N` gives a per-module minimum over the same data
    file.
  - pytest-cov reads `fail_under` and `precision` from `[tool.coverage.report]`.
- **Stale:** `quality.py` computes `as_of - latest.started_at > 7 days`.
  - A snapshot exactly 7 days old is not stale, which matches the spec's "more than 7 days".
  - A snapshot dated after the as-of time has a negative age and is not stale. No spec covers
    that case.
- **Synthetic command:** it opens (and so creates) the database before it checks any file. A
  refused file leaves a 12,288-byte database with no tables, and the command exits 2. The
  message reads "refused: <file>: refused: …".
- **Quality command:** it prints `--as-of` with the offset as given (`quality.py:222`). Snapshot
  times are UTC, because the connection pins UTC.
- **Live data** (read-only, counts only): one snapshot, `20261012T151909Z-5473f1`. Its only
  units are "1 Hour" and reservation terms, and all tiers are 0. It turns stale after
  2026-10-19 15:19 UTC.
- **Hypothesis 6.169.0** (PyPI, 2026-10-13):
  - MPL-2.0, Python ≥ 3.11, with one dependency, sortedcontainers.
  - It loads its built-in `ci` profile when the `CI` environment variable is set, as GitHub
    Actions sets it.
  - Its default example database writes `.hypothesis/`.
- **Mutation tools:** mutmut 3.x needs `fork`, so on Windows it runs only inside WSL. cosmic-ray
  8.7 runs on Windows, but it rewrites source files in place and brings heavy dependencies.

### Gap audit (tests in `tests/unit/` unless noted)

| Area | Already pinned (examples) | Gaps this phase closes |
|---|---|---|
| Units | `test_normalize::test_known_answers` (normal, not hourly, fractional, reservation); `test_checks::test_tampered_price_caught`; `test_azure_retail::test_item_known_answers`; `test_schema::test_non_usd_currency_rejected`; `test_calculator::test_fractional_and_maximum_hours_accepted` (8,784) | The exact unit match ("1 hour", "1 Hours", "100 Hours" excluded); exclusion order past the first reason; multiply-back over generated prices |
| Calculations | `test_calculator` (the PROJECT example at four prices, decline, refusal, fallback, headroom); `test_workload_check` (17 tests); the 400-price sweep; `test_groups::test_cross_region_summaries`; `test_checks` (17 tests) | `checks.py` 97, 101; `workload_check.py` 83, 180, 200; independence from row order; generated agreement between calculator and check |
| Missing data | `test_ingest::test_missing_values_stay_null`; `test_normalize` unmapped; `test_quality::test_no_snapshot_is_not_zero_prices`; `test_history::test_absent_once_then_not_listed`; `test_dashboard::test_chart_plots_only_listed_regions`; the calculator's "not computed" tests | History through real ingest (today only rows seeded by SQL); "not listed" after 3+ absences; reappearance at a new price; a run without a summary (`quality.py` 173→175); `app.py` error states; synthetic rollback and open-refusal paths; the empty database left by a refusal |
| Stale | `test_quality::test_fresh_and_stale` (2 and 8 days); `test_app::test_stale_framing_as_of_an_injected_time` | Exactly 7 days; latest succeeded run when a newer run is partial or failed; a non-UTC `--as-of`; a snapshot dated after the as-of time |

## Goals / Non-Goals

**Goals:**
- Close the gaps above with tests, pinning implicit boundaries in the specs.
- Run one end-to-end known-answer chain over three dated snapshots.
- Add property-based tests of the calculation invariants.
- Set coverage minimums that the gate and CI enforce.
- Fix the two small defects found, plus any bug D7 allows.
- Leave a traceability record for Phase 7's methodology document.

**Non-Goals:** as in the proposal.

## Decisions

| # | Decision | Who / basis |
|---|---|---|
| D1 | Scope: audit the four areas against the specs, write tests for every unpinned scenario and the edge cases in the gap audit, set the coverage threshold (D3), and add one end-to-end known-answer test (D17). Non-goals as in the proposal | **owner** (Scope) |
| D2 | Traceability record: a table in `docs/reviews/<date>-phase-6-tests.md`. Each row maps an area to its spec requirement or scenario and the test names, followed by the gaps closed and coverage before and after. No pytest markers, generator or `docs/testing.md`. Phase 7's methodology document cites it | **owner** (Scope) |
| D3 | Coverage threshold:<br>- **Total:** `[tool.coverage.report]` `fail_under = 99.0` with `precision = 1`, added once the gap tests land. If the final total is below 99.0, it is 98.0 and the change is recorded in the tasks.<br>- **Exclusion:** only `exclude_also = ['if __name__ == .__main__.:']`. No `# pragma: no cover`; the Streamlit code gets AppTest tests.<br>- **Core modules:** a gate step after pytest, `coverage report --include=<core modules> --fail-under=100`, over the same data. The core modules are `azure_retail`, `normalize`, `checks`, `gpu_map`, `rules`, `groups`, `history`, `quality`, `calculator`, `scenarios` and `workload_check`.<br>CI runs the gate, so it enforces both | **owner** (Scope, Value trade-off). Mechanism: fact (coverage 7.16.2 `results.py` `should_fail_under`; pytest-cov 7.1.0 `plugin.py`) |
| D4 | Hypothesis, a locked dev-only dependency, checks these properties:<br>- the calculator and `workload_check` agree on generated valid workloads, custom changes and budgets;<br>- cost is linear in GPUs and hours;<br>- exposure = scenario cost − base cost, with its sign following the change;<br>- `classify_azure`'s USD/GPU-hour × GPU count gives back the price;<br>- `groups.lowest` and `groups.stats` don't depend on row order.<br>The 400-price sweep stays | **owner** (Value trade-off) |
| D5 | No mutation testing in Phase 6; it is first on the cut list. If the owner wants a figure later: one cosmic-ray run on `calculator.py` and `workload_check.py` in a throwaway worktree, recorded in a review, adding no dependency or gate step | **owner** (Value trade-off, Authority) |
| D6 | Timebox: one session of about 3 h.<br>**Cut in this order:**<br>1. extras;<br>2. Hypothesis properties beyond calculator–check agreement and the multiply-back;<br>3. the `app.py` error-state tests (`fail_under` then becomes 98.0);<br>4. the end-to-end test, reduced to its stale and absence part.<br>**Never cut:**<br>- the threshold in the gate and CI;<br>- the 7-day boundary, not-listed, unit-rule and missing-field tests;<br>- the independent checks' failure branches;<br>- the traceability table;<br>- counts-only output | **owner** (Scope, Value trade-off, Private knowledge) |
| D7 | Bugs found while testing:<br>- **Inside the four areas:** fixed in this phase, in a `fix:` commit carrying the test that found it, with a delta spec when specified behaviour changes.<br>- **Frozen versions and definitions:** anything that would change `groups-v1`, `gpu-map-v1` or `scenarios-v1`, or a methodology definition (7-day stale, 2 absences, labels), goes to HANDOFF for an owner call and a new version. It is never edited in place.<br>- **Outside the four areas:** to HANDOFF, unless it takes a line or two in code this phase already touches.<br>- **Figures:** market review applies if a fix changes any price, cost or exposure figure | **owner** (Scope) |
| D8 | Another live snapshot is optional and the owner's choice, and not needed for acceptance. If the owner runs one collect plus normalize (at least 24 h after the last, at most one a day), the live regression (D12) adds counts-only changes and absent-once counts | **owner** (Gate, Private knowledge) |
| D9 | The synthetic command reads and checks every file before it opens the database. A refused file leaves no new database file and writes nothing, and the message says "refused" once. A test pins it (ADDED in `synthetic-marketplace`) | **owner** (Scope) |
| D10 | A snapshot dated after the as-of time is not stale and gets no new flag. A test pins today's behaviour (MODIFIED `data-quality`) | **owner** (Methodology) |
| D11 | Hypothesis settings:<br>- `tests/conftest.py` registers a `gate` profile (`derandomize=True`, `database=None`, `deadline=None`, `max_examples=200`, `print_blob=True`) and loads it unless `HYPOTHESIS_PROFILE` names another.<br>- An `explore` profile (random, `database=None`, more examples) is run by hand outside the gate.<br>- `.hypothesis/` is added to `.gitignore`. Hypothesis can still write a cache there | default and fact. Loading one profile everywhere stops Hypothesis switching to its `ci` profile under GitHub's `CI` variable, so local and CI runs stay the same. `database=None` keeps the tree clean (`dev-environment` "Clean tree after running the gate"). A deadline flakes on Windows timing. Source: Hypothesis docs (Context7, 2026-10-13) |
| D12 | Live regression: a one-off scratch script, not committed, on a read-only connection to `data/monitor.duckdb`. It runs:<br>- `checks.run`;<br>- the quality report counts;<br>- every live region-group member through the calculator and `workload_check`, as in Phase 5;<br>- the D4 properties over live starting prices.<br>Only pass/fail and counts are recorded in the review | recorded. The live-data gate allows "local storage and analysis only" (PROJECT.md §6). Method from `docs/reviews/2026-10-13-phase-5-calculator.md` |
| D13 | Specs: delta specs on the existing capabilities and no new capability:<br>- `quality-gate`: MODIFIED "Checks the gate runs" and "Tests run without network access";<br>- `dev-environment`: MODIFIED "Locked Python dependencies";<br>- `data-quality`: MODIFIED "Quality report" and "Quality command";<br>- `snapshot-history`: MODIFIED "Price changes" and "Absences and not listed";<br>- `price-normalization`: MODIFIED "Every observation normalized or excluded";<br>- `synthetic-marketplace`: ADDED "Synthetic command checks every file first".<br>Each MODIFIED block repeats every existing scenario | recorded (Phase 1 design: "each later phase's grilling turns its row into delta specs"; Phase 4 D22) and default |
| D14 | The `quality-gate` network exception names the dashboard AppTest module (`tests/unit/test_app.py`) beside the smoke test. Both may connect to 127.0.0.1 only | recorded (Phase 4 D19; `tests/unit/test_app.py:30`) |
| D15 | Two small fixes:<br>- the quality command converts `--as-of` to UTC before building and printing;<br>- the synthetic command's refusal reads "refused: <file>: <reason>" | recorded. Times are shown in UTC (Phase 4 D9), and the doubled prefix is a defect (D7) |
| D16 | Branch and change `phase-6-tests`; draft PR "Phase 6: Tests for units, calculations, missing data and stale offers". It is a code PR, so it gets `/code-review`. No diagram update | recorded (WORKFLOW.md § Pull requests; PROJECT.md §4: diagrams change with components, data flow or schema) |
| D17 | End-to-end test:<br>- **Fixtures:** three synthetic Azure-shaped files in `tests/fixtures/synthetic/azure_history/`, `snapshot-1.json` to `snapshot-3.json`, observed one week apart. They use mapped, unretired sizes from the demo (H100 ×8 `Standard_ND96isr_H100_v5`, T4 `Standard_NC4as_T4_v3`), and every price is invented. They cover a price change between snapshots 2 and 3; a listing absent from 3 only ("absent once"); one absent from 2 and 3 ("not listed", dated at snapshot 2); one absent from 2 and back in 3 at a new price (neither absent nor a change); and a non-hourly unit.<br>- **Test:** `tests/e2e/test_known_answers.py` ingests them with `synthetic.ingest_file` into a temporary database, then runs normalize, `checks.run`, `quality.build`, `groups.region_groups`, `history`, `calculator.calculate` and `workload_check.check`.<br>- **Answers:** asserted against the hand-worked answers in the fixtures README: counts, USD/GPU-hour, a 32-GPU × 720 h cost, every `scenarios-v1` exposure, and the stale flag at as-of +2 days, exactly +7 days and +7 days + 1 s | default. Synthetic data only (PROJECT §2, Phase 1 D4) |
| D18 | Property tests live in `tests/unit/test_properties.py`; the gap tests go into the existing module for each code module | default |
| D19 | Dependency: `hypothesis>=6.169` in the dev group. The `DEV` set in `tests/repo/test_dependencies.py` and the `dev-environment` requirement list it. `uv audit` runs before the PR is marked ready | default. Precedent: detect-secrets, Phase 2 D16 |
| D20 | The live regression stays a scratch script, not `scripts/`. A committed script would become an interface to maintain, and the Phase 5 method was a scratch script too | default. Changes if Phase 7 needs repeatable live checks |
| D21 | Evidence:<br>- the gate green with both coverage steps, and CI green on the branch;<br>- `uv audit` clean;<br>- the review record with the traceability table, coverage before and after, and the live regression's counts;<br>- the market-review read-through, if a figure changes (D7);<br>- `/code-review` findings resolved | recorded (Phase 1 acceptance row; WORKFLOW.md) |
| D22 | The archive commit marks Phase 6 Done in PROJECT.md §6, and §4 points to these decisions | recorded (WORKFLOW.md § Phase loop step 6) |

### Figures shown

None new. Phase 6 adds tests and two fixes. It changes no price, cost or exposure figure, and no
group key, unit or exclusion text.

### Non-negotiables check

| PROJECT.md §5 rule or §6 gate | How this design keeps it |
|---|---|
| Secrets never printed or committed | No secrets are involved |
| Never fabricate; label results; preserve failed runs | The new fixtures are labelled synthetic, with invented prices and hand-worked answers (D17). The live regression records only what it ran: pass/fail and counts (D12). Failures stay in the review |
| Operator resolves ⛔ gates | No gate is satisfied or waived. Another live snapshot is the owner's choice (D8) |
| Call the data published Azure list prices; label exposure as a scenario calculation | No wording changes. The end-to-end test asserts the existing labels on its figures |
| Deterministic code computes every figure | Unchanged. The tests strengthen the independent checks (D4, D17) |
| Compare only within comparable groups; state exclusions | Unchanged. Order-independence tests pin the group rules (D4) |
| Collector only reads published prices | No network code. Tests stay offline under pytest-socket |
| Within terms; missing stays missing | Tests pin "not listed", reappearance, a missing summary and "not computed". Nothing is filled in. Live figures stay on this PC (D12) |
| ⛔ live data | Honoured: no new reads by the agent. The regression is local analysis of stored rows |
| ⛔ scheduling / spend / publishing | Not acted on |

No exception to any rule is needed.

## Risks / Trade-offs

- [A 99.0% minimum makes later code harder to land] → Each new line needs a test or the
  `__main__` exclusion. Phase 7 adds little Python. The fallback is 98.0 (D3), and either way the
  value is recorded.
- [100% on the core modules can push toward tests of trivial branches] → Coverage only says a
  line ran, so the gap tests assert known answers rather than just running lines. The traceability
  table names each test's requirement.
- [Generated examples could make the gate flaky] → One derandomized profile with no deadline and
  no database (D11). `print_blob` makes any failure reproducible.
- [A property test could share a wrong assumption with the code] → Properties are stated from the
  specs (linearity, multiply-back, the sign of a change). The known-answer and end-to-end tests
  stay the primary evidence.
- [Checking files before opening the database changes the command's behaviour] → A file refused
  after earlier ones were stored used to leave them stored. Now a file-level refusal writes
  nothing at all. A database-level refusal (a run already stored) still comes from the database,
  after the file checks pass.
- [Fixture dates sit in the past] → Tests inject their as-of times. Snapshot-relative times keep
  the stale boundary exact.

## Migration Plan

New tests and fixtures, two small fixes, a dev dependency and gate settings. No schema change, and
nothing is written to `data/monitor.duckdb`. To roll back, revert the merge commit.

## Open Questions

None. Every grilling question is owner-answered (D1–D10) or settled with its basis (D11–D22).
