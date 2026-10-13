## Context

Phase 5 of PROJECT.md §6. Phase 4 delivered the read-only Streamlit dashboard. It shows region
groups, whose members carry their USD/GPU-hour, published VM-hour price and provenance, plus
cross-region summaries and a data-quality panel. Phase 1's acceptance row for Phase 5:
- Cost = GPUs × hours × USD/GPU-hour, plus storage only when the user enters a storage cost, with
  exclusions shown.
- Exposure = GPUs × hours × scenario change, under labelled hypothetical scenarios including a
  decline and a spike. Never a forecast.
- Evidence: 32 × 720 × $0.50 = $11,520 passes; known-answer tests; BCBS stress-testing principles
  used as the scenario checklist.

The Phase 5 grilling ran two rounds on 2026-10-13.
- **Round 1:** an informed-answerer subagent researched 19 questions and found 3 more.
- **Round 2:** it researched 5 more and found 3.
- **Main agent's re-check:** it reopened the sources behind the settled answers:
  - the Azure Linux VM pricing FAQ, Learn's pricing-calculator and Spot VM pages;
  - BCBS d450 pages 1 and 6, and the arXiv 2603.21690 abstract;
  - Streamlit 1.65's `number_input` and `selectbox` source;
  - the `dashboard` and `synthetic-azure-snapshots` spec headers;
  - the live counts, rerun with a counts-only script.
- **Owner:** accepted every recommendation in both rounds ("All Recommend", "All recommended").

Measured facts this design relies on (2026-10-13, local read-only commands, counts only):
- **Live data** (one live snapshot, `20261012T151909Z-5473f1`):
  - 929 region groups: 473 pay-as-you-go and 456 Spot.
  - GPUs per VM: 1 in 329 groups, 2 in 227, 4 in 157 and 8 in 216.
  - Members per group: 1 in 684 groups, 2 in 181 and 3 in 64.
  - Every unit is "1 Hour" and every currency USD.
- **Spot pairing (live):**
  - All 456 Spot groups have a pay-as-you-go group with the same variant, GPU count and region.
  - All 609 Spot members' sizes are listed on pay-as-you-go in the same region.
  - None is priced above its pay-as-you-go size; 48 are equal, 10 sit at 50–80% of it and 551
    below 50%.
  - Under the accepted scenarios, a Spot member's scenario price exceeds its size's pay-as-you-go
    price in 48 members under +25%, 73 under +$0.50 and 58 under +100%.
- **Flat $0.50 against the lowest listed price per group (live):** under 5% in 124 groups, 5–25%
  in 375, 25–100% in 356, and 100% or more in 74. In those 74 groups a −$0.50 change would reach
  zero or below.
- **Synthetic demo database:**
  - 10 region groups (8 pay-as-you-go, 2 Spot), with 1 and 8 GPUs per VM.
  - The eastus H100 ×8 Spot price equals its pay-as-you-go price; the westeurope one is below
    50% of it.
  - No demo Spot size lacks a pay-as-you-go listing.
  - T4 eastus has two sizes.
- **Streamlit 1.65.0:**
  - A widget that is not drawn loses its value unless `persist_state` is `"page"` or
    `"session"`, and a lazy tab leaves its widgets undrawn. Under AppTest, measured
    during task 3.2: `"page"` keeps the value in session state while the widget is
    undrawn but resets the widget to its default when it is drawn again; `"session"`
    keeps it. The app has one page, so the two scopes mean the same to a user.
  - A keyed `number_input` keeps its identity by key alone (`key_as_main_identity=True`): it
    keeps its value when min, max or step change. It resets to its default only when the value
    falls outside the new bounds, and it never checks the step.
  - A keyed `selectbox` keeps its value while that value is still among its options.
  - `value=None` leaves a `number_input` empty until the user types.
