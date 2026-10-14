# Phase 7 interface review (mock rounds, critiques, manual check, market review)

- **Scope:** OpenSpec change `phase-7-interface` on branch `phase-7-interface`, PR #13, at commit
  5ced028 plus the code-review fixes (§ Code review). It covers the dark desk theme, the
  answer-first layout from the approved mock v3, and the scenario ladder `ladder-v1` with its
  independent check.
- **Reviewer:** the main agent (Claude), with two isolated design reviewers for each critique.
  This is a read-through and evidence record, not the code review: `/code-review` runs on PR #13.
- **Evidence:**
  - **Gate:** green, all nine checks.
  - **Tests:** 784 after the code-review fixes (718 at the end of Phase 6), at 100.0% branch
    coverage overall. The core step holds its eleven modules at 100% (1,526
    statements, 468 branches), `scenarios` and `workload_check` included.
  - **Dependency audit:** `uv audit` found "no known vulnerabilities and no adverse project
    statuses in 69 packages". The phase added no dependency.
  - **Data:** every screenshot, figure and example here comes from the synthetic demo
    database. No live price, cost or exposure figure appears in this document, the PR, Git or
    Figma.
  - **Environment:** Windows 11, Python 3.13.16, uv 0.13.0, Streamlit 1.65.0, Altair 6.3.0,
    pandas 3.0.6.
- **Recheck when:** Streamlit changes minor version (theme keys, `st.table` widths, inline code
  size), a colour or cell width changes, a ladder step is added, or the demo is recorded.

## Brief, research and mock rounds (design D1–D46)

1. **First brief rejected.** impeccable `shape` produced a "desk risk sheet" with captions and
   numbered notes. The owner rejected it as too cluttered, with internal words such as
   "snapshot", and asked for the screen an options sales trader would keep beside Bloomberg
   terminals.
2. **Research.** The firms' internal tools are not public. Professional tools agree on a
   scenario grid of price moves against the current position, colour by sign, colour only for
   status, and dark grounds. Sources: the TT Options Risk Matrix, IB Risk Navigator, patent
   US7774249 and Bloomberg's colour-accessibility write-up (links in design.md).
3. **Quick mock 1.** The owner chose steel blue and renamed labels, then rejected the repeated
   group line and the explanatory text: "this needs to look official with no helpers".
4. **Quick mock 2** (Figma node 5:2), approved on 2026-10-14.
5. **Mock critique** (design-eval, reviewers A and B, no taste reviewer, D17): 25/40, 0 P0,
   4 P1, 1 P2. The owner chose to fix honesty and conditions first, then every P1 and P2.
6. **Mock v3** (node 7:2) with its states: refused input, check failed, Spot without a
   pay-as-you-go listing, storage and budget entered, and the live and stale headers.
7. **Grilling round 2:** the informed answerer's recommendations were agreed by the owner
   (D33–D39); D40–D46 are settled.

## Build critique (task 4.3, design D49)

design-eval on the built page, commit 77ee422. Reviewer A did the design review from five
synthetic screenshots, the source and mock v3. Reviewer B ran the detector on Styler HTML
exports and measured contrast. The browser overlay was skipped because the viewer had been
stopped when the PC ran low on memory.

| | Mock v2 | Build |
|---|---|---|
| Score | 25/40 | 27/40 |
| P0 / P1 / P2 | 0 / 4 / 1 | 0 / 1 / 4 |

**What works** (both reviewers): the scenario grid reads as a desk tool (sign plus colour, the
entered column marked three ways, a marked Spot → PAYG row); honesty is carried by structure
(amber label on every tab, "—" until the check passes, plain status words); every text colour
passes 4.5:1, the tightest being red on the entered-column shade at 4.79.

