## ADDED Requirements

### Requirement: Single gate command
The project SHALL provide one gate command, `uv run --locked python scripts/gate.py`, that
behaves the same in Git Bash, Windows PowerShell and Linux. It SHALL run every check even after
one fails, print each check's outcome and a summary, and exit non-zero if any check failed.

#### Scenario: All checks pass
- **WHEN** every check passes
- **THEN** the gate prints a passing summary that lists each check and exits 0

#### Scenario: One check fails
- **WHEN** one check fails, for example on a deliberately misformatted file
- **THEN** the gate still runs the remaining checks, names the failed check in its summary, and exits non-zero

### Requirement: Checks the gate runs
The gate SHALL run, in order: `uv lock --check`; `ruff format --check`; `ruff check`; `mypy` in
strict mode over `src`, `tests` and `scripts`; `pytest` with a branch-coverage report of `src`
and no coverage minimum; `openspec validate --all --strict --no-interactive` through the
repo-local CLI; and a Conventional Commits check of the commits on the branch.

#### Scenario: Type error fails the gate
- **WHEN** code under `src` assigns a value of the wrong type for its annotation
- **THEN** the mypy check fails and the gate exits non-zero

#### Scenario: Invalid OpenSpec artifact fails the gate
- **WHEN** an OpenSpec change has a requirement without a scenario
- **THEN** the OpenSpec check fails and the gate exits non-zero

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
