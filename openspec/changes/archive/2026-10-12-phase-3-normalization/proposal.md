## Why

PROJECT.md Phase 3: normalization to USD/GPU-hour, comparable-group mapping, duplicate handling
and quality checks. Phase 2 stores published Azure list prices per VM-hour, with no GPU
fields: the Retail Prices API has none. Until each size is mapped to its GPUs and each price is
sorted into a comparable group or excluded with a reason, nothing can be compared, and Phases
4, 5 and 7 have no figures to show.

The Phase 3 grilling (2026-10-12, one round) settled the methodology. The owner accepted every
recommendation. Design D1–D11 are owner decisions, and D12 onwards are settled with their basis.

## What Changes

- **GPU size map, version `gpu-map-v1`.** A hand-built CSV in the package, built only from
  Microsoft Learn VM size pages (CC BY 4.0, credited), with a source URL on every row. A size is
  mapped only when its exact `armSkuName` appears on the cited page. Unmapped sizes are flagged
  and counted, never dropped.
- **Rule set `groups-v1`.** Frozen parameters committed before any live result is computed:
  - compared rental types;
  - the exclusion reasons and their order;
  - government-cloud regions;
  - retirement dates with their Learn URLs;
  - stale and thin thresholds;
  - the D13 cost-exclusions text;
  - the map version.
- **Normalization.** Every price observation gets exactly one `normalized_price` row under
  `groups-v1`:
  - Compared rows get USD/GPU-hour = price ÷ GPU count, with GPU variant and count.
  - Every other row is excluded with the first reason that matches.
  - Compared means Linux pay-as-you-go or Spot, in a commercial-cloud region, for a mapped,
    whole-GPU, unretired size priced per hour.
- **Comparable groups.** Region groups (GPU variant, GPU count, region, rental type) per
  snapshot, with every member size listed and "single list price" when only one price exists.
  Cross-region summaries take the lowest listed size per region and report the region count,
  min, median and max, marked thin below 5 regions.
- **Snapshot history.** Price changes between consecutive succeeded snapshots. A size counts as
  "not listed" only after two consecutive succeeded snapshots without it; a single absence is
  "absent once (unconfirmed)".
- **Synthetic marketplace data.** Labelled synthetic snapshot files are ingested as `synthetic`
  runs into their own database file. The rules for machine-level duplicates, re-listing and thin
  samples (fewer than 5 distinct machines) are exercised on them.
- **Quality report.** Per source and latest snapshot, a counts-only report:
  - stale flag;
  - observations, normalized rows, and exclusions by reason;
  - unmapped sizes;
  - rejected, out-of-scope and repeated rows;
  - duplicates;
  - single-price and thin groups;
  - absences, delistings and changes.
- **Independent checks.** A checker that shares no code with normalization re-derives from
  stored rows:
  - USD/GPU-hour × GPU count reproduces the price;
  - one row per observation and rule version;
  - every excluded row has a reason;
  - the totals reconcile.
- **Command.** `uv run python -m compute_cost_risk_monitor.normalize` is idempotent, runs in one
  transaction, refuses changed frozen rules or map rows, runs the checks, and prints counts only.
- **Documents.** PROJECT.md §2, §3 and §4 record the decisions. HANDOFF.md is corrected and
  updated. The FigJam container view marks normalization as built and adds the synthetic
  database, with the SVGs re-exported.

## Non-goals

- No dashboard, calculator, cost or exposure scenarios (Phases 4–5).
- No new network code. Only the Azure adapter touches the network, and Phase 3 adds no
  scraper for Microsoft Learn: the map is hand-built.
- No schema change (owner, D10). No new tables or views, and schema 001–002 are unchanged.
- No new live run is required. A second owner-started run is optional (D11).
- No second source, scheduling, spending or publishing. No prices, USD/GPU-hour figures,
  statistics or rankings in Git, the PR or reviews.
- No aliases or inferred mappings for sizes Learn does not name exactly (D9). No fractional-GPU
  comparisons (Phase 1 D12).
- No trend claims. One live snapshot exists.
- No change to the constitution (PROJECT.md §5–6).

## Capabilities

### New Capabilities

- `price-normalization`: the GPU size map, the frozen rule set, sorting each observation into
  normalized or excluded, USD/GPU-hour, the normalize command and the independent checks.
- `comparable-groups`: region groups, cross-region summaries and synthetic marketplace groups,
  with single-price, thin and machine-duplicate labels.
- `snapshot-history`: snapshots, price changes, absences, "not listed" and re-listing
  continuity.
- `data-quality`: the counts-only quality report per source and snapshot, including the stale
  flag.
- `synthetic-marketplace`: ingesting labelled synthetic marketplace snapshot files as
  `synthetic` runs.

### Modified Capabilities

None. The stored data model (`price-data-schema`) already holds the map, the rule sets and the
derived rows, and its requirements do not change.

## Impact

- New:
  - Package code: `src/compute_cost_risk_monitor/` modules for the GPU map, rules,
    normalization, groups, history, quality, checks, synthetic marketplace ingest and the
    normalize command.
  - Map data: `src/compute_cost_risk_monitor/reference/gpu_sku_map_v1.csv`.
  - Tests: `tests/unit/` tests, plus synthetic multi-snapshot fixtures under
    `tests/fixtures/synthetic/`.
- Edited:
  - PROJECT.md §2–4 and §6 (Phase 3 status), and HANDOFF.md.
  - The FigJam board and `docs/architecture/c4-container.svg`.
- Local data:
  - The first normalize writes the `groups-v1` and `gpu-map-v1` rows into
    `data/monitor.duckdb` permanently, since DuckDB cannot update referenced rows. Later
    changes are new versions.
  - Synthetic runs go to `data/synthetic.duckdb`.
- Dependencies: none added.
- ⛔ gates: none acted on.
  - The live-data gate scope is honoured: no new reads, and any further run is owner-started,
    at most one a day.
  - Scheduling, spend and publishing are untouched.
- Constitution: no amendment.
