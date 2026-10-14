---
name: Compute Cost & Risk Monitor
description: A trading screen's discipline, not its costume. One dark desk theme for the cost of a GPU workload and its exposure to list-price moves.
colors:
  background: "#0E1116"
  panel: "#161B22"
  shade: "#1F2A3A"
  rule: "#2A313C"
  zero: "#4A5462"
  border: "#646E7C"
  muted: "#9AA3AE"
  text: "#E6E8EB"
  accent: "#7AA2D6"
  red: "#EF6B63"
  green: "#5CC98A"
  amber: "#F2CC60"
typography:
  body:
    fontFamily: "Source Sans, sans-serif"
    fontSize: "14px"
    fontWeight: 400
  strong:
    fontFamily: "Source Sans, sans-serif"
    fontSize: "14px"
    fontWeight: 700
  figure:
    fontFamily: "Source Sans, sans-serif"
    fontSize: "1.6rem"
    fontWeight: 400
  small:
    fontFamily: "Source Sans, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
  code:
    fontFamily: "Source Code, monospace"
    fontSize: "0.75em"
    fontWeight: 400
rounded:
  base: "4px"
components:
  status-title:
    textColor: "{colors.text}"
    typography: "{typography.strong}"
  status-data-label:
    textColor: "{colors.amber}"
    typography: "{typography.strong}"
  status-word:
    textColor: "{colors.text}"
    typography: "{typography.strong}"
  section-label:
    textColor: "{colors.muted}"
    typography: "{typography.strong}"
  key-figure:
    textColor: "{colors.text}"
    typography: "{typography.figure}"
  input:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.base}"
  tab-active:
    textColor: "{colors.accent}"
  tag:
    textColor: "{colors.muted}"
    typography: "{typography.body}"
  inline-code:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.muted}"
    typography: "{typography.code}"
  workload-column:
    width: "960px"
  grid-label-cell:
    textColor: "{colors.muted}"
    typography: "{typography.small}"
    width: "10rem"
  grid-cell:
    textColor: "{colors.text}"
    typography: "{typography.small}"
    width: "11.5rem"
  grid-cell-added:
    textColor: "{colors.red}"
  grid-cell-saving:
    textColor: "{colors.green}"
  grid-cell-not-computed:
    textColor: "{colors.muted}"
  grid-cell-entered:
    backgroundColor: "{colors.shade}"
    typography: "{typography.strong}"
  grid-header-entered:
    backgroundColor: "{colors.shade}"
    textColor: "{colors.accent}"
    typography: "{typography.strong}"
  cost-cell:
    textColor: "{colors.text}"
    typography: "{typography.small}"
    width: "9.5rem"
  cost-total:
    typography: "{typography.strong}"
  footer-line:
    textColor: "{colors.muted}"
    typography: "{typography.body}"
---

# Design System: Compute Cost & Risk Monitor

> **Precedence.** `src/compute_cost_risk_monitor/.streamlit/config.toml` holds the theme values and is their source of truth; this file mirrors it, and `dashboard.COLOURS` mirrors it in code (`tests/repo/test_streamlit_config.py` keeps the two equal). PROJECT.md §5 (the project constitution: data honesty, labels, non-negotiables) outranks this file. Where a visual choice here would weaken a §5 label, §5 wins.

## Overview

**Creative North Star: "The Desk Beside the Terminal"**

The screen sits on a front-office desk next to Bloomberg terminals and borrows their discipline, not their costume: the cost of a GPU workload and its exposure to list-price moves in one glance, every figure carrying its terms. One dark desk theme, a cool near-black ground, one low-chroma steel-blue accent, Streamlit's bundled Source Sans at a dense 14 px base. Labels are terse and terminal-like, always with units (USD/GPU-h, USD/VM-h, VM-h, h, VMs). Colour appears only where it means something: the sign of a cost change, the data label, and the current or selected state.

The page reads top to bottom as one story: a status line (title, amber data label, AS OF time), key figures, one row of inputs, the scenario grid with the entered GPU column shaded, a muted footer of required clauses, the COST table, and a closed Sources section that holds every explanation. At 1920×1080 everything down to the COST table fits above the fold, with the closed Sources bar just below it. Nothing on the page explains itself in helper sentences; the explanation is one click away.

The system is built from Streamlit 1.65 primitives only. Styling comes from `config.toml`, Streamlit's coloured-text markdown, and pandas Styler on tables drawn with `st.table`. No stylesheet is injected. The confirmed rejection is market costume: no tickers, bid/ask, flashing or animated values, or "live" badges, because the data is published list prices, not a market.