- **Azure billing (public pages, retrieved 2026-10-13):**
  - **Linux VM pricing FAQ:** "We charge for the number of full minutes your virtual machine is
    running"; "The operating system disk is charged at the regular rate for disks"; the local
    (temporary) disk is not charged.
  - **Learn, VM states and billing:** Stopped (allocated) is billed; Stopped (deallocated) is
    not, though disks continue to bill.
  - **Learn, Spot VMs (ms.date 2026-02-06):**
    - eviction "with 30-seconds notice", and "there's no SLA";
    - with max price `-1`, "You'll never be charged above the standard price";
    - a price above the max price evicts the VM;
    - the Deallocate policy keeps charging "storage costs for the underlying disks";
    - the FAQ recommends standard VMs "if you need capacity right away" after an eviction.
  - **Learn, "Estimate costs with the Azure pricing calculator" (ms.date 2025-07-21):** "a
    virtual machine configuration defaults to run for one month (730 hours)". This is the
    primary source that Phase 1 D17 lacked.
  - **Learn, disk billing:** managed disks are billed by tier and size, plus transactions or
    performance, not at one rate per GB.
- **BCBS d450, Stress testing principles (October 2018):**
  - Footnote 3: stress tests range "from sensitivity analysis, to more complex scenario analysis
    … and reverse stress tests".
  - Principle 4: a narrative "should articulate how the scenario captures the risks"; excluded
    risks are "explained and documented"; scenarios "should be sufficiently severe but
    plausible"; scenarios not based on history "may be warranted … if historical data do not
    contain a severe crisis episode"; reverse stress tests are named.
- **arXiv 2603.21690:** Yicai Xing, "AI Token Futures Market: Commoditization of Compute and
  Derivatives Contract Design", submitted 2026-03-23. It models compute-cost dynamics with "a
  mean-reverting jump-diffusion stochastic process" and evaluates hedging "during periods of
  increased demand". None of its numbers are used (Phase 1 D18).

## Goals / Non-Goals

**Goals:**
- A GPU buyer can take one listed size in one comparable group and see:
  - what a workload of whole VMs would cost for the hours entered, with every exclusion and
    assumption stated beside the figure;
  - how that cost would change under named, labelled, hypothetical price scenarios, and what
    price rise would use up a given budget.
- Every workload and exposure figure is computed by deterministic code from the stored, unrounded
  USD/GPU-hour. It is re-derived by independent code before it is shown, and it traces to its
  source record.
- Nothing reads as a forecast, a market price or what a customer would pay.

**Non-Goals:** as in the proposal.

## Decisions

