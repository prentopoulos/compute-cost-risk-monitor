# Compute Cost & Risk Monitor

Owner: Peter Rentopoulos. Created: 2026-10-11.

## 1. Goal

A tool that answers: **which comparable GPU rental offers are available, what would my
workload cost, and how exposed is my budget to changing prices?** It works today from
observed marketplace offers, without depending on compute futures launching.

- Users: a GPU buyer sizing a workload (the product persona). Audience for the demo:
  contacts and recruiters on trading-data, compute-market and AI-product teams. For sales
  recruiters, lead with the commercial decision it supports.
- What it demonstrates: market curiosity, quantitative reasoning, product delivery and
  research discipline. The methodology (comparability, units, data quality) is the centrepiece.
- What it is NOT: a market-wide benchmark or index, executed-trade prices, or a price
  forecast. The dataset is **observed marketplace asking prices**. Budget exposure is a
  calculation under labelled scenarios, not a prediction. Not a production service.
- Budget: seven focused sessions, roughly 20–25 hours, built alongside exams by replacing
  some study blocks rather than adding a full workload.

## 2. Current scope boundary

In scope (one phase per session, see §6):

- Live offer collection from one marketplace, Vast.ai: timestamped offers, original
  responses retained.
- Comparable pricing: separate GPU variants, GPU counts, regions and rental types; compute
  USD/GPU-hour.
- Workload calculator: GPU count, hours and storage in; cost out, with disclosed exclusions.
- Budget exposure: cost changes under explicitly labelled price scenarios. Example:
  32 GPUs × 720 hours × a $0.50/hour increase = $11,520 additional monthly expense.
- Data-quality panel: missing fields, duplicates, stale observations and thin samples.
- Market brief: observed changes, each linked to its underlying records.

Deferred or out of scope:

- A second source, added only after its access and comparable fields are verified (⛔ below).
- Trend claims, made only after several weeks of collection.
- The optional AI agent, which may only draft the market brief from validated numbers (⛔ spend).
  Before proposing it, install the setup kit's AI-ops skill and AI_OPS.md (deferred 2026-10-11).
- Renting, creating or modifying instances, or any account action beyond reading offers.
- Accounts, logins or multiple users. Hosting before Phase 7 (⛔ publishing).

Data: real public offer data from Vast.ai once its ⛔ gate is resolved. Tests use synthetic
or recorded fixtures, labelled as such. Runs single-user and local until the Phase 7 demo.

## 3. Acceptance and evidence

Per-phase acceptance criteria: Phase 1 writes them into OpenSpec; next-phase grills the
user before each later phase. Evidence that counts in every phase:

- Every price traces to its source record: offer ID, retrieval time (UTC), original
  response, currency, unit and rental type. Normalized figures record how they were derived.
- Units, normalization, cost and exposure maths pass pytest on fixtures with known answers,
  including missing data and stale offers.
- Prices, costs, exposure figures and the brief pass the compute-cost-risk-monitor-market-review
  checks before they are shown or reported.
- Synthetic, recorded, stale and live data are labelled; a mocked fetch is not a live result.
- Trends need several weeks of observations; until then the app says the sample is thin.

## 4. Stack and commands

- Python, pandas, DuckDB, Streamlit, pytest (decided). Phase 0 grilling, 2026-10-11 (all
  owner calls answered by the owner; settled answers cited in
  `openspec/changes/phase-0-toolchain/design.md` D1–D23): Python 3.13 managed by uv with a
  committed `uv.lock`; Ruff for format and lint; mypy strict; pytest with pytest-cov;
  commitizen for commit messages; OpenSpec CLI 1.6.0 pinned through npm; hosted CI on GitHub
  Actions (owner). Package `compute_cost_risk_monitor` (owner). Run Python only through uv:
  bare `python` differs by shell on the owner's PC.
- Data source: [Vast.ai API](https://vast.ai/developers/api) offer search (by GPU, price,
  location and other specifications). Not used yet; whether it needs an API key is checked in
  Phase 2 under its ⛔ gate.
