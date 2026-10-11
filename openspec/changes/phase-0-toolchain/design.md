## Context

Phase 0 of PROJECT.md §6. The repo holds only process documents and skills. The owner's PC is
Windows 11 with Git Bash and Windows PowerShell 5.1. Bare `python` is a conda env (3.10.20) in
Git Bash and Anaconda base (3.9) in PowerShell. The conda env also puts its own `ruff`, `mypy`
and `pre-commit` first on PATH. `py` lists 3.10–3.13. uv, make and just are not installed.
Node 22.19.0 and a global OpenSpec 1.6.0 are. `core.autocrlf=true`, and the tree mixes CRLF and
LF working copies. The remote is a private GitHub repo.

Decisions came from the Phase 0 grilling on 2026-10-11. An informed-answerer subagent researched
each question, and the main agent re-checked the sources. The owner answered every owner call
with the recommended option.

## Goals / Non-Goals

**Goals:**
- From a fresh clone, `uv sync --locked` and `npm ci` followed by one gate command give a green
  result on Windows and on Linux CI.
- The gate exercises every check Phases 1–7 will rely on, and smoke tests prove the decided
  stack works together.

**Non-Goals:** as listed in the proposal. There is no domain code, schema, Vast.ai access,
Streamlit page, coverage threshold, licence, pre-commit hook, secret scanner, branch protection
or OpenSpec upgrade.

## Decisions

Each decision records who made it. Owner calls are marked **owner**. Settled answers carry
their basis.