| # | Decision | Who / basis |
|---|---|---|
| D1 | Scope: the acceptance row. One calculator over one comparable group (Azure-shaped, D4) and `scenarios-v1` presets plus one custom scenario (D5, D6), plus the Spot to pay-as-you-go fallback (D7) and budget headroom (D9). Non-goals as in the proposal | **owner** (Scope) |
| D2 | Timebox: one session of about 3 h. Cut in this order: (1) the exposure chart and visual polish; (2) the Spot to pay-as-you-go fallback; (3) budget headroom; (4) the size choice, reduced to the group's lowest listed member; (5) the custom scenario, reduced to presets only. Never cut: the cost formula and its known-answer tests including 32 × 720 × $0.50 = $11,520; the decline and spike presets with their narratives; "Scenario calculation, not a forecast" on every exposure figure; group key, snapshot time (UTC) and run, data label and exclusions on every figure; the storage entry with its label; the whole-VM rule; the independent check; AppTest flows on synthetic data and the manual check; counts-only Git and PR with synthetic-only screenshots; the container diagram update | **owner** (Scope, Value trade-off, Private knowledge) |
| D3 | Starting price: one listed member (size) of the selected region group, chosen by the user and defaulting to its lowest listed member (the group's own order: USD/GPU-hour, then name). It is shown with its published VM-hour price and unit, item key and run ID. No entered price and no cross-region statistic | **owner** (Methodology) |
| D4 | Sources: Azure-shaped groups only, live and the synthetic Azure demo. With "Synthetic marketplace" selected, the tab says the calculator uses Azure list-price groups and that the marketplace data exercises the data-quality rules | **owner** (Scope, Showcase) |
| D5 | Scenario form: each scenario is a percentage of the starting price or an absolute change in USD/GPU-hour. Decline, increase and spike are percentages; PROJECT's +$0.50 is absolute. Every scenario row shows both the USD change and the % of the starting price. A scenario whose price would be zero or below is refused for that row ("not computed: the price would be zero or below"), never floored | **owner** (Methodology) |
| D6 | `scenarios-v1`, frozen in `scenarios.py`; its version is shown on every exposure figure. Each scenario has an ID, a name, a kind, a magnitude and a one-line narrative:<br>- `decline-25`, "Decline −25%": hypothetical list-price cut: the price of this size falls by a quarter;<br>- `increase-25`, "Increase +25%": hypothetical list-price rise: the price of this size rises by a quarter;<br>- `example-050`, "PROJECT example +$0.50/GPU-hour": PROJECT.md's worked example, a flat rise of USD 0.50 per GPU-hour whatever the starting price;<br>- `spike-100`, "Spike +100% (price doubles)": hypothetical demand shock. Jump models of compute costs (e.g. arXiv 2603.21690) motivate testing a jump; its size is not taken from any model.<br>A custom scenario (D24) sits beside them, outside the set. Every scenario figure states "Round sensitivities chosen by judgement, not calibrated to history (one snapshot) or to any model". The BCBS d450 checklist is below | **owner** (Methodology, Showcase, Thin evidence) |
| D7 | Cross-group scenarios: only "Spot to pay-as-you-go fallback", shown for Spot groups. It takes the same size in the same region at its pay-as-you-go list price (same variant, GPU count and region; rental type `on_demand`; same size name; same snapshot). Exposure = GPUs × hours × (pay-as-you-go − Spot USD/GPU-hour). It is labelled "crosses rental types (Spot → pay-as-you-go)" with both group keys. Without such a listing: "not computed: no pay-as-you-go listing for this size in this region". No "most expensive region" scenario. This settles the Spot versus pay-as-you-go comparison deferred by Phase 4 D4 | **owner** (Methodology, Scope, Showcase) |
| D8 | One horizontal Altair bar chart of exposure per computed scenario row, with a rule at zero, captioned like the scenario table. Refused rows are absent from it. First on the cut list | **owner** (Showcase, Scope) |
| D9 | Budget headroom: an optional budget B gives c = B ÷ (GPUs × hours), the rise in USD per GPU-hour that would use up B, also shown as % of the starting price. It is worded "A rise of USD c per GPU-hour (p% of starting price) would use up USD B over G GPUs × H h. Storage unchanged. Scenario calculation, not a forecast". It is a reverse stress test in BCBS d450's terms. Third on the cut list | **owner** (Scope) |
| D10 | Caption lines added to workload figures:<br>- **Storage**, when entered: "Storage: USD X entered by you for this period, not an Azure list price and not checked against Azure disk prices. The total adds it; every other exclusion still applies." Otherwise: "Storage not included." The stored `groups-v1` exclusions text is shown unchanged.<br>- **Spot**, on every Spot cost and exposure figure: "Spot: Azure can evict these VMs at any time with 30 seconds' notice and gives no SLA, and the Spot price is variable. This figure assumes every hour entered runs at this listed Spot price; evicted hours may not be delivered, and an evicted VM that is deallocated still bills for its disks."<br>- **Billing assumptions**, on every workload figure: "Assumes each VM is allocated for exactly the hours entered. Azure bills full minutes while a VM is allocated, including Stopped (allocated); only Stopped (deallocated) ends compute billing. Every VM has an OS disk, billed as storage and not in the GPU price; add it under storage." | **owner** (Methodology) |
| D11 | A Spot scenario, custom or headroom price above the same size's pay-as-you-go list price in the same region keeps its arithmetic and gets a note: "Above this size's pay-as-you-go list price (USD x/GPU-hour). With max price −1 Azure charges at most the pay-as-you-go price; with a lower max price the VM is evicted. This row shows the scenario's arithmetic, not what Azure would bill. See 'Spot to pay-as-you-go fallback'." Without a pay-as-you-go listing there is no note. No cap and no refusal | **owner** (Methodology) |
| D12 | Demo data: `azure_demo.json` gains one invented Spot `Standard_ND96isr_H100_v5` item in `uksouth`, a region with no pay-as-you-go listing for that size, labelled synthetic like the rest. The H100 ×8 Spot cross-region summary goes from 2 regions to 3 and stays thin; no other group changes. MODIFIED `synthetic-azure-snapshots`; the fixtures README is updated; `data/synthetic.duckdb` is rebuilt | **owner** (Scope, Showcase) |
| D13 | GPUs: the user enters total GPUs, which must be a whole multiple of the group's GPUs per VM (1, 2, 4 or 8). The pure validator refuses a non-multiple and names the nearest valid counts ("30 GPUs is not a whole number of 8-GPU VMs: use 24 or 32"), and the VM count is shown ("32 GPUs = 4 VMs"). No silent rounding | recorded (PROJECT §2 and the acceptance row use GPUs) and fact (Azure prices whole VMs; USD/GPU-hour = VM price ÷ GPU count, Phase 1 D13). Refusing rather than rounding is a default |
| D14 | Hours: "Hours in the period", entered by the user, fractional allowed, > 0 and ≤ 8,784 (366 × 24), default 720. Figures read "for the hours entered", never "monthly", and nothing is converted. Help text: "720 h = 30 days; Microsoft's pricing calculator uses 730 h for a month." The 730 h convention (Phase 1 D17) now has its primary source (Context) | recorded (Phase 1 D17) and fact (Azure bills full minutes; Learn pricing-calculator page) |
| D15 | Storage: one optional amount in USD for the period, entered by the user; empty means not included. No GB × rate input and no fetched disk prices | recorded (acceptance row: "plus storage only when the user enters a storage cost") and fact (disk billing by tier; the live-data gate allows the GPU filter only) |
| D16 | Exposure = GPUs × hours × (scenario − starting USD/GPU-hour), signed. Positive reads "additional expense", negative "lower expense", zero "no change". "Scenario calculation, not a forecast" is on every exposure figure. Refused rows show why and carry no figure | recorded (PROJECT §2, §5) and default (sign convention) |
| D17 | Placement: a fourth lazy tab, "Workload cost", after "Comparable groups", driven by the sidebar's group filters. Its inputs are keyed with `persist_state="session"`, so they keep their values when the user switches tabs | default (Phase 4 D28's layout) and fact (Streamlit 1.65, Context) |
| D18 | Tables: a cost breakdown (compute, storage, total) and one scenario table. Its columns are Scenario, Narrative, Change (USD/GPU-hour), Change (% of starting price), Scenario USD/GPU-hour, Scenario cost (USD), Exposure (USD), Effect and Note. The starting-price row comes first; the fallback and custom rows come after the presets. Scenario cost = GPUs × hours × scenario USD/GPU-hour, plus the storage amount when entered (unchanged across scenarios, as the caption says). The built-in CSV download stays on | recorded (Phase 4 D8, D24) and default |
| D19 | Modules:<br>- `scenarios.py`: frozen data only.<br>- `calculator.py`: pure; no Streamlit, no database. It holds the validator, starting price, cost, scenario rows, fallback, note and headroom.<br>- `workload_check.py`: imports no calculator code. It takes plain values (GPUs, hours, the starting member's VM-hour price and GPUs per VM, storage, the pay-as-you-go member's VM-hour price, the budget) and the result's figures, and re-derives every figure from `scenarios.py`'s definitions. It checks:<br>&nbsp;&nbsp;- VM-hour price ÷ GPUs per VM = starting USD/GPU-hour;<br>&nbsp;&nbsp;- VM-hour price × VMs × hours = compute cost;<br>&nbsp;&nbsp;- total = compute + storage;<br>&nbsp;&nbsp;- each scenario price from (kind, magnitude);<br>&nbsp;&nbsp;- exposure = GPUs × hours × change, and = scenario cost − starting cost;<br>&nbsp;&nbsp;- a row is refused exactly when its price ≤ 0;<br>&nbsp;&nbsp;- the fallback from the pay-as-you-go VM-hour price;<br>&nbsp;&nbsp;- G × H × c = B;<br>&nbsp;&nbsp;- every figure finite.<br>Comparisons use `math.isclose` (rel_tol 1e-9). The page runs the check on every result before drawing; a failure shows "The independent check failed: <checks>. No figures are shown." and no figures.<br>- `dashboard.py` builds frames, captions and the chart spec; `app.py` draws them.<br>No command-line tool | default. Mirrors Phase 3 D16 (`checks.py`) and Phase 4 D18; market-review ("Check outputs with deterministic code independent of the code that produced them") |
| D20 | Nothing is written: no schema change, no `rule_set` row, no saved calculation. `scenarios-v1` is a frozen code constant shown on every exposure figure; the dashboard stays read-only (Phase 4 D13) and the ERD is unchanged | recorded (Phase 4 D13) and default. Changes if scenarios must be stored; normalize could then store them without a schema change |
| D21 | Precision and bounds:<br>- **Display:** USD amounts at 2 decimals with thousands separators ("11,520.00"); USD/GPU-hour at 4 decimals (Phase 4 D9); percentages at 1 decimal. Every computation uses unrounded values.<br>- **Bounds:** GPUs an integer multiple of GPUs per VM, up to 100,000; hours > 0 and ≤ 8,784; storage 0 to 10,000,000 USD; custom % above −100 and up to 1,000; custom USD change −1,000 to 1,000, with the price staying above 0; budget above 0 and up to 10,000,000,000 USD.<br>- **Non-finite input:** NaN and ±infinity are refused by the pure validator | recorded (Phase 4 D9; market-review: prices finite and positive) and default |
| D22 | Evidence:<br>- **Known-answer tests:** 32 × 720 × $0.50 = $11,520; cost with and without storage.<br>- **Edge and impossible cases:** non-multiple GPUs with the nearest counts; zero, negative and non-finite inputs; a decline to ≤ 0; a Spot size without a pay-as-you-go listing; Spot equal to pay-as-you-go giving 0; a Spot scenario above pay-as-you-go carrying the note.<br>- **Independent check:** tests that tamper with each figure, plus a test that it imports no calculator code.<br>- **AppTest flows:** on synthetic databases with a fixed as-of time.<br>- **Manual check:** in Chrome on synthetic data.<br>- **Live check:** an AppTest run on the live database, reported as counts only.<br>- **Reviews:** the BCBS checklist (below), plus a market-review and build-safety read-through in `docs/reviews/`.<br>- **PR material:** synthetic-only screenshots.<br>- **Diagrams:** the FigJam container view marks the calculator built, with `c4-container.svg` re-exported | recorded (acceptance row; PROJECT §3; Phase 4 D16, D19–D21) |
| D23 | Specs:<br>- change and branch `phase-5-calculator`;<br>- new `workload-calculator`;<br>- `dashboard`: ADDED "Workload cost view", MODIFIED "Figure captions and framing line" and "Display formatting";<br>- `synthetic-azure-snapshots`: MODIFIED "Synthetic Azure snapshot files".<br>Each MODIFIED block repeats every existing scenario. `comparable-groups` is unchanged: `region_groups` already returns both rental types with the size, price and provenance the calculator needs | recorded (Phases 2–4 naming; commit 0ca6887) and default |
| D24 | Custom scenario: a keyed horizontal radio picks the kind, "% of starting price" or "USD per GPU-hour". Each kind has its own keyed input with `value=None` and `persist_state="session"`, so switching kind never reinterprets a value. An empty input adds no row. The row is named "Custom: <change> (entered by you, not part of scenarios-v1)" | default |
| D25 | Budget headroom input: `value=None`. Empty shows a one-line hint and no figure; 0 is refused ("enter an amount above zero"). The result appears only when the GPU and hours inputs are valid, and it carries the D11 note when the starting price + c exceeds pay-as-you-go on Spot | default |
| D26 | GPU input: one keyed input, `gpus`, with min = step = GPUs per VM, max 100,000, default 32 and `persist_state="session"`. 32 makes whole VMs for 1, 2, 4 and 8 GPUs per VM and reproduces PROJECT's example. A kept value below the new minimum resets to 32 (Streamlit); a kept value that is not a multiple is refused by the validator with the nearest counts | fact (Streamlit 1.65, Context) and default |
| D27 | Size choice: a selectbox keyed per group key, with `persist_state="session"`, shown when the group has more than one member. A new group starts at its lowest listed member, and returning to a group keeps its pick. The caption names the size and adds "(lowest listed in this group)" only when it is the lowest | fact (Streamlit 1.65: a shared selectbox would keep a size that is no longer the lowest) and default |
| D28 | The archive commit adds "the workload calculator and labelled exposure scenarios" to the `dashboard` spec's Purpose, which a delta does not rewrite | default |

