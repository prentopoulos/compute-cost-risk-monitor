# Current handoff

Read PROJECT.md and current user instructions. Inspect actual Git/OpenSpec state before resuming.

## Current checkpoint

Phase 0 (toolchain, lockfile, quality gate, smoke checks) is Done on branch
`phase-0-toolchain`, PR #3. All tasks pass, the code review is resolved, and the change is
archived as `openspec/changes/archive/2026-10-12-phase-0-toolchain`. Its specs now live in
`openspec/specs/` (dev-environment, quality-gate, hosted-ci). PR #3 is ready and waits only for
the owner's go-ahead to merge. PR #2 (setup-kit update) was merged on 2026-10-11 and its branch
deleted.

No Vast.ai data has been fetched and no Figma diagram exists; both start in later phases.

On 2026-10-11 the setup was compared with the updated kit (new_project_agent_setup_updated).
Its verbatim Agent Builder and grilling files are unchanged. Adopted: the runtime-secret wording,
recording operator gate decisions with scope and date, and `.env.*` ignore rules. AI-ops is
deferred: PROJECT.md §2 says to install it before the optional brief drafter is proposed. The
kit itself received this project's process improvements (informed answerer, PR TL;DRs and code
review, no session links, Figma diagrams); see its README "Process updates from projects".

## Implemented behavior

- Python 3.13.16 (uv-managed) with `uv.lock`: pandas 3.0.6, DuckDB 1.5.6, Streamlit 1.65.0;
  dev tools pytest 9.1.1, pytest-cov, Ruff 0.17.0, mypy 2.4.0 (strict), pandas-stubs and
  commitizen. OpenSpec CLI 1.6.0 pinned through `package.json` and `package-lock.json`.
- Empty typed package `src/compute_cost_risk_monitor`; smoke tests in `tests/smoke`.
- Gate: `uv run --frozen python scripts/gate.py` after `uv sync --locked` and
  `npm ci --ignore-scripts`. `--frozen` lets a stale `uv.lock` show up as a failed check.
- CI: `.github/workflows/ci.yml` runs the gate and `uv audit` on PRs and pushes to main.
- Dependabot alerts and security updates are on; version updates are off.
- uv 0.13.0 is installed on the owner's PC with winget. Its folder is on the user PATH, so it
  is reachable from shells started after the install.

## Verification

- Gate green on 2026-10-11 in Git Bash and in Windows PowerShell: all seven checks pass, with
  7 smoke tests passing.
- The gate failed as designed on four deliberate defects, each reverted: a misformatted file,
  a type error, an OpenSpec requirement without a scenario, and a commit titled "updated stuff".
  It reported format, types, openspec and commit messages as failed, and still ran every check.
- CI run 38186096043 on PR #3 succeeded in 47 s on ubuntu-latest, with Python 3.13.16 and all
  seven checks passing. After the review fixes, run 38186510955 succeeded in 37 s.
- Fresh clone of the branch from GitHub: `uv sync --locked`, `npm ci` and the gate all
  passed, code files checked out as LF, and `git status` was clean afterwards. Windows long
  paths are off on this PC, so a clone into a deep folder needs `git clone -c core.longpaths=true`.
- The gate reported a stale `uv.lock` as its only failed check and still ran every other check.
  With no commits ahead of `origin/main`, the commit check is skipped and the gate passes.
  `datetime.now()` without a time zone fails lint (DTZ005).
- Code review (`/code-review` on PR #3) found 10 issues. Fixed: the `--frozen` gate
  command, OpenSpec telemetry off, `npm ci --ignore-scripts`, main runs never cancelled, the
  exact audit command, `.editorconfig` scope, a stronger install smoke test and a repeated
  failure path. Answered rather than fixed: `.agents/` digests (pre-existing; see below) and
  the gate using the local `origin/main` without fetching (it prints which commit it used).
- `uv audit --locked --preview-features audit-command`: no known vulnerabilities in 63
  packages. It is experimental in uv 0.13.
- Not verified: GitHub's dependency graph detecting `uv.lock` and `package-lock.json`, which
  needs the manifests on main. Check it after merge.

## Findings for later phases

- DuckDB returns TIMESTAMPTZ in the machine's time zone (America/Toronto here) unless the
  connection runs `SET TimeZone = 'UTC'`. Phase 1's schema and every connection must set it
  for UTC retrieval times (PROJECT.md §3).
- npm's Windows `.cmd` shims, including `npx`, break on the `&` in this folder name. Run Node
  CLIs as `node node_modules/<pkg>/<bin>.js`.
- The build-safety source-manifest digests match only CRLF working copies of `.agents/`. They
  fail on an LF checkout such as CI; `.gitattributes` leaves `.agents/` alone (design D21). The
  fix is a small process PR: rehash the manifest from the LF bytes Git stores, or mark
  `.agents/** -text`.
- The globally installed OpenSpec CLI sends PostHog usage data unless `OPENSPEC_TELEMETRY=0`
  is set. The gate sets it; the owner may also set it user-wide.
- Phase 2: add pytest-socket network blocking and a secret scanner. Phase 4: commit
  `.streamlit/config.toml` with `gatherUsageStats = false`.

## Next action

On the owner's go-ahead, merge PR #3 with a merge commit. Then pull main, confirm the merge,
and delete `phase-0-toolchain` locally and on GitHub. Check that GitHub's dependency graph
detects `uv.lock` and `package-lock.json`. Then begin Phase 1 (requirements, data schema,
acceptance criteria, Figma diagrams) with next-phase grilling.
