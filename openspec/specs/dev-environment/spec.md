# dev-environment Specification

## Purpose
Reproducible Python and Node tooling for every phase: the pinned interpreter, locked
dependencies, the pinned OpenSpec CLI, package layout and line-ending rules.
## Requirements
### Requirement: Pinned Python interpreter
The project SHALL pin Python 3.13 in `.python-version` and declare `requires-python = ">=3.13"`
in `pyproject.toml`. Project commands SHALL run Python through uv, never through a bare
`python` or tool name taken from PATH.

#### Scenario: Interpreter resolved from the pin
- **WHEN** a developer runs `uv run --locked python -c "import sys; print(sys.version_info[:2])"`
- **THEN** it prints `(3, 13)` regardless of which Python an active conda or system environment provides

### Requirement: Locked Python dependencies
The project SHALL commit a uv lockfile that pins every runtime and dev dependency, including
transitive ones, with hashes for every platform uv supports. Runtime dependencies SHALL be
pandas, DuckDB, Streamlit, pytz and Altair. Dev dependencies SHALL be pytest, pytest-cov,
pytest-socket, Hypothesis, Ruff, mypy, pandas-stubs, types-pytz, commitizen and detect-secrets.

#### Scenario: Fresh environment from the lockfile
- **WHEN** a developer runs `uv sync --locked` in a fresh clone
- **THEN** uv creates `.venv` with exactly the locked versions and exits 0

#### Scenario: Stale lockfile rejected
- **WHEN** `pyproject.toml` changes a dependency without the lockfile being regenerated
- **THEN** `uv lock --check` exits non-zero

#### Scenario: Declared dependencies match the requirement
- **WHEN** `pyproject.toml` is read
- **THEN** its runtime dependencies are exactly pandas, DuckDB, Streamlit, pytz and Altair, and its dev group is exactly the dev dependencies listed above

#### Scenario: Property tests run the same everywhere
- **WHEN** the gate runs locally and in CI, where the `CI` environment variable is set
- **THEN** Hypothesis uses the same fixed profile in both, with derandomized examples and no example database, so it writes no tracked file

### Requirement: Locked OpenSpec CLI
The project SHALL pin the OpenSpec CLI (`@fission-ai/openspec`) at exactly 1.6.0 in
`package.json`, with a committed `package-lock.json`. The gate SHALL run the repo-local CLI
through `node` and the package's own entry point, not a global install or an npm shell shim.
npm's Windows `.cmd` shims break on the `&` in this repo's folder name.

#### Scenario: Repo-local CLI after bootstrap
- **WHEN** a developer runs `npm ci` and then `node node_modules/@fission-ai/openspec/bin/openspec.js --version`
- **THEN** it prints `1.6.0`

### Requirement: Package layout
The project SHALL provide an importable, typed package `compute_cost_risk_monitor` under
`src/` (distribution name `compute-cost-risk-monitor`) with a `py.typed` marker. Tests SHALL
live under `tests/`, with smoke tests in `tests/smoke/`.

#### Scenario: Package imports from the environment
- **WHEN** the smoke tests run in the synced environment
- **THEN** `import compute_cost_risk_monitor` resolves to the package under `src/` installed in `.venv`

### Requirement: Line endings for code and config
The project SHALL store Python, TOML, YAML, JSON and lockfile content with LF line endings,
through `.gitattributes`, and SHALL leave existing Markdown and `.agents/` files unchanged.

#### Scenario: LF checkout on Windows
- **WHEN** the repo is cloned on Windows with `core.autocrlf=true`
- **THEN** `git ls-files --eol` reports `w/lf` for `pyproject.toml`, `uv.lock` and every `*.py` file

### Requirement: Generated files stay untracked
The project SHALL ignore virtual environments, caches, coverage output, `node_modules/` and
`.env` variants other than `.env.example`.

#### Scenario: Clean tree after running the gate
- **WHEN** a developer bootstraps and runs the gate in a clean clone
- **THEN** `git status --porcelain` prints nothing

