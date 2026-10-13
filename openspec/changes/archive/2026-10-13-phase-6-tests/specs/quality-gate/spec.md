## MODIFIED Requirements

### Requirement: Checks the gate runs
The gate SHALL run these checks, in order:
1. `uv lock --check`
2. `ruff format --check`
3. `ruff check`
4. `mypy` in strict mode over `src`, `tests` and `scripts`
5. `pytest` with a branch-coverage report of `src` that fails when total branch coverage,
   rounded to one decimal, is below 99.0%. Only `if __name__ == "__main__":` blocks are
   excluded from measurement.
6. a coverage report over the same data, limited to the core calculation and data modules, that
   fails unless they are at 100%. The core modules are `azure_retail`, `normalize`, `checks`,
   `gpu_map`, `rules`, `groups`, `history`, `quality`, `calculator`, `scenarios` and
   `workload_check`.
7. `openspec validate --all --strict --no-interactive` through the repo-local CLI, with its
   telemetry turned off
8. a detect-secrets scan of the tracked files, and of new files Git does not ignore, against
   the committed `.secrets.baseline`, with network verification turned off
9. a Conventional Commits check of the commits on the branch

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

#### Scenario: Total coverage below the minimum fails the gate
- **WHEN** the test run's total branch coverage rounds to less than 99.0%
- **THEN** the tests check fails, the remaining checks still run, and the gate exits non-zero

#### Scenario: Core module below 100% fails the gate
- **WHEN** a line or branch in one of the core modules is not run by the tests
- **THEN** the core-module coverage check fails and names the module, and the gate exits non-zero

### Requirement: Tests run without network access
pytest SHALL run with sockets disabled through pytest-socket, so a test that opens a network
socket fails. The only exceptions SHALL be the Streamlit headless smoke test and the dashboard
AppTest module (`tests/unit/test_app.py`). Each is marked to allow connections to 127.0.0.1 only,
because asyncio on Windows opens a loopback socket pair for its own use.

#### Scenario: Network call in a test fails
- **WHEN** a test without the marker tries to open a network connection
- **THEN** the test fails with pytest-socket's blocked-socket error

#### Scenario: Streamlit smoke test still runs on Windows
- **WHEN** the gate runs on Windows
- **THEN** the Streamlit headless smoke test passes

#### Scenario: Dashboard tests reach loopback only
- **WHEN** the dashboard AppTest module runs
- **THEN** its tests may connect to 127.0.0.1 and no other host
