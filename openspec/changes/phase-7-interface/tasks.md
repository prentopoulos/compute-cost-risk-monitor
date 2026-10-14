## 1. Direction and mock

- [ ] 1.1 Run impeccable `shape` for the Workload cost screen (D17). Context comes from a scratch PRODUCT.md drawn from PROJECT.md §1 through `IMPECCABLE_CONTEXT_DIR`, with nothing committed (D22). The brief pins:
  - D4–D6, D9, D10 and D13;
  - the "Desk theme" and "Answer strips" requirements;
  - the never-cut list in D3.

  The owner confirms the brief
- [ ] 1.2 Search 21st.dev for references: dense dark data tables, one-line summary strips, a scenario grid (D15). Searches carry synthetic figures only. Use at most 2 code copies a day, check each one's licence, and copy only values (spacing, sizes, colours) into the brief or the mock. Record what was used in the review record
- [ ] 1.3 Draw the Figma mock (D14), loading the Figma skills first:
  - one Figma Design frame of the Workload cost screen at 1920×1080, on the owner's Pro seat;
  - the theme values, the real labels, captions and notes, and synthetic figures from the demo's H100 ×8 pay-as-you-go group at 32 GPUs × 720 h;
  - only elements Streamlit can build: sidebar, tabs, one-column flow, inputs in a row, strip, ladder table, cost and scenario tables, chart, numbered notes
- [ ] 1.4 Run design-eval on the mock (Figma target, no taste reviewer). Fix P0 findings in the mock and record the rest. The owner approves the mock before task 3 starts

## 2. Ladder

- [ ] 2.1 Freeze `ladder-v1` in `scenarios.py` and compute the ladder in `calculator.py`: rows, columns with the entered count marked, signed cells, and above-pay-as-you-go marks for Spot (ADDED "Scenario ladder ladder-v1"). Known-answer tests:
  - the four cells in design § Figures shown;
  - the 24-GPU column;
  - the match with `scenarios-v1`;
  - the Spot row at 60% of pay-as-you-go;
  - the frozen set
- [ ] 2.2 Re-derive every ladder cell, column set and mark in `workload_check.py` from plain values and `ladder-v1` (D20; MODIFIED "Independent check of workload figures"). Tests:
  - a tampered cell is named by step and column;
  - a dropped column, and a non-multiple column;
  - a wrong mark;
  - the correct result passes.

  Extend the calculator–check property test to the ladder. The core modules stay at 100% branch coverage

## 3. Theme and layout

- [ ] 3.1 Add the dark `[theme]` to `config.toml` with the approved mock's values (ADDED "Desk theme"; D4, D13, D26):
  - chart colours from the same values, replacing `POINT_COLOUR` and `RULE_COLOURS` (D24);
  - repo tests: base dark, no light or dark section, no font faces, no static serving, the 4.5:1 contrast floor, and no `<style>` in the source
- [ ] 3.2 Rework the Workload cost tab to the approved mock (MODIFIED "Workload cost view", ADDED "Answer strips"; D6, D7, D25):
  - make it the first tab;
  - put the inputs in one row;
  - draw the strip and the ladder (`st.table`, Styler colours by effect) only after the check;
  - keep the cost table, scenario table, chart and headroom
- [ ] 3.3 Captions and notes (MODIFIED "Figure captions and framing line"; D9):
  - a one-line caption per figure with note numbers;
  - numbered notes once per panel, always visible;
  - the above-pay-as-you-go rows name their note;
  - every caption and note text unchanged word for word
- [ ] 3.4 Add the Comparable groups strip and the same caption and notes treatment to the region-group, cross-region and marketplace views (D2, D6; cut item 3)
- [ ] 3.5 Check Group browser and Data quality under the theme. Restyle beyond the theme only if time allows (cut item 1)

## 4. Verification

- [ ] 4.1 AppTest flows on synthetic data:
  - the page opens on Workload cost;
  - the strip and ladder appear only after the check, with no price on a refused input or failed check;
  - the demo's ladder cells equal the `scenarios-v1` exposures;
  - every figure's note numbers resolve to notes outside any expander;
  - inputs are kept across tabs;
  - the marketplace and not-normalized states are unchanged
- [ ] 4.2 Local manual check on the synthetic database, in a visible Chrome window:
  - screenshots at 1920×1080 and 1440×900;
  - whether Source Sans's digits line up in the tables (D13);
  - the stock light theme from the Settings menu, viewed once (D4);
  - the caption and note contrast

  Screenshots show synthetic data only
- [ ] 4.3 Run design-eval on the built page (no taste reviewer). Fix every P0, and fix each P1 or record it with its reason (D2, D3)
- [ ] 4.4 Run the compute-cost-risk-monitor-market-review read-through of the ladder and strips (PROJECT.md §3). Then run the gate and `uv audit`
- [ ] 4.5 Derive DESIGN.md from the shipped build with impeccable's documenter (D12; cut item 4)

## 5. Records and review

- [ ] 5.1 Write `docs/reviews/<date>-phase-7-interface.md`:
  - the mock and build critiques;
  - the 21st.dev references used, and their licences;
  - the manual check with its screenshots, synthetic only;
  - the market-review read-through;
  - what was cut, if anything
- [ ] 5.2 Run `/code-review` on the PR, fix findings in new commits or answer them, and record the outcome in the PR body
- [ ] 5.3 Update HANDOFF.md for the checkpoint after the merge, and archive the change on the branch
