# Compute Cost & Risk Monitor

Owner: Peter Rentopoulos. Created: 2026-10-11.

## 1. Goal

A tool that answers: **which comparable GPU cloud options are listed, what would my
workload cost, and how exposed is my budget to changing prices?** It works today from
observed published prices, without depending on compute futures launching.

- Users: a GPU buyer sizing a workload (the product persona). Audience for the demo:
  contacts and recruiters on trading-data, compute-market and AI-product teams. For sales
  recruiters, lead with the commercial decision it supports.
- What it demonstrates: market curiosity, quantitative reasoning, product delivery and
  research discipline. The methodology (comparability, units, data quality) is the centrepiece.
- What it is NOT: a marketplace, a market-wide benchmark or index, executed-trade prices,
  what customers actually pay, or a price forecast. The dataset is **published retail list
  prices for GPU virtual machines from one cloud provider, Microsoft Azure**, observed
  through its public Retail Prices API. Budget exposure is a calculation under labelled
  scenarios, not a prediction. Not a production service.
- Source decision (owner, 2026-10-11, Phase 1 grilling): every GPU marketplace whose terms
  were checked (Vast.ai, SF Compute, RunPod, Lambda, TensorDock, Shadeform, Prime Intellect,
  io.net, Akash) forbids automated collection into a database without a written agreement,
  and the owner chose not to seek one. Labelled synthetic marketplace-style offers exercise
  the marketplace-only rules (duplicates, re-listing, thin samples).
- Budget: seven focused sessions, roughly 20–25 hours, built alongside exams by replacing
  some study blocks rather than adding a full workload.

## 2. Current scope boundary

In scope (one phase per session, see §6):

- Live price collection from the Azure Retail Prices API (public, no account): timestamped
  price rows, original responses retained.
- Comparable pricing: separate GPU variants, GPU counts, regions and rental types
  (pay-as-you-go and Spot, Linux, commercial-cloud regions, sizes Microsoft has not retired);
  compute USD/GPU-hour. GPU fields come from a map built only from Microsoft Learn; sizes it
  does not name exactly stay unmapped and are counted, never guessed.
- Synthetic marketplace-style offers, labelled synthetic: they exercise marketplace-only rules
  and are the public demo's dataset unless the publishing gate approves live Azure figures.
- Workload calculator: GPU count, hours and storage in; cost out, with disclosed exclusions.
- Budget exposure: cost changes under explicitly labelled price scenarios. Example:
  32 GPUs × 720 hours × a $0.50/hour increase = $11,520 additional monthly expense.
- Data-quality panel: missing fields, duplicates, stale observations and thin samples.
- Market brief: observed changes, each linked to its underlying records.

Deferred or out of scope:

- A second source, added only after its access, terms and comparable fields are verified
  (⛔ below). Cross-provider comparisons are out of scope.
- Trend claims, made only after several weeks of collection.
- The optional AI agent, which may only draft the market brief from validated numbers (⛔ spend).
  Before proposing it, install the setup kit's AI-ops skill and AI_OPS.md (deferred 2026-10-11).
- Renting, creating or modifying instances, or any account action beyond reading offers.
- Accounts, logins or multiple users. Hosting before Phase 7 (⛔ publishing).

Data: real public Azure list prices once the live-data ⛔ gate is resolved. Tests use
synthetic fixtures, labelled as such; no real source data is committed to Git. Runs
single-user and local until the Phase 7 demo.

## 3. Acceptance and evidence

Per-phase acceptance criteria: Phase 1 writes them into OpenSpec; next-phase grills the
user before each later phase. Evidence that counts in every phase:

- Every price traces to its source record: source item ID, retrieval time (UTC), original
  response, currency, unit and rental type. Normalized figures record how they were derived.
- Units, normalization, cost and exposure maths pass pytest on fixtures with known answers,
  including missing data and stale offers.
- Prices, costs, exposure figures and the brief pass the compute-cost-risk-monitor-market-review
  checks before they are shown or reported.
- Every collection run is labelled by how its bytes were obtained:
  - synthetic: invented data;
  - recorded: a new run built from responses kept from an earlier fetch;
  - live: fetched from the source by that run.

  Stale is a computed age flag (latest snapshot older than 7 days), not a label. A snapshot is
  one succeeded run. A mocked fetch is not a live result.