- Methodology reference: [Silicon Data's H100 index](https://www.silicondata.com/products/silicon-index/h100)
  adjusts for configuration and rental-condition differences. This project shows those
  problems are understood; it does not claim to be an index.
- Optional: an LLM to draft the market brief from validated numbers. Provider TBD (⛔ spend).
- Architecture diagrams: a new Figma draft on the owner's Pro seat, drawn to standard
  conventions (proposed: C4 context and container views plus an ERD of the DuckDB schema; to
  confirm in Phase 1). Exported into `docs/` so the repo shows them.
- Code review: every PR that changes code is reviewed before merge (WORKFLOW.md).

Gate: `uv run --locked python scripts/gate.py` after `uv sync --locked` and `npm ci`; CI runs it plus
`uv audit --locked` on every PR and push to main.
Remote: https://github.com/prentopoulos/compute-cost-risk-monitor (private). Push phase
branches and open PRs at the points WORKFLOW.md sets; nothing goes straight to main, and a PR
merges only after its review and the user's go-ahead. Follow WORKFLOW.md for phase work.

## 5. Non-negotiables

- Secrets use the runtime secret mechanism (gitignored .env for local development); never
  print, commit or include them in reports.
- Label mocked, local and live results accurately. Preserve failed runs.
- Operator resolves all ⛔ gates. The agent never satisfies or waives one itself.
- Call the data observed marketplace asking prices, never executed trades or a market-wide
  benchmark. Label every exposure figure as a scenario calculation, not a forecast.
- Deterministic code computes every price, cost and exposure figure. An AI agent, if used,
  only drafts prose from validated numbers, and every number it writes must match a computed one.
- Compare offers only within a comparable group (GPU variant, GPU count, region, rental
  type), or say plainly that a comparison crosses groups. State cost exclusions with every
  workload figure.
- The collector only reads offers. Never call endpoints that rent, create or change
  instances or spend account credit.
- Use a data source only within its terms of use and rate limits. Missing observations stay
  missing; never fill them in to make a chart look complete.

## 6. Milestones and gates

Milestones are ordered by dependency. Phases 1–7 are the brief's seven sessions. Every phase
tests what it builds; Phase 6 closes the gaps the brief lists.

| Phase | Deliverable | Status |
|---|---|---|
| 0 | Toolchain, lockfile, quality gate, smoke checks | In progress |
| 1 | Requirements, data schema and acceptance criteria; architecture diagrams in Figma | Planned |
| 2 | Working Vast.ai collector keeping original responses; observations start accumulating | Planned |
| 3 | Normalization to USD/GPU-hour, comparable-offer grouping, duplicate handling, quality checks | Planned |
| 4 | Streamlit dashboard with comparable-offer filters and the data-quality panel | Planned |
| 5 | Workload cost calculator and labelled budget-exposure scenarios | Planned |
| 6 | Tests for units, calculations, missing data and stale offers | Planned |
| 7 | Public demo, methodology document, market brief, two-minute walkthrough; diagrams updated | Planned |

### ⛔ Before reading live data from Vast.ai or any other source

- [ ] Operator confirms the source's terms of use and rate limits allow the planned
      collection, and puts any API key in .env.
- [ ] Before a second source: operator confirms access works and its fields are comparable.

### ⛔ Before scheduling unattended collection

- [ ] Operator approves where the collector runs (this PC, GitHub Actions or elsewhere) and
      how often.

### ⛔ Before spending money or paid quota

- [ ] Operator approves the service (paid API plan, LLM calls for the brief, hosting) and a
      budget. This project never spends Vast.ai account credit.
- Decision, 2026-10-11 (owner, Phase 0 grilling): GitHub Actions CI may use the account's free
  included minutes; the owner confirmed overage cannot bill. Scope: the Phase 0 CI workflow
  and its later updates. It approves no paid service.

### ⛔ Before publishing

- [ ] Operator approves making the GitHub repo public, deploying the demo, and sharing the
      walkthrough or brief, including the data and caveats they show.

Record explicit operator decisions already given, with scope and date; do not request them
again. Gates without such a decision remain unresolved. Local work proceeds independently.
