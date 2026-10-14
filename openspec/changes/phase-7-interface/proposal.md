## Why

PROJECT.md Phase 7: front-office interface. The owner added this phase on 2026-10-13, ahead of
the public demo, which becomes Phase 8. The dashboard still uses Streamlit's default theme;
Phase 4 D6 kept custom styling back until now. The demo audience includes sales and trading
staff at firms such as Jane Street, Optiver and Two Sigma. They read dense, answer-first
screens next to their Bloomberg terminals, and the walkthrough will be recorded on whatever
this phase ships.

The aim is to borrow a trading screen's discipline, not its costume. The data is published list
prices, so the page must never look like a live market (PROJECT.md §5).

The Phase 7 grilling ran one round on 2026-10-13:
- An informed-answerer subagent researched 14 questions and found 7 more.
- The main agent reopened its sources and moved two answers to settled.
- The owner reopened two settled answers (a Figma mock first, the 21st.dev free code copies).
- The owner then accepted every recommendation.

On 2026-10-13 and 2026-10-14 the owner corrected the design brief through two quick Figma mocks:
- plain, official wording with no helper text, "the way a Bloomberg terminal or quant tool
  reads";
- no line that repeats the sidebar;
- one scenario grid instead of a grid, a table and a chart.

The owner approved the second mock on 2026-10-14, and it now governs the layout.

Design D1–D15 and D27–D32 are owner decisions; D16–D26 are settled with their basis. D6–D10 and
D14 were revised after the mock.

## What Changes

- **Approved mock.** One Figma frame of the Workload cost screen at 1920×1080
  ([node 5:2](https://www.figma.com/design/aODgN8zO3eCm9bmN8sOSCK?node-id=5-2)). The build
  follows it.
- **Desk theme.**
  - A dark theme in the committed `config.toml`, with a steel-blue accent and Streamlit's
    bundled fonts.
  - Amber only for the data label and the stale warning; red and green only for a scenario's
    effect.
  - Chart colours come from the same values.
  - No custom CSS, no helper text, and no tickers, bid/ask, flashing prices or "live" badges.
- **Status line and key figures.**
  - **Status line:** one terse line, for example `COMPUTE COST & RISK MONITOR · SYNTHETIC DATA —
    NOT AZURE LIST PRICES · AS OF 12 OCT 2026 09:00 UTC`.
  - **Workload key figures:** COST, USD · USD / GPU-HOUR · VMS · +100%, USD, plus HEADROOM when a
    budget is entered. They appear only after the independent check passes.
  - **Comparable groups key figures:** the same style.
- **Scenario ladder `ladder-v1`, the single scenario grid.**
  - Rows: −50, −25, −10, +10, +25, +50 and +100% of the starting price, plus a flat +0.50
    USD/GPU-hour row. A custom move adds a row, and a Spot start adds a "Spot → pay-as-you-go"
    row that crosses rental types.
  - Columns: 8, 16, 32, 64 and 128 GPUs, plus the entered count; the entered column is shaded.
  - Cells: the signed change in cost in whole USD for the hours entered.
  - It is frozen in `scenarios.py`, and every cell passes the independent check before it is
    shown.
  - The `scenarios-v1` table and the exposure chart leave the page. `scenarios-v1` stays frozen
    and computed, and its moves are ladder rows.
- **Compliance footer and Sources.**
  - One footer line under the ladder: "Scenario calculation, not a forecast." followed by the
    exclusions sentence.
  - A closed "Sources" section holds the rest:
    - group key, snapshot time, run ID and data label code;
    - scenario-set versions;
    - the storage, billing, Spot, judgement and above-pay-as-you-go texts;
    - source records.
- **Plain names.** Regions are shown by the source's own `location` name. The repeated group line
  is gone.
- **Review.** A design-eval critique of the mock and of the built page without the taste
  reviewer, the market-review read-through of the ladder, and `/code-review`. A DESIGN.md is
  derived from the shipped build if time allows.
- **Documents.**
  - PROJECT.md gains the new phase and budget, and the demo becomes Phase 8.
  - AGENTS.md, `openspec/config.yaml` and the build-safety skill are renumbered.
  - HANDOFF and `design-skills.md` are updated.
  - Two calibration examples are added to the informed-answerer brief.

## Non-goals

- No stack change, new runtime dependency or custom CSS (D16).
- No new source, fetch or stored data. No schema change.
- No change to an existing calculation, group or map version. `scenarios-v1` is unchanged and no
  `scenarios-v2` is made (D8).
- No light theme and no self-hosted fonts (D4, D13).
- No rework of Group browser or Data quality beyond the theme and the status line (D2).
- No hosting, publishing, live-data screenshots or live figures in Git, the PR, Figma or 21st.dev.
- No diagram changes: no component, data flow or schema changes.
- No Phase 8 items: demo dataset, methodology document, market brief, walkthrough.
- No change to the constitution (PROJECT.md §5 and the ⛔ gates).

## Capabilities

### New Capabilities

None. The ladder extends `workload-calculator`, and the theme and layout extend `dashboard`.

### Modified Capabilities

- `workload-calculator`:
  - ADDED "Scenario ladder ladder-v1";
  - MODIFIED "Independent check of workload figures": it also re-derives every ladder cell.
- `dashboard`:
  - ADDED "Desk theme" and "Status line and key figures";
  - MODIFIED "Figure captions and framing line": the status line, the compliance footer and
    Sources;
  - MODIFIED "Workload cost view": first tab, key figures, the ladder and the cost table. No
    scenario table or chart.
  - MODIFIED "Comparable-group filters": regions by their source location name;
  - MODIFIED "Display formatting": whole USD in the ladder.

## Impact

- New:
  - `docs/reviews/<date>-phase-7-interface.md`;
  - the Figma design file, on the owner's Pro seat;
  - optionally `DESIGN.md`.
- Edited:
  - `src/compute_cost_risk_monitor/.streamlit/config.toml`;
  - `scenarios.py`, `calculator.py`, `workload_check.py`, `groups.py` (location name),
    `dashboard.py` and `app.py`;
  - their tests and `tests/repo/test_streamlit_config.py`;
  - PROJECT.md, AGENTS.md, `openspec/config.yaml`, the build-safety skill, HANDOFF.md,
    `.agents/skills/next-phase/design-skills.md` and `informed-answerer.md`.
- Dependencies: none.
- External services:
  - Figma, on the owner's seat;
  - 21st.dev, free tier, which was not needed for the approved mock.
  - Only synthetic figures reach either service.
- ⛔ gates:
  - Live data: honoured. There are no new reads, and live figures stay on this PC.
  - Spend: untouched.
  - Scheduling and publishing: untouched.
- Constitution: no amendment. The milestone table and budget are neither §5 rules nor ⛔ gates
  (D19). The required labels stay on screen in shorter form (D9).
