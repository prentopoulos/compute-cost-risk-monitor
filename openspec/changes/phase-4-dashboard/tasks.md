## 1. Foundations

- [x] 1.1 Add `read_only` to `db.connect` (UTC kept, no folder created when read-only). Test that a read-only connection cannot write, that a missing file is refused and not created, and that closing it lets a writer open the file
- [x] 1.2 Extend `groups.py`: `Member` gains published price, currency, price unit, run ID, raw-response file path, sequence number and SHA-256 from the existing `_ROWS` join. Add the MODIFIED "Region groups" known-answer test (7.0 USD per "1 Hour", 2 GPUs → 3.5, with its response's provenance)
- [x] 1.3 Commit `.streamlit/config.toml` (`gatherUsageStats = false`, `address = "127.0.0.1"`, `toolbarMode = "viewer"`) with a test that parses it. Declare `altair>=6.3,<7` as a direct dependency and relock without changing installed versions, with a test that the declared dependencies match the MODIFIED `dev-environment` requirement (D30). Reword the `__init__.py` docstring (D27)

## 2. Synthetic Azure demo data

- [x] 2.1 Share the Azure page classification (scope, rejection, repeats, flags, tallies) and row writing from `ingest.py` so a second caller can use them, with existing ingest tests unchanged and passing
- [x] 2.2 Add the synthetic Azure snapshot loader to `synthetic.py`: refuse unlabelled files, a missing or zone-less `observed_at` and empty `Items`; store one `azure-retail` run labelled `synthetic` in one transaction with the file's SHA-256 and a `file:` request URL; tell file kinds apart by shape in the existing command; keep refusing `data/monitor.duckdb`. Test the refusals, the stored run, a non-primary item rejected, and a re-ingest refused
- [x] 2.3 Write `tests/fixtures/synthetic/azure_demo.json` (invented round prices, real size names) and update the fixtures README. Test that, ingested and normalized, it has a multi-size group, a single-price group, a thin and a non-thin summary, a Spot row equal to pay-as-you-go, an `unmapped_sku` row and a `windows` row

## 3. View model

- [x] 3.1 Write `dashboard.py` dataset resolution and states: existing databases only, live default, overridable paths; no database, no rule set, no snapshot, `NOT NORMALIZED`, database in use; mixed-label detection. Unit-test each state
- [x] 3.2 Add cascading filter options (variant → GPU count → rental type → region, existing groups only, natural order) and the group browser frame (keys, member counts, labels, no prices, sorted by key). Unit-test both
- [x] 3.3 Add the region-group, cross-region and marketplace frames, the caption helper, the framing line (live, recorded, synthetic, stale) and display formats (4 decimals, full published precision, UTC). Unit-test captions on every frame and the known-answer summary (1, 2, 3, 4, 10)
- [x] 3.4 Add the cross-region chart spec (Altair points plus min, median and max rules, no line). Test the point count, rule values, missing regions absent and no line mark
- [x] 3.5 Add the data-quality panel model from `quality.build` (D25 mapping, secondary counts, "no snapshot"). Test that it matches the report on the demo dataset

## 4. Streamlit app

- [x] 4.1 Write `app.py`: `main(paths, as_of)`, sidebar dataset, source and filters, title and framing line, the three tabs (D28), a read-only connection per page run closed in `finally`, and no caching
- [x] 4.2 Write AppTest flows (marked `allow_hosts(["127.0.0.1"])`) on synthetic file databases with a fixed as-of time: dataset choice and default, filter cascade, region-group view and Source records, cross-region view, marketplace view with a duplicate, group browser, quality panel, every database state, mixed-label warning, stale framing, and a writer opening the file after a run. Add one `AppTest.from_file` run of `app.py`

## 5. Verification, review and documents

- [x] 5.1 Manual check: launch the dashboard locally on `data/synthetic.duckdb` (demo Azure data plus the marketplace snapshots) and on `data/monitor.duckdb`; confirm the flows, labels and local-only bind; record results as counts, keys and pass or fail only. Take PR screenshots from synthetic data only
- [x] 5.2 Update the FigJam container view (dashboard built, calculator planned) and re-export `docs/architecture/c4-container.svg`
- [x] 5.3 Run the market-review read-through of what the dashboard shows (keys, units, labels, exclusions, thin and single-price flags, no cross-group ranking) and the build-safety check (telemetry, network exposure, read-only access, CSV reading), and record them in `docs/reviews/`
- [x] 5.4 Run the gate green and `uv audit`, then record the output
- [ ] 5.5 Update PROJECT.md (§4 decisions pointer, §6 Phase 4 status) and HANDOFF.md with the checkpoint, evidence, limitations and the next task