### Figures shown

Every figure uses the starting member's stored, unrounded USD/GPU-hour.

| Figure | Comparable-group key | Units | Exclusions and labels |
|---|---|---|---|
| Starting price | variant, GPU count, region, rental type; snapshot and run; the member's size, item key and published VM-hour price | USD per GPU per hour, beside USD per VM per "1 Hour" | `groups-v1` exclusions text; data label |
| Compute cost and total | as above | USD for G GPUs (G ÷ GPUs per VM VMs) × H hours | exclusions text; storage line; billing assumptions line; Spot line on Spot groups |
| Scenario rows (`scenarios-v1` and custom) | as above | USD/GPU-hour change and %, scenario USD/GPU-hour, scenario cost and exposure in USD | as above, plus `scenarios-v1`, "Scenario calculation, not a forecast" and the judgement note; D11 note where it applies |
| Spot to pay-as-you-go fallback | crosses rental types: the Spot key and the pay-as-you-go key (same variant, count, region and size) | as above | as above, plus "crosses rental types (Spot → pay-as-you-go)" |
| Exposure chart | as the scenario table | USD exposure per scenario | as the scenario table |
| Budget headroom | as the starting price | USD per GPU-hour and % of starting price, for USD B over G GPUs × H h | "Scenario calculation, not a forecast"; storage unchanged; D11 note where it applies |

