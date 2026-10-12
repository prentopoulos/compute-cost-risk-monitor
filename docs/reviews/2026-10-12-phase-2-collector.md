# Phase 2 collector review (market review and build safety)

- **Scope:** OpenSpec change `phase-2-collector` at commit fa53b77, plus the first live run,
  `20261012T151909Z-5473f1` (started by the owner on 2026-10-12 at commit 73b35ac).
- **Reviewer:** the main agent (Claude). This is a read-through, not the code review, which
  `/code-review` does on PR #7.
- **Evidence:** the gate, unit and contract tests, and a check of the live run by a script
  independent of ingest. That script re-read and re-hashed the 15 kept bodies and compared
  every count with DuckDB. Counts only: no price appears in this document.
- **Recheck when:** the request, the row rules, the raw format, the schema or the pacing
  change, or a second source is added.

## Market review (compute-cost-risk-monitor-market-review)

| Check | Outcome | Evidence |
|---|---|---|
| Prices finite, positive, USD, with the original unit kept | Pass | Schema CHECKs. Live DB: 0 non-finite or ≤ 0 prices, all USD. `unit_of_measure` is kept verbatim; reservations carry "<term> term" (1, 3 and 5 Years) |
| USD/GPU-hour round trip | Not applicable | No per-GPU figure until Phase 3 (`gpu_model` and `gpu_count` stay NULL) |
| Every figure carries group key, snapshot time and exclusions | Not applicable | No figure is shown. The command prints counts only. Observations carry region, rental type and retrieval time |
| No duplicate (item, retrieval time); a re-listing is not a new item | Pass | Primary key plus first-copy-wins; later copies go to `observation_repeat`. Synthetic test with a changed price; 0 repeats live |
| Stale and thin flags | Not applicable | Phase 3. A snapshot is defined as one `succeeded` run |
| A failed or empty fetch is not "no prices" | Pass | `partial` and `failed` statuses; an empty page after a full page is fetched again; "not listed" is never inferred (design D7) |
| Results name inputs, code and versions | Pass | Runs record the Git SHA, dependency versions and request parameters. Responses record file, SHA-256, status and errors |
| Missing stays missing | Pass | Nullable-dtype inserts; 0 NaN unit prices live; the synthetic row missing optional fields stores NULLs |
| Labels | Pass | The live run is `live`; fixtures and tests are `synthetic`; the kept-page test builds a `recorded` run, which comes out `partial` |
| Framing | Pass | No code or document calls the data a market price, index, benchmark or what customers pay; "marketplace" appears only in the synthetic-data schema names |

Notes for Phase 3, which compares prices:
- **Windows rows:** 8,014 of the live run's 14,593 rows are Windows products. They are
  stored, and Phase 3 must exclude them from comparisons (Phase 1 D11).
- **Low Priority rows:** 1,824 are stored as `other` and are not compared.
- **5-year reservations:** these exist; reservations are never compared.
- **Offset paging:** it can miss rows silently when the catalogue changes mid-run. Infer "not
  listed" only from repeated absence.

## Build safety (compute-cost-risk-monitor-build-safety)

Workflows read: `assess_threat_vectors`, `generate_tool_schema`,
`configure_telemetry_schema` and `apply_finops_governance`. The agent, ADK, IAM and IaC
guidance does not apply: there is no model, no user accounts and no hosting.

| Threat or control | Disposition | Enforcement and test |
|---|---|---|
| Data or secret exfiltration | No secrets exist. Requests are GET only; next links are pinned to `https://prices.azure.com/api/retail/prices`; redirects are refused; there is no cookie handler | `azure_retail.next_link_problem`, `fetch._NoRedirect`; tests on evil hosts, `@` user-info, http, ports and redirects |
| SSRF, injection, path traversal | `--ingest-run` IDs must match `\d{8}T\d{6}Z-[0-9a-f]{6}`. Sidecar paths must be plain relative POSIX parts (a test caught the Windows forms `/x` and `C:x`). SQL takes fixed table and column names and parameterized or registered values | `raw_store.check_run_id`, `raw_store.read_body`, `ingest._insert`; tests in `test_raw_store.py`, `test_collect.py` |
| Poisoned or stale source data | Raw bytes are kept before parsing; SHA-256 is checked before ingest; deterministic row rules; schema CHECKs; staleness comes in Phase 3 | `test_tampered_body_refused_and_nothing_written`, the row-rule fixtures, the kept-page contract test |
| Supply chain | Lockfile pinned. New dev-only dependencies: pytest-socket 0.8.1 (MIT) and detect-secrets 1.5.0 (Apache-2.0, last release 2024-05). No new runtime dependency | `uv lock --check`; `uv audit` before ready (task 7.3) |
| Denial of service and cost | Requests ≥ 1 s apart (2 s after a 429); 5 attempts; caps of 200 pages, 30 minutes and 64 MiB per body; 24-hour guard between live runs; no paid service | `test_fetch.py` (pacing, caps, retries), `test_collect.py` (guard) |
| Tracing (run records) | Every attempt is a raw file plus a `raw_response` row; summary and tallies per run; write-once records | `test_ingest.py`; the live run's records match its files |
| Prompt injection, confused deputy, cross-user data, replay | Not applicable | No model, no users, no external writes |

Residual risks:
- **urllib's 30 s timeout applies per socket operation.** The 30-minute run cap bounds a slow
  response. Owner: accepted for a manual tool.
- **Rate limits are undocumented.** Azure sent `x-ms-ratelimit-remaining-retailprices-requests:
  9` on every response, and its meaning is unknown. The retry header is honoured after a 429.
  Recheck if a run is throttled.
- **detect-secrets scans files, not Git history.** Do a history scan before the repo goes
  public (Phase 0 D18).
- **`contains()` on `armSkuName` is undocumented.** It worked on the live run. If Azure drops
  it, rows become out of scope and the page cap stops the run as `partial`.
