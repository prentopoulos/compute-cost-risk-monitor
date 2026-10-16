## ADDED Requirements

### Requirement: Brief fact set
The `brief` module SHALL build a fact set from one database's `azure-retail` snapshots as of a
given time, reading stored rows only and computing every figure with the existing groups,
history, quality, calculator and scenario code. Each fact SHALL have:
- an ID from a closed list;
- its value and units;
- the comparable-group key, or the groups it crosses;
- its record links: run ID, item key, retrieval time in UTC, raw-response SHA-256, currency,
  original unit, rental type, rule version and map version. A derived fact SHALL instead list
  the fact IDs it is computed from.

The fact set SHALL be written as JSON with sorted keys, so the same database and as-of time give
the same bytes. Missing values SHALL stay null with a reason, never zero.

#### Scenario: Facts link to their records
- **WHEN** the fact set is built from the demo database as of 2026-10-12 09:00 UTC
- **THEN** the lowest listed H100 ×8 pay-as-you-go fact is 12.0000 USD/GPU-h in US East, with the 2026-10-12 run ID, its item key, retrieval time and raw-response SHA-256

#### Scenario: Reproducible bytes
- **WHEN** the fact set is built twice from the same database and as-of time
- **THEN** the two JSON files are byte-identical

#### Scenario: Missing stays missing
- **WHEN** a fact's source value is absent
- **THEN** the fact's value is null and carries its reason, and no figure is printed for it

### Requirement: Template brief
The `brief` module SHALL render a Markdown brief from the fact set, with no model involved. It
SHALL open with the data label, the source framing ("Published retail list prices for GPU VMs
from one cloud provider, Azure (Azure Retail Prices API)" or, for synthetic data,
"SYNTHETIC DATA — NOT AZURE LIST PRICES"), the snapshot start and the AS OF time in UTC, and STALE
when it applies. It SHALL then hold, in order:
1. the bottom line ("Brief bottom line");
2. changes between the two latest snapshots, each with both prices in USD/VM-h and USD/GPU-h and
   both snapshot times, or "No change between <time> and <time>.";
3. absences, using the exact terms "absent once (unconfirmed)" and "not listed";
4. groups per GPU variant, with "single list price" where a group has one price;
5. Spot against pay-as-you-go for the same size and region, each line marked "crosses rental
   types";
6. the cross-region spread per GPU variant and GPUs per VM, marked "crosses regions" and "thin"
   under 5 regions;
7. data-quality counts and the stale flag;
8. "Sample too thin for trends: <n> snapshots over <d> days.".

Every workload or scenario figure SHALL carry the exclusions sentence and "Scenario calculation,
not a forecast.", and the brief SHALL include the judgement note for scenarios and the Microsoft
Learn CC BY 4.0 credit for the GPU map. It SHALL end with a Records table: each fact ID used,
with its run ID, item key, retrieval time and raw-response SHA-256, or the fact IDs it derives
from. Figures SHALL use the dashboard's display formats.

#### Scenario: Changes on the demo
- **WHEN** the template brief is rendered for the demo database as of 2026-10-12 09:00 UTC
- **THEN** its changes section lists the US East H100 ×8 pay-as-you-go change from 88.00 to 96.00 USD/VM-h (11.0000 to 12.0000 USD/GPU-h) between 2026-10-05 09:00 and 2026-10-12 09:00 UTC, and its absences section names one listing "absent once (unconfirmed)" and one "not listed" since 2026-10-05

#### Scenario: Single snapshot
- **WHEN** a database holds one snapshot
- **THEN** the changes section says changes need a second snapshot, and the thin-sample line reads "Sample too thin for trends: 1 snapshot over 0 days."

#### Scenario: Every figure traced
- **WHEN** any template brief is rendered
- **THEN** every fact ID it uses appears in its Records table

### Requirement: Brief bottom line
The bottom line SHALL be a buyer's decision summary, never an investment conclusion or a
forecast. For a workload (default 32 GPUs × 720 hours) on a GPU variant and GPUs per VM (default
H100 NVLink 80GB × 8), it SHALL state, from the cross-region pay-as-you-go summary of that
variant and count:
- the workload cost at the lowest listed pay-as-you-go price, with its region, size and
  USD/GPU-h;
