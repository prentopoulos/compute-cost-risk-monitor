## 1. Dependencies and paths

- [x] 1.1 Add `pytz` (runtime) and `types-pytz` (dev) to `pyproject.toml`, relock, and confirm `uv lock --check` passes
- [x] 1.2 Add `data/` to `.gitignore` and confirm a file under `data/` is ignored

## 2. Schema and connection helper

- [x] 2.1 Write `src/compute_cost_risk_monitor/schema/001_initial.sql` with every table, key, foreign key and CHECK in design § Schema
- [x] 2.2 Write `src/compute_cost_risk_monitor/db.py`: `connect(path)` with `TimeZone=UTC`, and `create_schema(connection)`, which applies numbered SQL files in order, records `schema_version` and skips applied versions
- [x] 2.3 Confirm the SQL file ships with the installed package (read through `importlib.resources` from the synced environment)

## 3. Schema tests on synthetic fixtures

- [x] 3.1 Add labelled synthetic fixture rows under `tests/fixtures/synthetic/` (one Azure-shaped price row set and one marketplace-shaped offer set, with no real data)
- [x] 3.2 Test connection UTC and the round trip of a TIMESTAMPTZ value to Python and pandas
- [x] 3.3 Test schema creation, then a re-run as a no-op
- [x] 3.4 Test the rejections: duplicate observation; zero, negative, NaN and infinite prices; each missing provenance field; unknown label and rental type; synthetic marketplace data labelled live; zero GPU count; detail and derived rows without parents; raw response without a SHA-256
- [x] 3.5 Test the acceptances: unmapped observation with NULL GPU fields, a failed request recorded, one observation under two rule versions, and inserting the synthetic fixtures end to end

## 4. Architecture diagrams

- [x] 4.1 Create the FigJam file on the owner's Pro seat with the C4 system context diagram
- [x] 4.2 Add the C4 container diagram (each box marked built or planned) to the same file
- [x] 4.3 Add the ERD of schema version 1 to the same file
- [x] 4.4 Export all three as SVG to `docs/architecture/` and record the Figma URL in PROJECT.md §4

## 5. Review and documents

- [ ] 5.1 Run the market-review read-through of the schema (units, labels, group-key columns, missing-value handling) and record it in the PR
- [ ] 5.2 Run the gate green in Git Bash and PowerShell, and record the output
- [ ] 5.3 Update HANDOFF with the checkpoint, evidence and the next task (Phase 2 grilling, including the live-data gate for Azure)
