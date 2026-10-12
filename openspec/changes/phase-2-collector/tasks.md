## 1. Dependencies, network blocking and secret scan

- [x] 1.1 Add `pytest-socket` and `detect-secrets` as dev dependencies, relock, and confirm `uv lock --check` passes
- [x] 1.2 Run tests with `--disable-socket --allow-unix-socket`, mark the Streamlit smoke test to allow sockets, and show that a test opening a network socket fails
- [x] 1.3 Add the detect-secrets scan to `scripts/gate.py` with a committed `.secrets.baseline`. Show that a planted fake secret fails the gate, then remove it
- [x] 1.4 Reword the `pyproject.toml` description to the published Azure list-price framing

## 2. Schema version 2

- [x] 2.1 Write `schema/002_run_records.sql` with `collection_run_summary`, `collection_run_tally` and `observation_repeat`, as in design § Schema version 2
- [x] 2.2 Update the schema tests:
  - fresh databases hold versions 1 and 2, and an upgrade from version 1 applies only 2;
  - a referenced run row cannot be updated;
  - the summary identity, negative counts, unknown runs and sources, tally kind and zero counts, and repeat references are each rejected;
  - a reservation row with a term unit is accepted

## 3. Azure row rules (pure)

- [x] 3.1 Write `azure_retail.py`: the fixed first-page URL, and the next-link check (host, scheme, port, path, missing parameters)
- [x] 3.2 Add item classification (scope, rejection reasons, rental type, flags), the item key and the price unit
- [x] 3.3 Add labelled synthetic item fixtures and known-answer tests for normal, edge and deliberately failing items:
  - Spot on DevTest, disagreeing names, Low Priority and unknown types;
  - reservations with and without a term;
  - zero and NaN prices, non-USD, non-primary, missing fields and wrong types;
  - NP out of scope, a shared meter, and a non-hourly unit

## 4. Raw retention and fetching

- [x] 4.1 Write `raw_store.py`: write-once body (gzip level 9, mtime 0), sidecar and manifests, plus read-back with SHA-256 and length checks. Test byte equality, reproducibility, no overwrite, empty failed bodies and the sidecar's left-out fields
- [x] 4.2 Write the urllib fetcher: GET only, no redirects, identity encoding, User-Agent, 30 s timeout and 64 MiB cap. Test it with a fake opener
- [x] 4.3 Write the paced fetch loop with an injected fetcher, clock and sleep: pacing, slower pacing after a 429, `Retry-After` (seconds and HTTP date, capped), the 60 s and exponential waits, 5 attempts, no retry on other 4xx, page and time caps, the empty-page refetch, invalid and repeated next links, and Ctrl-C writing the end manifest. Test each

## 5. Ingest and command

- [x] 5.1 Write `ingest.py`:
  - read a run's files, verify them and parse;
  - classify the rows, keep first copies, record repeats and flags, and work out status and counts;
  - write everything in one transaction;
  - refuse a run already ingested, and write nothing on an integrity failure
- [x] 5.2 Write `collect.py`:
  - live fetch then ingest, labelled `live`;
  - `--ingest-run`;
  - the 24-hour guard;
  - exit codes, and a summary printed without prices
- [x] 5.3 Add an end-to-end contract test on a synthetic three-page run, and check it independently:
  - known counts, rental types, units and repeats;
  - the accounting identity;
  - every observation traces to a kept body whose SHA-256 matches;
  - also cover a partial run, a failed run and a crash restored with `--ingest-run`

## 6. Live run (owner)

- [ ] 6.1 The owner runs `uv run python -m compute_cost_risk_monitor.collect` once. Record the status and counts, and the answers to the design's Open Questions, without prices
- [ ] 6.2 Keep one real page under `data/`, and add the local-only contract test that skips when the file is absent

## 7. Diagrams, review and documents

- [ ] 7.1 Update the FigJam container view and ERD, and re-export the SVGs to `docs/architecture/`
- [ ] 7.2 Run the market-review read-through of stored rows (units, labels, missing values, reservations, repeats) and the build-safety check of the adapter, and record both in the PR
- [ ] 7.3 Run the gate green in Git Bash and PowerShell and `uv audit`, and record the output
- [ ] 7.4 Update HANDOFF.md with the checkpoint, evidence, limitations and the next task
