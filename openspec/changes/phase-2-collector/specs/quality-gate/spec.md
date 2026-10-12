## MODIFIED Requirements

### Requirement: Checks the gate runs
The gate SHALL run these checks, in order:
1. `uv lock --check`
2. `ruff format --check`
3. `ruff check`
4. `mypy` in strict mode over `src`, `tests` and `scripts`
5. `pytest` with a branch-coverage report of `src` and no coverage minimum
6. `openspec validate --all --strict --no-interactive` through the repo-local CLI, with its
   telemetry turned off
7. a detect-secrets scan of the tracked files against the committed `.secrets.baseline`, with
   network verification turned off
8. a Conventional Commits check of the commits on the branch

The gate makes no network calls.

#### Scenario: Type error fails the gate
- **WHEN** code under `src` assigns a value of the wrong type for its annotation
- **THEN** the mypy check fails and the gate exits non-zero

#### Scenario: Invalid OpenSpec artifact fails the gate
- **WHEN** an OpenSpec change has a requirement without a scenario
- **THEN** the OpenSpec check fails and the gate exits non-zero

#### Scenario: Planted secret fails the gate
- **WHEN** a tracked file gains a string that detect-secrets reports and the baseline does not list
- **THEN** the secret scan fails and the gate exits non-zero

## ADDED Requirements

### Requirement: Tests run without network access
pytest SHALL run with sockets disabled through pytest-socket, so a test that opens a network
socket fails. The only exception SHALL be the Streamlit headless smoke test, which is marked to
allow sockets because asyncio on Windows opens a loopback socket pair for its own use.

#### Scenario: Network call in a test fails
- **WHEN** a test without the marker tries to open a network connection
- **THEN** the test fails with pytest-socket's blocked-socket error

#### Scenario: Streamlit smoke test still runs on Windows
- **WHEN** the gate runs on Windows
- **THEN** the Streamlit headless smoke test passes
