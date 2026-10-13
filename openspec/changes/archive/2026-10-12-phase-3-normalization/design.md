## Context

Phase 3 of PROJECT.md §6. Phase 2 delivered the collector and one live snapshot:
- Run `20261012T151909Z-5473f1`, succeeded, with 14,347 stored Azure observations, 100 GPU
  sizes and 60 regions.
- `gpu_sku_map`, `rule_set` and `normalized_price` exist (schema 001) but are empty.
- `price_observation.gpu_model` and `gpu_count` are NULL and cannot be updated, so GPU fields
  live only in `normalized_price`, joined to `gpu_sku_map`.

The Phase 3 grilling ran one round on 2026-10-12:
- An informed-answerer subagent researched 14 questions and found 4 more.
- The main agent re-checked the settled answers' sources:
  - the MicrosoftDocs LICENSE;
  - the RTX PRO 6000, NCv3, NVv3 and NVv4 size pages;
  - Learn's retirements page;
  - the Retail Prices API page;
  - local read-only counts.
- The owner accepted every recommendation ("All recommended").

Measured facts this design relies on (2026-10-12, local read-only queries, counts only):
- **Windows rows:** 7,878. `productName`'s last word is "Windows" on 7,858 rows and "Win" on
  20. 679 rows end in "Linux".
  - HANDOFF's earlier 8,014 counted raw rows containing "Windows", which includes out-of-scope
    NP/NM rows and misses "Win".
  - All 3,803 Dev/Test rows are Windows.
- **One row per size:** among Linux pay-as-you-go and Spot rows, each (`armSkuName`, region,
  rental type) holds exactly one row.
- **Uniform fields:** `unitPrice` = `retailPrice` on every row. `tierMinimumUnits` is 0, and
  every unit is "1 Hour".
- **RTX PRO 6000:** 29 sizes are present. Learn lists 9 of them (NC36/72/144/288ds,
  NC24/36/72/144/288lds; checked 2026-10-12).
- **Government regions:** `usgovarizona` and `usgovvirginia` hold 485 rows, 157 of them Linux
  pay-as-you-go or Spot. The Retail Prices API page says `armRegionName` "only supports prices
  on Commercial Cloud".
- **Retirements on Learn (checked 2026-10-12):**
  - NCv3, including NC24rs, retired 2025-09-30 (retirements page, updated 2026-09-27).
  - NVv3 and NVv4 retired 2026-09-30. Their series pages, updated 2026-10-02 and 2026-09-30,
    say "retired on September 30, 2026"; the retirements table still says "Announced".
  - NC and NV, including Promo, retired 2023-09-06 (per the answerer's sources; re-checked when
    the parameters are written).
- **The OS signal:** Microsoft's API examples tell Windows from Linux only by `productName`
  ("Virtual Machines FS Series Windows", "Virtual Machines NP Series"). The API has no OS field.
- **Licence:** MicrosoftDocs/azure-compute-docs is CC BY 4.0 (LICENSE, checked 2026-10-12).

## Goals / Non-Goals

**Goals:**
- Every stored price is accounted for exactly once: compared with a USD/GPU-hour and a
  comparable-group key, or excluded with a reason, and the counts reconcile with the run
  records.
- Rules and the map are frozen and committed before any live figure is computed, and are
  versioned so later changes never rewrite history.
- Group outputs, history and quality counts are deterministic functions that Phase 4 displays
  and Phase 7 cites, checked by code that shares nothing with the code that computed them.
- Marketplace-only rules (machine duplicates, re-listing, thin samples) are exercised on
  labelled synthetic data.

**Non-Goals:** as in the proposal.

## Decisions

