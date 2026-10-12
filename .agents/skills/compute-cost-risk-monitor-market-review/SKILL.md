---
name: compute-cost-risk-monitor-market-review
description: Design or review Compute Cost & Risk Monitor offer data, comparable pricing, workload costs, budget exposure and the market brief with reproducible evidence and fair baselines. Use when any of these or the reported results change.
---

# Compute Cost & Risk Monitor market review

Read [PROJECT.md](../../../PROJECT.md) and the affected OpenSpec requirements. Follow
[compute-cost-risk-monitor-build-safety](../compute-cost-risk-monitor-build-safety/SKILL.md) when adapters,
recording or paid-call behavior also change.

## Define the question before running

The project makes three comparisons, and each is evidence of one thing only:
- Price versus price inside a comparable group (same GPU variant, GPU count, region and
  rental type): relative published Azure list price at that time, or relative asking price in
  labelled synthetic marketplace data. Not a market price or what customers pay.
- A group now versus earlier: a change in observed published prices over the stated window.
  Not a trend until several weeks of data exist, and never a forecast.
- Workload cost at observed prices versus a labelled scenario: budget exposure, i.e.
  GPUs × hours × price change. A calculation, not a prediction.

Separate what is compared from how it is computed. Use the same offers, filters, units and
exclusions for every candidate. Fix the comparable-group key, the snapshot or window and any
threshold before looking at results; never pick a window because it looks dramatic.

Label each case as normal, edge or deliberately failing. Label synthetic inputs as synthetic.

## Validate independently

Check schema, finite values, ranges and units before computing. Check outputs with
deterministic code independent of the code that produced them. Every output must satisfy:
- Prices are finite and positive, in USD, with the original unit kept beside USD/GPU-hour.
- USD/GPU-hour × GPU count reproduces the hourly price it came from, with the same inclusions.
- Workload cost = GPUs × hours × USD/GPU-hour, plus storage when included; exposure =
  GPUs × hours × scenario change. The 32 × 720 × $0.50 = $11,520 example passes.
- Every figure carries its comparable-group key, snapshot time and stated exclusions.
- No duplicate (offer ID, retrieval time) rows; a re-listed offer is not a new offer.
- Stale offers (older than the declared threshold) and thin groups (below the declared
  minimum count) are flagged, never silently averaged in.

Establish correctness on tiny fixtures with known answers, plus normal, edge and impossible
cases. A failed or empty fetch means nothing was collected, not that no offers exist; a run
without exceptions is not a correct run. Distinguish observed from estimated, and asking
prices from what a buyer would actually pay.

## Fix evaluation before tuning

Freeze the comparable-group rules, staleness and thin-sample thresholds, scenarios and
held-out fixtures before tuning charts or summaries. Version rule changes and recompute the
affected figures. Deterministic correctness is a hard gate; an AI-drafted brief is a
separately reviewed draft. Live fetches and paid calls stay out of ordinary tests and CI.

## Record and compare honestly

Every result names its inputs (offer IDs, raw-response hash, snapshot time), code,
dependency and rule versions, filters, scenario and exclusions, plus status, independent
validation outcome and figures. Missing fields stay unknown with a reason; an uncollected
price is null, not zero. Each collection run also records its request parameters, HTTP
status, offer count, raw-response file and failures.

Record failed runs. Statistics that exclude rows state their count and denominator.
A small sample establishes behavior on its tested offers, not market-wide prices or trends.

For live work, follow PROJECT's `⛔` gates and keep each original response with its
retrieval time. Never call an endpoint that rents or changes an instance; a request that
may have spent credit is investigated before any retry.

## Interpret and deliver

Distinguish source fact, user decision, assumption, scenario and observed result. Every
number in the market brief links to its records and matches a computed value. State the
offers, window and remaining unknowns. Completion is a traceable, independently checked
finding with limits, even when the honest finding is "no meaningful change" or "sample too thin".
