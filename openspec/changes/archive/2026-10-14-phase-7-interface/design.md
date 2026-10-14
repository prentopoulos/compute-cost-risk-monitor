## Context

This is Phase 7 of PROJECT.md §6, added by the owner on 2026-10-13. The owner asked whether the
interface should become "something more professional looking that suits a screen a jane street,
optiver, 2 sigma sales and options trader or other front office role would want to see in front
of them". Asked where that belongs, the owner chose "New phase before demo": this phase covers
the theme, an answer-first layout and a scenario ladder, and the demo becomes Phase 8.

The main agent's recommendation, accepted with that choice, has four parts:
- borrow a trading screen's discipline, not its costume;
- stay on Streamlit (PROJECT.md §4, "decided"), because a React rewrite would discard the
  AppTest-based tests;
- add a scenario ladder: price change × GPU count → signed change in cost;
- use 21st.dev for inspiration.

The grilling ran one round on 2026-10-13:
- **Round 1:** an informed-answerer subagent researched 14 questions and found 7 more. It was
  resumed once after an API usage limit stopped it.
- **Re-check:** the main agent reopened the sources behind the settled answers:
  - Streamlit 1.65's note preferring theming over custom CSS (`streamlit/elements/html.py`);
  - the workload-calculator spec's "Workload cost" and "Independent check" requirements;
  - Phase 5 design's live spread of a flat $0.50 against the lowest price per group;
  - PROJECT.md § Amending the constitution;
  - the references to Phase 7 in PROJECT.md, AGENTS.md and the build-safety skill.
- **Reclassified as settled:** 21st.dev use, on a fact (`get_usage`, 2026-10-13: free tier, AI
  generation off, 0 credits, 2 free code copies a day); and impeccable's PRODUCT.md, on a
  recorded basis.
- **Owner reopened:** a Figma mock first, and the free 21st.dev code copies. Both became owner
  calls (D14, D15).
- **Owner:** accepted every recommendation ("agreed on your changes then proceed").

### Brief, research and mock rounds (2026-10-13 to 2026-10-14)

1. **First brief rejected.** impeccable `shape` produced a brief, a "desk risk sheet" with one-line
   captions and numbered notes. The owner rejected it as "too cluttered". The owner asked for no
   internal terms ("snapshot") and for the screen an options sales trader at Jane Street, Optiver
   or Citadel Securities would keep next to their Bloomberg terminals, and asked for research.