| # | Decision | Who / basis |
|---|---|---|
| D1 | Scope: map, frozen rules, normalization, comparable groups, quality report, synthetic marketplace ingest and rules, **plus** price changes and "not listed" between snapshots (pure functions, tested on synthetic multi-snapshot fixtures). Non-goals as in the proposal | **owner** (Scope) |
| D2 | Timebox: one session of about 3 h. Cut in this order if it overruns: (1) diagram polish beyond marking normalization built; (2) changes and "not listed", moved to a follow-up; (3) cross-region statistics reduced to region count plus the thin flag; (4) the stored synthetic ingest reduced to in-memory tests. Never cut: a Learn URL on every map row; `groups-v1` committed before the first live normalize; exactly one `normalized_price` row per observation; the independent checker; the known-answer fixtures; counts-only output | **owner** (Scope, Value trade-off) |
| D3 | GPU variant = model + form factor + per-GPU memory, spelled as Learn spells it: `<model>[ <form factor>] <memory>GB`, with the form factor left out when Learn names none. Learn says "NVLink", never "SXM". Examples: "H100 NVL 94GB", "H100 NVLink 80GB", "A100 PCIe 80GB", "A100 NVLink 40GB", "A100 NVLink 80GB". The confidential size NCC40ads_H100_v5 is its own variant, "H100 NVL 94GB confidential". The full label goes in `gpu_model`; form factor and memory also go in their own map columns | **owner** (Methodology, Showcase) |
| D4 | Exclusion reasons, first match wins, in this order: `rental_type_not_compared` (anything but `on_demand` and `spot`) → `government_cloud` → `windows` → `unit_not_hourly` → `unmapped_sku` → `fractional_gpu` → `retired_size`. A row that matches none is normalized | **owner** (Methodology) |
| D5 | Retired sizes are excluded as `retired_size` when their Learn retirement date is on or before the snapshot's UTC start date. Dates and URLs are frozen in `groups-v1`. An older snapshot keeps a size that was live then | **owner** (Methodology) |
| D24 | Refinement of D5: where Learn gives a later retirement date for a named region, that region's date applies.<br>- NCv3: Jio India West until 2027-06-30, and US Gov Virginia and Arizona until 2026-12-31 (those two are excluded as `government_cloud` anyway).<br>- NVv3: UAE North until 2027-01-31.<br>In the live snapshot this keeps 10 Linux pay-as-you-go and Spot rows comparable that a series-wide date would exclude. Stored as `region_extensions` in `groups-v1` | main agent, found while writing the rules (Learn retirement pages ncv3-retirement and nvv3-series-retirement, retrieved 2026-10-12). **Flagged for owner review on the PR** |
| D6 | Phase 3 computes group outputs; Phase 4 only displays them.<br>- Region group (variant, GPU count, region, rental type, snapshot): every member size with its USD/GPU-hour, the member count, and the label "single list price" when it holds one observation.<br>- Cross-region summary (variant, count, rental type, snapshot): each region contributes its lowest member, named and labelled "lowest listed per region". It reports region count, min, median and max (no mean), and is "thin" below 5 regions | **owner** (Methodology, Scope) |
| D7 | History:<br>- "Not listed" means seen in a succeeded snapshot, then absent from the next two consecutive succeeded snapshots, dated at the first absence.<br>- A single absence is "absent once (unconfirmed)".<br>- Partial and failed runs never count.<br>- Azure absence is tracked per size: (`armSkuName`, region, rental type, OS).<br>- A price change is the same item key (Phase 1 D15) in consecutive succeeded snapshots with a different price, rolled up to its group. This narrows Phase 1 D15's one-snapshot rule, because `$skip` paging can miss rows silently (Phase 2 D20) | **owner** (Methodology, Conflict) |
| D8 | Synthetic marketplace rules:<br>- **Machine duplicate:** two or more offers from one `machine_id` in one snapshot and group. Statistics take one price per machine, its lowest. The others are flagged `machine_duplicate`, and sample size is distinct machines.<br>- **Re-listing:** in the next snapshot, the same machine with a new `offer_id` and the same GPU name, count, region and rental type is the same offer continuing.<br>- **Thin:** fewer than 5 distinct machines. **Stale:** 7 days.<br>- **GPU names:** a small synthetic name map onto D3 labels. An unknown name, or a VRAM that does not match, is `unmapped_gpu_name`.<br>- **Storage:** offers are stored by synthetic ingest runs into `data/synthetic.duckdb`, never `data/monitor.duckdb`. Tests use in-memory databases | **owner** (Methodology) |
| D9 | Strict map: a size is mapped only when its exact `armSkuName` appears on the cited Learn page. There are no aliases and nothing is inferred from naming patterns or third-party sites. Expected coverage of the live snapshot is 51 of 100 (35 whole, 16 fractional), and the other 49 are flagged `unmapped_sku` and counted. GB200: Learn counts four 192 GB Blackwell GPUs per VM, so USD/GPU-hour is per Blackwell GPU | **owner** (Methodology) |
| D10 | No schema change: no new tables or views. Groups, quality, history and marketplace flags are SQL and functions in code. The first normalize writes `groups-v1` and `gpu-map-v1` into `data/monitor.duckdb` for good, and later changes are new versions | **owner** (One-way door) |
| D11 | A second live run is optional and not part of acceptance. If the owner starts one (≥ 24 h after the last), the phase reports its change and absence counts locally | **owner** (Gate, Private knowledge) |
| D12 | Every observation gets exactly one `normalized_price` row per rule version. An excluded row keeps its reason and has no USD/GPU-hour. When the size is mapped, it still names its mapping and GPU fields | recorded. `price-data-schema` "Excluded row kept with its reason"; Phase 1 acceptance row ("flagged, not dropped"); market-review (state count and denominator) |
| D13 | OS: a row is Windows when `productName`'s last word is "Windows" or "Win", and Linux otherwise. A row whose `productName`, `skuName` or `meterName` contains "Win" elsewhere is flagged `os_ambiguous` in the quality report; there are none today | fact. Retail Prices API page (updated 2026-01-06); local counts above |
| D14 | The map is a hand-built CSV at `src/compute_cost_risk_monitor/reference/gpu_sku_map_v1.csv`, version `gpu-map-v1`. Each row records the size, variant label, form factor, per-GPU memory, GPU count (a fraction such as `1/4` where Learn gives one), source URL, and notes with the retrieval date. A header comment and `reference/README.md` carry "Contains material from Microsoft Learn, licensed CC BY 4.0", with a link. There is no scraper. The loader rejects missing columns, duplicate sizes, non-Learn URLs, a count ≤ 0 and memory ≤ 0 | recorded (Phase 1 D12, owner); licence by fact (MicrosoftDocs LICENSE, 2026-10-12) |
| D15 | Command `uv run python -m compute_cost_risk_monitor.normalize [--db PATH]`, default `data/monitor.duckdb`:<br>- in one transaction, it inserts the map and rule-set rows when absent, and refuses with exit code 2 when stored ones differ from the code;<br>- it inserts rows for observations that lack one under `groups-v1`, so a re-run adds nothing;<br>- it then runs the checks (D16) and prints counts only.<br>The CSV and `groups-v1` are committed before the first live normalize | default. Pattern of Phase 2 D18; one commit undoes it |
| D16 | `checks.py` does not import normalization code; it reads stored rows and the stored `rule_set` parameters. It checks:<br>- `usd_per_gpu_hour` × `gpu_count` matches the observation's price (`math.isclose`, rel_tol 1e-9);<br>- exactly one row per observation and rule version;<br>- excluded rows have a reason and no price, and compared rows have no reason;<br>- each Azure row uses the map row for its observation's own size, or names no map row when the size is not mapped, and `gpu_count` and `gpu_model` equal that row's;<br>- each row's reason equals the first one re-derived from the stored rules, including retirements and regional extensions, and belongs to its source;<br>- a compared row has a compared rental type, a whole GPU count and an hourly unit;<br>- normalized + excluded rows = observations, and per run = `observations_stored`.<br>A failure exits non-zero | recorded. Market-review skill |
| D17 | Git, the PR and reviews carry counts, size names and group keys only: never prices, USD/GPU-hour, statistics or price-ordered rankings. Command output is counts only | recorded. PROJECT §6 Azure scope (no redistribution); publishing gate; Phase 2 practice |
| D18 | Mark normalization as built in the FigJam container view, add `data/synthetic.duckdb`, and re-export `c4-container.svg`. The ERD is unchanged (D10) | recorded. PROJECT §4; Phase 1 D5 and D20 |
| D19 | Statistics conventions:<br>- The median of an even count is the mean of the two middle values, the standard definition. It is labelled "median" and is not an observed price.<br>- Ties for a region's lowest member, or a machine's lowest offer, go to the lexically first size or offer ID, so output is deterministic.<br>- Figures are stored and returned at full precision; rounding is for display (Phase 4) | default. Two-way door, invisible until Phase 4 |
| D20 | Government cloud = a region whose name starts with `usgov` or `usdod` (the Azure Government region names). The prefixes are frozen in `groups-v1` | default. Implements D4. Only `usgovarizona` and `usgovvirginia` occur today |
| D21 | Snapshot = one succeeded run, timed by `started_at` (Phase 2 D7). Its date for D5 is the UTC date of `started_at`. Stale = the latest snapshot of a source is more than 7 days before an injected `as_of` time (Phase 1 D16). Nothing reads the system clock except the command's default `as_of` | recorded (Phase 2 D7, Phase 1 D16) and default (injection) |
| D22 | Synthetic marketplace snapshots are JSON files labelled `"_label": "synthetic"`. Each file is ingested as one `synthetic-marketplace` run labelled `synthetic`: one `raw_response` row per file (repo-relative path, SHA-256 of its bytes), one `price_observation` and `marketplace_offer` row per offer. The item key is the offer ID, and the run starts at the file's `observed_at`. A file without the synthetic label is refused. Marketplace normalization: USD/GPU-hour = offer price ÷ `num_gpus`, with variant from the D8 name map, no `gpu_sku_map` reference, and reasons `rental_type_not_compared` and `unmapped_gpu_name` | default. Uses schema 001 as built (`marketplace_offer`, FK chain forcing the synthetic label) |
| D23 | Marketplace "not listed" and changes use the continuity key (`machine_id`, GPU name, `num_gpus`, region, rental type) in place of the item key, so re-listing (D8) is neither a delisting nor a new offer. When a machine has several offers with one key, its lowest price stands for it | default. Implements D7 and D8 together |
| D25 | Code review of PR #8 (2026-10-12) found 15 issues; 12 were fixed with tests:<br>- The checker missed a wrong map row, a mapped size marked unmapped, a retired size left in comparisons, and wrong-source or out-of-order reasons. It now compares each Azure row with the map row for its own size, and a new check, `reasons_rederived`, re-derives every row's reason from the stored rules.<br>- Quality flags a latest snapshot that is not normalized yet and names the unmapped sizes.<br>- Synthetic run IDs use UTC; out-of-range numbers, re-saved snapshots and database errors are refused cleanly; duplicates are found in one pass.<br>- The map loader tolerates a byte-order mark; normalize and quality refuse (exit 2) on a bad map or an unopenable database.<br>- A changed rule set names the keys that differ.<br>- Absences use one SQL aggregate and the shared OS rule.<br>Not changed, with reasons: a shared SQL view for the run join (D10 rules out views; the join is the plain foreign-key path); one helper for "a machine's lowest offer" (groups and history apply the same rule to different keys by design, D8 and D23). | main agent. Source: `/code-review` findings on PR #8 |

