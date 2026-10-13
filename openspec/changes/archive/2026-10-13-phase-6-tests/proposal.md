## Why

PROJECT.md Phase 6: tests for units, calculations, missing data and stale offers. Phase 1's
acceptance row asks this phase to close the gaps in those four areas and set the coverage
threshold deferred in Phase 0, with the gate and CI green at that threshold.

Phases 2–5 test each stage well on its own: 649 tests, 98.4% branch coverage on main at
a79f0e0. A spec-by-spec audit (design § Context) found the gaps:
- Azure history and staleness are tested only on runs written straight into the tables, never
  through the real row rules.
- No test chains several snapshots from ingest to the calculator.
- Some boundaries are unpinned: a snapshot exactly 7 days old, "not listed" after three or more
  absences, the exact "1 Hour" unit match, and exclusion order past the first reason.
- Some failure branches of the independent checks are untested, and so are some dashboard error
  states.

The Phase 6 grilling ran one round on 2026-10-13, and the owner accepted every recommendation
("All recommended"). Design D1–D10 are owner decisions; D11 onwards are settled with their basis.

## What Changes

- **Gap tests in the four areas.** These are pinned with known answers:
  - units: the exact unit match, exclusion order past the first reason;
  - calculations: the independent checks' untested failure branches, results that don't depend
    on row order;
  - missing data: "not listed" after three or more absences, a reappearance at a new price, a
    run with no summary, the dashboard's untested error states, synthetic rollback paths;
  - stale: exactly 7 days, the latest succeeded run when a newer run is partial or failed, a
    non-UTC as-of time, a snapshot dated after the as-of time.
- **One end-to-end known-answer test.** Three dated synthetic Azure-shaped snapshots go through
  the live row rules, normalize, the independent checks, the quality report, groups, history,
  the calculator and the workload check. Every expected number is worked out by hand in the
  fixtures README. Together they cover:
  - fresh, exactly 7 days and stale as-of times;
  - a price change, "absent once" and "not listed";
  - a workload cost and its exposure.
- **Property-based tests** with Hypothesis, a new dev-only dependency, under one fixed profile
  that runs the same locally and in CI. They check:
  - the calculator and the independent check agree;
  - cost is linear in GPUs and hours;
  - exposure has the right sign and scale;
  - USD/GPU-hour × GPUs gives back the VM price;
  - the lowest listed member and the statistics don't depend on row order.

  The existing 400-price sweep stays.
- **Coverage threshold.** Total branch coverage must be at least 99.0%. A second gate step
  requires 100% on the eleven calculation and data modules. The only exclusion is
  `if __name__ == "__main__":`. CI enforces both through the gate.
- **Fixes:**
  - The synthetic command checks every file before it opens the database, so a refused file
    leaves no empty database behind, and its message says "refused" once.
  - The quality command prints its as-of time in UTC.
  - Found during implementation (D7):
    - a run without a summary row reports its counts as unknown, not 0;
    - hours and budgets below 0.01 are refused, because their headroom could overflow or
      underflow (D23).
- **Traceability record.** The review record maps each area to its spec requirements and the
  tests that cover them, with the gaps closed and coverage before and after.
- **Live regression, counts only.** A one-off scratch script runs over the local live snapshot.
  Only pass/fail and counts are recorded.
- **Documents.** PROJECT.md §4 points to the decisions, and §6 marks Phase 6. The quality-gate
  spec's network exception is brought in line with Phase 4 D19. HANDOFF.md is updated.

## Non-goals

- No new features and no UI changes, except the fixes above and any bug fix D7 allows.
- No live reads by the agent. Another live snapshot is optional and the owner's choice (D8).
- No new `groups`, `gpu-map` or `scenarios` version, and no change to a methodology definition:
  7-day stale, 2 absences, labels. A bug that needs one goes to HANDOFF for an owner call.
- No schema migration and no new runtime dependency.
- No mutation testing (D5).
- No Phase 7 items: demo dataset, branding, scenario rename, methodology document, market brief.
- No diagram changes: no component, data flow or schema changes.
- No hosting, publishing, scheduling or spending. No live figure in Git, the PR or reviews.
- No change to the constitution (PROJECT.md §5–6).

## Capabilities

### New Capabilities

None. Test traceability is evidence in the review record, not product behaviour.

### Modified Capabilities

- `quality-gate`:
  - MODIFIED "Checks the gate runs": a total coverage minimum, plus a 100% step for the core
    modules.
  - MODIFIED "Tests run without network access": the dashboard AppTest module joins the smoke
    test as a loopback-only exception (Phase 4 D19).
- `dev-environment`: MODIFIED "Locked Python dependencies": Hypothesis joins the dev group.
- `data-quality`:
  - MODIFIED "Quality report": exactly 7 days is not stale; staleness comes from the latest
    succeeded run; a snapshot dated after the as-of time is not stale.
  - MODIFIED "Quality command": the as-of time is printed in UTC.
- `snapshot-history`:
  - MODIFIED "Price changes": a listing that comes back at a new price after an absence is not a
    change.
  - MODIFIED "Absences and not listed": still `not listed`, dated at the first absence, after
    three absences.
- `price-normalization`: MODIFIED "Every observation normalized or excluded": the unit must be
  exactly `1 Hour`, and the first reason wins when later reasons also match.
- `synthetic-marketplace`: ADDED "Synthetic command checks every file first".
- `workload-calculator`: MODIFIED "Workload inputs" and "Budget headroom". Hours and budget must
  be at least 0.01, a fix found by the property tests (design D23).

## Impact

- New:
  - `tests/conftest.py`, holding the Hypothesis profiles;
  - property tests;
  - the end-to-end test and its three fixture files;
  - gap tests across the existing test modules;
  - `docs/reviews/<date>-phase-6-tests.md`.
- Edited:
  - `src/compute_cost_risk_monitor/synthetic.py` (files checked before the database) and
    `quality.py` (as-of time in UTC);
  - `scripts/gate.py` (the core-module coverage step) and `pyproject.toml` (coverage report
    settings, Hypothesis);
  - `uv.lock`, `.gitignore` (`.hypothesis/`) and `tests/repo/test_dependencies.py`;
  - `tests/fixtures/synthetic/README.md`;
  - PROJECT.md §4 and §6, and HANDOFF.md.
- Dependencies: Hypothesis (dev only, MPL-2.0) and its one dependency, sortedcontainers.
  `uv audit` runs before the PR is marked ready.
- Local data: nothing is written to `data/monitor.duckdb`. The live regression opens it
  read-only.
- ⛔ gates:
  - Live data: honoured. The agent makes no new reads, and the regression is local analysis only.
  - Scheduling, spend and publishing: untouched.
- Constitution: no amendment.