**Key Characteristics:**
- One dark theme only; Streamlit's menu is hidden so it cannot be switched to light.
- Flat tonal layering: background, panel, and the entered-column shade; no shadows of its own.
- Dense 14 px type, key figures at 1.6rem, bold for structure rather than size.
- Colour carries meaning only, and never alone: every red or green figure carries its sign.
- Numbers right-aligned, labels left, fixed decimals per unit.
- Plain status words in text colour instead of alert boxes.

## Colors

A cool, near-neutral dark palette (hue around 257° at very low chroma) with one steel-blue accent and three signal colours held to strict meanings.

### Primary
- **Desk Steel Blue** (accent, #7AA2D6): the current or selected state only. Streamlit paints it on the active tab, the chosen custom unit, a toggle that is on and keyboard focus rings, which cannot be separated without injected CSS (D49). In the scenario grid it colours the entered GPU column's header. Never on a price, a price change, a statistic or a zero change.

### Secondary
- **Added-Cost Red** (red, #EF6B63): a grid cell whose cost rises, always with "+". Nothing else is red.
- **Saving Green** (green, #5CC98A): a grid cell whose cost falls, always with "−" (a true minus sign). Nothing else is green; inline code is explicitly recoloured away from it (D48). Red and green differ in lightness (relative luminance 0.30 against 0.46), but under a deuteranopia simulation they come within 1.23:1, so the sign, not the hue, carries the meaning.

### Tertiary
- **Data-Label Amber** (amber, #F2CC60): the status line's data label (`SYNTHETIC DATA — NOT AZURE LIST PRICES` or `AZURE PUBLISHED LIST PRICES`, amber in both cases, D42), the `STALE — OLDER THAN 7 DAYS AS OF …` warning, and the mixed-labels warning, which concerns the data label (D41). Streamlit's yellow and orange both map to it.

### Neutral
- **Desk Black** (background, #0E1116): the page ground.
- **Panel Slate** (panel, #161B22): the sidebar, inputs, table header background, and the ground under inline code.
- **Entered-Column Shade** (shade, #1F2A3A): fills the entered GPU column of the scenario grid, header and cells. Its 1.31:1 against the background is a named exception: bold weight and the accent header also mark the column, so the shade is never the only cue.
- **Table Rule** (rule, #2A313C): Streamlit's table and dataframe borders (`dataframeBorderColor`); quiet by intent.
- **Zero Rule** (zero, #4A5462): the 2 px rule in the scenario grid between the −10% and +10% rows, separating price falls from rises. Decorative (2.46:1 on the background): the row labels and cell signs carry the meaning.
- **Control Border** (border, #646E7C): input and widget borders (`showWidgetBorder = true`), the 1 px rule above the grid's flat and extra rows, and the rule above the COST total.
- **Muted Grey** (muted, #9AA3AE): section labels (SCENARIO GRID, COST, ACROSS REGIONS), grid row labels, the footer, tags, "n/a" cells, storage not entered, inline code, the chart's minimum and maximum rules.
- **Desk White** (text, #E6E8EB): all running text, figures, zero-change cells, status words, the chart's points and median rule.

### Named Rules
**The Colour Means Something Rule.** Red only for an added cost with "+", green only for a saving with "−", amber only for the data label and the stale warning, the accent only for the current or selected state and the entered grid column. Everything else, including prices, price changes, statistics, zero changes and every state message, is neutral.

**The Sign Before Colour Rule.** Colour is never the only cue. A coloured figure always carries its sign, a not-computed cell says "n/a", and the entered column is bold as well as shaded.

**The Contrast Floor Rule.** Text, red, green, accent, amber and muted each reach at least 4.5:1 against the background, the panel and the entered-column shade; the control border reaches at least 3:1 against the background and the panel. Measured: text 15.41 / 14.09 / 11.79, muted 7.41 / 6.77 / 5.67, accent 7.17 / 6.56 / 5.49, red 6.26 / 5.73 / 4.79, green 9.16 / 8.38 / 7.02, amber 12.23 / 11.19 / 9.36; border 3.66 on the background and 3.35 on the panel. `tests/repo/test_streamlit_config.py` enforces the floor from the committed config; a new colour must pass it before it ships.

**The One Theme Rule.** One dark theme (`base = "dark"`), no `[theme.light]` or `[theme.dark]` section, and Streamlit's menu hidden (`client.toolbarMode = "minimal"`, D47), because the grid's colours are tuned for the dark ground only: in Streamlit's stock light theme red fell to 3.02:1, green to 2.06:1 and the entered column to 1.16:1.

## Typography

**Body Font:** Source Sans (Streamlit's bundled sans, with sans-serif fallback)
**Label/Mono Font:** Source Code (Streamlit's bundled mono, for identifiers drawn as inline code)

**Character:** one humanist sans at two dense sizes, with hierarchy made by weight, case and colour rather than by scale; the mono appears only for identifiers.

### Hierarchy
- **Figure** (400, 1.6rem, about 22 px at the 14 px base): key-figure values only (`metricValueFontSize`), deliberately smaller than Streamlit's default hero metric.
- **Strong** (700, at the size of its text): the status line's title and data label, section labels in upper case, status words (REFUSED, CHECK FAILED, NO SNAPSHOT), the grid's entered column and the COST total row.
- **Body** (400, 14px, `baseFontSize = 14`): the status line, section labels, tags, the footer, status messages and Sources.
- **Small** (400, 0.875rem, 12.25 px measured): Streamlit's own size for table cells and headers, widget labels and key-figure labels.
- **Code** (400, 0.75em, which Streamlit fixes for inline code): identifiers only, such as a size name on Data quality, muted on the panel colour. Tags are not drawn as code, because 0.75em of the body is 10.5 px, below the 12 px floor (D49).

### Named Rules
**The Terse Label Rule.** Labels are short, terminal-style and carry their unit: "Cost, USD", "USD/GPU-h · PAYG", "VMs", "GPUs × h", "Storage, USD", "Contingency, USD", "Custom, %". Section labels are upper case and muted ("SCENARIO GRID", "COST"). No "(optional)", no hints, no "monthly": costs are for the hours entered.

**The Fixed Decimals Rule.** Format by unit, for display only, never computing from a rounded value (D32):
- grid cells: whole USD with sign and thousands separators (+11,520, −27,648);
- key figures and COST: 2 decimals (276,480.00);
- USD/GPU-h and statistics: 4 decimals (12.0000);
- published USD/VM-h in COST: every stored decimal, never fewer than two (96.00);
- percentages: 1 decimal;
- times in UTC, the status line as `12 OCT 2026 09:00 UTC`;
- "n/a" for a grid cell not computed, "—" for an empty input or a figure withheld before the check.

A non-zero value that would round to zero shows 3 significant digits instead.

## Layout

Streamlit's wide layout with a sidebar holding the cascading filters (Dataset, Catalogue, GPU, GPUs per VM, Pricing, Region, all dropdowns). Above every tab sits one status line, its parts joined by " · ". Four lazy tabs follow, opening on Workload cost; only the open tab is drawn.

On Workload cost, the key figures form one row packed to the left (each figure 1.2 parts of a 6-part row; the remainder is empty). One row of inputs follows, bottom-aligned, the custom unit switch stacked above its input in the same column. Everything under the inputs (a status message, the grid, its footer, COST and Sources) sits in one fixed 960 px column. Table cell minimum widths size the tables inside it: the grid fills the column (at least 945 px: 10rem label + 5 × 11.5rem), and COST takes its content width, 539 px measured (10rem + 3 × 9.5rem), at the 14 px rem.

The target screen is 1920×1080 at 100% zoom, where everything down to the COST table fits above the fold and the closed Sources bar sits just below it. At 1440×900 there is no horizontal scroll and the inputs stay on one row. Spacing is Streamlit's own; the system adds no spacing scale.

### Named Rules
**The One Column Rule.** Under the inputs, the story reads down one 960 px column: grid, footer, COST, Sources. Nothing sits beside the grid.

**The Answer First Rule.** Status line, then key figures, then inputs, then the grid. Explanations come last, closed, in Sources.

## Elevation & Depth

Flat. The system defines no shadows. Depth is tonal: the background is the ground, the panel lifts the sidebar, inputs and table headers one step, and the entered-column shade marks the one column the user chose. Horizontal rules, not boxes, separate rows. Streamlit's own popovers keep their defaults and are not part of the system.

### Named Rules
**The Tonal Step Rule.** Separate surfaces by background step (background → panel → shade) and by horizontal rules, never by shadow or outline boxes.

## Shapes

Gently squared corners on controls (4px, `baseRadius`). Tables are drawn with horizontal borders only (`border="horizontal"`), no vertical cell walls. The scenario grid adds three rule weights: the quiet table rule between rows, a 1 px control-border rule above the flat "+0.50 USD/GPU-h" row and above the first extra row (fallback or custom), and a 2 px zero rule between −10% and +10%. COST adds a 1 px control-border rule above its total row.

## Components

### Status Line
One markdown line over every tab: `COMPUTE COST & RISK MONITOR · SYNTHETIC DATA — NOT AZURE LIST PRICES · AS OF 12 OCT 2026 09:00 UTC`. The title is bold in text colour; the data label is bold amber; the time is in text colour. A stale snapshot appends the bold amber STALE clause.

### Key Figures
- **Style:** `st.metric`, terse label above, value below at 1.6rem in text colour; no delta, no arrow.
- **Demo row:** Cost, USD 276,480.00 · USD/GPU-h · PAYG 12.0000 · VMs 4 × ND96isr H100 v5 · GPUs × h 32 × 720 (synthetic demo, 32 GPUs × 720 h × USD 12.0000).
- **Withheld:** with a refused input or a failed check, each label shows "—" and no value.

### Inputs / Fields
- **Style:** Streamlit number inputs and selects on the panel colour, with a visible control border (3.66:1) and 4px corners.
- **Focus:** Streamlit's focus ring in the accent.
- **Empty:** optional inputs show "—" as their placeholder, never hint text.
- **Unit switch:** a horizontal radio ("%" / "USD/GPU-h") above the Custom input; the chosen unit takes the accent.

### Navigation
- **Tabs:** Workload cost, Comparable groups, Group browser, Data quality. The active tab's label and underline take the accent; the rest stay neutral.
- **Sidebar:** dropdown filters on the panel colour, offering only groups that exist.

### Tags
- **Style:** muted text at body size, joined by " · " (`single list price`, `thin`, `crosses regions`), after a section label or above the members table. Never the saving green, and never inline code, which Streamlit draws at 10.5 px here.

### Scenario Grid (signature)
The single scenario grid: Δ price rows (−50, −25, −10, +10, +25, +50, +100%, then "+0.50 USD/GPU-h", then "Spot → PAYG *" or Custom when present) by GPU columns (8, 16, 32, 64, 128, plus the entered count). Titled by a muted bold "SCENARIO GRID" followed by bold "Δ cost, USD · 720 h". Drawn with `st.table` and a pandas Styler, never `st.dataframe`, whose canvas does not paint in a hidden window (D25).
- **Cells:** right-aligned whole USD with sign; red for "+", green for "−", text colour for 0, muted "n/a" across a row not computed.
- **Row labels:** left-aligned, muted; a "†" mark when the row is above the pay-as-you-go price.
- **Entered column:** shaded, bold, header in the accent; no extra label.
- **Rules:** see Shapes.

### Grid Footer
Muted lines under the grid, one clause per line, joined by hard line breaks, mark first: "Scenario calculation, not a forecast." with the exclusions sentence word for word, then each clause that applies (storage entered, "*" crossing, "†" above pay-as-you-go, not computed).

### COST Table
A muted bold "COST" label, then a three-row table (Compute, Storage, Total) by USD/VM-h, VM-h and USD; labels left, numbers right; storage not entered shows a muted "—"; the Total row is bold under a 1 px control-border rule. Demo: Compute 96.00 · 2,880 · 276,480.00.

### Status Words
A state is a bold word in text colour (REFUSED, CHECK FAILED, NO SNAPSHOT, NO GROUPS, WITHHELD, IN USE, NO DATABASE, CANNOT OPEN) with its fixed message below, in text colour. No alert box, no icon.

### Sources
A closed `st.expander` titled "Sources" at the end of each tab: a bullet list of the group key, snapshot, run, data label code, set versions and every explanatory note, then the source-record table.

## Do's and Don'ts

### Do:
- **Do** take every theme value from `src/compute_cost_risk_monitor/.streamlit/config.toml` and keep `dashboard.COLOURS` equal to it.
- **Do** colour a grid cell red only for an added cost with "+" and green only for a saving with "−".
- **Do** keep amber for the data label, the stale warning and the mixed-labels warning, and the accent for the current or selected state and the entered grid column.
- **Do** pass every new text colour at 4.5:1 against the background (#0E1116), the panel (#161B22) and the shade (#1F2A3A), and every control border at 3:1, before it ships.
- **Do** draw styled tables with `st.table(..., border="horizontal")` and a pandas Styler: numbers right-aligned, labels left.
- **Do** show states as a bold status word in text colour with its message below.
- **Do** put every explanation in the closed Sources section, and keep the footer's required clauses on the page.
- **Do** use Streamlit's bundled Source Sans and Source Code only, and keep tags and labels at 12 px or more, so never draw them as inline code.

### Don't:
- **Don't** inject CSS: no `<style>` element, no `st.html`, no `unsafe_allow_html`, no stylesheet. Styler colours, weights, widths and borders scoped to an `st.table` are the only cell-level styling.
- **Don't** use Streamlit's coloured alert boxes (`st.warning`, `st.error`, `st.info`, `st.success`) for any state.
- **Don't** put helper sentences, hints or "(optional)" markers on the page; only required labels, footer clauses and state messages appear outside Sources.
- **Don't** add tickers, bid/ask labels, flashing or animated values, or "live" badges, and never name a dataset or catalogue "live". The stored data label code appears only in Sources.
- **Don't** fetch or self-host fonts: no `fontFaces`, no font URL, no `server.enableStaticServing`.
- **Don't** add a light theme or a `[theme.light]` / `[theme.dark]` section, or bring Streamlit's menu back.
- **Don't** colour prices, price changes, statistics, zero changes or state messages.
- **Don't** let colour be the only cue: no coloured figure without its sign, no shade without bold.