### Rule set `groups-v1`

Stored once in `rule_set.parameters` as JSON, and equal to a constant in `rules.py`:

```text
rule_version: groups-v1
map_version: gpu-map-v1
compared_rental_types: [on_demand, spot]
exclusion_order: [rental_type_not_compared, government_cloud, windows, unit_not_hourly,
                  unmapped_sku, fractional_gpu, retired_size]
marketplace_exclusion_order: [rental_type_not_compared, unmapped_gpu_name]
marketplace_gpu_names: {listed name: {variant, vram_gb}, …}   synthetic names (D8)
government_region_prefixes: [usgov, usdod]
windows_product_suffixes: [Windows, Win]
hourly_unit: "1 Hour"
retirements: [{series, sizes[], retired_on, region_extensions{region: date}, source_url}, …]
stale_after_days: 7
thin_below_regions: 5
thin_below_machines: 5
not_listed_after_absences: 2
exclusions: "Excludes disks and storage, egress, public IPs, licences, taxes, negotiated
             discounts, reservations and savings plans, Spot eviction risk, capacity and quota."
```

The `exclusions` text is Phase 1 D13's list. It is written to every `normalized_price` row and
returned with every figure.

### Module layout

Pure rules sit apart from I/O, as in Phase 2:

```text
compute_cost_risk_monitor/
  reference/gpu_sku_map_v1.csv, reference/README.md   map data and its attribution
  gpu_map.py      load and validate the CSV; MapRow; write gpu_sku_map rows (insert or refuse)
  rules.py        GROUPS_V1 parameters; write the rule_set row (insert or refuse)
  normalize.py    pure: classify an Azure or marketplace observation → Normalized | Excluded;
                  I/O: rows lacking a normalized_price row → one transaction; command main()
  groups.py       snapshots; region groups; cross-region summary; marketplace groups by machine
  history.py      consecutive-snapshot changes; absent once / not listed; continuity keys
  quality.py      counts-only report per source and latest snapshot (as_of injected)
  checks.py       independent validation over stored rows (imports db only)
  synthetic.py    synthetic marketplace snapshot files → synthetic runs
```

