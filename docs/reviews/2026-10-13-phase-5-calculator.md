# Phase 5 calculator review (manual check, market review and build safety)

- **Scope:** OpenSpec change `phase-5-calculator` at commit a084b45, plus the code-review fixes
  at 2abdeb1 (§ Code review): the scenario set
  (`scenarios.py`), the calculator (`calculator.py`), the independent check
  (`workload_check.py`), the workload view model in `dashboard.py`, the "Workload cost" tab in
  `app.py`, and the demo fixture's uksouth Spot item.
- **Reviewer:** the main agent (Claude). This is a read-through plus the manual check, not the
  code review, which `/code-review` does on PR #10.
- **Evidence:**
  - the gate: 628 tests, 98% branch coverage overall and 100% for `calculator.py`;
  - the known-answer tests, the independent check's tamper tests and the AppTest flows on
    synthetic file databases;
  - a manual check in Chrome against a rebuilt `data/synthetic.duckdb`;
  - the calculator, the independent check and the real tab run on the live local database,
    printing counts, keys and pass or fail only.

  Counts only: no live price, cost or exposure figure appears in this document. No screenshot
  was taken: the Chrome window was hidden during the check, so the table canvases did not
  paint (§ Manual check).
- **Recheck when:** `scenarios-v1` gains a version, the cost formula or a caption changes, the
  page gains an input or export, the Streamlit version changes, or the publishing gate is
  resolved.

## Manual check (task 4.1, 2026-10-13)

`data/synthetic.duckdb` was rebuilt from the updated demo file and the three marketplace
snapshots, then normalized; all seven independent normalization checks pass on its 46 rows. The
previous copy was moved to `tmp/synthetic.pre-phase5.duckdb`. The dashboard was launched headless
on port 8517: it listened on `127.0.0.1` only (netstat), as the Phase 4 config requires.

Synthetic data, in Chrome. Values were read from the page text and the data grid's accessible
cells, because the window was in the background (`document.visibilityState` was "hidden"), so
the grid canvases and some screenshots did not paint:

| Flow | Outcome |
|---|---|
| Framing line says "Synthetic data: invented prices …"; the tab opens with the starting size, "(lowest listed in this group)", its published VM-hour price, item key and run | Pass |
| H100 ×8 eastus pay-as-you-go, 32 GPUs × 720 h: "32 GPUs = 4 VMs of 8 GPUs"; compute 276,480; PROJECT example exposure 11,520; decline −69,120; increase 69,120; spike 276,480 (invented prices: 12.0 USD/GPU-hour) | Pass |
| Every workload caption holds the group key, snapshot and run, `synthetic` label, exclusions, "Storage not included.", the billing-assumptions line and "Costs are for the hours entered"; scenario captions add `scenarios-v1`, "Scenario calculation, not a forecast" and the judgement note | Pass |
| Inputs kept across tabs: 16 GPUs entered, "Group browser" opened (no workload input drawn there), "Workload cost" reopened with 16 GPUs | Pass |
| uksouth Spot: compute 69,120 for 16 GPUs; the Spot line on all three workload figures; the fallback row carries no figure | Pass after fix |
| Budget headroom: "A rise of USD 0.5000 per GPU-hour (… of starting price) would use up USD 11,520.00 over 32 GPUs × 720 h. Storage unchanged. Scenario calculation, not a forecast." | Pass |

Found and fixed in the check (commit a084b45):
- In a wide scenario table, the Effect and Note columns sat off-screen to the right of the long
  narrative, so "not computed" and the above-pay-as-you-go note were easy to miss. The outcome
  columns now come first and the narrative last.
- The fallback caption named the uksouth pay-as-you-go key without saying it is absent. It now
  adds "(not listed in this snapshot)".

Found while writing the AppTest flows (commit 82b99db): with `persist_state="page"`, a remounted
widget reset to its default under AppTest. The inputs use `"session"`; the app has one page, so
the two scopes mean the same to a user (design Context, D17).

After a server restart, the page reopened on its default, the live database, and the browser's
later clicks did not register. One read of the headroom text came from a live group before the
browser session was closed. Its figures stay on this PC and are not recorded here.

Live local data (counts and pass or fail only; scratch script, read-only connection):
- snapshot `20261012T151909Z-5473f1`, label `live`, 929 region groups, 1,238 members;
- every member as the starting price, each with the default workload plus USD 100 of storage,
  once alone and once with a −0.50 USD/GPU-hour custom change and a USD 11,520 budget:
  2,476 results, all passing the independent check, and the PROJECT example exactly 11,520 in
  all 2,476;
- fallback rows: 1,122 additional expense and 96 no change (48 sizes priced equal, twice); none
  "not computed", because every live Spot size is listed on pay-as-you-go in its region;
- the above-pay-as-you-go note on 358 rows, twice the 179 found in grilling (48 + 73 + 58);
- the −0.50 custom change is refused, never floored, for the 136 members listed at
  0.50 USD/GPU-hour or less;
- the real tab through AppTest for one group per variant and rental type: 33 of 33 render with
  two tables and the chart, each captioned with the `live` label, the forecast label on the
  scenario table and chart, and the Spot line on Spot groups.

Not checked: a screenshot of the tables (window hidden), a screen reader, and a narrow window.

## Market review (compute-cost-risk-monitor-market-review)

