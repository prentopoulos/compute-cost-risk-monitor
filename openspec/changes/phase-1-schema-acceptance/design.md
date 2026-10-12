## Context

Phase 1 of PROJECT.md §6. Phase 0 delivered the toolchain, the gate and CI. No price data exists
and no provider has been called.

The Phase 1 grilling ran two rounds on 2026-10-11, with an informed-answerer subagent and the
main agent re-checking its sources. Round 1 found that Vast.ai's terms (version 2026-09-01)
forbid the core plan without a written agreement. Round 2 surveyed replacement sources and found
that no GPU marketplace qualifies. The Azure Retail Prices API does: its docs invite tools "for
internal analysis and price comparison across SKUs and regions". The owner answered every owner
call; the decision list below records who decided each item.

Measured facts this design relies on:
- DuckDB 1.5.6 returns TIMESTAMPTZ in the machine's zone (America/Toronto) unless the session
  zone is UTC.
- `fetchone()` on TIMESTAMPTZ needs `pytz`, which is not otherwise locked.
- The Azure Retail Prices API returns 1,000 rows per page with a `NextPageLink`.
- It has no GPU fields, so GPUs come from a SKU mapping.

## Goals / Non-Goals

**Goals:**
- A tested schema that later phases write to and read from, with constraints that enforce the
  market-review evidence rules at the storage boundary.
- Requirement-level acceptance criteria for Phases 2–7 (table below). Each later phase's
  grilling turns its row into that phase's own specs with scenarios.
- Three architecture diagrams that show what exists and what is planned.
- Project documents that say truthfully what the data is.

**Non-Goals:** as in the proposal.

## Decisions

