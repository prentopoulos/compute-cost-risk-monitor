## 1. GPU size map and frozen rules

- [x] 1.1 Build `reference/gpu_sku_map_v1.csv` and `reference/README.md` from Microsoft Learn size pages, under the strict exact-name rule (D9). Every row needs its URL and retrieval date, labels follow D3, and the CC BY 4.0 credit is included. Re-check retirement dates and URLs on Learn
- [x] 1.2 Write `gpu_map.py`: load and validate the CSV (columns, duplicates, Learn URLs, counts and memory, fractions, label form), and insert-or-refuse into `gpu_sku_map`. Test valid, fractional and invalid maps
- [x] 1.3 Write `rules.py` with the `groups-v1` constant (design § Rule set) and insert-or-refuse into `rule_set`. Test first store, equal re-store and changed-parameter refusal
- [x] 1.4 Commit the map and rules before any live normalize (D2, D15)

## 2. Normalization and independent checks

- [x] 2.1 Write the pure Azure classifier in `normalize.py`: the D4 exclusion order, the D13 OS rule, D5 retirement by snapshot date, and USD/GPU-hour. Add known-answer tests for the normal, missing, stale, fractional, unmapped, Windows, government, retired, non-hourly and impossible cases
- [x] 2.2 Add the database step: one transaction that stores the rules and map, then writes one row for each observation lacking one, idempotently. Test rollback on error and a re-run that adds nothing
- [x] 2.3 Write `checks.py`, independent of `normalize.py` (D16). Test that it passes on fixtures and fails on a tampered price, a missing row, a wrong GPU count, a reason on a normalized row and broken totals
- [x] 2.4 Write the `normalize` command: `--db`, the repo-anchored default, the checks, counts-only output, exit codes 0, 1 (check failed) and 2 (frozen mismatch). Test that the output holds no fixture prices
- [x] 2.5 Assert that a non-primary item never reaches `normalized_price` (ingest rejects it as `not_primary_meter`)

## 3. Synthetic marketplace

- [x] 3.1 Add labelled synthetic snapshot files under `tests/fixtures/synthetic/marketplace/` (at least three consecutive snapshots), covering:
  - same-group machine duplicates;
  - a re-listing;
  - a thin group and a group of at least 5 machines;
  - unknown GPU names and VRAM mismatches;
  - a non-compared rental type;
  - a price change;
  - a listing absent once and one absent twice
- [x] 3.2 Write `synthetic.py`: refuse unlabelled files and duplicate offer IDs, and ingest each file as one `synthetic` run in one transaction, with the file's SHA-256, defaulting to `data/synthetic.duckdb` and refusing `data/monitor.duckdb`. Add the synthetic name map and marketplace normalization (`unmapped_gpu_name`)

## 4. Groups, history and quality

- [x] 4.1 Write `groups.py`:
  - snapshots: succeeded runs only;
  - region groups with `single list price`;
  - the cross-region summary (lowest per region, min, median and max, `thin` below 5, `crosses regions`);
  - marketplace groups (one price per machine, `machine_duplicate`, `thin` below 5 machines, `synthetic`).

  Add known-answer tests, including the even-count median and tie-breaks
- [x] 4.2 Write `history.py`: consecutive-snapshot changes (item key, or continuity key for the marketplace), `absent once (unconfirmed)`, `not listed` after two absences, reappearance, and re-keyed meters. Test on the synthetic snapshots and on multi-snapshot Azure fixtures
- [x] 4.3 Write `quality.py`: the counts-only report per source as of an injected time, with the stale flag, reasons, unmapped names, run-record counts, duplicates, missing fields, `os_ambiguous`, single-price and thin counts, history counts, and "no snapshot". Test fresh, stale, reconciling and no-snapshot cases

## 5. Live normalize, review and documents

- [x] 5.1 Run `normalize` on the local `data/monitor.duckdb`. Record counts by reason, mapped coverage and check results, without prices, and confirm the counts against an independent query
- [x] 5.2 Update the FigJam container view (normalization built, synthetic database) and re-export `docs/architecture/c4-container.svg`
- [x] 5.3 Run the market-review read-through of the normalized live rows and groups (units, keys, exclusions, labels, thin and single-price flags) and the build-safety check, and record them in `docs/reviews/`
- [x] 5.4 Run the gate green and `uv audit`, then record the output
- [x] 5.5 Update HANDOFF.md with the checkpoint, the corrected counts, evidence, limitations and the next task