Data flow: DuckDB observations → `normalize.py` (with the map and rules) → `normalized_price`
→ `groups.py`, `history.py` and `quality.py` read stored rows → Phase 4. `checks.py` reads the
same stored rows on its own path.

### Figures introduced

| Figure | Comparable-group key | Units | Exclusions |
|---|---|---|---|
| USD/GPU-hour per observation | variant, GPU count, region, rental type | USD per GPU per hour, from Azure's "1 Hour" VM price ÷ mapped GPUs | D13 list, on every row |
| Region-group members | as above, per snapshot | as above | as above |
| Cross-region min / median / max | variant, count, rental type, per snapshot; crosses regions and says so ("lowest listed per region", region count) | as above | as above, plus "thin" below 5 regions |
| Marketplace group min / median / max | variant, count, region, rental type; one price per machine | USD per GPU per hour, **synthetic** | as above, plus "thin" below 5 machines |
| Price change | item key (Azure) or continuity key (marketplace), consecutive snapshots | the source's price unit, plus USD/GPU-hour when both rows are normalized | as above |

### Non-negotiables check

| PROJECT.md §5 rule or §6 gate | How this design keeps it |
|---|---|
| Secrets never printed or committed | No secrets are involved. detect-secrets stays in the gate |
| Never fabricate; label results; preserve failed runs | Excluded rows are kept with reasons (D12). Synthetic data is labelled, refused without its label, and kept in its own database (D8, D22). Partial and failed runs are kept and never count as snapshots (D7). Statistics state their counts |
| Operator resolves ⛔ gates | Nothing is gated here. A second live run is the owner's choice (D11) |
| Call the data published Azure list prices | Labels and output say "list price" and "lowest listed"; the median is labelled as a statistic. The marketplace is "synthetic" in every output |
| Deterministic code computes every figure | All figures come from pure functions with known-answer tests, checked independently (D16). There is no AI |
| Compare only within comparable groups; state exclusions | Group keys follow D3–D6. The cross-region summary says it crosses regions. The D13 exclusions travel with every row and figure |
| Collector only reads published prices | No network code is added. The map is hand-built |
| Within terms; missing stays missing | Unmapped, fractional and unknown values stay NULL, with a reason. "Not listed" needs two absences and is never filled in (D7). No Azure data enters Git; the map is Learn content under CC BY 4.0 with credit (D14) |
| ⛔ live data / scheduling / spend / publishing | Not acted on. No new reads, schedules, spending or published figures. Counts only in Git (D17) |

