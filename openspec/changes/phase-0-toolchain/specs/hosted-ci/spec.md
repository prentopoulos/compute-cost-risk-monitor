## ADDED Requirements

### Requirement: CI runs the gate
A GitHub Actions workflow SHALL run on pull requests and on pushes to `main`. It SHALL
bootstrap with `uv sync --locked` and `npm ci --ignore-scripts` (no package install
scripts), run the same gate command as local development, and fail when the gate fails.

#### Scenario: Pull request with a failing check
- **WHEN** a pull request contains a lint error
- **THEN** the CI run fails on the gate step

#### Scenario: Commit check sees the branch history
- **WHEN** CI checks out a pull request
- **THEN** it fetches full history so that `origin/main..HEAD` resolves

### Requirement: Dependency audit in CI
The CI workflow SHALL run `uv audit --locked` after the gate. A known vulnerability SHALL fail
the run unless it is ignored by ID with the reason recorded in the PR. The offline local gate
SHALL NOT require this network check.

#### Scenario: Audit runs after a green gate
- **WHEN** the gate passes in CI
- **THEN** the workflow runs `uv audit --locked` and reports its result as a separate step

### Requirement: CI bounds
The workflow SHALL run on `ubuntu-latest` with `permissions: contents: read`, a 10-minute job
timeout, a per-ref concurrency group that cancels superseded pull-request runs (runs for
pushes to `main` always complete), actions pinned by full
commit SHA, and no repository secrets. It SHALL use only GitHub's free included Actions
minutes, per the operator's 2026-10-11 decision under the spend ⛔ gate.

#### Scenario: Superseded run cancelled
- **WHEN** a new commit is pushed to a branch whose previous CI run is still in progress
- **THEN** the previous run is cancelled

#### Scenario: Read-only token
- **WHEN** the workflow runs
- **THEN** its `GITHUB_TOKEN` has read-only contents permission and no write scopes
