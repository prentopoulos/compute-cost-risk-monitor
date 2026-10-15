## Context

This is Phase 8 of PROJECT.md §6, the last planned phase. Phases 0–7 are Done: the collector,
normalization, comparable groups, history, the dashboard, the calculator with `ladder-v1`, the
gap tests and the desk interface. One live Azure snapshot exists on the owner's PC
(`20261012T151909Z-5473f1`). The synthetic demo database is built from `azure_demo.json`, a single
snapshot dated 2026-10-12 09:00 UTC, plus three synthetic marketplace snapshots.

### Grilling (2026-10-14 to 2026-10-15)

- **Round 1.** An informed-answerer subagent researched 22 questions and found 8 more; an API
  usage limit stopped it once and it was resumed.
  - The main agent reopened the sources behind the settled answers:
    - the setup kit's AI-ops files;
    - the schema history and diagram titles;
    - the `.codex/config.toml` key (key names only);
    - Anthropic's pricing and rate-limit pages;
    - Streamlit's Community Cloud limits.
  - The owner added the AI drafter ("Yes i do want the ai element in").
  - The owner made this the final phase ("i want this to be the final phase"), with USD 5 of API
    credit and USD 5 more if needed.
  - The owner added four items: a clear conclusion, limitations and model risk, an excellent
    README and a five-slide presentation.
  - The main agent reframed "investment conclusion" as a buyer's bottom line (§1 and §5 forbid
    forecasts), and the owner agreed.
- **Round 2.** 7 questions. R1 reopened the owner's data answer, because the README and the
  brief would have shown two sets of figures. The owner agreed every recommendation and confirmed
  the full decision list ("yes agreed").