- A listing counts as "not listed" only after two consecutive snapshots without it; one absence
  is "absent once (unconfirmed)", because offset paging can miss rows (Phase 3 grilling, owner).
- Trends need several weeks of observations; until then the app says the sample is thin.

## 4. Stack and commands

- Python, pandas, DuckDB, Streamlit, pytest (decided). Phase 0 grilling, 2026-10-11 (all
  owner calls answered by the owner; settled answers cited in
  `openspec/changes/archive/2026-10-12-phase-0-toolchain/design.md` D1–D23): Python 3.13 managed by uv with a
  committed `uv.lock`; Ruff for format and lint; mypy strict; pytest with pytest-cov;
  commitizen for commit messages; OpenSpec CLI 1.6.0 pinned through npm; hosted CI on GitHub
  Actions (owner). Package `compute_cost_risk_monitor` (owner). Run Python only through uv:
  bare `python` differs by shell on the owner's PC.
- Data source: [Azure Retail Prices API](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices)
  (unauthenticated; the docs invite "your own tools for internal analysis and price comparison
  across SKUs and regions"). The live-data gate is resolved for this API (§6, 2026-10-12), and
  the Phase 2 collector reads it. Phase 2 grilling decisions are cited in
  `openspec/changes/archive/2026-10-12-phase-2-collector/design.md` D1–D28. Phase 3 grilling
  decisions (normalization, comparable groups, history, synthetic marketplace rules; owner
  answered every owner call on 2026-10-12) are cited in
  `openspec/changes/archive/2026-10-12-phase-3-normalization/design.md` D1–D25. Vast.ai
  was dropped: its terms (version 2026-09-01) forbid automated collection, price-comparison
  use and redistribution without a written agreement.
- Methodology reference: [Silicon Data's H100 index](https://www.silicondata.com/products/silicon-index/h100)
  adjusts for configuration and rental-condition differences. This project shows those
  problems are understood; it does not claim to be an index.
- Optional: an LLM to draft the market brief from validated numbers. Provider TBD (⛔ spend).
- Architecture diagrams: [FigJam board](https://www.figma.com/board/JISCFP9eQzMq5QVg1k2V2A)
  on the owner's Pro seat (Projects team), confirmed in Phase 1 (owner): C4 system context, C4
  container (built or planned) and an ERD of the DuckDB schema. The C4 views are flowcharts in
  C4 notation because Figma's diagram tool has no C4 type. Exported as SVG to
  `docs/architecture/`; update them when a phase changes components, data flow or schema.
- Code review: every PR that changes code is reviewed before merge (WORKFLOW.md).

Gate: `uv run --frozen python scripts/gate.py` after `uv sync --locked` and `npm ci --ignore-scripts`; CI runs it plus
`uv audit --locked --preview-features audit-command` on every PR and push to main.
Remote: https://github.com/prentopoulos/compute-cost-risk-monitor (private). Push phase
branches and open PRs at the points WORKFLOW.md sets; nothing goes straight to main, and a PR
merges only after its review and the user's go-ahead. Follow WORKFLOW.md for phase work.

## 5. Non-negotiables

These rules and the ⛔ gates in §6 are this project's constitution. They override AGENTS.md,
WORKFLOW.md, the skills, OpenSpec specs and HANDOFF.md; only the owner's current instructions
and recorded gate decisions come before them.

**Version 2.1.0** · Ratified 2026-10-11 · Last amended 2026-10-12

- Secrets use the runtime secret mechanism (gitignored .env for local development); never
  print, commit or include them in reports.
- Never fabricate results or external-service output. Label mocked, local and live results
  accurately. Preserve failed runs.
- Operator resolves all ⛔ gates. The agent never satisfies or waives one itself.
- Call the data published Azure list prices: never a marketplace, market price, index,
  benchmark, executed trades or what customers pay. Synthetic marketplace data is labelled
  synthetic. Label every exposure figure as a scenario calculation, not a forecast.
- Deterministic code computes every price, cost and exposure figure. An AI agent, if used,
  only drafts prose from validated numbers, and every number it writes must match a computed
  one.
- Compare offers only within a comparable group (GPU variant, GPU count, region, rental type),
  or say plainly that a comparison crosses groups. State cost exclusions with every workload
  figure.
- The collector only reads published prices. Never call endpoints that create or change
  resources or spend account credit.
- Use a data source only within its terms of use and rate limits. Missing observations stay
  missing; never fill them in to make a chart look complete.

### Amending the constitution

- Only the owner amends it: a change to a rule above, or adding, removing or loosening a ⛔
  gate. Recording an operator decision on a gate (§6) is not an amendment.
- An amendment states its reason and goes in its own `docs:` commit. That commit updates the
  verbatim copies in AGENTS.md and `openspec/config.yaml` and adds a row below.
  `tests/repo/test_constitution.py` fails the gate if a copy or the version line drifts.
- Version: major when a rule is removed or redefined, minor when one is added or materially
  widened, patch for wording only.

| Version | Date | Change | Decided by |
|---|---|---|---|
| 1.0.0 | 2026-10-11 | Ratified at setup, for observed marketplace asking prices | Owner (setup) |
| 1.1.0 | 2026-10-11 | Secrets may use the runtime secret mechanism; .env stays for local development | Owner (PR #2) |
| 2.0.0 | 2026-10-12 | Data redefined as published Azure list prices plus labelled synthetic marketplace data; the collector reads published prices only | Owner (Phase 1 grilling on 2026-10-11, PR #5) |
| 2.1.0 | 2026-10-12 | §5–6 named the constitution, with precedence, versions and this amendment rule; "never fabricate" added | Owner (PR #6) |

## 6. Milestones and gates

Milestones are ordered by dependency. Phases 1–7 are the brief's seven sessions. Every phase
tests what it builds; Phase 6 closes the gaps the brief lists.

| Phase | Deliverable | Status |
|---|---|---|
| 0 | Toolchain, lockfile, quality gate, smoke checks | Done |
| 1 | Requirements, data schema and acceptance criteria; architecture diagrams in Figma | Done |
| 2 | Working Azure Retail Prices collector keeping original responses; observations start accumulating | Done |
| 3 | Normalization to USD/GPU-hour, comparable-group mapping, duplicate handling, quality checks | Done |
| 4 | Streamlit dashboard with comparable-group filters and the data-quality panel | Planned |
| 5 | Workload cost calculator and labelled budget-exposure scenarios | Planned |
| 6 | Tests for units, calculations, missing data and stale offers | Planned |
| 7 | Public demo, methodology document, market brief, two-minute walkthrough; diagrams updated | Planned |

### ⛔ Before reading live data from any source

- [ ] Operator confirms the source's terms of use and rate limits allow the planned
      collection, and puts any API key in .env.
- Finding, 2026-10-11 (Phase 1 grilling): Vast.ai's terms forbid the planned collection
  without a written agreement; the owner chose not to seek one and switched the source to
  the Azure Retail Prices API. That API needs no key; the operator still confirms its terms
  and the pacing (at most 1 request per second, back off on 429) before the first live read.
- Decision, 2026-10-12 (owner, Phase 2 grilling): the operator accepts that the Azure Retail
  Prices API may be read for this project, on the reading that portfolio use counts as internal
  analysis and as personal, non-commercial use. Microsoft's API page invites "your own tools for
  internal analysis and price comparison across SKUs and regions". No page says which terms
  govern this unauthenticated API. Scope:
  - unauthenticated GET of `https://prices.azure.com/api/retail/prices` only, with the Phase 2
    GPU filter;
  - runs the owner starts by hand, at most one a day;
  - at most 1 request per second, backing off on 429 and honouring Retry-After;
  - local storage and analysis only, with no redistribution.

  It approves no other source, no scheduled runs and no publishing.
- [ ] Before a second source: operator confirms access works and its fields are comparable.

### ⛔ Before scheduling unattended collection

- [ ] Operator approves where the collector runs (this PC, GitHub Actions or elsewhere) and
      how often.

### ⛔ Before spending money or paid quota

- [ ] Operator approves the service (paid API plan, LLM calls for the brief, hosting) and a
      budget. This project never spends cloud or marketplace account credit.
- Decision, 2026-10-11 (owner, Phase 0 grilling): GitHub Actions CI may use the account's free
  included minutes; the owner confirmed overage cannot bill. Scope: the Phase 0 CI workflow
  and its later updates. It approves no paid service.

### ⛔ Before publishing

- [ ] Operator approves making the GitHub repo public, deploying the demo, and sharing the
      walkthrough or brief, including the data and caveats they show.

Record explicit operator decisions already given, with scope and date; do not request them
again. Gates without such a decision remain unresolved. Local work proceeds independently.