### BCBS d450 checklist (scenario design)

The principles are written for banks and supervisors. This project applies them proportionately,
as their introduction allows, to a single buyer's price scenarios.

| Principle | How Phase 5 applies it |
|---|---|
| 1 Clearly articulated objectives | Objective, stated in the tab and the design: show how the cost of one workload would change under labelled price changes. It is not a prediction, a market price or what a customer pays |
| 2 Effective governance | The owner approved the scenario set (D5, D6) and the cross-group rule (D7). Changes need a new version (`scenarios-v2`), never an edit in place |
| 3 Risk management tool; key assumptions and limitations understood | Every figure carries the exclusions text and the billing assumptions, storage and Spot lines (D10); magnitudes are labelled as judgement (D6) |
| 4 Material risks; severe but plausible; narratives; excluded risks documented; reverse stress tests | Covered risks: list-price falls, rises and jumps for one size, and Spot capacity loss (D7). Each scenario has a narrative. Excluded risks are documented: capacity and quota, Spot eviction frequency, currency, taxes, reservations and negotiated prices, and storage and egress price changes. History has no episode to draw on (one snapshot), so hypothetical scenarios are warranted. Budget headroom is the reverse stress test (D9) |
| 5 Resources and organisation | Not applicable: a single-owner project |
| 6 Accurate, granular data and robust systems | Figures use stored, unrounded rows with provenance. The independent check (D19), the NOT NORMALIZED withholding and the stale flag stop bad inputs reaching a figure |
| 7 Fit-for-purpose methodology | Linear arithmetic with known-answer tests (D22). The method does not model eviction, discounts or price dynamics, and says so |
| 8 Challenge and regular review | The market-review read-through and `/code-review` of the PR. The owner reviews the draft PR |
| 9 Communication | The tab and every caption state the assumptions and limitations alongside the figures |

