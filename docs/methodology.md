# Methodology

This page explains how Compute Cost & Risk Monitor turns Azure's published GPU prices into a
workload cost and a set of what-if figures. It covers what the tool leaves out, how each number is
checked, and where the tool can be wrong. Every example uses the invented demo prices.

## 1. The question

A team that rents GPUs to train or run AI models needs to know two things:

- **What will this job cost?** For example, 32 GPUs for 720 hours, at today's list price.
- **How exposed is that budget?** How much more, or less, it would cost if list prices moved.

The tool answers both for one workload at a time, from Microsoft Azure's published list prices.
It is a calculator, not a price model: it makes no prediction.

## 2. The data

**Source.** The [Azure Retail Prices API](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices)
is public and needs no account. The collector:
- only reads, with a filter for GPU virtual machines (VMs), page by page;
- runs at most once a day, and only when started by hand;
- sends at most one request per second, and waits when the API asks it to (HTTP 429 and
  Retry-After);
- saves every response to disk, exactly as received, before reading it.

Every run is labelled by how its data was obtained: `synthetic` (invented), `recorded` (rebuilt
from saved responses) or `live` (fetched by that run).

**What a list price is not.** A list price is what Azure publishes. It is not what a customer pays
after negotiated discounts, not a traded price, and not a market index.

**Why the public figures are invented.** Microsoft's API page invites "your own tools for internal
analysis and price comparison across SKUs and regions". If the Microsoft APIs Terms of Use govern
this API, they forbid redistributing "any data obtained" (§3(b)(14)), and no Microsoft page says
which terms apply. So real prices are read for local analysis only, and none is published.

The public demo uses invented prices with real Azure size names, so the GPU map and every rule
work exactly as they would on real data. Every screen, the brief and the deck carry the label
**SYNTHETIC DATA — NOT AZURE LIST PRICES**. Design and review records mention counts from the one
real snapshot, such as how many rows it held. No real price, cost or size-level price appears in
the repository.

## 3. The rules

The rules are versioned and stored with the data: `groups-v1`, `gpu-map-v1`, `scenarios-v1` and
`ladder-v1`. The thresholds were set before any results were looked at.

### 3.1 What gets compared

Each price row either joins the comparison or is set aside, with the first reason that applies, in
this order:

1. **Rental type not compared.** Only pay-as-you-go and Spot are compared. Reservations, savings
   plans and dev/test prices are set aside.
2. **Government cloud region**, such as `usgov` and `usdod`.
3. **Windows.** Only Linux prices are compared.
4. **Unit not hourly.** Only prices per hour are used.
5. **Unmapped size.** GPU models and counts come from a map built only from Microsoft Learn's
   VM size pages. A size the map doesn't name exactly stays unmapped. It is counted, never
   guessed.
6. **Fractional GPU.** Sizes that share one GPU between VMs.
7. **Retired size**, by Microsoft Learn's retirement dates, including regions that were given
   more time.

Rows set aside are counted in the data-quality panel; none disappear silently.

### 3.2 Price per GPU-hour

```text
USD per GPU-hour = the VM's hourly list price ÷ the GPUs in that VM
```

For example, 96.00 USD an hour for an 8-GPU H100 VM is 12.0000 USD per GPU-hour. Stored values
are never rounded; the screen shows four decimals. Each stored price keeps its source item ID,
retrieval time (UTC), currency, unit, rental type and the saved response it came from, so every
figure can be traced back.

### 3.3 Comparable groups

A **comparable group** is the same GPU model and variant, the same GPUs per VM, the same region
and the same rental type. Prices are compared only inside a group.

- A group with one price is shown as a **single list price**: there is nothing to compare.
- A **cross-region summary** takes the lowest listed price in each region for one GPU variant, GPU
  count and rental type. It shows the number of regions, the lowest, median and highest price,
  and is labelled as crossing regions.
- A cross-region summary is **thin** when it covers fewer than 5 regions.

### 3.4 Changes over time

A **snapshot** is one successful run. A **change** is the same listing at a different price in two
snapshots in a row.

- A listing missing from one snapshot is **absent once (unconfirmed)**, because paging through the
  API can miss rows.
- A listing missing from two snapshots in a row is **not listed**, dated at the first absence.
- A missing price is never filled in.
- The data is **STALE** once the latest snapshot is more than 7 days old, and every screen says so.
- There are no trend claims: the history is far too short.

### 3.5 Workload cost

```text
workload cost = GPUs × hours × USD per GPU-hour   (+ storage, only when entered)
```

On the demo, 32 H100 GPUs (4 VMs of 8) for 720 hours at 12.0000 USD per GPU-hour cost
276,480.00 USD. GPU counts go up to 100,000, and hours from 0.01 to 8,784 (a leap year).