No exception to any rule is needed.

## Risks / Trade-offs

- [The strict map leaves 49 of 100 sizes unmapped, including several H100 variants] → They
  are counted and named in the quality report. A later `gpu-map-v2` can add sizes when Learn
  documents them; it is a new version, so `groups-v1` results stay reproducible.
- [Learn pages change, and retirement tables lag series pages] → Every map row and retirement
  entry carries its URL and retrieval date. The rule uses the series page's "retired on" date
  when the two disagree, as for NVv3 and NVv4.
- [Learn counts GPUs on dual-GPU boards inconsistently (M60 card vs die, K80 dies)] → Only
  retired sizes are affected (D5, D9). Memory is taken per GPU from each series' description.
- [The OS rule relies on product-name wording] → Unknown wording counts as Linux. The
  `os_ambiguous` flag and the quality report surface any change, and a new product suffix would
  show up as Windows rows dropping.
- [The first normalize fixes `groups-v1` in the local database for good] → The CSV and rules
  are committed first, and the command refuses mismatches. A mistake is fixed by a new version,
  or by rebuilding the local database from the kept raw files (`--ingest-run`).
- [With one live snapshot, history has no real data] → It is tested on synthetic snapshots.
  Live history waits for owner-started runs (D11).
- [The median of an even count is not an observed price] → It is labelled "median" and shown
  beside min and max with the region or machine count (D19).

## Migration Plan

New modules, a reference CSV and tests. No schema change. The first `normalize` run on
`data/monitor.duckdb` adds `gpu_sku_map`, `rule_set` and `normalized_price` rows. To roll back,
revert the merge commit; the local database can be rebuilt from raw files with `--ingest-run`.
`data/synthetic.duckdb` is disposable.

## Open Questions

None for the owner. Results of the first live normalize (counts by reason, and coverage) are
recorded in HANDOFF, counts only.