| # | Decision | Who / basis |
|---|---|---|
| D1 | Phase 0 goal, non-goals and acceptance as in the proposal. Acceptance evidence: gate output from a fresh clone, the gate shown failing once on a deliberate defect, CI green, every `TBD in Phase 0` replaced, and the stale Python facts corrected | **owner** (Scope) |
| D2 | Timebox about 2 hours: setup outside the seven brief sessions, logged against the 20–25 h total | **owner** (Scope, Private knowledge, Value trade-off) |
| D3 | Install uv with `winget install --id=astral-sh.uv -e`, then `uv python install 3.13` (3.13.16) so local and CI share a patch line | **owner** (Authority) |
| D4 | Hosted CI on GitHub Actions for PRs and pushes to main. The owner confirmed that free included minutes are within the spend ⛔ gate and that overage cannot bill | **owner** (Gate, Private knowledge) |
| D5 | Distribution `compute-cost-risk-monitor`, import package `compute_cost_risk_monitor` | **owner** (Showcase, One-way door) |
| D6 | Dependabot alerts and security updates on; version-update PRs off | **owner** (Authority) |
| D7 | Streamlit boot check via `AppTest.from_function` inside pytest. No app file or `streamlit run` | default. Source: Streamlit docs (Context7 /streamlit/docs) |
| D8 | Python 3.13: `.python-version` and `requires-python >=3.13` | fact + default. Sources: endoflife.date (3.10 EOL 2026-10-01; 3.13 to 2029-10); PyPI (pandas 3.0.6 needs ≥3.11, numpy 2.5.4 ≥3.12, duckdb 1.5.6 lacks cp315). 3.13 over 3.14 because it is installed |
| D9 | uv with a committed universal `uv.lock`; `uv lock --check` in the gate; commands as `uv run --locked` | default. Source: uv docs (Context7 /websites/astral_sh_uv) |
| D10 | Ruff format and lint, rules `E,W,F,I,UP,B,SIM,DTZ,S`, `S101` allowed in tests | default. Source: Ruff docs. DTZ supports PROJECT §3 UTC times |
| D11 | mypy `strict = true`; pandas-stubs pinned to the pandas minor | default. Source: pandas-stubs PyPI page (tested with mypy). Relax per module if pandas typing costs more than it saves |
| D12 | pytest 9 native `[tool.pytest]` with `strict = true`; branch coverage reported, no minimum until Phase 6 | default. Source: pytest docs (`[tool.pytest]` since 9.0; `strict`) |
| D13 | OpenSpec CLI pinned at 1.6.0 via `package.json` and `package-lock.json`; `npm ci` bootstrap | default. Source: npm registry (latest 1.14.1; global 1.6.0 matches the skills' `generatedBy`) |
| D14 | Gate: `uv run --locked python scripts/gate.py`. It runs every step, prints a summary and exits non-zero on any failure. Tools are never called by bare name | default. Make and just are absent, and conda tools shadow PATH in Git Bash |
| D15 | Commit check: `cz check --rev-range origin/main..HEAD` (commitizen), skipped with a notice on an empty range | default. Source: commitizen source (default `allowed_prefixes` include Merge/Revert; `NoCommitsFoundError` on an empty range) |
| D16 | CI: one `ubuntu-latest` job, `contents: read`, 10-minute timeout, per-ref cancel-in-progress, SHA-pinned actions, gate then `uv audit --locked` | default. Source: build-safety `orchestrate_ci_cd.md` step 1 |
| D17 | `uv audit --locked` runs in CI and before marking a PR ready, not in the offline local gate | default. Source: uv CLI reference (`uv audit`, needs network) |
| D18 | No secret scanner in Phase 0. Add one in Phase 2 (first credential) and recheck before going public | recorded. Source: SECURITY_BASELINE B01 and its absence rule |
| D19 | No branch protection or required checks | recorded. Source: WORKFLOW.md (review and owner go-ahead before every merge) |
| D20 | src layout; `tests/smoke` now, `tests/unit` and `tests/fixtures` later; `.gitattributes` forces LF for code and config only; `.editorconfig`; no `.env.example` until Phase 2 | default |
| D21 | Leave `.agents/` line endings alone. The skill source-manifest digests verify only on CRLF checkouts, and HANDOFF notes it | default. Checked: one file's working-copy digest matches the manifest, but its committed bytes do not |
| D22 | Replace the stale "Python 3.10 is installed" lines and every `TBD in Phase 0` gate line | fact |
| D23 | Later phases: pytest-socket network blocking in Phase 2; Streamlit `gatherUsageStats = false` in Phase 4 | default, recorded for those phases |

**Alternatives considered:**
- pip-tools: rejected because it needs per-platform compiled files and manual interpreter choice.
- Poetry: rejected because it does not manage interpreters.
- conda: rejected because it has no hashed cross-platform lock without conda-lock.
- pyright: rejected because its PyPI wrapper downloads Node at run time.
- ty: rejected because it is in beta.
- commitlint: rejected because it adds a second toolchain for commit checks.
- A global OpenSpec install: rejected because it can't be reproduced from a clone.
- make or just: rejected because neither is installed and neither is native to Windows.

**Dependency bounds:** `pyproject.toml` sets lower bounds at the current minor version
(pandas, DuckDB, Streamlit). The lockfile fixes exact versions. pandas-stubs follows pandas
`3.0.*`.

## Risks / Trade-offs

- [Strict mypy fights pandas typing] → per-module overrides; D11 is reopenable.
- [Streamlit caps pyarrow below 26] → uv resolves within Streamlit's bounds; the lockfile
  records the result.
- [The commit check needs `origin/main` locally] → the gate reports a clear failure when the
  ref is missing; CI checks out with `fetch-depth: 0`.
- [CI minutes] → runs are bounded by a timeout and cancel-in-progress. Usage stays within the
  free quota under D4; public repos (Phase 7) run free.
- [Dependabot cannot read `uv.lock`] → the audit in CI covers Python advisories; this is
  checked during implementation and recorded.
- [AppTest on Windows] → it runs in-process. If it fails on Windows, the failure is recorded,
  not hidden.

## Migration Plan

Phase 0 adds new files and only edits documentation lines. To roll back, revert the Phase 0
merge commit. uv on the owner's PC is removed with `winget uninstall astral-sh.uv`. Dependabot
settings are switched off in the repo settings.

## Open Questions

None. Every grilling question is owner-answered or settled above.