**Not included, and said with every cost:** disks and storage (unless entered), data transfer
out, public IP addresses, licences, taxes, negotiated discounts, reservations and savings plans,
the risk of Spot capacity being reclaimed, and capacity and quota limits.

### 3.6 What-if price moves

```text
budget exposure = GPUs × hours × the change in USD per GPU-hour
```

The **what-if grid** (`ladder-v1`) shows the change in cost for list-price moves of −50%, −25%,
−10%, +10%, +25%, +50%, +100% and a flat +0.50 USD per GPU-hour, for 8, 16, 32, 64 and 128 GPUs.
On the demo, a 25% rise adds 69,120.00 USD.

- The move sizes are round numbers chosen by judgement. With one snapshot of history there is
  nothing to calibrate them against. The +100% row tests a sudden jump, an idea taken from
  jump models of compute costs ([arXiv 2603.21690](https://arxiv.org/abs/2603.21690)); its size is
  not taken from any model.
- The **Spot to pay-as-you-go** row shows the cost of moving a Spot job to pay-as-you-go if Spot
  capacity is reclaimed. It crosses rental types and says so. Where the size has no pay-as-you-go
  price in that region, the row says "not computed".
- A move that would take the price to zero or below is not computed.
- A **contingency**, money set aside for price rises, is turned into the rise it covers. For
  example, 11,520 USD set aside for 32 GPUs over 720 hours covers a rise of 0.50 USD per GPU-hour.
- Every figure carries the label "Scenario calculation, not a forecast".

### 3.7 Data quality

The data-quality panel shows counts, never prices:
- how fresh the latest snapshot is;
- how every row was handled: compared, or set aside and why;
- rows the run rejected or saw twice;
- missing optional fields;
- thin groups, and groups that hold a single price.

## 4. How the numbers are checked

**Code computes every number.** On top of that, three checking modules work the numbers out again
in their own way. None of them imports the code it checks:

| Check | What it re-derives |
| --- | --- |
| `checks` | Every stored price per GPU-hour, by multiplying back to the VM price; one result per price row; totals that match the run records |
| `workload_check` | Every workload cost and what-if figure, from VM-hour prices and VM counts instead of the stored per-GPU price |
| `brief_check` | Every number in the written brief, with its own database queries and arithmetic |

A figure that fails its check is not shown.

**Tests.** Every test runs on invented data, with the network blocked:
- known-answer tests on hand-worked examples (`tests/e2e/`);
- property tests with Hypothesis;
- 100% branch coverage for the calculation and data modules.

The same quality gate runs locally and in CI on every pull request.

## 5. The written brief and the AI

The **market brief** is a one-page written summary of a snapshot. It opens with a buyer's bottom
line: the workload cost at the lowest listed price, the range across regions, and how much to
set aside for a +25% or +50% price move. Changes, absences, groups, Spot prices, regions and data
quality follow. Code computes every number and links it to its records.

**The AI-powered brief.** Claude (`claude-opus-5-5`) drafts the brief's text:
- It never sees a number. It sees blanks such as `[[bl_cost]]`, and code fills in the numbers.
- A draft is rejected if it contains a digit, a number word, a banned word, or misses a required
  blank. Banned words include "market price", "index", "forecast", "trend", "will", "cheapest",
  "hedge" and "futures".
- Claude gets two tries. If both are rejected, a plain template is used.
- `brief_check` then re-derives every number in the finished text.
- Drafts are run by hand, on invented prices only. They never run in the tests, CI or the app, and
  never see real Azure prices.

**The real runs, 15 October 2026.** The first run rejected both drafts: they wrote digits inside
GPU names and used the word "one". The fix treats GPU, size and region names as names, not
numbers. The second prompt version lists the names Claude may write and says "a listing", never
"one listing". The second run passed. The two runs cost about USD 0.14 together. Both run records are kept, including
the failed one, and the current one is in [`docs/brief/run-record.json`](brief/run-record.json).

## 6. Limitations and model risk

This section follows the three parts of the US banking regulators' guidance on model risk
([Federal Reserve SR 11-7](https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm)):
conceptual soundness, outcomes analysis and ongoing monitoring.

**Conceptual soundness.** The tool is a list-price calculator. Its assumptions are plain:
- the list price is the price paid;
- cost grows in a straight line with GPUs and hours;
- a per-GPU price is the VM price split evenly;
- what-if sizes are judgement.

None of these holds for a buyer with negotiated discounts or reserved capacity.

**Outcomes analysis.** The tool makes no forecast, so there is nothing to backtest. Instead, every
number is compared with a hand-worked answer in tests, and re-derived independently before it is
shown.

**Ongoing monitoring.** Each run updates the data-quality panel, and the STALE label appears after
7 days. The independent checks run after every normalization, before any workload figure is
shown, and before any brief is written. The gate runs on every change. The model and prompt are pinned, and each AI run keeps a record of its prompt, its
attempts and its cost.

| Area | What could go wrong | Control | Covering tests |
| --- | --- | --- | --- |
| Data | A size gets the wrong GPU model or count | Map built only from Microsoft Learn; sizes it doesn't name exactly stay unmapped and are counted | `test_gpu_map.py`, `test_checks.py` |
| Data | Paging misses rows, and a listing looks withdrawn | "Absent once" before "not listed" | `test_history.py`, `tests/e2e/` |
| Data | Old prices read as current | STALE after 7 days | `test_quality.py`, `tests/e2e/` |
| Data | The API changes its response format | Responses saved as received; rows that don't fit are rejected and counted | `test_ingest.py`, `test_real_page.py` (local only) |
| Method | Unlike machines compared | Comparable groups; any comparison across groups is labelled | `test_groups.py` |
| Method | A list price read as what customers pay, or a what-if read as a forecast | Labels and exclusions with every figure | `test_dashboard.py`, `test_workload_view.py`, `test_scenarios.py` |
| Method | An arithmetic slip | Independent re-derivation in a different form; property tests | `test_workload_check.py`, `test_properties.py` |
| Process | A code change breaks a number | The gate on every pull request; known answers; full coverage of the core modules | `scripts/gate.py`, `tests/e2e/` |
| Process | A secret or a real price is published | Secret scan in the gate and over the whole history; real data stays in the ignored `data/` folder | `.secrets.baseline`, the Phase 8 review record |
| Process | Collection goes beyond the API's terms | Read-only, one run a day by hand, one request per second | `test_collect.py`, `test_fetch.py` |
| AI | The AI writes a wrong number | It never sees or writes a number; `brief_check` re-derives every one | `test_drafter.py`, `test_brief_check.py`, `test_committed_brief.py` |
| AI | The AI overclaims ("cheapest", "forecast", "index") | Banned words; the plain template if both tries fail | `test_drafter.py` |
| AI | Spending runs away | Runs by hand only; two tries; a 4,000-token cap; a USD 10 limit in the provider console | `docs/brief/run-record.json`, `AI_OPS.md` |

**Limits to keep in mind.**
- One provider, list prices only, with no cross-provider comparison.
- One real snapshot so far, so no trends, and the what-if sizes can't be calibrated.
- Sizes that Microsoft Learn doesn't name exactly are left out, not guessed.
- The risk of Spot capacity being reclaimed is not priced.
- The public figures are invented.

## 7. Compute futures, as of 15 October 2026

Exchanges are preparing futures on GPU rental prices, but none trades yet.
- **NYMEX (CME Group)** filed H100 and B200 rental-index futures that settle on Silicon Data's
  indexes. On 21 September 2026 the CFTC
  [extended its review](https://www.cftc.gov/filings/documents/2026/orgdcmnymexcompcontr260921.pdf)
  to the end of 9 November 2026, citing "novel or complex issues". It pointed to its open Request
  for Comment on the Listing of Compute Derivatives Contracts (91 FR 54259), which closes on
  20 October 2026.
- **ICE** plans H100 and B200 futures on Ornn's Compute Price Index. Its
  [29 September 2026 notice](https://www.ice.com/publicdocs/futures_us/exchange_notices/ICE_Futures_US_Exchange_Notice_ORNN_Compute_4Q2026_20260929.pdf)
  says "no listing date or timeline has been set". In the meantime, ICE publishes hypothetical
  daily settlement prices.

This project doesn't use or depend on these contracts or indexes. It builds the groundwork they
rely on: prices made comparable, and a clear measure of how exposed a budget is. Both documents
were rechecked on 15 October 2026.

## 8. Credits and further reading

- **GPU map:** contains material from Microsoft Learn, © Microsoft, licensed under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). See
  [its attribution](../src/compute_cost_risk_monitor/reference/README.md).
- **Silicon Data's [H100 index](https://www.silicondata.com/products/silicon-index/h100)**
  adjusts for differences in configuration and rental conditions. It is a reference for the
  problems this project handles. This project is not an index and doesn't claim to be one.

Further reading:
- Byrne, Corrado and Sichel, *The Rise of Cloud Computing: Minding Your P's, Q's and K's*, NBER
  Working Paper 25188: price indexes for cloud services that adjust for quality.
- Agmon Ben-Yehuda et al., *Deconstructing Amazon EC2 Spot Instance Pricing*, ACM TEAC, 2013:
  evidence that EC2 Spot prices were set by the provider, not by the market.
- Kilcioglu and Rao, *Competition on Price and Quality in Cloud Computing*, WWW 2016: cloud
  prices differ by product rather than converging.
- Basel Committee on Banking Supervision, *Stress testing principles* (d450), 2018: the basis for
  labelled, judgement-based scenarios.
- Javadi, Thulasiram and Buyya, *Characterizing spot price dynamics in public cloud
  environments*, Future Generation Computer Systems, 2013.
