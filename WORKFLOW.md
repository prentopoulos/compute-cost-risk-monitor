# Phase workflow

Read PROJECT.md for current scope and [.agents/skills/next-phase/SKILL.md](.agents/skills/next-phase/SKILL.md)
for the task router. HANDOFF.md records current recovery context; OpenSpec owns task status.

## Delivery

Remote: https://github.com/prentopoulos/compute-cost-risk-monitor (private). Push phase
branches and open PRs at the points below; nothing goes straight to main, and a PR merges
only after its review and the user's go-ahead.
Use Conventional Commits: docs for planning, feat/fix/refactor for implementation, chore for
setup/archive. Preserve spec-first history, task commits and archive-before-merge with a
merge commit (GitHub "Create a merge commit", the equivalent of `git merge --no-ff`; never
squash or rebase-merge). Preserve unrelated work; do not reset or stash it automatically.
Commits and PR bodies carry no Claude session links; `.claude/settings.json` turns them off.

## Pull requests and code review

One phase is one branch and one PR into main. Main took one direct commit, the setup.

Every PR body opens with a **TL;DR**: two to four plain sentences a non-engineer can follow,
naming things by what they do. It says what changed, why, and what the owner needs to do (often
nothing, or approve the merge); if the PR changes what the app shows, it says how. Keep it
current as the PR changes, with the technical detail below it.

1. Spec ready: after the spec-only `docs:` commit, push the branch and open a **draft** PR
   titled `Phase N: <deliverable>`. The body links the OpenSpec change, lists the ⛔ gates the
   phase touches and holds a checklist of its tasks. The user reviews the proposal there.
2. Building: push task commits as they land. The PR stays draft while tasks remain open.
3. Code review: when every task passes and the local gate is green, review the PR before
   marking it ready. Run `/code-review` on the PR for correctness and check the diff against
   the change's requirements and tasks and the design's non-negotiables check. Add compute-cost-risk-monitor-market-review when the PR
   changes prices, costs, exposure or the brief. Fix findings in new commits or answer them
   on the PR, and record the outcome in the PR body.
4. Ready: archive on the branch (`chore:`), rerun validation and the gate, push, mark ready.
5. Merge: only on the user's go-ahead, with a merge commit. Then pull main, confirm the merge
   landed, and delete the branch locally and on GitHub. The phase is now at its clean
   checkpoint (below).

Docs- or process-only PRs get a read-through instead of a code review. `/code-review ultra`
is billed and user-triggered: suggest it for high-stakes PRs, never launch it.

## Fresh session per phase

Each phase starts in a fresh agent session. A conversation left over from the last phase
crowds the context and lets stale details leak into new decisions (context rot), so nothing
the next phase needs may live only in the chat.

- **Before the PR is marked ready:** move what the conversation decided or learned into the
  repo: decisions to PROJECT.md and the design, findings and the next action to HANDOFF.md.
  Word the next action so it is still true after the merge.
- **Clean checkpoint:** the phase PR and any process PR opened alongside it are merged,
  their branches are deleted locally and on GitHub, main is pulled and the tree is clean.
  Stop there and tell the owner the context can be cleared. Don't start the next phase's
  grilling in the same session unless the owner asks.
- **Next phase:** the owner clears the context (`/clear` in Claude Code) and runs
  `/next-phase`, which rebuilds the picture from PROJECT.md, HANDOFF.md, OpenSpec and Git.
- **Mid-phase:** if a session must end before its phase does, first commit and push a HANDOFF
  update naming the branch, the finished and open tasks and the next step.

## Phase loop

1. Inspect actual branch/tree and active OpenSpec status. Resume an existing authorized
   phase on its branch. Select a bounded task slice; planning readiness is not implementation.
2. Read affected artifacts and PROJECT gates. Explore unresolved feasibility before relying
   on it. Use compute-cost-risk-monitor-build-safety for relevant engineering boundaries and
   compute-cost-risk-monitor-market-review for prices, costs, exposure and the brief.
3. For new phases grill the user on open decisions (see next-phase), then propose a scoped
   change, branch and create a spec-only docs commit, then push and open the draft PR.
   Make the result reviewable. Honor requested review pauses and unresolved material choices;
   an already authorized slice needs no repeated approval for reversible refinements.
4. Implement via the apply workflow, committing tasks or logical groups. Set the phase to
   In progress with its first implementation. Keep future tasks open.
5. Verify the selected scope. Mark only evidenced tasks complete. A completed milestone
   inside an unfinished phase does not authorize archival or marking the whole phase Done.
6. When all requirements/tasks pass, archive on the same branch, sync main specs, update
   phase Done in the archive commit, rerun validation and the local gate, then finish the PR
   (code review, ready, merge on the user's go-ahead) as above.
   Delete only a verified merged branch. No force deletion to finish a checklist.
7. Update HANDOFF with scope, checks, limitations and the next task; begin a genuinely new
   phase in a fresh session from the clean checkpoint (§ Fresh session per phase).

## Prerequisites and authority

Technical checks can be established by evidence. Product decisions reuse accepted scope.
PROJECT's explicit `⛔` gates are operator-resolved: surface and stop the dependent action;
never satisfy or waive them yourself. PROJECT.md §5–6 are the constitution: they override the
other project documents, and only the owner amends them (PROJECT.md § Amending the constitution). Unresolved live access/budget does not block local work.
Skills grant no spending, outreach, deployment or real-data transfer authority.

## Verification by scope

- Planning/skills: frontmatter where relevant, local links, source digests for carryover,
  consistency, strict OpenSpec validation, whitespace and candidate-file inspection.
- Runtime: `uv run --frozen python scripts/gate.py`. It runs the lockfile check, Ruff format and lint, strict mypy,
  pytest with coverage, `openspec validate --all --strict` and the commit-message check. Run
  `uv audit --locked --preview-features audit-command` before marking a code PR ready (CI also runs it). Add meaningful affected
  boundary tests.
- Results and model behavior: independent checks of outputs, cases fixed before measuring,
  honest run records. No fabricated remote results.
- UI: actual local-flow verification using synthetic scenarios.

Local checks are not hosted CI, live-service access or production evidence. Record failures
and untested boundaries. Reuse still-valid scoped evidence rather than repeatedly running checks.

The initial skill setup was committed on main. Later process-document changes go through a
small PR like any other. Product phases use their spec-first branch. Skills installation is
setup, not completion of application tasks.