| Check | Outcome | Evidence |
|---|---|---|
| Workload cost = GPUs × hours × USD/GPU-hour, plus storage only when entered | Pass | `calculator.cost`; `test_known_cost_without_and_with_storage`; spec "Workload cost" scenarios |
| Exposure = GPUs × hours × scenario change; 32 × 720 × $0.50 = $11,520 | Pass | `test_project_example_whatever_the_starting_price` (four starting prices, exact); live: 2,476 of 2,476 |
| Outputs checked independently of the code that produced them | Pass | `workload_check` imports no calculator code (`test_check_imports_no_calculator_code`) and re-derives from VM-hour prices; tamper tests name each figure; the page withholds figures when it fails (`test_failed_check_shows_no_figures`) |
| Same inputs, units and exclusions for every scenario | Pass | One starting member and one workload per result; storage unchanged across rows; the stored `groups-v1` exclusions text in every caption |
| Scenarios fixed before looking at results | Pass | `scenarios-v1` was set by the owner in grilling (design D5, D6) before any figure was computed, and is frozen in code (`test_set_cannot_be_changed_in_place`) |
| Every figure carries key, snapshot, label and exclusions | Pass | `workload_caption` and `scenario_caption`; AppTest counts three captioned figures; live AppTest on 33 groups |
| Comparisons within one group, or crossing said plainly | Pass | One region group per calculation; the only crossing, Spot → pay-as-you-go, is labelled with both keys, the second marked when not listed |
| Missing stays missing | Pass | No pay-as-you-go listing gives "not computed", never a price (`test_fallback_not_computed_without_the_size_on_pay_as_you_go`, the uksouth demo flow) |
| Prices finite and positive | Pass | A scenario price at or below zero is refused, never floored (`test_custom_row_comes_last_and_a_price_at_or_below_zero_is_refused`); non-finite inputs refused by the validator |
| Scenario calculation, not a forecast | Pass | On every exposure figure and on headroom; narratives say "hypothetical"; magnitudes labelled as judgement |
| Asking price versus what a buyer pays | Pass | The Spot note says a row above pay-as-you-go is arithmetic, not what Azure would bill; the billing line names full-minute billing, stopped states and the OS disk |
| Display does not change values | Pass | USD at 2 decimals with separators, USD/GPU-hour at 4, percentages at 1; frames hold unrounded values (`test_display_formats_and_text`) |

The BCBS d450 checklist is in the design (§ BCBS d450 checklist). The magnitudes' severity is a
judgement with no history to test it against; that limit is stated on every scenario figure.

## Build safety (compute-cost-risk-monitor-build-safety)

Workflows read (2026-10-13), applied through the skill's project adaptation:
- `assess_threat_vectors`: the new entry points are the numbers typed into the tab. The
  relevant threats are query execution, stale or poisoned source data, and cost abuse; agent and
  prompt threats do not apply (no model).
- `generate_eval_metrics`: ground truth is deterministic, from hand-worked fixtures; normal,
  edge, impossible and dependency-missing cases were fixed in the specs before measuring.
- `define_release_gates`: the gate, `uv audit`, this check and the code review are the release
  evidence for the PR. This is a reversible local prototype, so no hosted gates apply.

| Threat or control | Disposition | Enforcement and test |
|---|---|---|
| User input reaching SQL | None does: inputs feed pure arithmetic after the group is read | `calculator.py` has no database import; the page's queries are unchanged from Phase 4 |
| Impossible or huge inputs | Bounded and validated, never rounded; non-finite refused | `calculator.workload`, `custom`, `budget`; the input-refusal tests in `test_calculator.py`; `test_impossible_hours_refused` |
| Stale or unnormalized data priced as current | STALE framing kept; the tab withholds figures while a snapshot is `NOT NORMALIZED` | `test_workload_withheld_when_not_normalized` |
| A wrong figure shown | The independent check runs before drawing; a failure shows an error and no figure | `test_failed_check_shows_no_figures`; live 2,476 of 2,476 pass |
| Writes or locks on the live database | None added: one read-only connection per page run, as in Phase 4 | Phase 4 tests; no new connection code |
| Live figures leaving the PC | No screenshot or figure of live data in Git, the PR or this review; the server binds 127.0.0.1 only | Phase 4 config; netstat in the manual check |
| Personal data | None; entered values live only in the browser session | Session-scoped widget state; nothing is written |
| Supply chain | No dependency added. `uv audit`: no known vulnerabilities in 67 packages | `uv.lock` unchanged |

The scheduling, spend and publishing gates are untouched. Nothing here is hosted.

## Code review (2026-10-13)

`/code-review` (high) on PR #10 found 14 issues; all were fixed with tests in 2abdeb1 (design
D29). The ones that touched this review's checks:
- **The check could reject valid input.** The calculator and the check priced a percentage
  scenario with two formulas, so a custom change of −99.99999% failed the check on about 17% of
  prices and the page showed no figures. Both now use one formula per kind, at tolerances scaled
  to each figure; a test runs extreme changes over 400 invented prices and two workloads.
- **A large storage entry could hide a cent.** Tolerances included the storage amount. Storage
  now adds only its sum's rounding (`test_a_large_storage_amount_never_hides_a_cent`).
- **Unchecked labels.** Each row's effect, the storage shown, notes on rows that may not carry
  one, and the member the figures were priced from are now checked.
- **A price before the check.** The starting price was drawn before validation and the check;
  it now appears only with the checked figures, under the cost table's caption.
- **Traceability (main agent, same pass):** the fallback caption now names the pay-as-you-go
  size and item key, so the fallback price traces to its record.

After the fixes the live check was rerun with the stricter check: 2,476 of 2,476 results pass,
with the same counts as above. The gate is green (§ Evidence in the PR).
