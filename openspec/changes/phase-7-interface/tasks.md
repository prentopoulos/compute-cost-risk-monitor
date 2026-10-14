## 1. Direction and mock

- [x] 1.1 Run impeccable `shape` for the Workload cost screen (D17), with a scratch PRODUCT.md drawn from PROJECT.md §1 through `IMPECCABLE_CONTEXT_DIR` and nothing committed (D22). The owner rejected the first brief as too cluttered and asked for research on front-office screens. The research and the corrected direction are recorded in design § Brief, research and mock rounds
- [x] 1.2 21st.dev references (D15). Dropped: the owner approved the mock without them. No code copies were used
- [x] 1.3 Draw the Figma mock (D14) of the Workload cost screen at 1920×1080, on the owner's Pro seat, with synthetic demo figures and only Streamlit-buildable elements. Two quick rounds; the second ([node 5:2](https://www.figma.com/design/aODgN8zO3eCm9bmN8sOSCK?node-id=5-2)) was approved by the owner on 2026-10-14
- [x] 1.4 Run design-eval on the approved mock (Figma target, no taste reviewer):
  - v2 scored 25/40, with 0 P0, 4 P1 and 1 P2;
  - the owner chose the fixes, which became mock v3 and its state frames;
  - the second grilling round settled the open points, and the owner approved v3 on 2026-10-14 (D33–D46)

## 2. Ladder

- [x] 2.1 Freeze `ladder-v1` in `scenarios.py` (seven % steps and +0.50 USD/GPU-hour). Compute the ladder in `calculator.py` (ADDED "Scenario ladder ladder-v1"):
  - rows, plus the Custom and fallback rows;
  - columns, with the entered count marked;
  - signed cells, refused rows, and above-pay-as-you-go marks for Spot.

  Known-answer tests:
  - the five cells in design § Figures shown;
  - the 24-GPU column;
  - the match with `scenarios-v1`;
  - the refused Custom row;
  - the fallback row (240);
  - the Spot row at 60% of pay-as-you-go;
  - the frozen set
- [x] 2.2 Re-derive every ladder row, column, cell, refusal and mark in `workload_check.py` from plain values and `ladder-v1` (D20; MODIFIED "Independent check of workload figures"). Tests:
  - a tampered cell is named by row and column;
  - a dropped column, and a non-multiple column;
  - a wrong refusal or mark;
  - the correct result passes.

  Extend the calculator–check property test to the ladder. The core modules stay at 100% branch coverage

## 3. Theme and layout

- [x] 3.1 Add the dark `[theme]` to `config.toml` with v3's values (ADDED "Desk theme"; D4, D10, D13, D26, D31):
  - `primaryColor` #7AA2D6, `borderColor` #646E7C, red #EF6B63, green #5CC98A, `orangeColor` #F2CC60;
  - the grid's entered-column shade #1F2A3A as a dashboard constant;
  - chart colours from the same values, replacing `POINT_COLOUR` and `RULE_COLOURS` (D24).

  Repo tests:
  - base dark; no light or dark section, font faces or static serving;
  - the 4.5:1 floor for text, red, green, accent and amber on both backgrounds and the shade;
  - the 3:1 floor for the border;
  - no `<style>` in the source
- [x] 3.2 Sidebar and status line (MODIFIED "Dataset and source choice", "Comparable-group filters"; ADDED "Status line and key figures"; D28, D30, D33, D37, D42, D45):
  - "Dataset" and "Catalogue" dropdowns, with the "(synthetic)" suffix read from the run;
  - the "GPU", "GPUs per VM", "Pricing" and "Region" dropdowns;
  - regions by their stored `location` name;
  - the status line on every tab, with the data label in amber, AS OF in text colour, and STALE
- [x] 3.3 State messages as plain status words (D40, D41): REFUSED, CHECK FAILED, NOT NORMALIZED, NO SNAPSHOT, IN USE and open errors. Keep every existing message word for word and use no alert boxes
- [x] 3.4 Rework the Workload cost tab to v3 (MODIFIED "Workload cost view"; D6, D7, D25, D27, D29, D32, D34, D38, D46):
  - first tab, and no group line;
  - key figures (Cost, USD · USD/GPU-h · PAYG|SPOT · VMs · GPUs × h · Headroom), with "—" before the check;
  - the inputs row, including the custom unit switch;
  - the scenario grid (`st.table` and Styler: colours by sign, the entered column shaded and bold, the zero rule, "n/a" for refused rows, "*" and "†" marks);
  - the footer and its clauses (D9, D35, D36, D39);
  - the COST table, then Sources at full width;
  - remove the `scenarios-v1` table, the exposure chart, the workload introduction and the budget hint
- [x] 3.5 Sources everywhere (MODIFIED "Figure captions and framing line", "Region-group view", "Cross-region summary view", "Group browser"; D9, D27):
  - move every explanatory sentence and provenance field into Sources, word for word;
  - keep the terse tags on the page;
  - one exclusions footer per tab
- [x] 3.6 Apply the Comparable groups key figures in v3's grammar (cut item 3), and check Group browser and Data quality under the theme (cut item 1)

## 4. Verification

- [x] 4.1 AppTest flows on synthetic data:
  - the page opens on Workload cost;
  - the status line text: synthetic and live in amber, and STALE at an injected time;
  - the dataset and catalogue names;
  - key figures only after the check, with "—" and no price on a refused input or a failed check;
  - the demo's key figures and grid cells equal the `scenarios-v1` exposures;
  - the footer clauses for storage, "*", "†" and not-computed rows;
  - "n/a" cells;
  - the custom unit switch keeps each value;
  - no scenario table, chart, helper sentence or alert element on the page, and each sentence is in Sources;
  - inputs kept across tabs;
  - the marketplace and not-normalized states
- [x] 4.2 Local manual check on the synthetic database, in a visible Chrome window:
  - screenshots at 1920×1080 and 1440×900, compared with mock v3 and its state frames;
  - whether Source Sans's digits line up in the tables (D13);
  - the stock light theme from the Settings menu, viewed once (D4)

  Screenshots show synthetic data only
- [x] 4.3 Run design-eval on the built page (no taste reviewer). Fix every P0, and fix each P1 or record it with its reason (D2, D3)
- [x] 4.4 Run the compute-cost-risk-monitor-market-review read-through of the ladder, the key figures and the moved labels (PROJECT.md §3). Then run the gate and `uv audit`
- [ ] 4.5 Derive DESIGN.md from the shipped build with impeccable's documenter (D12; cut item 4)

## 5. Records and review

- [ ] 5.1 Write `docs/reviews/<date>-phase-7-interface.md`:
  - the brief, the research sources and the two mock rounds;
  - the mock and build critiques;
  - the manual check with its screenshots, synthetic only;
  - the market-review read-through;
  - what was cut, if anything
- [ ] 5.2 Run `/code-review` on the PR, fix findings in new commits or answer them, and record the outcome in the PR body
- [ ] 5.3 Update HANDOFF.md for the checkpoint after the merge, and archive the change on the branch
