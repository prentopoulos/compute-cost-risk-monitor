## ADDED Requirements

### Requirement: Drafter request
With `--draft`, the brief command SHALL ask a hosted model for the brief's prose through the
official Anthropic SDK, from `drafter.py` only:
- model `claude-opus-5-5`, effort `low`, `max_tokens` 4,000, one request per attempt;
- a versioned system prompt stored in the package (`prompt v2`), whose SHA-256 is recorded;
- structured output: one prose string per brief section;
- one user message holding the fact IDs with their meanings and units.

It SHALL set no fallback model. It SHALL read the key from `ANTHROPIC_API_KEY` and never print,
log or record it. Without the key, it SHALL refuse with exit code 2 before any request.

#### Scenario: Missing key refused
- **WHEN** `--draft` is given and `ANTHROPIC_API_KEY` is not set
- **THEN** the command exits 2, sends no request and writes nothing

#### Scenario: Request shape
- **WHEN** a draft is requested through an injected fake client
- **THEN** the request names `claude-opus-5-5`, effort `low`, `max_tokens` 4000, the `prompt v2` system prompt and the section schema, and sets no fallback

### Requirement: Synthetic inputs only
The drafter SHALL run only on a snapshot labelled `synthetic`. For a `live` or `recorded`
snapshot, `--draft` SHALL be refused with exit code 2 before any request, and the template brief
is the only brief for collected prices.

#### Scenario: Collected prices never sent
- **WHEN** `--draft` is given for a database whose latest snapshot is labelled `live`
- **THEN** the command exits 2 and no request is sent

### Requirement: Placeholders and fill
The drafter's prose SHALL contain no numbers. Every figure SHALL be a placeholder `[[fact_id]]`
naming a fact in the fact set. Code SHALL replace each placeholder with its value in the
dashboard's display formats, and SHALL insert every required text itself:
- the data label, the source framing, the snapshot and AS OF times, and STALE when it applies;
- the exclusions sentence with every workload figure, and "Scenario calculation, not a
  forecast." with every scenario figure;
- the judgement note, the crossing notices, the "thin" and "single list price" labels;
- the history terms and the thin-sample line;
- the Microsoft Learn credit;
- the closing line "Prose drafted by claude-opus-5-5 (prompt v2); every number placed and
  checked by code.".

The filled brief SHALL pass the independent brief check before it is written.

#### Scenario: Filled from facts
- **WHEN** a valid draft's bottom-line prose uses `[[workload_cost_lowest]]`
- **THEN** the written brief shows 276,480.00 in its place on the demo, and the brief check passes

### Requirement: Draft validator
A deterministic validator SHALL reject a draft section that has:
- a digit outside placeholders and outside the snapshot's GPU, size and region names
  (H100 and US West 3 are names, not figures, as in the independent check);
- a number word outside placeholders: zero to twenty, thirty to ninety by tens, hundred,
  thousand, million, billion, half, halves, twice, double, doubled, triple, tripled, quarter,
  percent, per cent, dozen;
- a placeholder that names no fact in the fact set;
- a missing required placeholder for its section (the bottom line needs the workload cost, its
  region, the regional range and both contingencies);
- a banned word or phrase, matched case-insensitively at word boundaries: market price, market
  rate, marketplace, index, benchmark, executed, trade, traded, trading, "what customers pay",
  "customers pay", "actual cost", forecast, predict, prediction, projected, projection, trend,
  trending, live, will, expect, expected, likely, capacity, availability, "in stock", AWS,
  Amazon, Google Cloud, GCP, Oracle, CoreWeave, Lambda, "other clouds", market-wide, "the
  market", industry, ticker, bid, "bid/ask", monthly, "per month", "a month", cheapest, spread,
  deal, bargain, guarantee, safe, risk-free, hedge, futures.

A refusal, a `max_tokens` stop or output that does not match the section schema SHALL count as a
rejection. After filling, the validator SHALL confirm that every required text is present. It
SHALL scan only the model's prose, never code-filled text.

#### Scenario: Each rejection case
- **WHEN** fake responses hold, one at a time, a digit, the word "twice", an unknown placeholder, a bottom line without its contingency placeholders, the word "cheapest", the word "will", a refusal stop and a `max_tokens` stop
- **THEN** each draft is rejected with its reason named

#### Scenario: Valid draft accepted
- **WHEN** a fake response uses only known placeholders, no numbers and no banned words
- **THEN** the draft is accepted and filled

### Requirement: Retry and fallback
After a rejected draft, the drafter SHALL try once more. When the second draft is also
rejected, or the request fails, the command SHALL write the template brief, record every
rejection reason, and exit 1 for the draft while still writing the checked template brief.

#### Scenario: Two rejections fall back
- **WHEN** two fake responses in a row are rejected
- **THEN** exactly two requests are made, the written brief is the template brief, the run record names both reasons, and the exit code is 1

#### Scenario: Second attempt accepted
- **WHEN** the first fake response is rejected and the second is valid
- **THEN** the written brief is the filled draft and the run record names the first reason

### Requirement: Drafter run record
Every brief command run SHALL write `run-record.json` beside the brief, holding:
- provider, model ID and SDK version;
- prompt version and SHA-256, and the fact set's SHA-256;
- for each attempt: request ID, stop reason, input, output and thinking tokens, and the
  validator outcome with its reasons;
- the estimated cost in USD, with the pricing date it uses;
- the text used ("draft" or "template"), the data label and the git commit.

A template-only run SHALL record that no request was made. The record SHALL never hold the key.

#### Scenario: Record of a drafted run
- **WHEN** a draft is accepted on its first attempt through a fake client
- **THEN** the run record names `claude-opus-5-5`, `prompt v2`, one attempt with its token counts and outcome, the text used "draft" and the data label `synthetic`

### Requirement: Offline tests
Tests SHALL inject a fake client and SHALL need no key and no network. Fixture responses SHALL be
labelled synthetic. Only a run the owner starts by hand, under the PROJECT.md §6 spend gate, SHALL
reach the model API.

#### Scenario: No network in tests
- **WHEN** the test suite runs with sockets disabled and no `ANTHROPIC_API_KEY`
- **THEN** every drafter test passes
