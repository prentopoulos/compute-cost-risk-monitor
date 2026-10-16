## Why

PROJECT.md Phase 8: public demo, methodology document, market brief, two-minute walkthrough and
updated diagrams. The owner made it the **final phase**. It may run over several sessions as one
phase, and it ends with the repository ready to make public on GitHub, so a recruiter can be
shown it. Phase 1's acceptance row "7 Demo and brief" applies: the public dataset is synthetic,
every brief number links to its records and matches a computed value, and the futures sentence
is reframed.

The owner also put the optional AI element in scope: an LLM drafts the brief's prose only, from
numbers the code has already computed and checked (PROJECT.md §5).

The Phase 8 grilling ran two rounds on 2026-10-14 and 2026-10-15, with an informed-answerer
subagent and the main agent re-checking its sources:
- **Round 1:** 22 questions, plus 8 the research found. The owner answered every owner call. The
  owner revised two of them: no split into two phases, and the spend budget. The owner added
  four items: a buyer's bottom line, a model-risk section, an excellent README and a five-slide
  deck. The main agent moved the pre-publication questions forward, because a public-ready end
  depends on them.
- **Round 2:** 7 questions. One reopened the owner's data answer, to give the public demo a
  single consistent dataset.
- **Agreement:** the owner agreed every recommendation and confirmed the full decision list.
- **Before this spec:** PR #14 added the first README (shaped like the owner's fundamental-engine
  repo), the MIT licence, the AI-ops skill and `AI_OPS.md`, and ignore rules for local agent
  config. Reviewing that README, the owner asked for the scenario grid's footer to read less like
  prose. The owner chose terse desk labels that keep §5's labels on screen.

Design D1–D31 are owner decisions; D32–D45 are settled with their basis.

## What Changes

- **One public synthetic dataset.** Two earlier synthetic Azure snapshots (2026-09-28 and
  2026-10-05) go in front of the unchanged `azure_demo.json`. They add one price change, one
  listing "absent once (unconfirmed)" and one "not listed". The dashboard, screenshots, brief,
  bottom line, README and deck then all show the same figures.
- **One-command demo.** `uv run --locked python -m compute_cost_risk_monitor.demo [--serve]`
  builds `data/synthetic.duckdb` fresh from the committed files and never touches the collected
  database.
- **Market brief.** A deterministic `brief` module and CLI build a fact set from a database's
  snapshots. Every number in it links to its records: run, item, retrieval time, response hash,
  currency, unit, rental type and rule versions. Code renders a template brief from it:
  - the **bottom line**, a buyer's decision conclusion, never an investment conclusion;
  - changes and absences between the two latest snapshots;
  - groups per GPU, Spot against pay-as-you-go, and the cross-region spread with thin flags;
  - data-quality counts, the stale flag and "Sample too thin for trends".

  An independent `brief_check`, which never imports `brief`, recomputes every number in the
  final text. The committed public brief is synthetic, in `docs/brief/`. A brief from collected
  Azure prices stays on the owner's PC.
- **AI drafter.** The Claude API (`claude-opus-5-5`, low effort) writes the brief's prose. It
  writes no numbers: it uses placeholders from a closed list, and code fills them. A validator
  rejects:
  - digits and number words;
  - unknown placeholders;
  - missing caveats;
  - banned words.

  On rejection there is one retry, and then the template brief is used. The drafter sees
  synthetic figures only, runs only when the owner starts it, and writes a JSON run record. Tests
  use a fake client, with no key and no network.
- **Grid labels.** "NOT A FORECAST" joins the scenario grid's title, and the exclusions become
  one "EXCL." tag line that lists every exclusion. The crossing, storage, "†" and not-computed
  lines stay. A quick Figma mock comes first. A tiny grid change never prints in exponent form.
- **Documents:**
  - `docs/methodology.md`, with a "Limitations and model risk" section framed on SR 11-7 and a
    dated paragraph on compute futures;
  - the README extended with the bottom line, the one-command setup and links;
  - a five-slide deck in Figma Slides, exported as a PDF to `docs/`;
  - a timed walkthrough script that the owner records;
  - the C4 context and container diagrams updated (the ERD is unchanged).
