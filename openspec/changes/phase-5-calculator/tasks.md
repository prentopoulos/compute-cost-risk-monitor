## 1. Calculation core

- [x] 1.1 Write `scenarios.py`: a frozen `scenarios-v1` (version, and per scenario ID, name, kind, magnitude and narrative) plus the judgement note, as data only (D6). Test the contents (a decline and a spike, four scenarios, narratives) and that the set cannot be changed
- [x] 1.2 Write `calculator.py` (D3, D5, D13–D16, D18, D21, D24): the workload validator (whole VMs with the nearest counts; hours, storage and custom bounds; non-finite refused), the starting price from a region group and an optional picked size, compute cost and total, scenario rows with signed exposure and effect, the price ≤ 0 refusal and the custom row. Known-answer tests: 32 × 720 × $0.50 = $11,520, the spec's decline, cost with and without storage, and every refusal
- [x] 1.3 Add the Spot to pay-as-you-go fallback, the above-pay-as-you-go note and budget headroom to `calculator.py` (D7, D9, D11, D25). Test fallback priced, equal (0, "no change"), missing ("not computed"), no fallback on pay-as-you-go, the note on a crossing row and not below, known headroom and the zero-budget refusal
- [x] 1.4 Write `workload_check.py` (D19): imports no calculator code; re-derives every figure from plain values and `scenarios.py`; names failing checks. Test that a correct result passes, that tampering with each figure kind fails with its name, and, by inspecting imports, that it imports nothing from `calculator.py`

## 2. Demo data

- [x] 2.1 Add the invented uksouth Spot `Standard_ND96isr_H100_v5` item to `tests/fixtures/synthetic/azure_demo.json` and update the fixtures README (D12). Update the demo coverage test (MODIFIED `synthetic-azure-snapshots`) and any test that counts the demo's groups or Spot regions

## 3. View model and page

- [x] 3.1 Extend `dashboard.py` (D10, D16, D18, D21): the starting-price text, cost breakdown and scenario frames, workload captions (storage, billing assumptions, Spot, crossing rental types, `scenarios-v1`, "Scenario calculation, not a forecast", judgement note), USD and % display formats, the headroom text and the exposure chart spec (D8). Unit-test captions on every frame, formats, and the chart's bars, zero rule and absent refused rows
- [x] 3.2 Add the "Workload cost" tab to `app.py` (D17, D24–D27): size choice per group, inputs with `persist_state="page"`, custom scenario and budget inputs, the marketplace note, the database states, validator messages, and the independent check run before drawing, with its failure message. AppTest flows on synthetic file databases with a fixed as-of time: the known workload, inputs kept across tabs, a group change with a non-multiple GPU count, the size choice, the custom scenario, headroom, the uksouth fallback "not computed", the marketplace note, NOT NORMALIZED and a failed check

## 4. Verification, review and documents

- [ ] 4.1 Manual check: rebuild `data/synthetic.duckdb` and run the tab in Chrome on synthetic data; run an AppTest pass on `data/monitor.duckdb`, reported as counts, keys and pass or fail only. Take PR screenshots from synthetic data only
- [ ] 4.2 Update the FigJam container view (calculator built) and re-export `docs/architecture/c4-container.svg`
- [ ] 4.3 Run the market-review read-through (formulas, units, labels, exclusions, the crossing label, refusals, the BCBS checklist) and the build-safety check (read-only access, no network, inputs), and record them in `docs/reviews/`
- [ ] 4.4 Run the gate green and `uv audit`, then record the output
- [ ] 4.5 Update PROJECT.md (§6 Phase 5 status) and HANDOFF.md with the checkpoint, evidence, limitations and the next task
- [ ] 4.6 Run `/code-review` on the PR and resolve its findings with tests