### Non-negotiables check

| PROJECT.md §5 rule or §6 gate | How this design keeps it |
|---|---|
| Secrets never printed or committed | No secrets are involved |
| Never fabricate; label results; preserve failed runs | Every figure shows its snapshot's recorded label. Refused scenarios and a missing pay-as-you-go listing show "not computed", never a figure (D5, D7). Magnitudes are labelled as judgement (D6). The demo item is invented and labelled synthetic (D12) |
| Operator resolves ⛔ gates | No gate is satisfied or waived. Storage is entered by the user, because fetching disk prices would fall outside the live-data gate's scope (D15) |
| Call the data published Azure list prices; label exposure as a scenario calculation | The framing line is unchanged. "Scenario calculation, not a forecast" is on every exposure figure and on headroom (D9, D16). Spot rows above pay-as-you-go say they are arithmetic, not what Azure would bill (D11) |
| Deterministic code computes every figure | `calculator.py` computes, and `workload_check.py` independently re-derives before display (D19). There is no AI |
| Compare only within comparable groups; state exclusions | The calculator uses one member of one region group (D3). The only crossing, Spot to pay-as-you-go, says "crosses rental types" with both keys (D7). Every workload figure carries the exclusions text plus the storage and billing lines (D10) |
| Collector only reads published prices | No network code is added; stored rows are read read-only |
| Within terms; missing stays missing | Live figures stay on this PC (Phase 4 D11, D20). A missing pay-as-you-go listing gives "not computed" (D7). Hours are not converted to months and storage is never estimated (D14, D15) |
| ⛔ live data | Honoured: no new reads. Stored live rows are used locally only, and the CSV reading of Phase 4 D8 applies |
| ⛔ scheduling / spend / publishing | Not acted on |

