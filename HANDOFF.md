# Current handoff

Read PROJECT.md and current user instructions. Inspect actual Git/OpenSpec state before resuming.

## Current checkpoint

Phase 0 (toolchain, lockfile, quality gate, smoke checks) is implemented on branch
`phase-0-toolchain`, OpenSpec change `phase-0-toolchain`, draft PR #3. All tasks pass. Code review,
archive and merge remain (WORKFLOW.md § Pull requests and code review, steps 3–5).
The branch also carries commit e8195fa from PR #2 (setup-kit update), which is not merged yet.
Merge #2 first, then #3; the second diff then shows only Phase 0.

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
- Gate: `uv run --locked python scripts/gate.py` after `uv sync --locked` and `npm ci`.
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
  seven checks passing.
- `uv audit --locked`: no known vulnerabilities in 63 packages. It is experimental in uv 0.13.
- Not verified: GitHub's dependency graph detecting `uv.lock` and `package-lock.json`, which
  needs the manifests on main. Check it after merge.

## Findings for later phases

- DuckDB returns TIMESTAMPTZ in the machine's time zone (America/Toronto here) unless the
  connection runs `SET TimeZone = 'UTC'`. Phase 1's schema and every connection must set it
  for UTC retrieval times (PROJECT.md §3).
- npm's Windows `.cmd` shims, including `npx`, break on the `&` in this folder name. Run Node
  CLIs as `node node_modules/<pkg>/<bin>.js`.
- The build-safety source-manifest digests match only CRLF working copies of `.agents/`. They
  fail on an LF checkout such as CI; `.gitattributes` leaves `.agents/` alone (design D21).
- Phase 2: add pytest-socket network blocking and a secret scanner. Phase 4: commit
  `.streamlit/config.toml` with `gatherUsageStats = false`.

## Next action

Phase 0 PR #3: run `/code-review` and check the diff against the specs, resolve the findings,
archive the change on the branch (`chore:`, phase Done), rerun validation and the gate, push and
mark ready. Merge #2 and then #3 only on the owner's go-ahead. Then begin Phase 1 with
next-phase grilling.
