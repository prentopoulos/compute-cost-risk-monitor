## Why

PROJECT.md Phase 5: a workload cost calculator and labelled budget-exposure scenarios. The Phase 4
dashboard shows the listed USD/GPU-hour of one comparable group, but a GPU buyer still cannot
answer the project's second and third questions: what their workload would cost, and how exposed
their budget is to a change in price.

The Phase 5 grilling (2026-10-13, two rounds) settled the scope. The owner accepted every
recommendation ("All Recommend", "All recommended"). Design D1–D12 are owner decisions; D13 onwards
are settled with their basis.

## What Changes

- **Workload cost.** The user picks one listed size in the comparable group chosen in the
  sidebar, defaulting to the group's lowest listed size, and enters:
  - total GPUs, which must make whole VMs;
  - hours for the period;
  - optionally, a storage amount in USD.

  Cost = GPUs × hours × USD/GPU-hour, plus the storage amount when one is entered. Every figure
  carries its group key, snapshot, data label, the exclusions text, a storage line and a billing
  assumptions line.
- **Labelled exposure scenarios.** A frozen scenario set, `scenarios-v1`:
  - Decline −25%;
  - Increase +25%;
  - PROJECT example +$0.50/GPU-hour;
  - Spike +100%;
  - one custom change the user enters, as a percentage or in USD/GPU-hour.

  Exposure = GPUs × hours × (scenario price − starting price), signed and worded "additional
  expense", "lower expense" or "no change". Every exposure figure is labelled "Scenario
  calculation, not a forecast" and names `scenarios-v1`. A scenario that would take the price to
  zero or below is refused, never floored.
- **Spot to pay-as-you-go fallback.** For a Spot group, one extra scenario prices the same size
  in the same region at its pay-as-you-go list price. It is labelled "crosses rental types",
  with both group keys. When that size has no pay-as-you-go listing there, it shows "not
  computed", never a filled-in price. A Spot scenario price above the size's pay-as-you-go list
  price carries a note saying what Azure would actually charge.
- **Budget headroom.** An optional budget B gives the price rise per GPU-hour that would use it
  up: B ÷ (GPUs × hours). This is a reverse calculation, labelled a scenario calculation.
- **Independent check.** A separate module, importing no calculator code, re-derives every
  workload figure before the page shows it. The checks are:
  - VM-hour price × VMs × hours;
  - each scenario price from its definition;
  - exposure two ways;
  - totals and headroom.

  If any check fails, the page shows an error instead of figures.
- **Dashboard tab.** A fourth lazy tab, "Workload cost", driven by the existing sidebar filters:
  - the inputs keep their values when the user switches tabs or groups;
  - a cost breakdown, a scenario table and one bar chart of exposure per scenario;
  - on the synthetic marketplace source, a note that the calculator uses Azure list-price groups.
- **Demo data.** `azure_demo.json` gains one invented Spot H100 ×8 item in a region with no
  pay-as-you-go listing for that size, so the "not computed" fallback can be seen in the demo.
- **Documents.**
  - PROJECT.md §4 points to the decisions.
  - The FigJam container view marks the calculator built, and `c4-container.svg` is re-exported.
  - The design records the BCBS d450 checklist and the primary source for 730 h a month.
  - HANDOFF.md is updated.

## Non-goals

- No forecasts or probabilities. No scenarios built from history or trends: only one live
  snapshot exists.
- No reservations, savings plans or negotiated prices, and no comparison that crosses regions in
  the calculator. The Spot to pay-as-you-go fallback is the only scenario that crosses groups.
- No fetching of disk, storage or any other prices. The live-data gate allows the Phase 2 GPU
  filter only, so storage is an amount the user enters.
- No saved calculations, named workloads or multi-workload portfolios. Nothing is written to any
  database, and there is no schema change.
- No calculator on synthetic marketplace groups, and no cross-provider comparison.
- No AI and no market brief (Phase 7). No new command-line tool.
- No "monthly" figures: the calculator reports for the hours entered.
- No hosting, publishing, live read, schedule or spending. No live figure in Git, the PR or
  reviews.
- No change to the constitution (PROJECT.md §5–6).

## Capabilities

### New Capabilities

- `workload-calculator`: workload inputs and their validation, the starting price, workload cost,
  the `scenarios-v1` scenario set, scenario figures and exposure, the Spot to pay-as-you-go
  fallback, the note for Spot prices above pay-as-you-go, budget headroom, and the independent
  check.

### Modified Capabilities

- `dashboard`:
  - ADDED "Workload cost view": the fourth tab and its states.
  - MODIFIED "Figure captions and framing line": workload and exposure captions, including
    "crosses rental types" and the scenario label.
  - MODIFIED "Display formatting": USD amounts at 2 decimals and percentages at 1 decimal.
- `synthetic-azure-snapshots`: "Synthetic Azure snapshot files": the demo file also covers a Spot
  size with no pay-as-you-go listing in its region.

## Impact

- New:
  - Package code:
    - `src/compute_cost_risk_monitor/scenarios.py`, frozen data only;
    - `calculator.py`, pure, with no Streamlit and no database;
    - `workload_check.py`, the independent check.
  - Tests:
    - calculator known-answer, edge and impossible cases;
    - independent-check tests, including tampered results and an import-independence test;
    - view-model unit tests;
    - AppTest flows on synthetic databases.
- Edited:
  - `dashboard.py`: workload frames, captions, formats and the chart spec.
  - `app.py`: the fourth tab.
  - `tests/fixtures/synthetic/azure_demo.json` and its README.
  - PROJECT.md §4 and §6, HANDOFF.md, the FigJam board and `docs/architecture/c4-container.svg`.
- Dependencies: none added. Altair and Streamlit are already declared.
- Local data: nothing is written to `data/monitor.duckdb`. The disposable `data/synthetic.duckdb`
  is rebuilt from the updated demo file.
- ⛔ gates:
  - Live data: honoured. The calculator reads stored rows read-only and fetches nothing, and live
    figures stay on this PC.
  - Scheduling, spend and publishing: untouched.
- Constitution: no amendment.
