## Why

PROJECT.md Phase 0: toolchain, lockfile, quality gate, smoke checks. Phases 1–7 need one
reproducible Python environment and one command that says whether the repo is healthy. Today
there is no `pyproject.toml`, no lockfile, no tests, and the gate is `TBD in Phase 0`. Bare
`python` also differs by shell on the owner's PC: a conda 3.10 env in Git Bash, Anaconda 3.9 in
PowerShell. Python 3.10 reached end of life on 2026-10-01, and pandas 3 needs 3.11 or newer.

## What Changes

- Pin Python 3.13 and manage the environment with uv and a committed, hashed `uv.lock`.
  Runtime dependencies are pandas, DuckDB and Streamlit. Dev dependencies are pytest,
  pytest-cov, Ruff, mypy, pandas-stubs and commitizen.
- Pin the OpenSpec CLI at 1.6.0 through `package.json` and `package-lock.json`.
- Add an empty, typed `compute_cost_risk_monitor` package in a src layout, `tests/smoke`, and
  line-ending and editor settings for code and config.
- Add a single cross-platform gate, `uv run --frozen python scripts/gate.py`. It runs the
  lockfile check, format check, lint, strict type check, pytest with branch coverage (no
  minimum), OpenSpec strict validation and a Conventional Commits check of the branch.
- Add smoke tests: imports, a pandas → in-memory DuckDB → pandas round trip that checks values
  and column types, and a headless Streamlit `AppTest` run.
- Add a GitHub Actions workflow that runs the gate and `uv audit` on pull requests and pushes
  to main, with a read-only token, a 10-minute timeout and SHA-pinned actions.
- Turn on Dependabot alerts and security updates (owner-approved), with no version-update PRs.
- Replace every `TBD in Phase 0` gate line, and correct the stale "Python 3.10 is installed" facts.

## Non-goals

- No domain code, data schema or acceptance criteria (Phase 1).
- No Figma architecture diagrams (Phase 1).
- No Vast.ai calls, API key, `.env` or `.env.example` (Phase 2, behind the live-data ⛔ gate).
- No Streamlit pages, app file or `streamlit run` (Phase 4).
- No coverage threshold (Phase 6), licence choice or publishing (Phase 7).
- No pre-commit hooks, secret scanner, branch protection, Dependabot version updates or
  OpenSpec CLI upgrade.

## Capabilities

### New Capabilities

- `dev-environment`: reproducible Python and Node tooling: interpreter pin, lockfiles,
  bootstrap commands, package layout and line-ending rules.
- `quality-gate`: the single local gate command, the checks it runs, how it reports, and the
  smoke tests it executes.
- `hosted-ci`: the GitHub Actions workflow that runs the gate and the dependency audit, and its
  spend and permission bounds.

### Modified Capabilities

None. `openspec/specs/` is empty.

## Impact

- New files: `pyproject.toml`, `uv.lock`, `.python-version`, `package.json`,
  `package-lock.json`, `scripts/gate.py`, `src/compute_cost_risk_monitor/`, `tests/smoke/`,
  `.gitattributes`, `.editorconfig`, `.github/workflows/ci.yml`.
- Edited: `.gitignore`, PROJECT.md §4 and §6, AGENTS.md, CLAUDE.md, WORKFLOW.md, next-phase
  SKILL.md §4, HANDOFF.md.
- Owner's machine: uv installed with winget and Python 3.13.16 installed by uv (owner-approved
  2026-10-11).
- GitHub: Actions minutes from the free included quota (owner decision under the spend ⛔
  gate, 2026-10-11). Dependabot alerts and security updates are repository settings.
- ⛔ gates touched: spend (CI minutes only, within the recorded decision). Live data, scheduled
  collection and publishing are not touched.