| # | Decision | Who / basis |
|---|---|---|
| D1 | Phase 1 delivers an executable schema with tests, the Phase 2–7 acceptance table in this design (not delta specs: archiving would sync unbuilt behaviour into main specs) and three diagrams. Non-goals and evidence as in the proposal | **owner** (Scope, Conflict) |
| D2 | Timebox: one session, about 3 h. If it overruns, cut container-diagram detail, never the schema tests | **owner** |
| D3 | Raw responses: the exact response bytes, gzip, one file per request under `data/raw/<source>/YYYY/MM/DD/<run>-<seq>.json.gz`, written once before parsing. A SHA-256 of the uncompressed bytes and a sidecar `.meta.json`; the auth header is never recorded. Failed requests are recorded. Kept outside DuckDB | **owner** (One-way door) |
| D4 | No real source data in Git, not even trimmed fixtures, until terms and the publishing gate allow it. Tests use synthetic fixtures | **owner** (Gate, One-way door) |
| D5 | Diagrams: one FigJam file with a C4 context, a C4 container (built or planned marked) and an ERD. C4 is drawn as flowcharts in C4 notation, because Figma's tool does not support C4. The agent creates the file on the owner's Pro seat | **owner** (Showcase, Authority) |
| D6 | Instants are TIMESTAMPTZ. Every connection goes through `db.connect`, which sets `TimeZone=UTC`. `pytz` is a runtime dependency | **owner** (One-way door) |
| D7 | Provenance label per run: `synthetic`, `recorded` or `live`. Stale is a computed age flag | **owner** (Methodology) |
| D8 | Source: no Vast.ai, and no contact with any provider. The Azure Retail Prices API is the v1 source for collection, local storage and comparison. Publishing live Azure figures stays under the publishing gate | **owner** (Gate, Scope) |
| D9 | Framing: "published retail list prices for GPU VMs from one cloud provider, Azure". Never a marketplace, market price, benchmark, what customers pay, capacity, or cross-provider comparisons | **owner** (Scope, Methodology, Showcase) |
| D10 | Hybrid data: live Azure for local analysis in Phases 2–6. Labelled synthetic marketplace-style offers exercise duplicates, re-listing and thin samples, and are the public demo dataset unless the publishing gate approves live figures | **owner** (Scope, Value trade-off) |
| D11 | Rental types compared: pay-as-you-go (`on_demand`) and Spot, Linux only. Reservation, savings plan, dev/test, Windows and low-priority rows are stored but not compared | **owner** (Methodology) |
| D12 | Comparable-group key: GPU model and variant, GPU count, Azure region, rental type. GPU fields come from a versioned `gpu_sku_map` built from Microsoft Learn VM size pages (CC BY 4.0, credited; content in Phase 3). Fractional-GPU sizes are left out of v1 | **owner** (Methodology) |
| D13 | USD/GPU-hour = Azure `retailPrice` (USD per VM per "1 Hour") ÷ mapped GPU count. Exclusions stated with every figure: disks and storage, egress, public IPs, licences, taxes, negotiated discounts, reservations and savings plans, Spot eviction risk, capacity and quota | **owner** (Methodology) |
| D14 | Typed columns: the Azure price fields in `azure_retail_price`, plus derived GPU fields and mapping version (in `normalized_price` and `gpu_sku_map`) | **owner** (One-way door) |
| D15 | Duplicates: within a snapshot, (meterId, skuId, region, priceType, reservationTerm, tierMinimumUnits, currency) is unique, and repeats are flagged. Primary meters only. A change is the same key with a new price. A size missing from a snapshot is recorded as "not listed", never filled in | **owner** (Methodology) |
| D16 | Thresholds: stale when the latest snapshot is over 7 days old. A one-price group is labelled "single list price". A cross-region statistic needs ≥ 5 regions, otherwise it is "thin" | **owner** (Methodology) |
| D17 | 730 h per month for monthly figures (unverified on primary pages; stated with each use). Calculator hours stay a user input, and PROJECT's 32 × 720 × $0.50 example stands | **owner** (Methodology) |
| D18 | The owner's links are narrative only: ICE/Ornn and SF Compute in Phase 7; Silicon Data stays the methodology reference. The arXiv 2603.21690 model is not used for numbers; it only motivates a labelled "spike" scenario. PROJECT §1's futures sentence stays until trading is confirmed (CME's page still said "later this year, pending regulatory review" on 2026-10-12) | **owner** |
| D19 | `data/` is gitignored; the local database is `data/monitor.duckdb`; synthetic fixtures live under `tests/fixtures/synthetic/` | default |
| D20 | Diagram exports are SVG in `docs/architecture/` (`c4-context.svg`, `c4-container.svg`, `erd.svg`) | default |
| D21 | Versioning: `schema_version` with forward-only numbered SQL files and a small runner (no migration library); `rule_set` holds frozen parameters as JSON; runs record the git SHA, schema version and dependency versions; derived rows carry `rule_version` and are recomputed, keeping old versions | default. Sources: build-safety and market-review skills |
| D22 | Azure rows carry no personal data. Synthetic marketplace fixtures contain no host IPs or hostnames | default |
| D23 | Schema shape: a source-neutral core (`price_observation`) with per-source detail tables (`azure_retail_price`, `marketplace_offer`), so the hybrid plan (D10) uses one set of rules and checks. Enumerations are CHECK lists, so a migration can extend them | default. Two-way door while no live data exists |
| D24 | Vast.ai findings kept for reference: its rate limits, API key requirement and price fields (round 1). Not used | recorded |

## Schema (version 1)

```text
schema_version(version PK, applied_at, description)
collection_run(run_id PK, source, data_label, started_at, finished_at, status,
               code_version, schema_version, dependency_versions JSON, request_params JSON, notes)
raw_response(response_id PK, run_id → collection_run, seq, file_path, sha256, byte_length,
             request_url, http_status, requested_at, received_at, item_count, parse_status,
             error; UNIQUE(run_id, seq))
price_observation(source, item_key, retrieved_at  [PK], response_id → raw_response,
                  rental_type, region, price, currency, price_unit, gpu_model?, gpu_count?)
azure_retail_price(source, item_key, retrieved_at [PK, → price_observation], meter_id, sku_id,
                   arm_sku_name, arm_region_name, location, price_type, retail_price,
                   unit_price, unit_of_measure, effective_start_date, product_id,
                   product_name, sku_name, meter_name, service_name, service_family,
                   is_primary_meter_region, reservation_term, tier_minimum_units,
                   savings_plan JSON)
marketplace_offer(source, item_key, retrieved_at [PK, → price_observation], offer_id,
                  machine_id, gpu_name_listed, num_gpus, gpu_vram_gb, country_code)
gpu_sku_map(mapping_version, arm_sku_name [PK], gpu_model, gpu_form_factor, gpu_vram_gb,
            gpu_count, source_url, notes)
rule_set(rule_version PK, created_at, description, parameters JSON)
normalized_price(source, item_key, retrieved_at, rule_version [PK]; → price_observation,
                 → rule_set; usd_per_gpu_hour, gpu_model, gpu_count, region, rental_type,
                 mapping_version, exclusions, excluded_reason)
```

`?` marks a nullable field that stays NULL when unknown. A `price_observation.price` is the
source's price for the whole item: one VM-hour for Azure, one offer-hour for a marketplace.
USD/GPU-hour exists only in `normalized_price`.

## Acceptance criteria for Phases 2–7

Each later phase's grilling turns its row into delta specs with scenarios and may refine it.

| Phase | Requirement-level acceptance | Evidence (PROJECT §3) |
|---|---|---|
| 2 Collector | Only `GET https://prices.azure.com/api/retail/prices` with a fixed filter (Virtual Machines, USD, primary meters, GPU families), following `NextPageLink`. Pacing ≤ 1 request/s, back off on 429, bounded retries and timeout. Each response's exact bytes are saved (D3) before parsing. Rows go into `price_observation` and `azure_retail_price`, repeats are flagged and counted, and every run (including failed ones) records counts, status, versions and its label | Contract tests on synthetic pages shaped like the documented example. Network blocked in tests (pytest-socket). A secret scanner is added. One live run only after the operator resolves the live-data gate, labelled `live` |
| 3 Normalization and quality | `gpu_sku_map` v1 is built from Microsoft Learn (credited) and unmapped SKUs are flagged, not dropped. USD/GPU-hour = retail price ÷ GPU count, checked by multiplying back. `rule_set` `groups-v1` is frozen before looking at results (D11–D17). Synthetic marketplace fixtures exercise machine-level duplicates, re-listing and thin samples | Known-answer fixtures: normal, missing, stale, fractional, unmapped, Windows, non-primary and impossible cases. Market-review checks pass |
| 4 Dashboard | Streamlit filters by comparable group. Every figure shows its group key, snapshot time, exclusions and data label. A data-quality panel shows missing, duplicate, stale, thin and unmapped counts. Usage telemetry is off | AppTest flows on synthetic data, plus a local manual check |
| 5 Calculator and exposure | Cost = GPUs × hours × USD/GPU-hour, plus storage only when the user enters a storage cost, with exclusions shown. Exposure = GPUs × hours × scenario change, under labelled hypothetical scenarios including a decline and a spike. Never a forecast | 32 × 720 × $0.50 = $11,520 passes. Known-answer tests. BCBS stress-testing principles used as the scenario checklist |
| 6 Tests | Close the gaps in units, calculations, missing data and stale data. Set the coverage threshold deferred in Phase 0 | Gate and CI green with the threshold |
| 7 Demo and brief | The public dataset is synthetic unless the publishing gate approves derived live Azure figures. Methodology document, a market brief with every number linked to its records, a two-minute walkthrough, updated diagrams, and the futures sentence reframed | Market-review read-through; every brief number matches a computed value |

## Diagrams

All three live in one FigJam file on the owner's Pro seat, each titled with the date and schema
version:
- **System context:** the GPU buyer, the monitor and the Azure Retail Prices API, with the
  optional LLM brief drafter dashed as "deferred".
- **Container:** collector, raw-response files, DuckDB, the normalization and quality module,
  and the Streamlit dashboard and calculator, each marked built or planned.
- **ERD:** the schema above.

## Reading list (settled, fact)

For Phases 3, 5 and 7:
- Byrne, Corrado & Sichel, NBER WP 25188 (hedonic cloud price indexes)
- Agmon Ben-Yehuda et al., ACM TEAC 2013 (EC2 spot prices were provider-set)
- Kilcioglu & Rao, WWW 2016 (cloud prices differentiate rather than converge)
- BCBS d450 (2018) stress-testing principles
- Javadi, Thulasiram & Buyya, FGCS 2013 (low weight)

## Risks / Trade-offs

- [Azure's API terms limit redistribution] → the public demo uses synthetic data unless the
  publishing gate approves derived live figures (D8, D10).
- [Response shapes for GPU rows are unverified] → the detail table is nullable where the docs
  are silent, and Phase 2 confirms against a recorded page kept locally.
- [DuckDB foreign keys block updating or deleting referenced rows] → observations are
  immutable by design (D21), so this is acceptable.
- [`pytz` is a legacy library] → used only by DuckDB's conversion; project code uses
  `datetime.UTC`.

## Migration Plan

New files only, apart from documentation edits. To roll back, revert the merge commit. The
FigJam file can be deleted by the owner.

## Open Questions

None for Phase 1. The live-data gate (Azure terms and pacing confirmation) is the operator's
call before Phase 2's first live read.
