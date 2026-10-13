## 1. Fixes and tooling

- [x] 1.1 Make the synthetic command read and check every file (label, time, shape, offers or Azure row rules) before it opens the database, and say "refused" once (D9, D15; ADDED `synthetic-marketplace` requirement). Tests: a refused file with a new database path leaves no file and stores no earlier valid file; a refused file leaves an existing database's runs unchanged; the message wording; the rollback paths and the open refusal in `synthetic.py`
- [x] 1.2 Convert the quality command's `--as-of` to UTC before building and printing (D15; MODIFIED "Quality command"). Test with a `-04:00` offset: the printed time and the stale judgement
- [x] 1.3 Add Hypothesis as a dev dependency (D11, D19): `pyproject.toml`, `uv.lock`, the `DEV` set in `tests/repo/test_dependencies.py`, `tests/conftest.py` with the `gate` and `explore` profiles, and `.hypothesis/` in `.gitignore`. Test that the `gate` profile is loaded when `CI` is set

## 2. Gap tests in the four areas

- [x] 2.1 Units: unit `1 Hour` against `1 hour`, `1 Hours` and `100 Hours`; a Windows row with a non-hourly unit excluded as `windows` (MODIFIED "Every observation normalized or excluded")
- [x] 2.2 Calculations: the untested failure branches of `checks.py` (a row with neither reason nor price, a normalized row without a GPU variant; both blocked by the schema's CHECKs, so tested on a copy without them) and `workload_check.py` (a missing expected figure, and the lines at 180 and 200), each by tampering with a correct result
- [x] 2.3 Missing data:
  - history: still `not listed` after three absences, dated at the first; a return at a new price is not a change, through `quality.build` (MODIFIED `snapshot-history`);
  - a run without a summary row;
  - the `app.py` states at 94, 221, 272–273, 287, 319–321 and 327–329;
  - the remaining uncovered lines in `collect.py`, `db.py`, `dashboard.py`, `ingest.py`, `normalize.py` and `raw_store.py`, each with a known answer
- [x] 2.4 Stale: exactly 7 days not stale and 7 days + 1 s stale; staleness from the latest succeeded run when the newest run is partial or failed; a snapshot dated after the as-of time is not stale (D10; MODIFIED "Quality report")

## 3. Property tests

- [x] 3.1 Write `tests/unit/test_properties.py` (D4), first the never-cut pair:
  - the calculator and `workload_check` agree on generated valid workloads, custom changes and budgets;
  - `classify_azure`'s USD/GPU-hour × GPU count gives back the price.
- [x] 3.2 Add the rest:
  - cost is linear in GPUs and hours;
  - exposure = scenario cost − base cost, with its sign following the change;
  - `groups.lowest` and `groups.stats` don't depend on row order.

## 4. End-to-end known-answer test

- [x] 4.1 Write `tests/fixtures/synthetic/azure_history/snapshot-1.json` to `snapshot-3.json`, labelled synthetic with invented prices, one week apart. Work every expected answer by hand in the fixtures README (D17): counts by reason, USD/GPU-hour, the change, absent once, not listed, the return at a new price, the non-hourly unit, a 32-GPU × 720 h cost with every `scenarios-v1` exposure, and the stale flag at +2 days, exactly +7 days and +7 days + 1 s
- [x] 4.2 Write `tests/e2e/test_known_answers.py`: ingest with `synthetic.ingest_file`, normalize, `checks.run`, `quality.build`, `groups.region_groups`, `history`, `calculator.calculate` and `workload_check.check`, asserting the README's answers

## 5. Coverage threshold

- [x] 5.1 Add `[tool.coverage.report]` with `fail_under = 99.0`, `precision = 1` and `exclude_also` for the `__main__` guard. Add the core-module step to `scripts/gate.py`, `coverage report --include=<core modules> --fail-under=100` (D3; MODIFIED "Checks the gate runs"). Show that the step fails when a core-module line is not run. If the total is below 99.0, set 98.0 and record that here and in the review

## 6. Verification, review and documents

- [x] 6.1 Run the live regression as a scratch script on a read-only connection (D12): `checks.run`, the quality report counts, every live member through the calculator and `workload_check`, and the properties over live starting prices. Record counts and pass/fail only
- [x] 6.2 Write `docs/reviews/<date>-phase-6-tests.md` (D2, D21). It holds:
  - the traceability table (area → requirement or scenario → tests);
  - the gaps closed;
  - coverage before and after;
  - the live regression;
  - the build-safety read-through for the new dependency;
  - a market-review read-through if any figure changed
- [x] 6.3 Run the gate green with both coverage steps and `uv audit`, then record the output
- [ ] 6.4 Update PROJECT.md (§6 Phase 6 status) and HANDOFF.md with the checkpoint, evidence, limitations and the next task
- [x] 6.5 Run `/code-review` on the PR and resolve its findings with tests
