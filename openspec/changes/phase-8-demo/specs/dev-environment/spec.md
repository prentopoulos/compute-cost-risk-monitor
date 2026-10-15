## MODIFIED Requirements

### Requirement: Locked Python dependencies
The project SHALL commit a uv lockfile that pins every runtime and dev dependency, including
transitive ones, with hashes for every platform uv supports. Runtime dependencies SHALL be
pandas, DuckDB, Streamlit, pytz, Altair and anthropic (the official Anthropic SDK, imported only
by the brief drafter). Dev dependencies SHALL be pytest, pytest-cov, pytest-socket, Hypothesis,
Ruff, mypy, pandas-stubs, types-pytz, commitizen and detect-secrets.

#### Scenario: Fresh environment from the lockfile
- **WHEN** a developer runs `uv sync --locked` in a fresh clone
- **THEN** uv creates `.venv` with exactly the locked versions and exits 0

#### Scenario: Stale lockfile rejected
- **WHEN** `pyproject.toml` changes a dependency without the lockfile being regenerated
- **THEN** `uv lock --check` exits non-zero

#### Scenario: Declared dependencies match the requirement
- **WHEN** `pyproject.toml` is read
- **THEN** its runtime dependencies are exactly pandas, DuckDB, Streamlit, pytz, Altair and anthropic, and its dev group is exactly the dev dependencies listed above

#### Scenario: Property tests run the same everywhere
- **WHEN** the gate runs locally and in CI, where the `CI` environment variable is set
- **THEN** Hypothesis uses the same fixed profile in both, with derandomized examples and no example database, so it writes no tracked file

#### Scenario: SDK only in the drafter
- **WHEN** the package's modules are searched for imports of `anthropic`
- **THEN** only `drafter.py` imports it
