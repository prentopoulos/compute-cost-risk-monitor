## Why

PROJECT.md Phase 7: front-office interface. The owner added this phase on 2026-10-13, ahead of
the public demo, which becomes Phase 8. The dashboard still uses Streamlit's default theme;
Phase 4 D6 kept custom styling back until now. The demo audience includes sales and trading
staff at firms such as Jane Street, Optiver and Two Sigma. They read dense, answer-first
screens, and the walkthrough will be recorded on whatever this phase ships.

The aim is to borrow a trading screen's discipline, not its costume. The data is published list
prices, so the page must never look like a live market (PROJECT.md §5).

The Phase 7 grilling ran one round on 2026-10-13:
- An informed-answerer subagent researched 14 questions and found 7 more.
- The main agent reopened its sources and moved two answers (21st.dev use, impeccable's
  PRODUCT.md) to settled, on a verified fact and a recorded basis.
- The owner reopened two settled answers (a Figma mock first, the 21st.dev free code copies),
  and both became owner calls.
- The owner then accepted every recommendation ("agreed on your changes then proceed").

Design D1–D15 are owner decisions; D16 onwards are settled with their basis.

## What Changes

- **Figma mock first.** One frame of the Workload cost screen at 1920×1080. It uses the dark
  theme, the real labels and synthetic figures, and only what Streamlit can build. The design
  review critiques it and the owner approves it before any layout code (D14).
- **Desk theme.** A dark theme in the committed `config.toml`, with one muted accent colour and
  Streamlit's bundled fonts. Chart colours come from the same values. There is no custom CSS,
  and no tickers, bid/ask, flashing prices or "live" badges. Red and green mark only a scenario's
  effect on the budget, always with its sign and words.
- **Answer first.**
  - The page opens on the "Workload cost" tab.
  - After the independent check passes, a one-line strip gives the total for the hours entered,
    the starting price and size, and the largest additional expense with its scenario name and
    set version.
  - "Comparable groups" gets a similar strip.
- **Scenario ladder `ladder-v1`.**
  - Rows: −50, −25, −10, +10, +25, +50 and +100% of the starting price.
  - Columns: 8, 16, 32, 64 and 128 GPUs, plus the entered count, all at the hours entered.
  - Cells: the signed exposure in USD for the hours entered.
  - It is frozen in `scenarios.py`, and every cell passes the independent check before it is
    shown.
- **Captions and notes.** Each figure keeps a one-line caption: group key, snapshot time, run
  ID, data label and its note numbers. Scenario figures also carry "Scenario calculation, not a
  forecast" and the set version. The full exclusions, storage, billing, Spot, judgement and
  above-pay-as-you-go texts appear once per panel as numbered notes, always visible, directly
  under it. No caption text is reworded.
- **Review.** A design-eval critique of the built page without the taste reviewer, the
  market-review read-through of the ladder, and `/code-review`. A DESIGN.md is derived from the
  shipped build if time allows.
- **Documents.**
  - PROJECT.md gains the new phase and budget, and the demo becomes Phase 8.
  - AGENTS.md, `openspec/config.yaml` and the build-safety skill are renumbered.
  - HANDOFF and `design-skills.md` are updated.
  - Two calibration examples are added to the informed-answerer brief.

## Non-goals

- No stack change, new runtime dependency or custom CSS (D16).
- No new source, fetch or stored data. No schema change.
- No change to an existing calculation, scenario set, group or map version. `scenarios-v1` keeps
  its names; the "PROJECT example" rename waits for Phase 8 (D8).
- No caption rewording: only where captions sit changes (D9).
- No hosting, publishing, live-data screenshots or live figures in Git, the PR, Figma or 21st.dev.
- No light theme and no self-hosted fonts (D4, D13).
- No rework of Group browser or Data quality beyond the theme (D2).
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
  - ADDED "Desk theme";
  - ADDED "Answer strips";
  - MODIFIED "Figure captions and framing line": a one-line caption per figure, plus numbered
    notes under each panel;
  - MODIFIED "Workload cost view": first tab, the strip, the ladder, and the starting price
    shown only after the check passes.

## Impact

- New:
  - `docs/reviews/<date>-phase-7-interface.md`;
  - the Figma design file, on the owner's Pro seat;
  - optionally `DESIGN.md`.
- Edited:
  - `src/compute_cost_risk_monitor/.streamlit/config.toml`;
  - `scenarios.py`, `calculator.py`, `workload_check.py`, `dashboard.py` and `app.py`;
  - their tests and `tests/repo/test_streamlit_config.py`;
  - PROJECT.md, AGENTS.md, `openspec/config.yaml`, the build-safety skill, HANDOFF.md,
    `.agents/skills/next-phase/design-skills.md` and `informed-answerer.md`.
- Dependencies: none.
- External services:
  - Figma, on the owner's seat;
  - 21st.dev, free search plus at most 2 code copies a day under the free tier (AI generation
    is off, with 0 credits).
  - Only synthetic figures reach either service.
- ⛔ gates:
  - Live data: honoured. There are no new reads, and live figures stay on this PC.
  - Spend: untouched. The 21st.dev free tier cannot charge.
  - Scheduling and publishing: untouched.
- Constitution: no amendment. The milestone table and budget are neither §5 rules nor ⛔ gates
  (D19).
