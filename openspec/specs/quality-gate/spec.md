# quality-gate Specification

## Purpose
One offline command that says whether the repo is healthy: the checks it runs, how it
reports them, and the smoke tests that prove the stack works together.
## Requirements
### Requirement: Single gate command
The project SHALL provide one gate command, `uv run --frozen python scripts/gate.py`, that
behaves the same in Git Bash, Windows PowerShell and Linux. It SHALL run every check even after
one fails, print each check's outcome and a summary, and exit non-zero if any check failed.

#### Scenario: All checks pass
- **WHEN** every check passes
- **THEN** the gate prints a passing summary that lists each check and exits 0

#### Scenario: Stale lockfile reported by the gate
- **WHEN** `pyproject.toml` changes a dependency without re-locking and the gate runs
- **THEN** the lockfile check fails, every other check still runs, and the summary names the lockfile check

#### Scenario: One check fails
- **WHEN** one check fails, for example on a deliberately misformatted file
- **THEN** the gate still runs the remaining checks, names the failed check in its summary, and exits non-zero

### Requirement: Checks the gate runs
The gate SHALL run these checks, in order:
1. `uv lock --check`
2. `ruff format --check`
3. `ruff check`
4. `mypy` in strict mode over `src`, `tests` and `scripts`
5. `pytest` with a branch-coverage report of `src` and no coverage minimum
6. `openspec validate --all --strict --no-interactive` through the repo-local CLI, with its
   telemetry turned off
7. a detect-secrets scan of the tracked files, and of new files Git does not ignore, against
   the committed `.secrets.baseline`, with network verification turned off
8. a Conventional Commits check of the commits on the branch

The gate makes no network calls.

#### Scenario: Type error fails the gate
- **WHEN** code under `src` assigns a value of the wrong type for its annotation
- **THEN** the mypy check fails and the gate exits non-zero

#### Scenario: Invalid OpenSpec artifact fails the gate
- **WHEN** an OpenSpec change has a requirement without a scenario
- **THEN** the OpenSpec check fails and the gate exits non-zero

#### Scenario: Planted secret fails the gate
- **WHEN** a tracked or new unignored file gains a string that detect-secrets reports and the baseline does not list
- **THEN** the secret scan fails and the gate exits non-zero

### Requirement: Commit message check
The gate SHALL check commits in `origin/main..HEAD` against Conventional Commits, accepting
merge and revert commits. When the range has no commits, the gate SHALL report the check as
skipped, with the reason, rather than failed.

#### Scenario: Non-conventional commit
- **WHEN** a branch contains a commit titled `updated stuff`
- **THEN** the commit check fails and names that commit

#### Scenario: No commits ahead of main
- **WHEN** the gate runs on a branch with no commits ahead of `origin/main`
- **THEN** the commit check is reported as skipped and does not fail the gate

### Requirement: Smoke tests
The test suite SHALL include smoke tests that need no network or credentials and prove that
pandas, DuckDB and Streamlit import; that a pandas DataFrame round-trips through an in-memory
DuckDB connection with its values and column types checked; and that a trivial Streamlit
script runs headlessly through `streamlit.testing.v1.AppTest` without an exception.

#### Scenario: DuckDB round trip keeps values and types
- **WHEN** a DataFrame with integer, float, string and UTC timestamp columns is queried through `duckdb.connect(":memory:")` and read back with `.df()`
- **THEN** the values are equal and each column's dtype matches the expected dtype asserted in the test

#### Scenario: Streamlit runs headlessly
- **WHEN** the smoke test runs a one-line Streamlit script through `AppTest.from_function`
- **THEN** the run completes with no exception, no server and no browser

### Requirement: Lint and type rules
Ruff SHALL enforce rule sets `E`, `W`, `F`, `I`, `UP`, `B`, `SIM`, `DTZ` and `S`, with `S101`
allowed under `tests/`. mypy SHALL run with `strict = true` and pandas-stubs pinned to the
pandas minor version.

#### Scenario: Naive datetime flagged
- **WHEN** code calls `datetime.now()` without a timezone
- **THEN** `ruff check` reports a `DTZ` violation

### Requirement: Tests run without network access
pytest SHALL run with sockets disabled through pytest-socket, so a test that opens a network
socket fails. The only exception SHALL be the Streamlit headless smoke test. It is marked to allow
connections to 127.0.0.1 only, because asyncio on Windows opens a loopback socket pair for its own
use.

#### Scenario: Network call in a test fails
- **WHEN** a test without the marker tries to open a network connection
- **THEN** the test fails with pytest-socket's blocked-socket error

#### Scenario: Streamlit smoke test still runs on Windows
- **WHEN** the gate runs on Windows
- **THEN** the Streamlit headless smoke test passes

