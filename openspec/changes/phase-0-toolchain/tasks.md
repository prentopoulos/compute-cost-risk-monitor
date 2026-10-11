## 1. Machine prerequisites (owner-approved, D3)

- [x] 1.1 Install uv with `winget install --id=astral-sh.uv -e` and confirm `uv --version` in Git Bash and PowerShell
- [x] 1.2 Run `uv python install 3.13` and confirm uv resolves 3.13.16

## 2. Environment and layout

- [x] 2.1 Add `.python-version` (3.13), `pyproject.toml` (name, `requires-python`, runtime and dev dependencies, uv_build build backend, Ruff, mypy and pytest config) and the `src/compute_cost_risk_monitor` package with `__init__.py` and `py.typed`
- [x] 2.2 Generate and commit `uv.lock`; confirm `uv sync --locked` and `uv lock --check` exit 0
- [x] 2.3 Add `package.json` (private, exact `@fission-ai/openspec` 1.6.0) and `package-lock.json`; confirm `npm ci` and `node node_modules/@fission-ai/openspec/bin/openspec.js --version` print 1.6.0 (npx shims fail on the `&` in the folder name)
- [x] 2.4 Add `.gitattributes` (LF for code, config and lockfiles only), `.editorconfig`, and the `.gitignore` entries for venv, caches, coverage and `node_modules/`; confirm `git ls-files --eol` and a clean `git status` after the gate

## 3. Smoke tests

- [ ] 3.1 Add import smoke tests for pandas, DuckDB, Streamlit and `compute_cost_risk_monitor`
- [ ] 3.2 Add the pandas → in-memory DuckDB → pandas round trip, asserting values and dtypes for integer, float, string and UTC timestamp columns
- [ ] 3.3 Add the headless Streamlit `AppTest.from_function` smoke test

## 4. Gate

- [ ] 4.1 Add `scripts/gate.py`: runs lock check, format check, lint, strict mypy, pytest with branch coverage, OpenSpec strict validation and the commit check; runs every step, prints a summary, and exits non-zero on any failure; skips the commit check with a notice on an empty range
- [ ] 4.2 Run the gate green in Git Bash and in PowerShell, and record the output
- [ ] 4.3 Show the gate failing on a deliberate defect (a misformatted file, a type error and a non-conventional commit message, each reverted) and record the output

## 5. Hosted CI and repository settings

- [ ] 5.1 Add `.github/workflows/ci.yml` per D16 (ubuntu-latest, `contents: read`, 10-minute timeout, cancel-in-progress, SHA-pinned actions, `fetch-depth: 0`, `uv sync --locked`, `npm ci`, gate, `uv audit --locked`)
- [ ] 5.2 Push and confirm the CI run on the Phase 0 PR is green; record the run URL and duration
- [ ] 5.3 Turn on Dependabot alerts and security updates (D6) and record which manifests GitHub's dependency graph detects

## 6. Documents

- [ ] 6.1 Replace every `TBD in Phase 0` gate line (PROJECT.md §4, AGENTS.md, CLAUDE.md, WORKFLOW.md, next-phase SKILL.md §4) with the gate command and bootstrap commands
- [ ] 6.2 Replace "Python 3.10 is installed" and the TBD environment line in AGENTS.md with the 3.13 pin, the bootstrap commands and "run Python only through uv" (PROJECT.md §4 was updated in the spec commit)
- [ ] 6.3 Update HANDOFF with the checkpoint, the gate evidence, the CRLF-only skill digest note (D21) and the next task
