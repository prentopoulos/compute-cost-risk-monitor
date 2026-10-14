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
- add a scenario ladder: price change × GPU count → signed exposure;
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
- **Reclassified as settled:**
  - 21st.dev use, on a fact: `get_usage` on 2026-10-13 showed the free tier, with AI generation
    off, 0 credits and 2 free code copies a day;
  - impeccable's PRODUCT.md, on a recorded basis.
- **Owner reopened:** a Figma mock first, and the free 21st.dev code copies ("that's a reason to
  constrain the mock, not skip it"). Both became owner calls (D14, D15).
- **Owner:** accepted every recommendation ("agreed on your changes then proceed").

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
- **Caption length:** a Spot Workload tab repeats about 930–1,230 characters of caption text
  under each of its four figures today, about 4,300 in all. Measured lengths, in characters:

  | Text | Length |
  |---|---|
  | exclusions | 158 |
  | billing | 280 |
  | Spot | 289 |
  | storage entered | 176 |
  | hours note | 60 |
  | judgement | 98 |
  | above pay-as-you-go | 280 |
- **Flat $0.50 against the lowest listed price per group (live, Phase 5 design):**

  | Share of the price | Groups |
  |---|---|
  | under 5% | 124 |
  | 5–25% | 375 |
  | 25–100% | 356 |
  | 100% or more | 74 |
- **Display:** the owner's PC has one 1920×1080 display at 100% scaling.
- **21st.dev:** the plugin is installed, `API_KEY_21ST` is set in the user environment, and the
  account is free tier (`get_usage`, 2026-10-13).
- **Hard-coded chart colours:** `dashboard.py` sets `POINT_COLOUR` and `RULE_COLOURS` for the
  default light theme.

## Goals / Non-Goals

**Goals:**
- Make the dashboard read like a front-office screen without implying a market.
- Lead with the commercial answer: cost and exposure for the workload.
- Add the scenario ladder, checked like every other figure.
- Keep every required label and text visible while cutting repetition.

**Non-Goals:** as in the proposal.

## Decisions

| # | Decision | Who / basis |
|---|---|---|
| D1 | Roadmap: a new Phase 7 before the demo, which becomes Phase 8. One more session | **owner** (Scope) |
| D2 | Scope:<br>- a custom theme for the whole app;<br>- an answer-first rework of "Workload cost" and "Comparable groups", whose region-group, cross-region and marketplace views share the `_groups` code;<br>- the scenario ladder.<br>Group browser and Data quality get the theme only.<br>**Acceptance:**<br>- AppTest flows on synthetic data, including known-answer ladder cells;<br>- every ladder cell passes the independent check, with the core modules still at 100% branch coverage;<br>- a local manual check with synthetic-only screenshots at 1920×1080 and 1440×900;<br>- one design-eval run without the taste reviewer: no P0 open, and every P1 fixed or recorded with its reason;<br>- the market-review read-through of the ladder, and `/code-review`.<br>No diagram change | **owner** (Scope) |
| D3 | Timebox: one session of about 3¾ h, including about 45 min for the Figma mock (D14).<br>**Cut in this order:**<br>1. restyling Group browser and Data quality beyond the theme;<br>2. chart restyling beyond theme colours;<br>3. the Comparable groups strip;<br>4. DESIGN.md (D12);<br>5. P1 fixes after the first pass, recorded for Phase 8. P0 fixes are always made.<br>**Never cut:**<br>- every caption field and note text with every figure;<br>- the framing line and the STALE, NOT NORMALIZED, thin and single-list-price labels;<br>- the independent check on every shown figure, and no price before it passes;<br>- the D10 colour rules and no market costume;<br>- the three local-only config settings;<br>- the theme, the Workload strip and the ladder with its known-answer tests;<br>- AppTest flows, the manual check, the green gate, counts-only Git;<br>- the Figma mock and the design-eval run | **owner** (Scope, Value trade-off, Private knowledge) |
| D4 | Visual direction: one dark "desk" theme.<br>- `[theme] base = "dark"`, a near-black neutral background, one low-chroma accent, and chart palettes from the theme;<br>- no `[theme.light]` or `[theme.dark]` sections;<br>- no logo, only the title text.<br>Streamlit's Settings menu can still switch a viewer to its stock light theme. That is accepted and checked in the manual check | **owner** (Showcase) |
| D5 | Target screen: 1920×1080 first (Chrome maximised, 100% zoom), checked at 1440×900 | **owner** (Private knowledge, Showcase) |
| D6 | Answer-first layout:<br>- **Tab order:** Workload cost, Comparable groups, Group browser, Data quality. The page opens on Workload cost.<br>- **Workload strip:** one line, drawn only after the independent check passes: "Total USD X for the hours entered (G GPUs = V VMs × H h) · starting USD p/GPU-hour, \<size\> · largest additional expense: \<scenario name\> +USD y · scenarios-v1 · Scenario calculation, not a forecast". "Largest" is the plain maximum over computed `scenarios-v1` rows; the custom and fallback rows are not in it.<br>- **Below the strip:** the inputs in one row, the ladder, the cost table, the scenario table, the chart and headroom.<br>- **Comparable groups strip:** group key · lowest listed USD/GPU-hour (size) · members N · labels · snapshot UTC · run ID · data label.<br>- The sidebar stays (Phase 4 D28).<br>- The starting price appears only with the checked figures, after the check passes; previously it sat "under the cost table's caption" | **owner** (Showcase, Scope) |
| D7 | Scenario ladder `ladder-v1`, frozen in `scenarios.py`:<br>- **Rows:** −50, −25, −10, +10, +25, +50 and +100% of the starting price.<br>- **Columns:** 8, 16, 32, 64 and 128 GPUs, plus the entered count (marked) when it is not one of them, all at the hours entered.<br>- **Cells:** signed exposure in USD, "for the hours entered"; storage is unchanged.<br>- **Labels:** `ladder-v1`, "Scenario calculation, not a forecast" and the judgement note.<br>Percentages mean the same thing in every group, while a USD step does not (Measured facts). The rows include v1's −25, +25 and +100 as cross-checks. The steps are judgement, like `scenarios-v1` | **owner** (Methodology, Scope, Showcase) |
| D8 | Keep `scenarios-v1` unchanged, including "PROJECT example +$0.50/GPU-hour". Its name, and any `scenarios-v2`, are decided at the start of Phase 8 with the demo copy | **owner** (Methodology, Showcase) |
| D9 | Captions in a dense layout:<br>- **Caption line:** each figure gets one line: group key (or "crosses regions" with variant, count and rental type) · snapshot UTC · run ID · data label · "notes 1–n".<br>- **Scenario figures:** exposure and headroom figures also carry "Scenario calculation, not a forecast" and the set version on that line. The fallback row keeps "crosses rental types (Spot → pay-as-you-go)" and both keys inline.<br>- **Notes:** the full texts (exclusions, storage, billing assumptions, hours note, Spot line, judgement note, above-pay-as-you-go note) appear once per panel as numbered notes directly under it. They are always visible, never in an expander, and in text no smaller or fainter than a caption.<br>- No text is reworded | **owner** (Methodology, Conflict, Showcase) |
| D10 | Colour:<br>- red marks additional expense and green marks lower expense, always with the sign and the effect words;<br>- the two shades also differ in lightness, checked with a colour-blindness simulation in the critique;<br>- no change, prices, price changes and statistics stay neutral;<br>- no tickers, bid/ask, flashing or animated values, or "live" badges | **owner** (Showcase) |
| D11 | Phase name: "Front-office interface" | **owner** (Showcase) |
| D12 | DESIGN.md: written last (cut item 4) with impeccable's documenter, derived from the shipped `config.toml` and code. It says that `config.toml` holds the theme values and that PROJECT.md §5 outranks it. Rules that are requirements go into the dashboard spec | **owner** (Value trade-off, Showcase) |
| D13 | Fonts: Streamlit's bundled Source Sans and Source Code. No font URL and no self-hosting. `st.dataframe` draws cells in the body font, so the whole app in monospace would be the costume D10 rules out. Whether Source Sans's default digits are tabular is measured in the manual check | **owner** (Showcase) |
| D14 | Figma mock first:<br>- one frame of the Workload cost screen at 1920×1080, in a Figma Design file on the owner's Pro seat;<br>- the D4 theme values, real labels and synthetic figures;<br>- only elements Streamlit can build: sidebar, tabs, a one-column flow, inputs in a row, the strip, the ladder as a plain table, the cost and scenario tables, the chart and the numbered notes.<br>A design-eval critique (Figma target, no taste reviewer) runs on it, P0 findings are fixed, and the owner approves it before layout code. The owner reopened this from "settled (default): no mock": "that's a reason to constrain the mock, not skip it" | **owner** (Showcase, Value trade-off) |
| D15 | 21st.dev:<br>- free search for references, such as dark data tables and dense summary lines;<br>- at most 2 code copies a day, only for components whose exact values are copied into the theme or the mock, never pasted React;<br>- each component's licence is checked before anything from it enters the repo;<br>- only synthetic figures go into any search.<br>The owner reopened this from "settled: search only", pointing to the free code copies | **owner** (Private knowledge) |
| D16 | Styling uses only `config.toml` `[theme]`, `st.column_config`, pandas Styler colours on the ladder, and theme-driven Altair colours. No injected CSS. What would change it: a P0 or P1 finding that no theme key can fix. Then one CSS file loaded with `st.html`, targeting only documented `st-key-<key>` classes, with a test pinning Streamlit 1.65 | settled (default). Streamlit 1.65 `elements/html.py`: "Prefer native Streamlit features and theming over custom CSS or HTML"; Emotion class names change between versions; AppTest cannot see CSS |
| D17 | Process: impeccable `shape` writes the brief, which the owner confirms; then the Figma mock (D14), the build, a design-eval critique without the taste reviewer, and an impeccable polish pass. The tasteskill is not used | recorded. `.agents/skills/next-phase/design-skills.md` (dashboards route to impeccable and design-eval; the tasteskill is not for app screens) |
| D18 | Renumbering:<br>- **Phases:** Phase 7 is the interface and Phase 8 the demo.<br>- **Budget:** eight sessions, about 24–29 h.<br>- **Phase 7 references updated:** PROJECT.md §1, §2 and §6, AGENTS.md, `openspec/config.yaml` and the build-safety skill; HANDOFF's demo findings are relabelled Phase 8.<br>- **Archives:** not edited. Phase 1's acceptance row "7 Demo and brief" now applies to Phase 8 | recorded. D1; PROJECT.md:26 (seven sessions, about 20–25 h) plus about 3¾ h (D3) |
| D19 | Not a constitution amendment. PROJECT.md §5 defines the constitution as the §5 rules plus the ⛔ gates in §6, and an amendment as changing a rule or adding, removing or loosening a gate. The milestone table and budget are neither, and the publishing gate's wording is unchanged | recorded. PROJECT.md § Amending the constitution; `tests/repo/test_constitution.py` checks only the §5 copies and the version line |
| D20 | Ladder checks:<br>- `workload_check` re-derives every ladder cell from the VM-hour price, GPUs per VM, hours and `ladder-v1`, imported as data;<br>- for a Spot start, a ladder row priced above the size's pay-as-you-go price is marked and gets the above-pay-as-you-go note;<br>- nothing is shown unless every check passes | recorded. workload-calculator spec, "Independent check of workload figures" and "Spot price above pay-as-you-go" |
| D21 | The ladder and strips say "for the hours entered", never "monthly" | recorded. workload-calculator spec, "Workload cost" ("never converted to a month"); Phase 5 D14 |
| D22 | No PRODUCT.md (impeccable's product file) is committed. impeccable reads a scratch PRODUCT.md drawn from PROJECT.md §1 through `IMPECCABLE_CONTEXT_DIR`. `.impeccable/` stays out of Git, and the scored review goes to `docs/reviews/` with synthetic figures only | recorded. PROJECT.md owns scope (AGENTS.md); PR #6 kept the rules in PROJECT.md rather than adding files that drift |
| D23 | Records corrected: `design-skills.md` and HANDOFF now say the 21st plugin is installed, the key is in the user environment, and the account is free tier with AI generation off | fact. `installed_plugins.json`; `get_usage` on 2026-10-13 |
| D24 | Chart colours come from the theme's values, replacing `POINT_COLOUR` and `RULE_COLOURS`, with their contrast checked on the dark background. One commit undoes it | settled (default) |
| D25 | The ladder, about 7 × 6 cells, is drawn with `st.table` and Styler colours, not `st.dataframe`. An HTML table paints in a hidden Chrome window and reads as page text, and AppTest exposes it. The scenario tables keep `st.dataframe` and its CSV download. What would change it: the owner wants the ladder as CSV | settled (default). HANDOFF (the data grid's canvas does not paint in a hidden window) |
| D26 | Contrast floor: `textColor`, `redColor` and `greenColor` each reach at least 4.5:1 against `backgroundColor` and `secondaryBackgroundColor`, checked by a repo test from the committed config | settled (default). WCAG 2.2 AA 1.4.3; D10 needs red and green readable as text |

### Figures shown

- **Ladder cell:**
  - formula: GPUs × hours × starting USD/GPU-hour × step ÷ 100, signed;
  - group key: the starting member's region group (variant, GPU count, region, rental type);
  - units: rows in % of the starting USD/GPU-hour; cells in USD for the hours entered;
  - texts: the exclusions, storage, billing and, for Spot, the Spot line, as numbered notes,
    plus `ladder-v1`, "Scenario calculation, not a forecast" and the judgement note.
- **Known answers** (2.5 USD/GPU-hour, 720 h):

  | GPUs | Step | Exposure (USD) |
  |---|---|---|
  | 32 | +25% | 14,400.00 |
  | 32 | −50% | −28,800.00 |
  | 32 | +100% | 57,600.00 |
  | 8 | +10% | 1,440.00 |
- **Workload strip:** shows figures already computed and checked: the total, the starting price
  and the largest `scenarios-v1` exposure. It adds no new figure.
- **Comparable groups strip:** shows the group's existing lowest listed USD/GPU-hour and its
  member count, with the group key. It adds no new figure.

### Non-negotiables check

| PROJECT.md §5 rule or §6 gate | How this design keeps it |
|---|---|
| Secrets never printed or committed | `API_KEY_21ST` stays in the user environment and is never read into output |
| Never fabricate; label results; preserve failed runs | The mock and screenshots use synthetic figures, labelled. Critique results are recorded as found |
| Operator resolves ⛔ gates | No gate is satisfied or waived |
| Call the data published Azure list prices; label exposure as a scenario calculation | No market costume (D10). The framing line is unchanged. Every ladder, strip and scenario figure carries "Scenario calculation, not a forecast" and its set version on the caption line (D9) |
| Deterministic code computes every figure | Ladder cells come from the calculator, and the independent check re-derives each one (D20) |
| Compare only within comparable groups; state exclusions | The ladder stays inside the starting member's group. Exclusions appear as always-visible notes under every panel with a workload figure (D9, owner reading) |
| Collector only reads published prices | No network code |
| Within terms; missing stays missing | No new data. "not computed" rows stay as they are. Live figures never reach Figma or 21st.dev (D14, D15) |
| ⛔ live data | Honoured: no new reads |
| ⛔ spend | Untouched: the 21st.dev free tier has AI generation off and 0 credits |
| ⛔ scheduling / publishing | Not acted on. The Figma file is private to the owner's seat |

The one reading that needed the owner: notes directly under a panel count as stated "with" each
workload figure (D9).

## Risks / Trade-offs

- [The numbered notes could read as fine print] → They are always visible and never fainter
  than a caption (D9). Their contrast is checked in the critique.
- [A dark-only theme can be switched to stock light by a viewer] → That is accepted (D4). Charts
  take theme colours, and the manual check looks at the stock light theme once.
- [Opening on Workload cost hides the group context] → The sidebar filters and the strip's group
  key stay visible, and the caption line names the group.
- [3¾ h is tight with a mock and a critique] → D3's cut order cuts polish before content and
  never cuts a label.
- [Styler colours could fall out of step with the theme] → Both read the same values in
  `dashboard.py`, and D26's test checks the config values.

## Migration Plan

Theme, layout, a frozen ladder set and its check, with no schema change and no stored-data
change. To roll back, revert the merge commit.

## Open Questions

None. Every grilling question is owner-answered (D1–D15) or settled with its basis (D16–D26).