**Findings and what was done** (owner's answers, 2026-10-14):

| Finding | Done |
|---|---|
| P1: "Budget, USD" beside "Cost, USD" invited a total budget. A total of 300,000 against a cost of 276,480.00 showed headroom "+13.0208 (108.5%)"; the true margin was +1.0208 (8.5%) | Relabelled "Contingency, USD", money set aside for price rises. The calculation and the independent check are unchanged; the refusal messages say "Contingency". Commit c91f2e7 |
| P2: the build lost mock v3's single column. The grid rendered 665 px against the mock's 950, and the footer ran to about 170 characters | Everything under the inputs sits in a 960 px column; the grid fills it (cell minimum 11.5rem) and COST takes its content width, 539 px. Commits c91f2e7, 3b2d8cf |
| P2: the %/USD switch sat 11 px from Storage, so it read as Storage's unit | Moved into the Custom column, above its input |
| P2: footer clauses ran together | One clause per line, its mark first; wording unchanged |
| P2: Streamlit paints the accent on the selected radio, toggles and focus rings | Accepted: the accent means the current or selected state, plus the entered column. The spec says so |
| P2: units spelled three ways, COST showing "96", 36 axis ticks | USD/GPU-h everywhere, "96.00" (every stored decimal, never fewer than two), about 8 ticks |

**Closing audit** on the synthetic viewer, after the fixes:
- group tags were inline code, which Streamlit fixes at 0.75em (10.5 px), below the 12 px
  floor. They are now muted text at 14 px. Commit 3b2d8cf;
- measured type: table cells, headers and widget labels 12.25 px; body and footer 14 px;
  key-figure values 22.4 px;
- the cross-region table's last-column digits end 8 px inside the frame (Streamlit's cell
  padding), not clipped, as a downscaled screenshot had suggested.

**Recorded, not fixed:**
- the 2 px zero rule measures 2.46:1 on the ground; it is decorative, since signs mark the
  same boundary;
- a tiny custom move can print a grid cell in exponent form ("+6e-09");
- Data quality keeps large headings, raw field names and "Stale: no (latest snapshot older
  than 7 days…)", and its size names stay inline code at 10.5 px. D2 gives that tab the theme
  and status line only;
- "AS OF" means the snapshot time in the status line and the check time in the STALE clause.
  The wording is owner-approved (D9, D28);
- the region is not added to the price label, since the owner rejected the repeated group line
  in mock 1;
- a power user cannot load a group from the Group browser or export the grid; these are
  features for a later phase.

The snapshots stay in `.impeccable/critique/`, which Git ignores (D22).

## Manual check (task 4.2)

On the synthetic database only, from a scratch launcher that offers only
`data/synthetic.duckdb`. Screenshots in `2026-10-14-phase-7-screenshots/`, taken at 1920×1080
(the JPEGs are 1568×744 downscales of a 1920×911 viewport):
- `workload-spot-synthetic.jpg`: H100 NVLink 80GB × 8, EU West, Spot, 32 GPUs × 720 h, with
  the Spot → PAYG * row and its footer line;
- `comparable-groups-synthetic.jpg`: the same group, its tags, the cross-region table by region
  name and the chart;
- `group-browser-synthetic.jpg` and `data-quality-synthetic.jpg`.

Findings:
- **1920×1080:** everything down to the COST table fits above the fold, with the closed
  Sources bar just below it. Before D49 added height, the Sources bar fitted too.
- **1440×900** (measured in a 1440×900 frame): no horizontal scroll, the five inputs on one
  row, no key figure overflowing, the 960 px column fitting.
- **Digits:** Source Sans has tabular figures; six 1s, 0s and 8s measure the same width
  (36.53 px at 12.25 px).
- **Stock light theme:** Streamlit's menu could not be opened under browser automation, so it
  was measured instead: red 3.02, green 2.06 and the entered column 1.16 against 4.5:1 on white.
  The owner chose to hide the menu (D47, commit 6970602).
- **Two fixes from the check** (D48, commit 77ee422): tags drew in the saving green, since
  Streamlit colours inline code green by default; and the cross-region table, its chart and the
  Group browser showed region codes while the filter showed names.
- **Every figure matched a recomputation** written without the project's code: 32 × 720 × 12.0
  = 276,480; the −50% cell at 8 GPUs −34,560; +100% at 128 GPUs +1,105,920; the +0.50 row at
  32 GPUs +11,520; Spot EU West 115,200 with the fallback to 12.5 at +172,800; headroom 11,520 ÷
  (32 × 720) = 0.5000 (4.2%); the Spot median of 5, 6 and 12 is 6.

## Market-review read-through (task 4.4)