No exception to any rule is needed.

## Risks / Trade-offs

- [Scenario magnitudes are judgement and could be read as predictions] → Each figure carries
  "Scenario calculation, not a forecast" and the judgement note. Narratives say "hypothetical".
  The set is versioned (D6).
- [A Spot scenario price above pay-as-you-go is not what Azure would bill] → The D11 note says so
  and points to the fallback row. The arithmetic is kept, so the scenario means the same thing in
  every group.
- [Users may read cost as the full bill] → The exclusions, storage and billing-assumption lines
  sit under every workload figure (D10). The OS disk is named as storage to add.
- [Streamlit widget state across lazy tabs and group changes] → `persist_state="session"`, keyed
  inputs and AppTest flows that switch tabs and groups (D17, D26, D27). `"page"` scope lost the
  value on remount under AppTest (Context), so the manual check also switches tabs.
- [The independent check could share a bug with the calculator] → It imports no calculator code,
  re-derives from VM-hour prices and scenario definitions, and has tests that tamper with each
  figure (D19, D22).
- [Synthetic fixtures turn stale after 2026-10-19] → STALE is shown as computed; tests inject
  their as-of time (Phase 4 D15, D16).

## Migration Plan

New modules, edited view model and page, one fixture item and tests. No schema change, and nothing
is written to `data/monitor.duckdb`. `data/synthetic.duckdb` is disposable and is rebuilt from the
updated demo file with the commands in HANDOFF.md. To roll back, revert the merge commit.

## Open Questions

None. Every grilling question is owner-answered (D1–D12) or settled with its basis (D13–D28).