- **Before the spec, PR #14** added the README (shaped like the owner's
  [fundamental-engine](https://github.com/prentopoulos/fundamental-engine)), the MIT licence, the
  AI-ops skill, `AI_OPS.md` and ignore rules. Reviewing it, the owner asked to remove the grid
  footer's "Scenario calculation…" text as reading like AI prose. Told that it is §5's required
  label, the owner chose terse desk labels (D30).
- **Calibration:** the owner reopened no settled answer and said no owner call was unnecessary,
  so the informed-answerer brief is unchanged.

### Measured facts (2026-10-14 to 2026-10-15, main at 6ffd49d)

- **Pricing** (Anthropic pricing page, retrieved 2026-10-14):
  - `claude-opus-5-5` costs USD 4 per million input tokens and 20 per million output tokens;
  - `claude-sonnet-5-5` costs 2 and 10, and `claude-haiku-5-5` 0.10 and 0.50.
  - Thinking tokens bill as output, and Opus 5.5 cannot turn thinking off.
  - At 5,000 input and up to 4,000 output tokens, one draft costs about USD 0.04–0.10.
- **Spend controls** (Anthropic rate-limits page, retrieved 2026-10-14):
  - an organisation spend limit is set on the Console's Billing page;
  - at the limit, requests return HTTP 400;
  - the default workspace cannot take a workspace limit.
- **Data handling:** Anthropic keeps API inputs and outputs for up to 30 days and does not train
  on them (privacy page and commercial terms, retrieved 2026-10-14).
- **Streamlit Community Cloud** forces `gatherUsageStats = true`, `showErrorDetails = false`,
  `runOnSave`, XSRF protection and `fastReruns` (Context7 `/streamlit/docs`, status and
  limitations).
- **Microsoft terms:** the API page invites "your own tools for internal analysis and price
  comparison". The Microsoft APIs Terms of Use, if they govern this API, forbid redistributing
  "any data obtained" (§3(b)(14)). No Microsoft page addresses counts or metadata.
- **Compute futures, as of 2026-10-14:**
  - nothing US-regulated trades;
  - the CFTC extended its review of NYMEX's Silicon Data H100/B200 rental-index futures to
    9 November 2026;
  - ICE has set no listing date for its Ornn-index futures;
  - CME's own product page did not load.
- **Clone path length:** a fresh clone into a deep Windows folder fails with "Filename too long";
  the longest tracked path is 124 characters. The quick start works from a short path, and the
  app answers on 127.0.0.1.
- **Live-derived content in Git:**
  - no live price value appears in any tracked file or in history;
  - counts (for example 14,347 rows and 929 region groups) appear in designs, reviews and
    HANDOFF;
  - coarse price-derived distributions appear in the Phase 4, 5 and 7 designs (for example the
    flat USD 0.50 share buckets 124 / 375 / 356 / 74).
- **Demo prices:** `azure_demo.json`'s H100 ×8 pay-as-you-go prices are 96, 100, 104, 112 and
  120 USD/VM-h in US East, EU West, US South Central, US West 3 and Sweden Central, which is
  12.0000–15.0000 USD/GPU-h.
- **Diagrams:** `erd.svg` is titled "schema v2". No schema file changed after 906976f
  (2026-10-12).

## Goals / Non-Goals

**Goals:**
- A recruiter can open the public repository and, in two minutes, see:
  - the question;
  - a buyer's bottom line from one consistent synthetic dataset;
  - how it was computed and checked;
  - its limits and model risk.

  They can run the demo with one command.
- The brief proves the evidence chain: every number links to stored records and matches an
  independent recomputation. The AI writes words, never numbers.
- Nothing collected from Azure leaves the owner's PC as a price, cost or exposure figure.

**Non-Goals:** as in the proposal.

## Decisions

| # | Decision | Who / basis |
|---|---|---|
| D1 | Phase 8 is the final phase. It may span several sessions as one phase (WORKFLOW.md § Mid-phase) and ends public-ready on GitHub.<br>**Must-haves:**<br>- the brief with its bottom line, its independent check and one real AI-drafted run;<br>- the methodology with its model-risk section;<br>- the README with the one-command setup;<br>- the five-slide deck;<br>- the futures sentence;<br>- the pre-publication check and the publishing list.<br>**Should-haves:** the walkthrough video, the diagrams and the grid-cell fix. The hours may pass PROJECT.md §1's 24–29 h; actual hours are recorded | **owner** (Scope, Value trade-off, Private knowledge) |
| D2 | Non-goals: as in the proposal | **owner** (Scope) |
| D3 | **Cut in this order:**<br>1. diagram polish;<br>2. the grid "+6e-09" fix;<br>3. the video recording (the script stays).<br>**Never cut:**<br>- `brief_check` and the validator;<br>- the methodology;<br>- the pre-publication check | **owner** (Scope, Value trade-off) |
| D4 | Public form: the repository is made public and the app runs from a clone. No hosted app: Community Cloud forces usage statistics on, against the dashboard's telemetry-off rule, and its terms allow personal, non-commercial use only | **owner** (Gate, One-way door, Showcase) |
| D5 | The publishing gate comes last, after the review, with an exact list of what goes public. Nothing is shared before the decision, including a private video link | **owner** (Gate) |
| D6 | The public demo uses synthetic data only. Derived live Azure figures are not put to the gate | **owner** (Gate) |
| D7 | One public synthetic dataset:<br>- two synthetic Azure snapshots, 2026-09-28 and 2026-10-05 at 09:00 UTC, go in front of the unchanged `azure_demo.json`;<br>- they hold at least one price change into 2026-10-12 (US East H100 ×8 pay-as-you-go 88 → 96 USD/VM-h), one listing absent once and one not listed;<br>- no Spot price is above its pay-as-you-go price in any snapshot;<br>- one database drives the dashboard, screenshots, brief, bottom line, README and deck;<br>- `azure_history` stays the end-to-end test fixture.<br>This reopens round 1's answer, which used `azure_history` for the brief | **owner** (Conflict, Showcase, Methodology) |
| D8 | Brief sections, in order:<br>1. bottom line;<br>2. changes since the previous snapshot;<br>3. absences, with the exact terms "absent once (unconfirmed)" and "not listed";<br>4. groups per GPU variant, with "single list price" labels;<br>5. Spot against pay-as-you-go in the same size and region, stated as crossing rental types;<br>6. the cross-region spread, with thin flags;<br>7. data-quality counts and the stale flag;<br>8. "Sample too thin for trends: n snapshots over d days".<br>No marketplace section: the brief covers Azure-shaped data only | **owner** (Methodology, Showcase) |
| D9 | Before the local brief from collected prices, the owner starts at least one more collect plus normalize, 24 h or more after the last and at most one a day. Two on different days are better | **owner** (Gate, Private knowledge) |
| D10 | Walkthrough:<br>- the agent writes a timed script and shot list in `docs/walkthrough.md`;<br>- the owner records screen and voice with Snipping Tool, from the synthetic database only, and trims in Clipchamp;<br>- the video stays out of Git and goes up unlisted only after the publishing gate;<br>- the order is: question and bottom line, comparable groups, data quality, the brief and its checks, limits | **owner** (Showcase, Gate, Private knowledge) |
| D11 | Futures:<br>- PROJECT.md §1's sentence becomes "It works from observed published list prices alone and does not use or depend on compute futures or GPU price indexes.";<br>- the methodology gets a dated paragraph on the status of compute futures, rechecked before publishing | **owner** (Showcase, Conflict) |
| D12 | README:<br>- the bottom line in the first screen, the buyer's question first;<br>- one synthetic screenshot;<br>- what the data is and is not;<br>- the one-command setup;<br>- links to the methodology, brief, deck and video;<br>- one plain AI sentence;<br>- limits, licence and credits;<br>- the CI badge.<br>Its shape follows fundamental-engine (PR #14) | **owner** (Showcase) |
| D13 | Methodology, `docs/methodology.md`, about 3–4 pages, for trading-data, compute-market and AI-product readers. It covers every recorded rule plus:<br>- **AI-drafted prose and its checks;**<br>- **compute futures context (dated);**<br>- **why the public data is synthetic;**<br>- **credits:** the Microsoft Learn CC BY 4.0 credit, and Silicon Data as a reference, not an index claim;<br>- **reading list:** the Phase 1 reading list;<br>- **"Limitations and model risk":** framed on SR 11-7's conceptual soundness, outcomes analysis and ongoing monitoring. It names data, method, process and AI risks, each with its control and covering test, and a short version goes in the README and on slide 5 | **owner** (Showcase, Methodology) |
| D14 | Of the Phase 7 leftovers, only the "+6e-09" grid cell is fixed: 3 significant digits in positional form. No mock, because it restores D32's approved format | **owner** (Scope, Showcase) |
| D15 | The owner rotates the 21st.dev key and moves it out of the repo folder. The ignore rules landed in PR #14 | **owner** (Authority, Private knowledge) |
| D16 | Drafter: the Anthropic Claude API, `claude-opus-5-5`, effort `low` (thinking cannot be disabled on this model), `max_tokens` 4,000, one call per draft | **owner** (Gate, Private knowledge, Value trade-off) |
| D17 | Spend-gate record (operator, 2026-10-14), copied into PROJECT.md §6:<br>- approved: the Anthropic Claude API, `claude-opus-5-5`, to draft the Phase 8 market brief's prose only;<br>- budget: USD 5, up to USD 10 in total if needed;<br>- runs are started by hand, use synthetic figures only, and never run in CI, tests or the app;<br>- an organisation spend limit of USD 10, automatic top-up off, and the API key in the user environment, never in the repo.<br>No dedicated workspace | **owner** (Gate) |
| D18 | The drafter receives synthetic figures only. A brief from collected prices uses the template only and is never committed | **owner** (Gate, Conflict with "local storage only, no redistribution") |
| D19 | The drafter writes no numbers. It returns structured output: one prose field per section, using placeholders `[[fact_id]]` from the closed list in the fact set.<br>**A validator rejects a draft with:**<br>- a digit or a number word outside placeholders;<br>- an unknown placeholder;<br>- a section missing one of its required placeholders;<br>- a banned word (D28, D44).<br>**Then:**<br>- code fills the placeholders in the dashboard's formats;<br>- `brief_check` verifies the final text;<br>- on any failure there is one retry, then the template brief, with the reasons recorded and a non-zero exit for the draft | **owner** (Methodology) |
| D20 | Licence: MIT, confirmed 2026-10-15 after comparing it with fundamental-engine's PolyForm Noncommercial. `LICENSE` landed in PR #14 | **owner** (One-way door, Showcase) |
| D21 | The author email stays in history. New commits use the GitHub noreply address, set in this repo on 2026-10-15 | **owner** (Private knowledge, One-way door) |
| D22 | The vendored skill files are published as they are: Agent Builder, the AI-ops synthesis of course pages, and grilling (MIT) | **owner** (Private knowledge) |
| D23 | Personal details are neutralised in the current, non-archived files: "built alongside exams", the Windows username path, and the kit path in `source-manifest.json`. History keeps them | **owner** (Private knowledge) |
| D24 | The conclusion is a buyer's decision "Bottom line", never an investment conclusion: workload cost at list price, the lowest listed option, the contingency for +25% and +50% list-price moves, and what is not priced. Every figure is computed and scenario-labelled, and forward-looking words are banned | **owner** (Methodology, Showcase, Conflict with §1 and §5) |
| D25 | Deck: five slides in Figma Slides on the owner's Pro seat:<br>1. Bottom line;<br>2. Data and method;<br>3. The tool (Workload cost screenshot with the grid);<br>4. The brief, the AI drafter and its checks;<br>5. Limits and model risk, plus what comes next.<br>The owner approves a draft, then exports the PDF to `docs/` | **owner** (Showcase, Private knowledge) |
| D26 | Live-derived content already in Git (counts and coarse distributions; no price) is put to the gate as aggregate, non-price metadata. Archives are not edited and history is not rewritten. The publishing list says: "No live Azure price, cost, exposure or SKU-level price figure appears. Aggregate counts and coarse distributions from the one local snapshot appear in design and review records." | **owner** (Gate, One-way door) |
| D27 | Bottom-line template, every field filled by code from the fact set. On the demo it reads:<br>"**Bottom line** — SYNTHETIC DATA — NOT AZURE LIST PRICES · prices as of 2026-10-12 09:00 UTC.<br>32 H100 NVLink 80GB GPUs (4 × ND96isr H100 v5) for 720 hours cost USD 276,480.00 at the lowest listed pay-as-you-go price for this size: US East, 12.0000 USD/GPU-h.<br>This size lists in 5 regions at 12.0000–15.0000 USD/GPU-h, so the same workload costs USD 276,480.00–345,600.00. This compares across regions.<br>A contingency of USD 69,120.00 covers a +25% list-price move, and USD 138,240.00 a +50% move. Scenario calculation, not a forecast.<br>Not priced: [exclusions sentence, word for word]"<br>It says "lowest listed", never "cheapest", and "720 hours", never "monthly". "Thin" is added under 5 regions. Spot is never the anchor | **owner** (Showcase, Methodology) |
| D28 | Banned words added to the recorded list: cheapest, spread, deal, bargain, guarantee, safe, risk-free, hedge, futures. The brief ends with "Prose drafted by claude-opus-5-5 (prompt v2); every number placed and checked by code." when the draft is used (prompt v1 until D46) | **owner** (Methodology) |
| D29 | As-of: the brief CLI takes `--as-of`.<br>- The committed brief is pinned to the latest snapshot's start, 2026-10-12 09:00 UTC, so it is reproducible.<br>- A local brief defaults to now (UTC).<br>- Screenshots and the video are taken before 2026-10-19 09:00 UTC if possible.<br>- The README says the demo is dated 12 October and shows STALE after 7 days, by design | **owner** (Methodology, Showcase) |
| D30 | Grid labels:<br>- the grid title becomes "SCENARIO GRID · Δ cost, USD · <hours> h · NOT A FORECAST". As with the Phase 7 footer (D9, D39, the owner's one-label-per-screen reading), it labels every scenario figure on the tab, the Headroom key figure included;<br>- the footer's first sentence becomes one tag line, "EXCL." followed by every exclusion item in stored order, joined by " · ";<br>- the Comparable groups tab uses the same tag line;<br>- the storage, "*" crossing, "†" and not-computed lines are unchanged.<br>A quick Figma mock with synthetic figures is approved first. This keeps §5 without amendment | **owner**, 2026-10-15 (Conflict, Showcase) |
| D31 | The first README landed before this spec (PR #14) and is extended in this phase | **owner**, 2026-10-15 |
| D32 | Brief architecture:<br>- `brief.py` builds a JSON fact set from stored rows through `groups`, `history`, `quality`, `calculator` and `scenarios`. Each fact has an ID, a value, units and record links: run ID, item key, retrieval time, raw-response SHA-256, currency, unit, rental type, rule and map versions.<br>- It renders the template brief.<br>- `brief_check.py` never imports `brief`. It re-derives every figure from the database with plain SQL and arithmetic, as `workload_check` does, and matches every number in the final Markdown, half up at its stated decimals | settled (recorded). PROJECT.md §5; market-review skill; Phase 7 D20 |
| D33 | Diagrams:<br>- **context view:** the brief drafter moves from "deferred" to built, labelled "drafts prose only";<br>- **container view:** add the brief and its check, the drafter and the demo CLI, and fix the Phase 4 label overlap;<br>- re-export the SVGs; the ERD is unchanged | settled (recorded, fact). PROJECT.md §4; `erd.svg` title; git log of `schema/` |
| D34 | `.codex/config.toml` and the generated skill copies are ignored (done in PR #14) | settled (recorded). PROJECT.md §5 |
| D35 | The AI-ops skill and `AI_OPS.md` were installed before this proposal (PR #14). AI_OPS.md's evidence locations are filled as the drafter is built | settled (recorded). PROJECT.md §2 |
| D36 | Drafter tests and records:<br>- the client sits behind a protocol, and tests inject a fake one: no key, no network (pytest-socket);<br>- fixtures are synthetic responses for the normal case and every rejection case, including refusal and `max_tokens` stops;<br>- each run writes a JSON record: provider, model ID, SDK version, prompt version and SHA-256, fact-set SHA-256, input, output and thinking tokens, cost estimate with its pricing date, request ID, stop reason, validator outcome and reasons, the text used (draft or template), the data label and the git commit;<br>- the official `anthropic` SDK is a runtime dependency pinned in `uv.lock`, imported only by `drafter.py` | settled (recorded, default). PROJECT.md §3; Anthropic's guidance to use its SDK in Python. Would change for another provider |
| D37 | Brief files:<br>- the committed synthetic brief, its fact set and its run record go in `docs/brief/`;<br>- briefs from collected prices go to gitignored `data/briefs/`;<br>- the CLI refuses to write a non-synthetic brief outside `data/`.<br>No new database tables | settled (default). Files are a two-way door; tables would change the schema |
| D38 | Figma Slides exports PDF or PPTX on any plan. The Figma tools can build slides; the owner exports by hand | settled (fact). Figma help "Export from Figma Slides", retrieved 2026-10-14; the figma-use-slides skill |
| D39 | `uv run --locked python -m compute_cost_risk_monitor.demo [--serve]`:<br>- builds into a temporary file from the fixed list: three Azure demo snapshots, then three marketplace snapshots;<br>- runs normalize on it and stops on a non-zero exit;<br>- replaces `data/synthetic.duckdb`, refuses any path that resolves to `data/monitor.duckdb`, and prints counts only;<br>- `--serve` starts the dashboard | settled (default). Reuses the `synthetic` and `normalize` CLIs |
| D40 | A repo test checks every figure in the README's bottom line against the committed fact set | settled (default) |
| D41 | The publishing list uses D26's wording | settled. Follows D26 |
| D42 | The demo-history items and their answers are hand-worked in the fixtures README before the test is written | settled (default). The `azure_history` pattern |
| D43 | No banned-word scan on the README or the deck: they must name what the data is not ("not a forecast", "not an index"). The market-review read-through covers them | settled (default). The answerer suggested a scan with exemptions |
| D44 | The recorded banned list, matched case-insensitively at word boundaries in drafter prose only:<br>- market price, market rate, marketplace, index, benchmark, executed, trade, traded, trading, "what customers pay", "customers pay", "actual cost";<br>- forecast, predict, prediction, projected, projection, trend, trending, live;<br>- will, expect, expected, likely;<br>- capacity, availability, "in stock";<br>- AWS, Amazon, Google Cloud, GCP, Oracle, CoreWeave, Lambda, "other clouds";<br>- market-wide, "the market", industry, ticker, bid, "bid/ask";<br>- monthly, "per month", "a month".<br>Code-filled text is not scanned | settled (recorded). §1, §2, §5; Phase 1 D9; Phase 7 D21, D37; design-skills.md; market-review; owner C1 |
| D45 | Required text, inserted by code and confirmed present by the validator:<br>- the data label and the source framing;<br>- snapshot and AS OF in UTC, and STALE when it applies;<br>- the exclusions sentence with every workload figure, and "Scenario calculation, not a forecast." with every scenario figure;<br>- the judgement note;<br>- the crossing notices, and the "thin" and "single list price" labels;<br>- the history terms;<br>- the thin-sample line;<br>- the Microsoft Learn credit;<br>- the D28 disclosure when the draft is used | settled (recorded). §3, §5; Phase 1 D9, D12, D16; Phase 7 D9, D35, D39 |
| D46 | Names are not figures in the draft validator, as in the independent check (D32): the snapshot's GPU, size and region names (H100, ND96isr H100 v5, US West 3) are removed before the digit and number-word checks. Rejection reasons quote the offending word, and each attempt's reply is kept in the run record (synthetic figures only). The prompt becomes `prompt v2`: it lists the names the model may write and says "a listing", never "one listing". Evidence: the first real run (2026-10-15, commit 0730db0) rejected both drafts for digits in changes, groups and regions, and once for "one" | settled (recorded). D19's intent (no numbers written by the model) is unchanged; D32's masking of names |

### Drafter request

- **Call:** `anthropic.Anthropic().messages.create`, with:
  - `model="claude-opus-5-5"` and `max_tokens=4000`;
  - `output_config={"effort": "low", "format": <JSON schema with one string per section>}`;
  - a versioned system prompt (`prompt v2` since D46, stored in the package, its SHA-256 recorded);
  - one user message holding the fact IDs, their meanings and their units. Values may be
    included for context, since they are synthetic (D18), but the reply may only use IDs.
- **Key:** `ANTHROPIC_API_KEY` from the environment. The CLI refuses without it (exit 2) and
  never prints it.
- **No fallback model.** The server-side `fallbacks` parameter is deliberately not set, because
  the spend gate approves one model (D17). A refusal or a `max_tokens` stop counts as a rejection
  (D19).
- **Usage:** the token counts come from `usage`, and the cost estimate uses the pricing recorded
  on 2026-10-14.

### Demo-history cases (to be hand-worked, D42)

| Listing | 2026-09-28 | 2026-10-05 | 2026-10-12 (`azure_demo.json`) |
|---|---|---|---|
| US East H100 ×8 pay-as-you-go | 88 | 88 | 96 (a change: 11.0000 → 12.0000 USD/GPU-h) |
| US East H100 ×8 Spot | ≤ 88 | ≤ 88 | 96 (equal to pay-as-you-go) |
| One size, present then | yes | yes | absent → "absent once (unconfirmed)" |
| Another size | yes | absent | absent → "not listed" since 2026-10-05 |
| Every other `azure_demo` item | as in `azure_demo` | as in `azure_demo` | unchanged |

## Non-negotiables check

| PROJECT.md §5 rule or §6 gate | How this design keeps it |
|---|---|
| Secrets | The API key comes from the user environment. It is never read from or written to the repo, and never printed. `.codex/config.toml` is ignored (D34). The pre-publication check scans every historical blob |
| Never fabricate; label results | Every brief number is computed and re-derived (D32). The drafter writes no numbers (D19). Synthetic data is labelled on every page, brief, slide and screenshot. A fake client's responses in tests are labelled synthetic, and a run record names the model that ran |
| Operator resolves ⛔ gates | Spend: recorded as the operator gave it (D17). Publishing: put to the operator last (D5). The agent changes repository visibility only after that decision |
| Published Azure list prices, never a market; synthetic labelled; scenarios not forecasts | The bottom line is a buyer's conclusion, not an investment call (D24). Banned words (D28, D44). The grid keeps "NOT A FORECAST" and the brief keeps "Scenario calculation, not a forecast." (D30, D45) |
| Deterministic code computes every figure; the AI only drafts prose | Placeholders only, the validator, and `brief_check` on the final text (D19, D32) |
| Comparable groups; exclusions with every workload figure | The bottom line states that it compares across regions. Spot never anchors it (D27). The "EXCL." tag line lists every exclusion on every screen with a workload figure, and the brief repeats the exclusions sentence (D30, D45) |
| The collector only reads | No new endpoint. The drafter calls the model API only, under the spend gate |
| Source terms; missing stays missing | No live figure leaves the PC (D6, D18, D26). Absences are reported with their recorded terms, never filled |
| Live-data gate | The owner starts collects by hand, at most one a day (D9) |
| Scheduling gate | Untouched: no scheduled runs, and the drafter never runs unattended |

## Risks / Trade-offs

- [A public repo shows invented prices] → every page says so, and the methodology explains why
  (Microsoft's terms and the gate). A recruiter sees the method, not Azure's current prices.
- [Recruiters will not clone] → the README's first screen, the screenshot, the deck and the video
  carry the demo. Running it is optional.
- [The drafter adds cost and a third party] → at most USD 10. Synthetic inputs only. A template
  fallback keeps the brief correct without it.
- [The model's words can still mislead without numbers] → banned words, required caveats, and the
  market-review read-through of the committed brief.
- [Live-derived counts become public with history] → the operator decides at the gate (D26); a
  history rewrite was rejected as one-way.
- [The demo goes STALE on 19 October] → screenshots and the video come first if possible. The
  README explains the flag (D29).
- [Thin legal reading of Microsoft's terms for counts] → stated in the publishing list for the
  operator; no price-level figure is published.
- [Multi-session phase] → each session ends with a pushed HANDOFF naming the open tasks
  (WORKFLOW.md § Mid-phase).

## Migration Plan

- **New:** modules, fixtures and documents.
- **Edited:**
  - `dashboard.py` changes only labels and the grid-cell format;
  - `pyproject.toml` and `uv.lock` gain `anthropic`;
  - `data/synthetic.duckdb` is rebuilt by the demo CLI.
- **To roll back:** revert the merge commit.
- **After the merge:** on the operator's publishing decision, the repository's visibility is
  changed to public, and the owner uploads the video unlisted. Both are recorded in HANDOFF. The
  video link enters the README before the merge, once uploaded (D5).

## Open Questions

None. Exact fixture items (D42), the grid labels' final look (D30, mock) and the deck's visual
draft (D25) are settled during the build with the owner's approval where marked.