- **Public-ready.** A pre-publication check covers:
  - a secret scan over all history;
  - a survey of figures from collected data;
  - personal details in current files;
  - licence and credits.

  It produces an exact publishing list for the operator. Making the repository public is the
  last step and needs the operator's gate decision.
- **Project records.** PROJECT.md records:
  - the reframed futures sentence;
  - Phase 8 as final and possibly multi-session;
  - the drafter moved into scope, and no hosting;
  - the spend-gate decision;
  - the Phase 8 decision citation.

  The build-safety skill and AI_OPS.md follow.

## Non-goals

- No second source, scheduled collection, trend claim or hosted app.
- No brief view in the dashboard: the brief is a document.
- No LLM use beyond drafting brief prose. No model in the dashboard, tests, CI or a schedule, and
  no model-computed figure.
- No live Azure price, cost, exposure or SKU-level figure in any public file, prompt, screenshot,
  video or deck.
- No investment conclusion and no forecast (§1, §5).
- No change to a calculation, rule set, map version, scenario set or the schema.
- No fixes from the Phase 7 critiques beyond the grid labels and the exponent-form cell. Hours
  start, Group browser loading and grid export stay recorded.
- No history rewrite. Old commits keep the author email and the earlier personal details.
- No change to the constitution. §5's labels stay on screen in shorter form (D30). The spend-gate
  entry records an operator decision, which is not an amendment (PROJECT.md § Amending the
  constitution).

## Capabilities

### New Capabilities

- `market-brief`: the fact set, the template brief and its bottom line, the independent brief
  check, the CLI, and where briefs are written.
- `brief-drafter`: the hosted-model drafter, its placeholder output, the validator, retry and
  fallback, run records and its limits.
- `demo-setup`: the one-command synthetic demo build.
- `public-release`: the README's bottom line matching the committed brief, the licence and
  credits, and the pre-publication record.

### Modified Capabilities

- `dashboard`:
  - MODIFIED "Figure captions and framing line": "NOT A FORECAST" in the grid title, and the
    "EXCL." tag line in place of the footer's first sentence;
  - MODIFIED "Display formatting": grid cells never in exponent form;
  - MODIFIED "Workload cost view": the demo scenario names the new grid title.
- `synthetic-azure-snapshots`: ADDED "Synthetic demo history", the two earlier snapshots with
  hand-worked known answers.
- `dev-environment`: MODIFIED "Locked Python dependencies", which adds the `anthropic` SDK as a
  runtime dependency.

## Impact

- New code: `brief.py`, `brief_check.py`, `drafter.py` and `demo.py` under
  `src/compute_cost_risk_monitor/`, with tests and synthetic fixtures (two demo-history
  snapshots and fake drafter responses).
- Edited code: `dashboard.py`, plus `pyproject.toml` and `uv.lock`, which gain `anthropic`.
- New documents:
  - `docs/methodology.md`;
  - `docs/brief/` (the synthetic brief, its fact set and run record);
  - `docs/walkthrough.md`;
  - the deck PDF;
  - `docs/assets/` screenshots;
  - `docs/reviews/<date>-phase-8-demo.md`.
- Edited documents: README.md, PROJECT.md, AI_OPS.md, HANDOFF.md, the build-safety skill, the
  fixtures README and the diagrams.
- External services:
  - the Claude API, under the spend gate, with synthetic figures only;
  - Figma, on the owner's Pro seat, for the grid mock, the diagrams and the deck;
  - YouTube or similar, unlisted, only after the publishing gate.
- ⛔ gates:
  - **Spend:** resolved by the operator on 2026-10-14 for this use.
  - **Publishing:** the operator decides last, from the exact list.
  - **Live data:** honoured. The owner may start collects, at most one a day, and collected
    figures never leave the PC.
  - **Scheduling:** untouched.