- the number of regions, the lowest and highest listed USD/GPU-h and the matching cost range,
  marked as comparing across regions, and "thin" under 5 regions;
- the contingency that covers a +25% and a +50% list-price move, from `ladder-v1`, followed by
  "Scenario calculation, not a forecast.";
- "Not priced:" followed by the exclusions, word for word.

It SHALL say "lowest listed", never "cheapest", and "for <hours> hours", never "monthly". Spot
SHALL NOT anchor it.

#### Scenario: Bottom line on the demo
- **WHEN** the template brief is rendered for the demo database as of 2026-10-12 09:00 UTC
- **THEN** its bottom line states 32 H100 NVLink 80GB GPUs (4 × ND96isr H100 v5) for 720 hours cost USD 276,480.00 at US East, 12.0000 USD/GPU-h; 5 regions at 12.0000–15.0000 USD/GPU-h, so USD 276,480.00–345,600.00, comparing across regions; contingencies of USD 69,120.00 for +25% and USD 138,240.00 for +50%, then "Scenario calculation, not a forecast."; and the exclusions

#### Scenario: No pay-as-you-go listing
- **WHEN** the chosen GPU variant and count has no pay-as-you-go listing in the snapshot
- **THEN** the bottom line says so and states no cost

### Requirement: Independent brief check
A `brief_check` module, which SHALL NOT import `brief`, SHALL re-derive every figure in a final
brief from the database with its own queries and arithmetic, as `workload_check` does. It SHALL
extract every number in the brief outside the Records table, run IDs, item keys and hashes, and
SHALL pass only when each one equals a re-derived value at its displayed decimals, rounded half
up. Snapshot and as-of times SHALL match the stored runs and the given as-of time. A failure
SHALL name each unmatched number and its position.

#### Scenario: Correct brief passes
- **WHEN** the template brief for the demo is checked
- **THEN** every number matches and the check passes

#### Scenario: Tampered number named
- **WHEN** one figure in a brief is changed by 0.01
- **THEN** the check fails and names that number and its line

#### Scenario: Unknown number named
- **WHEN** a brief contains a number that no re-derived value matches
- **THEN** the check fails and names it

### Requirement: Brief command
`python -m compute_cost_risk_monitor.brief --db FILE [--as-of TIME] [--out DIR] [--draft]` SHALL
build the fact set, render the brief (drafted when `--draft` is given, see `brief-drafter`), run
the independent check, and write `brief.md`, `facts.json` and `run-record.json` to the output
folder only when the check passes. `--as-of` SHALL default to now in UTC. Any offset SHALL be
converted to UTC. The output SHALL default to `data/briefs/<run ID>/`.

It SHALL refuse (exit 2, writing nothing) a database without a succeeded `azure-retail` snapshot,
and a non-synthetic snapshot with an output folder outside `data/`. It SHALL exit 1, writing
nothing, when the independent check fails on the template brief. With `--draft`, a fallback to
the checked template brief writes that brief and exits 1 (see `brief-drafter`). Otherwise it
SHALL exit 0. It SHALL print counts and paths only, never a price.

#### Scenario: Collected prices stay local
- **WHEN** the latest snapshot is labelled `live` and the output folder is `docs/brief`
- **THEN** the command refuses with exit code 2 and writes nothing

#### Scenario: Check failure writes nothing
- **WHEN** the independent check fails
- **THEN** the command exits 1 and the output folder holds no new brief

#### Scenario: Pinned as-of
- **WHEN** the command runs twice with `--as-of 2026-10-12T09:00:00Z` on the same demo database without `--draft`
- **THEN** both runs write byte-identical `brief.md` and `facts.json`

### Requirement: Committed synthetic brief
The repository SHALL commit, in `docs/brief/`, a brief built from the demo database as of
2026-10-12 09:00 UTC, with its fact set and run record. The brief SHALL pass the independent
check. No brief built from collected prices SHALL be committed.

#### Scenario: Committed brief still checks
- **WHEN** the demo database is rebuilt and the committed brief is checked against it
- **THEN** the check passes, and the committed fact set equals a freshly built one