- **The ladder** (`ladder-v1`) is frozen data, versioned, and fixed before any result was
  viewed. Each cell is GPUs × hours × price change, and the independent check re-derives every
  column, row and cell in the VM-hour form without importing the calculator.
  - The PROJECT example holds: 32 × 720 × 0.50 = 11,520.
  - The entered column equals the `scenarios-v1` exposures.
- **Labels that moved:**
  - The data label is in the status line on every tab: "SYNTHETIC DATA — NOT AZURE LIST
    PRICES" or "AZURE PUBLISHED LIST PRICES", from the run, never from the file name.
  - "Scenario calculation, not a forecast." and the exclusions sit directly under the grid, word
    for word.
  - The Spot → PAYG row says it crosses rental types, and a row above the pay-as-you-go list
    price is marked as "the arithmetic, not what Azure would bill".
- **Key figures** appear only after the check passes; a refused input or a failed check shows
  "—" and no price. A not-computed cell is "n/a", never 0.
- **Contingency:** the rename removes a misreading without changing a number; the headroom is
  still the rise that would use the entered amount up.
- **Synthetic labelling:** dataset "Synthetic demo", catalogue "(synthetic)" read from the run,
  and the amber label.
- **No forecast and no market costume:** no ticker, bid/ask, flashing value or "live" badge.

## What was cut (design D3)

- **Cut item 1:** Group browser and Data quality got the theme, the status line, region names
  and neutral tags, and nothing more.
- **Cut item 2:** chart restyling went no further than the theme colours, the axis title and
  the tick count.
- **Done in full:** cut items 3 (Comparable groups key figures), 4 (DESIGN.md) and 5 (the P1
  fixes).
- **Timebox:** the phase ran over D3's one-session timebox, through the two mock rounds and
  two grilling rounds.
- **Polish pass:** D17's impeccable polish pass was folded into the critique fixes and the
  closing audit; no separate `/impeccable polish` run was made.

## Code review

`/code-review` on PR #13 found 15 issues. It traced the ladder's cells, columns, refusals and
marks through `calculator.ladder` and `workload_check._ladder`, and found the maths and the
check sound. Design D50 records each finding. Fixed with tests:
1. **Grid width:** an entered count outside 8–128's five columns (24 GPUs) added a sixth column
   that needed about 1,106 px in the 960 px column. The GPU columns now share 57.5rem.
2. **Withheld message:** a snapshot that is not normalized showed the workload message on
   Comparable groups and "NO GROUPS" on Group browser. Both now say "The group views are
   withheld until this snapshot is normalized."
3. **Above-PAYG note:** it pointed to "Spot to pay-as-you-go fallback", a row of the removed
   scenarios table. It now says "See the 'Spot → PAYG *' row." (workload-calculator, MODIFIED).
4. **Custom label:** a computed move of −99.99999% read "Custom −100%". Labels now keep more
   decimals when 4 would round the value.
5. **Catalogue:** a run that stopped before drawing it (IN USE) dropped the choice, so the next
   run switched to Azure VMs. The test fails without the fix and passes with it.
6. **Region names:** they were the smallest stored name across every run, and a blank one could
   win. They now come from the shown snapshot's run, and a blank one counts as none.
7. **Sources:** the Workload tab's Sources now holds the several-sizes note when the tab offers a
   Size choice, as the spec requires.
8. **Offer IDs:** shortening was applied to marketplace offer IDs; only Azure `Standard_` names
   are shortened now.
9. **Grid title:** "SCENARIO GRID · Δ cost, USD · 720 h", as D7 says.
10. **Rounding:** grid cells rounded half to even (+2.5 showed "+2"); they now round half up.
11. **Cleanup:** the grid's rules follow each row's kind and sign rather than ladder-v1's IDs;
    the snapshot line reuses `plain_caption`; the grid frame is built once; the custom names
    share one helper; the unused `CROSSED` is removed.

Answered without a change:
- **Two row assemblies:** the ladder and the `scenarios-v1` rows stay separate computations,
  since `scenarios-v1` is frozen and still computed and checked (D8).
- **Unread fields:** `calculator.FALLBACK_LABEL` and the ladder rows' price and change stay as
  the calculator's own record of each row; the page shows its shorter label.
- **`cost_styles`:** it builds its table once, so that part of the efficiency finding does not
  apply.

After the fixes: 784 tests at 100.0% branch coverage, and the gate is green.