2. **Research (2026-10-13).** The firms' internal tools are not public. Professional tools agree
   on four things:
   - a scenario grid of price moves with profit and loss against the current position, which is
     marked ([TT Options Risk Matrix](https://library.tradingtechnologies.com/trade/orm-options-risk-matrix-display.html);
     [IB Risk Navigator](https://www.interactivebrokers.com/campus/trading-lessons/risk-navigator-plot-viewer-selector/));
   - colour by sign: green gain, red loss ([US7774249](https://patents.google.com/patent/US7774249));
   - colour only for status, with one neutral colour for everything else and a colour-blind
     scheme ([Bloomberg UX](https://www.bloomberg.com/ux/2021/10/14/designing-the-terminal-for-color-accessibility/));
   - dark grounds for long hours in dim rooms.
3. **Quick mock 1.** The owner chose steel blue, rename now, no bar chart, and inputs under the
   key figures. The owner then corrected it: "this is repetition" (the group line repeats the
   sidebar), and "remove the AI explainers ... this needs to look official with no helpers like
   bloomberg terminal or quant analysis tool".
4. **Quick mock 2** ([node 5:2](https://www.figma.com/design/aODgN8zO3eCm9bmN8sOSCK?node-id=5-2)),
   approved by the owner on 2026-10-14 ("i like this design approved"). It has:
   - terse labels with units, and no helper text;
   - one status line;
   - key figures, then inputs;
   - one scenario grid, and one compliance footer;
   - a cost table, and a closed Sources section.

   D6–D10 and D14 below are revised to match it, and D27–D32 record its other choices.
5. **design-eval on v2 (2026-10-14):** reviewer A did the design review, reviewer B the detector
   and contrast evidence, and the taste reviewer was not run (D17).
   - Result: 25/40, 0 P0, 4 P1, 1 P2. The snapshot is local in `.impeccable/critique/`.
   - The owner chose, in order: fix honesty and conditions first, then all P1 and P2; keep the
     GPU columns; put "GPUs × h" where "+100%, USD" was.
6. **Mock v3 and its states** ([node 7:2](https://www.figma.com/design/aODgN8zO3eCm9bmN8sOSCK?node-id=7-2)):
   - the main screen, plus refused input (8:2), check failed (8:115), Spot without a
     pay-as-you-go listing (8:228), and storage and budget entered (8:519);
   - live (8:799) and stale (8:806) headers.

   Measured contrast (design-eval `contrast.mjs`):

   | Pair | Ratio |
   |---|---|
   | red on the entered-column shade | 4.79 |
   | red on the background | 6.26 |
   | accent on the shade | 5.49 |
   | green on the shade | 7.02 |
   | control borders on the background | 3.66 |
   | control borders on the panel | 3.35 |
   | shade on the background | 1.31 |

   The 1.31 is a named exception: bold text and the accent header also mark the column. The
   closing audit found no text under 12 px and no faded layers.
7. **Grilling round 2 (2026-10-14).** The informed answerer researched 8 questions and found 7 more.
   The owner agreed every recommendation ("Agrees"). Those are D33–D39; D40–D46 are settled.
   Where v3 and these decisions differ (the custom unit switch, "n/a" cells, the † mark and the
   footnote wording), the decisions and the specs govern the build.

### Measured facts (2026-10-13, main at 2c0eb60)

- **Versions:** Streamlit 1.65.0 and Altair 6.3.0 (`uv.lock`).
- **Theming:**
  - `[theme]` takes a base, colours, chart palettes, dataframe header and border colours, radii
    and bundled or self-hosted fonts.
  - `[theme.light]` and `[theme.dark]` make switchable themes.
  - `base`, `fontFaces`, `baseFontSize` and the metric font options go in `[theme]` only.
  - Source: Context7 `/streamlit/docs`, config.toml reference.
- **GPUs per VM:** compared rows have 1, 2, 4 or 8 GPUs per VM. Fractional sizes are excluded
  (`normalize.py`, `fractional_gpu`), so 8, 16, 32, 64 and 128 are whole multiples for every
  group.
- **Region names:** the schema stores Azure's `location` display name beside `arm_region_name`
  (`schema/001_initial.sql`, `azure_retail.py`). It is optional, so it can be missing.
- **Flat $0.50 against the lowest listed price per group (live, Phase 5 design):**

  | Share of the price | Groups |
  |---|---|
  | under 5% | 124 |
  | 5–25% | 375 |
  | 25–100% | 356 |
  | 100% or more | 74 |
- **Display:** the owner's PC has one 1920×1080 display at 100% scaling.
- **Synthetic demo figures used in the mock:** H100 NVLink 80GB × 8, eastus, pay-as-you-go,
  Standard_ND96isr_H100_v5, 12.0000 USD/GPU-hour (96.00 USD per VM-hour), snapshot 2026-10-12
  09:00 UTC. 32 GPUs × 720 h = 276,480.00 USD.
- **Hard-coded chart colours:** `dashboard.py` sets `POINT_COLOUR` and `RULE_COLOURS` for the
  default light theme.

## Goals / Non-Goals

**Goals:**
- Make the dashboard read like an official desk tool without implying a market.
- Lead with the commercial answer: cost and its sensitivity to price moves.
- Make the ladder the single scenario grid, checked like every other figure.
- Keep every required label on screen in its shortest honest form, and put the rest one click
  away.

**Non-Goals:** as in the proposal.

## Decisions

| # | Decision | Who / basis |
|---|---|---|
| D1 | Roadmap: a new Phase 7 before the demo, which becomes Phase 8. One more session | **owner** (Scope) |
| D2 | Scope:<br>- a custom theme for the whole app;<br>- the approved layout for "Workload cost" and "Comparable groups", whose region-group, cross-region and marketplace views share the `_groups` code;<br>- the ladder.<br>Group browser and Data quality get the theme and the status line only.<br>**Acceptance:**<br>- AppTest flows on synthetic data, including known-answer ladder cells;<br>- every ladder cell passes the independent check, with the core modules still at 100% branch coverage;<br>- a local manual check with synthetic-only screenshots at 1920×1080 and 1440×900, compared with the approved mock;<br>- design-eval on the mock and on the build without the taste reviewer: no P0 open, and every P1 fixed or recorded with its reason;<br>- the market-review read-through of the ladder, and `/code-review`.<br>No diagram change | **owner** (Scope) |
| D3 | Timebox: one session of about 3¾ h, including the mock. The mock rounds ran over (two quick mocks); the build session keeps the cut order.<br>**Cut in this order:**<br>1. restyling Group browser and Data quality beyond the theme and status line;<br>2. chart restyling beyond theme colours;<br>3. the Comparable groups key figures;<br>4. DESIGN.md (D12);<br>5. P1 fixes after the first pass, recorded for Phase 8. P0 fixes are always made.<br>**Never cut:**<br>- the data label, the as-of time and the compliance footer;<br>- the Sources section;<br>- the independent check on every shown figure, and no price before it passes;<br>- the D10 colour rules and no market costume;<br>- the three local-only config settings;<br>- the theme, the Workload layout and the ladder with its known-answer tests;<br>- AppTest flows, the manual check, the green gate, counts-only Git;<br>- the design-eval runs | **owner** (Scope, Value trade-off, Private knowledge) |
| D4 | Visual direction: one dark "desk" theme.<br>- `[theme] base = "dark"`, a near-black neutral background, a second neutral for the sidebar and inputs, and chart palettes from the theme;<br>- no `[theme.light]` or `[theme.dark]` sections;<br>- no logo.<br>Streamlit's menu is hidden (D47), so a viewer cannot switch to its stock light theme | **owner** (Showcase); revised by D47 |
| D5 | Target screen: 1920×1080 first (Chrome maximised, 100% zoom), checked at 1440×900 | **owner** (Private knowledge, Showcase) |
| D6 | Layout, revised 2026-10-14 to mock v3 (Figma node 7:2):<br>- **Status line:** `COMPUTE COST & RISK MONITOR` · data label · `AS OF <d MON yyyy HH:MM> UTC`, separated by "·", plus STALE when it applies (D9).<br>- **Tabs:** Workload cost, Comparable groups, Group browser, Data quality. The page opens on Workload cost.<br>- **Workload key figures:** "Cost, USD" · "USD/GPU-h · PAYG" (or "· SPOT") · "VMs" (count × short size name, D46) · "GPUs × h" · "Headroom, USD/GPU-h" when a budget is entered. They are drawn only after the independent check passes; otherwise each label shows "—".<br>- **Inputs**, one row under the key figures: Size (only when the group has several members), GPUs, Hours, "Storage, USD", "Custom, %" or "Custom, USD/GPU-h" with a unit switch (D34), "Budget, USD".<br>- **Below the inputs:** the scenario grid, its footer, the COST table (USD/VM-h, VM-h, USD for compute, storage and total), then a closed "Sources" section at full width.<br>- **Comparable groups:** the same status line; key figures "Lowest, USD/GPU-h · PAYG" (or "· SPOT"), "Size" and "Members", with tags; the member and cross-region tables; the footer; Sources.<br>- No group line (the sidebar shows the selection), no `scenarios-v1` table, no exposure chart.<br>- The starting price appears only with the checked figures | **owner** (Showcase, Scope); revised after the owner's mock corrections and the v2 critique |
| D7 | Scenario ladder `ladder-v1`, frozen in `scenarios.py`, revised 2026-10-14 to be the single scenario grid:<br>- **Rows:** −50, −25, −10, +10, +25, +50 and +100% of the starting price, then a flat "+0.50 USD/GPU-h" row (PROJECT.md §1's worked example).<br>- **Extra rows:** a "Custom" row when a custom move is entered; a "Spot → pay-as-you-go" row for a Spot start, which crosses rental types and is marked.<br>- **Columns:** 8, 16, 32, 64 and 128 GPUs, plus the entered count when it is not one of them, all at the hours entered. The entered column is shaded and bold, with no label.<br>- **Cells:** the signed change in cost, in whole USD, for the hours entered. Storage is unchanged.<br>- A row whose price would be zero or below, or a fallback row with no pay-as-you-go listing, shows "n/a" in every cell (D38), with its reason as a footer clause.<br>- The grid is titled "SCENARIO GRID · Δ cost, USD · <hours> h", with a 2 px zero rule between −10% and +10% and a 1 px rule above the flat and extra rows.<br>- `ladder-v1`, "Scenario calculation, not a forecast" and the judgement note are carried by the footer and Sources (D9) | **owner** (Methodology, Scope, Showcase) |
| D8 | `scenarios-v1` stays frozen and computed in the calculator and its check, and in the end-to-end and property tests. The page no longer shows its table. Its moves appear as ladder rows labelled by the move itself, which meets the owner's "rename now" ("+0.50 USD/GPU-h" replaces "PROJECT example +$0.50/GPU-hour" on screen). No `scenarios-v2` | **owner** (Methodology, Showcase); revised 2026-10-14 |
| D9 | Required labels, revised 2026-10-14:<br>- **Status line:** the data label (`SYNTHETIC DATA — NOT AZURE LIST PRICES`, or `AZURE PUBLISHED LIST PRICES`), `AS OF` the snapshot start in UTC, and `STALE — OLDER THAN 7 DAYS AS OF <UTC>` when stale.<br>- **Footer:** under the grid, "Scenario calculation, not a forecast." followed by the exclusions sentence word for word. Then, only when they apply:<br>&nbsp;&nbsp;- "Total includes USD X storage entered by you.";<br>&nbsp;&nbsp;- the "*" crossing clause (D35);<br>&nbsp;&nbsp;- the "†" above-pay-as-you-go clause (D36);<br>&nbsp;&nbsp;- each not-computed reason.<br>- The footer labels every scenario figure on the screen, Headroom included (D39).<br>- **Sources section,** closed, one click away:<br>&nbsp;&nbsp;- the group key and snapshot start (UTC);<br>&nbsp;&nbsp;- the run ID and data label code (`live`, `recorded`, `synthetic`);<br>&nbsp;&nbsp;- `ladder-v1` and `scenarios-v1`;<br>&nbsp;&nbsp;- the storage, billing assumptions, Spot, judgement and above-pay-as-you-go texts;<br>&nbsp;&nbsp;- the source records (item key, raw file, SHA-256).<br>- The owner's reading: one footer on a screen states the exclusions with every workload figure on that screen | **owner** (Methodology, Conflict, Showcase); approved with the mock |
| D10 | Colour:<br>- red marks an added cost and green a saving, always with the sign;<br>- the two shades also differ in lightness, checked with a colour-blindness simulation in the critique;<br>- amber only for the data label, live or synthetic (D42), and the stale warning;<br>- the steel-blue accent only for the active tab and the entered column;<br>- everything else neutral, including every state message: REFUSED, CHECK FAILED, NOT NORMALIZED, NO SNAPSHOT, IN USE and open errors are plain status words in text colour, never Streamlit's coloured alert boxes (D40, D41);<br>- no tickers, bid/ask, flashing or animated values, or "live" badges | **owner** (Showcase); amber and accent use approved with the mock |
| D11 | Phase name: "Front-office interface" | **owner** (Showcase) |
| D12 | DESIGN.md: written last (cut item 4) with impeccable's documenter, derived from the shipped `config.toml` and code. It says that `config.toml` holds the theme values and that PROJECT.md §5 outranks it | **owner** (Value trade-off, Showcase) |
| D13 | Fonts: Streamlit's bundled Source Sans and Source Code. No font URL and no self-hosting. Whether Source Sans's default digits are tabular is measured in the manual check | **owner** (Showcase) |
| D14 | Figma mock first, constrained to what Streamlit can build. It was drawn on the owner's Pro seat (Projects team) in "Compute Cost & Risk Monitor · Interface (Phase 7)". There were two quick rounds, and the second was approved on 2026-10-14. design-eval ran on it, without the taste reviewer. The fixes became v3 and its state frames, approved on 2026-10-14 (D33) as the build target. The owner reopened this from "settled (default): no mock": "that's a reason to constrain the mock, not skip it" | **owner** (Showcase, Value trade-off) |
| D15 | 21st.dev: free search and at most 2 code copies a day, values only, licences checked, synthetic figures only. Not used: the owner approved the mock without 21st.dev references | **owner** (Private knowledge) |
| D16 | Styling uses only:<br>- `config.toml` `[theme]`;<br>- `st.column_config`;<br>- pandas Styler colours, font weights and borders on the grid and the COST table (Styler styles are scoped to that table by `st.table`);<br>- Streamlit's coloured-text markdown for the status line;<br>- theme-driven Altair colours.<br>No injected CSS. What would change it: a P0 or P1 finding that no theme key can fix. Then one CSS file loaded with `st.html`, targeting only documented `st-key-<key>` classes, with a test pinning Streamlit 1.65 | settled (default). Streamlit 1.65 `elements/html.py`: "Prefer native Streamlit features and theming over custom CSS or HTML" |
| D17 | Process: impeccable `shape` brief, then the Figma mock (D14), a design-eval critique of the mock, the build, a design-eval critique of the build, and an impeccable polish pass. The tasteskill is not used | recorded. `.agents/skills/next-phase/design-skills.md` |
| D18 | Renumbering:<br>- Phase 7 is the interface, and Phase 8 the demo.<br>- The budget is eight sessions, about 24–29 h.<br>- Phase 7 references are updated in PROJECT.md §1, §2 and §6, AGENTS.md, `openspec/config.yaml` and the build-safety skill, and HANDOFF's demo findings are relabelled Phase 8.<br>- Archives are not edited. Phase 1's acceptance row "7 Demo and brief" now applies to Phase 8 | recorded. D1; PROJECT.md:26 plus about 3¾ h (D3) |
| D19 | Not a constitution amendment. PROJECT.md §5 defines the constitution as the §5 rules plus the ⛔ gates in §6, and an amendment as changing a rule or adding, removing or loosening a gate. The milestone table and budget are neither, and the publishing gate's wording is unchanged | recorded. PROJECT.md § Amending the constitution |
| D20 | Ladder checks:<br>- `workload_check` re-derives every ladder cell from plain values and `ladder-v1`, imported as data. That covers the % rows, the USD row, the custom row and the fallback row.<br>- For a Spot start, a row priced above the size's pay-as-you-go price is marked and gets the above-pay-as-you-go note in Sources.<br>- Nothing is shown unless every check passes | recorded. workload-calculator spec, "Independent check of workload figures" and "Spot price above pay-as-you-go" |
| D21 | The ladder and key figures state the hours entered, never "monthly" | recorded. workload-calculator spec, "Workload cost"; Phase 5 D14 |
| D22 | No PRODUCT.md (impeccable's product file) is committed. impeccable reads a scratch PRODUCT.md drawn from PROJECT.md §1 through `IMPECCABLE_CONTEXT_DIR`. `.impeccable/` stays out of Git, and the scored reviews go to `docs/reviews/` with synthetic figures only | recorded. PROJECT.md owns scope (AGENTS.md); PR #6 |
| D23 | Records corrected: `design-skills.md` and HANDOFF now say the 21st plugin is installed, the key is in the user environment, and the account is free tier with AI generation off | fact. `installed_plugins.json`; `get_usage` on 2026-10-13 |
| D24 | Chart colours come from the theme's values, replacing `POINT_COLOUR` and `RULE_COLOURS`, with their contrast checked on the dark background. One commit undoes it | settled (default) |
| D25 | The ladder is drawn with `st.table` and Styler colours, not `st.dataframe`. An HTML table paints in a hidden Chrome window and reads as page text, and AppTest exposes it | settled (default). HANDOFF (the data grid's canvas does not paint in a hidden window) |
| D26 | Contrast floor, checked by a repo test from the committed config and the grid's shade constant:<br>- `textColor`, `redColor`, `greenColor`, `primaryColor` and the amber each reach at least 4.5:1 against `backgroundColor`, against `secondaryBackgroundColor` and against the entered-column shade;<br>- `borderColor` reaches at least 3:1 against both backgrounds.<br>Values from v3: text #E6E8EB, red #EF6B63, green #5CC98A, accent #7AA2D6, amber #F2CC60, shade #1F2A3A, border #646E7C | settled (default). WCAG 2.2 AA 1.4.3 and 1.4.11; measured in round 1 of the v2 critique and on v3 |
| D27 | No helper text: terse labels with units, no explanatory sentences, hints or "(optional)". Explanations live in Sources. Input placeholders are "—" | **owner**, 2026-10-14: "this needs to look official with no helpers like bloomberg terminal or quant analysis tool" |
| D28 | The time label is "AS OF", not "snapshot". The owner asked for a plain date and time. "As of" was chosen over "last updated" because the time is when the prices were fetched, not when Microsoft changed them | **owner** (request and approved mock); wording by the main agent |
| D29 | The exposure bar chart is removed from Workload cost | **owner**, 2026-10-13 |
| D30 | Regions are shown by the source's stored `location` display name, falling back to the region code when it is missing. No hand-made name map | settled (default). Fact: `location` is stored (schema 001). What would change it: the owner wants different names |
| D31 | Accent: steel blue, `#7AA2D6` in the mock, tuned only to meet D26 | **owner**, 2026-10-13 (mock A) |
| D32 | Number format: ladder cells in whole USD with a sign and thousands separators; key figures and the cost table to 2 decimals; USD/GPU-hour to 4 decimals | **owner** (approved mock) |
| D33 | Mock v3 (node 7:2) and its state frames (8:2, 8:115, 8:228, 8:519, 8:799, 8:806) replace v2 as the build target. Their new copy is approved:<br>- "Catalogue" and "Azure VMs (synthetic)" / "Marketplace (synthetic)";<br>- "REFUSED" and "CHECK FAILED";<br>- "Total includes USD X storage entered by you.";<br>- "GPUs × h" and "Headroom, USD/GPU-h".<br>The "(synthetic)" suffix is read from the source's latest succeeded run label, never from the file; live and recorded data get no suffix, never "(live)" | **owner**, 2026-10-14 ("Agrees") |
| D34 | Custom move: one number input and a horizontal unit switch "%" / "USD/GPU-h" (`custom_kind`). The label follows the unit ("Custom, %" or "Custom, USD/GPU-h"). As in Phase 5 D24, each unit has its own keyed input with `value=None`, so switching never reinterprets a value | **owner** (Showcase, Methodology); TT Options Risk Matrix offers an absolute or a percentage adjustment; Phase 5 D5 |
| D35 | A grid row that crosses rental types is labelled "Spot → PAYG *". The footer always shows "* Crosses rental types (Spot → pay-as-you-go): same size, same region.", plus "Not computed: no pay-as-you-go listing for this size in this region." when it is not computed. Sources names both group keys. This states the crossing plainly (PROJECT.md §5) | **owner** (Conflict, Methodology) |
| D36 | Spot rows priced above the same size's pay-as-you-go list price, and the headroom figure when it is, carry "†". The footer adds "† Above this size's pay-as-you-go list price (USD x/GPU-h): the arithmetic, not what Azure would bill." The full note stays in Sources | **owner** (Showcase, Methodology) |
| D37 | Dataset names: "Synthetic demo" (`data/synthetic.duckdb`) and "Azure list prices (local only)" (`data/monitor.duckdb`). The word "live" is never used | **owner** (Showcase) |
| D38 | A ladder cell that is not computed shows "n/a". "—" means an empty input or storage not entered | **owner** (Showcase; thin evidence that a dash reads as zero) |
| D39 | The footer's "Scenario calculation, not a forecast." labels every scenario figure on the screen, the Headroom key figure included. The headroom sentence moves to Sources | **owner** (Conflict, Methodology) |
| D40 | Refused input and a failed check show a plain status word ("REFUSED" or "CHECK FAILED") in text colour, with the existing message word for word below it, and no alert box | settled (recorded). The specs never name `st.warning` or `st.error`; D10 |
| D41 | Every other state message is also a plain neutral status word plus its existing text: NOT NORMALIZED, NO SNAPSHOT, IN USE and open errors. The mixed-labels warning may use amber, since it concerns the data label | settled (recorded). Streamlit's alerts take the theme's basic palette (Context7 `/streamlit/docs`, 2026-10-14), which D10 reserves |
| D42 | The live data label is amber too | settled (recorded). The Desk theme spec and D10 already say "amber only for the data label"; §5 governs the label's words, not its colour |
| D43 | Renaming "Source" to "Catalogue" (D33) changes the marketplace note's source name and the Data quality panel headings, and tests that read sidebar options by position | settled (fact). `test_app.py`, `dashboard.SOURCE_NAMES` |
| D44 | A refused Custom row is shown like the fallback: "n/a" cells, and "Not computed: the price would be zero or below." as a footer clause | settled (recorded). workload-calculator delta |
| D45 | Dataset and Catalogue are dropdowns (`st.selectbox`), as in the mock, and the position-based tests are updated. What would change it: test churn too large for the budget | settled (default). Owner-approved mock |
| D46 | Key figures show short size names: drop the `Standard_` prefix and turn `_` into spaces. Stored names stay in the member table and Sources | settled (recorded). Owner-approved v2 ("4 × ND96isr H100 v5") |
| D47 | `client.toolbarMode = "minimal"` hides Streamlit's menu, which removes its theme switch. The manual check (task 4.2) measured the grid in the stock Light theme: red 3.02, green 2.06 and the entered column 1.16 against 4.5:1, because the grid's colours are tuned for the dark theme. It also hides the print and screencast items; developer options and Deploy were already hidden | **owner**, 2026-10-14 ("Hide the menu"); Streamlit config docs (Context7 `/streamlit/docs`): "minimal" shows only options set externally, and hides the menu when none are left |
| D48 | Two fixes from the manual check on the Comparable groups tab. (1) Tags are inline code, which Streamlit colours with `greenTextColor` by default, so they showed in the saving green; `codeTextColor` is now the muted grey on the panel colour. (2) The ACROSS REGIONS table, its chart and the Group browser showed region codes while the Region filter showed stored names (D30); they now show the same names, sorted by name ignoring case. Sources keep the code, since it is part of the group key | settled (recorded). D10 "everything else neutral"; the filter requirement's "Regions SHALL be shown by the source's stored `location` name"; Context7 `/streamlit/docs`: `codeTextColor` "defaults to the resolved value of `greenTextColor`" |
| D49 | The build critique (task 4.3; 27/40, 0 P0, 1 P1, 4 P2) and the owner's answers:<br>- **P1, Budget:** the input is relabelled "Contingency, USD". It holds money set aside for price rises, which the headroom (B ÷ (GPUs × h)) uses up. Beside "Cost, USD", "Budget" invited a total budget: 300,000 against a 276,480.00 cost showed "+13.0208 (108.5%)", not the true +1.0208 (8.5%). The calculation, the independent check and the Sources sentence are unchanged; the four refusal messages say "Contingency";<br>- **P2, one column:** everything under the inputs sits in `st.container(width=960)`. The Styler minimum widths size the grid to about 945 px (10rem + 5 × 11.5rem) and COST to about 540 px (10rem + 3 × 9.5rem), as in mock v3; the built grid had been 665 px. The unit switch moves into the Custom column, above its input;<br>- **P2, footer:** each clause on its own line, its mark first, joined by hard line breaks. The wording is unchanged;<br>- **P2, accent:** Streamlit paints `primaryColor` on the selected radio, a toggle that is on and focus rings, which cannot be separated without injected CSS. The accent now means the current or selected state, plus the entered column;<br>- **P2, drift:** USD/GPU-h in every table header and the chart axis; COST's USD/VM-h keeps every stored decimal and never fewer than two (D32); the chart axis asks for about 8 ticks. Unused scenario-table format names are removed.<br>- **Closing audit:** the build's group tags were inline code, which Streamlit fixes at 0.75em (10.5 px), below the 12 px floor; they are now muted text at body size (14 px). COST is sized to its content (`width="content"`, 539 px). Measured: table cells, headers and widget labels 12.25 px; body and footer 14 px; key-figure values 22.4 px. At 1920×1080 everything down to COST fits above the fold and the closed Sources bar sits just below it;<br>Recorded, not fixed: the faint 2 px zero rule (2.46:1, decorative), exponent form for a tiny custom move, Data quality's headings and field names (out of scope by D2), the two meanings of "AS OF" (D9, D28), and the region in the price label (the owner rejected the repeated group line in mock 1) | **owner**, 2026-10-14 ("Rename the label", "P1 + all P2s", "Match the mock, ~950 px", "Accept as selected state"); reviewers A and B; Context7 `/streamlit/docs` and the installed 1.65 signature: `st.container(width=int)` sets a fixed width, capped at the parent's |
| D50 | `/code-review` on PR #13 (15 findings; the ladder maths and its independent check held). Fixed:<br>- **Grid width:** the GPU columns share 57.5rem, so a sixth column for an entered count (24 GPUs) keeps the grid inside the 960 px column; it had needed about 1,106 px;<br>- **Withheld:** Comparable groups and Group browser say "The group views are withheld…" when the snapshot is not normalized; they had shown the workload message and "NO GROUPS";<br>- **Above-PAYG note:** it ends "See the 'Spot → PAYG *' row."; it had named a row of the removed scenarios table;<br>- **Custom label:** up to 4 decimals, more when 4 would round it, so −99.99999% is not labelled −100%; the two custom names share one helper;<br>- **Catalogue:** kept through a run that stops before drawing it (`persist_state`), so an IN USE run no longer switches the page back to Azure VMs;<br>- **Region names:** read from the shown snapshot's run, and a blank location counts as none; they had been the smallest name across every run;<br>- **Sources:** the Workload tab's Sources holds the several-sizes note when the group offers a Size choice;<br>- **Offer IDs:** shown as stored; only Azure `Standard_` names are shortened;<br>- **Grid title:** "SCENARIO GRID · Δ cost, USD · <hours> h", as D7 says;<br>- **Rounding:** grid cells round half up (Python's `round()` goes to even);<br>- **Rules and reuse:** the grid's rules follow each row's kind and sign, not ladder-v1's IDs; the sentence-case snapshot line reuses `plain_caption`; the grid frame is built once; the unused `CROSSED` is removed.<br>Answered without a change: the ladder and the scenarios-v1 rows stay separate computations, since scenarios-v1 is frozen and still computed and checked (D8); `calculator.FALLBACK_LABEL` and the ladder rows' price and change stay as the calculator's own record of each row, though the page shows its shorter label; `cost_styles` builds its table once | settled (recorded). Code review on PR #13, 2026-10-14; each fix has a test |

### Figures shown

- **Ladder cell:**
  - formula: column GPUs × hours × (scenario − starting USD/GPU-hour), signed. A % row's change
    is starting price × step ÷ 100; the USD row's change is +0.50 exactly;
  - the custom row uses the entered move, and the fallback row uses the same size's
    pay-as-you-go USD/GPU-hour;
  - group key: the starting member's region group (variant, GPU count, region, rental type),
    shown by the sidebar and in Sources. The fallback row crosses rental types and is marked;
  - units: rows as a % or a USD/GPU-hour move; cells in USD for the hours entered;
  - texts: the footer and Sources.
- **Known answers** (2.5 USD/GPU-hour, 720 h):

  | GPUs | Step | Change in cost (USD) |
  |---|---|---|
  | 32 | +25% | 14,400 |
  | 32 | −50% | −28,800 |
  | 32 | +100% | 57,600 |
  | 8 | +10% | 1,440 |
  | 32 | +0.50 USD | 11,520 |
- **Key figures:**
  - "Cost, USD" is the total and "USD/GPU-h" the starting price;
  - "GPUs × h" echoes the checked inputs;
  - "Headroom, USD/GPU-h" is the existing budget headroom with its % of the starting price.

  None is a new calculation.
- **Comparable groups key figures:** the group's existing lowest listed USD/GPU-hour, its size
  and member count.

### Non-negotiables check

| PROJECT.md §5 rule or §6 gate | How this design keeps it |
|---|---|
| Secrets never printed or committed | `API_KEY_21ST` stays in the user environment and is never read into output |
| Never fabricate; label results; preserve failed runs | The mock and screenshots use synthetic figures, labelled. Critique results are recorded as found |
| Operator resolves ⛔ gates | No gate is satisfied or waived |
| Call the data published Azure list prices; label exposure as a scenario calculation | The status line names the data on every tab (`AZURE PUBLISHED LIST PRICES` or `SYNTHETIC DATA — NOT AZURE LIST PRICES`). The ladder's footer says "Scenario calculation, not a forecast." No market costume (D10) |
| Deterministic code computes every figure | Ladder cells come from the calculator, and the independent check re-derives each one (D20) |
| Compare only within comparable groups; state exclusions | The ladder stays inside the starting member's group, except the fallback row, which is marked as crossing rental types. The exclusions sentence is the footer on every screen with a workload figure (D9, owner reading) |
| Collector only reads published prices | No network code |
| Within terms; missing stays missing | No new data. "not computed" rows stay. A missing `location` falls back to the code, not a guess (D30). Live figures never reach Figma or 21st.dev |
| ⛔ live data | Honoured: no new reads |
| ⛔ spend | Untouched |
| ⛔ scheduling / publishing | Not acted on. The Figma file is private to the owner's seat |

One reading needed the owner: a single footer per screen states the exclusions with every
workload figure on it (D9).

## Risks / Trade-offs

- [A terse screen can hide a caveat a reviewer needs] → The constitution's labels stay on screen.
  Everything else is one click away in Sources, and the code review checks that nothing was lost.
- [Removing the scenario table removes the per-row effect words] → Sign and colour carry the
  effect, colour is never the only cue, and the effect words stay in `scenarios-v1` and its
  check.
- [A dark-only theme can be switched to stock light by a viewer] → That is accepted (D4).
- [Opening on Workload cost hides the group context] → The sidebar shows the selection, and
  Sources shows the group key.
- [The build may not match the mock exactly] → Streamlit's own spacing and title sizes differ.
  The manual check compares the build with the mock, and differences go in the review record.

## Migration Plan

Theme, layout, a frozen ladder set and its check, with no schema change and no stored-data
change. To roll back, revert the merge commit.

## Open Questions

None. Every grilling question is owner-answered (D1–D15, D27–D29, D31–D39, D47, D49) or settled with its
basis (D16–D26, D30, D40–D46).
