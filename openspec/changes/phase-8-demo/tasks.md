## 1. Records

- [x] 1.1 Record the grilling decisions (D1–D45), each with who made it:
  - **PROJECT.md:**
    - §1: Phase 8 is final and may span several sessions; the reframed futures sentence (D11);
    - §2: the drafter is in scope and hosting is not;
    - §4: the LLM line and the Phase 8 citation;
    - §6: the spend-gate decision (D17) and the Phase 8 row.
  - **Also:** the build-safety skill's drafter route, and HANDOFF

## 2. Demo data and setup

- [x] 2.1 Hand-work the two demo-history snapshots (2026-09-28 and 2026-10-05) and their known answers in the fixtures README (D7, D42). Then:
  - write the files;
  - write the known-answer test: changes, absences, quality counts and no Spot above pay-as-you-go (ADDED "Synthetic demo history").

  Existing demo tests stay green
- [x] 2.2 Add `demo.py` (D39, `demo-setup`), with tests:
  - a fresh build into a temporary repository layout;
  - a rebuild;
  - the refused collected database;
  - a failed step that leaves the old file;
  - `--serve` starting the app with an injected launcher.

## 3. Market brief

- [x] 3.1 Build the fact set in `brief.py` (`market-brief` "Brief fact set"; D32): IDs, values, units, group keys, record links and derived-from lists, as sorted JSON. Known-answer tests on the demo history; nulls with reasons
- [x] 3.2 Render the template brief and the bottom line ("Template brief", "Brief bottom line"; D8, D24, D27, D45), with known-answer tests:
  - the demo bottom line, word for word;
  - the changes and absences sections;
  - one snapshot only;
  - no pay-as-you-go listing;
  - the Records table covering every fact used.
- [x] 3.3 Write `brief_check.py`, which never imports `brief` ("Independent brief check"; D32). Tests:
  - the correct brief passes;
  - a tampered figure and an unknown number are named;
  - an import guard.

  Keep the core coverage list at 100%, adding `brief` and `brief_check`
- [x] 3.4 Add the brief command ("Brief command"; D29, D37). Tests:
  - pinned as-of bytes;
  - refusals: no snapshot, and collected prices aimed at `docs/`;
  - exit codes;
  - printed output with no price.

  Build the committed template brief in `docs/brief/` from the demo database as of 2026-10-12 09:00 UTC ("Committed synthetic brief")

## 4. AI drafter

- [x] 4.1 Add `anthropic` as a runtime dependency (MODIFIED `dev-environment`; D36):
  - update `pyproject.toml`, `uv.lock` and `tests/repo/test_dependencies.py`;
  - test that only `drafter.py` imports the SDK;
  - run `uv audit`;
  - check the SDK calls against the current docs (the claude-api skill; Context7).
- [x] 4.2 Write `drafter.py` (`brief-drafter`; D16, D18, D19, D28, D44, D45):
  - the request;
  - placeholders and fill;
  - the validator;
  - retry and fallback;
  - the run record;
  - the synthetic-only and missing-key refusals.

  Fake-client tests cover every rejection case, a second attempt accepted, two rejections falling back, and the request shape, with no key and no network
- [x] 4.3 Update AI_OPS.md: the inference and prompt capabilities become enabled once 4.2 passes, with their evidence locations filled in (D35)
- [x] 4.4 On the owner's go-ahead, with the key in the user environment and the USD 10 organisation limit set (D17), run `brief --draft` once on the demo database as of 2026-10-12 09:00 UTC, with at most one retry inside the command. Then:
  - commit the drafted brief, its fact set and run record when the check passes;
  - otherwise commit the template brief with the run record of the rejected attempts;
  - record the actual tokens and cost.

## 5. Dashboard labels

- [x] 5.1 Draw a quick Figma mock of the grid title with "NOT A FORECAST" and the "EXCL." tag line, synthetic figures only, and get the owner's approval (D30). Mock v4: [Workload](https://www.figma.com/design/aODgN8zO3eCm9bmN8sOSCK?node-id=21-2) and [Spot, no pay-as-you-go listing](https://www.figma.com/design/aODgN8zO3eCm9bmN8sOSCK?node-id=21-280), copies of v3 with only the labels changed. Approved by the owner on 2026-10-15
- [x] 5.2 Build D30 (MODIFIED "Figure captions and framing line", "Workload cost view"). Update the AppTest flows:
  - the title;
  - the tag line on Workload cost and Comparable groups;
  - the unchanged storage, "*", "†" and not-computed lines;
  - no "Scenario calculation" sentence on the page.
- [x] 5.3 Grid cells in positional form (MODIFIED "Display formatting"; D14; cut item 2), with the 0.000000006 test (shown as +0.000000006)

## 6. Documents and visuals

- [x] 6.1 Write `docs/methodology.md` (D13, D11): every recorded rule; the AI section; "Limitations and model risk" on SR 11-7 (data, method, process and AI risks, each with its control and test); why the data is synthetic; credits; the reading list; and a compute-futures paragraph rechecked against primary sources on the day. Done on 2026-10-15 in plain language; the futures paragraph was rechecked that day against the CFTC letter of 21 September 2026 and the ICE notice of 29 September 2026
- [x] 6.2 Take Workload cost screenshots (US East H100 ×8 pay-as-you-go, 32 × 720) and one Comparable groups screenshot from the demo database into `docs/assets/`, named `*-synthetic`, before 2026-10-19 09:00 UTC if possible (D29). Taken 2026-10-15 at 1920×1080 from a scratch launcher offering only the synthetic database, with headless Edge over the DevTools protocol; the figures checked by hand (276,480; +69,120; +1,105,920; median 13)
- [x] 6.3 Extend the README (D12, D31). Done on 2026-10-15, with `tests/repo/test_readme.py`:
  - the bottom line first;
  - the new screenshot;
  - the one-command setup;
  - links to the methodology, brief, deck and video;
  - one AI sentence;
  - the model-risk summary;
  - the STALE note.

  Add the repository tests for "README matches the brief" and "Licence and credits"
- [x] 6.4 Draft the five-slide deck in Figma Slides (D25) from the demo figures. The owner approves the draft, then exports the PDF to `docs/` (D38). Done on 2026-10-15: six plain-language slides (the owner asked for a newcomer-friendly story and a markets slide), approved by the owner; the PDF was exported slide by slide through the Figma tools and merged, `docs/compute-cost-risk-monitor-deck.pdf`
- [x] 6.5 Write `docs/walkthrough.md`, the timed script and shot list (D10). The owner records it from the demo database (cut item 3). Done on 2026-10-15: the owner was away and asked Claude to record it. It was recorded from the synthetic-only launcher, bound to 127.0.0.1, with headless Edge: 1:58 at 1920 × 1080, with captions and no voice. The MP4 stays out of Git (`tmp/`) until the owner decides where it goes (task 9.1)
- [x] 6.6 Update the FigJam context and container views (D33), fix the label overlap and re-export the SVGs to `docs/architecture/`. Polish is cut item 1. Done on 2026-10-15: the context view shows the Anthropic Claude API as built; the container view adds the market brief and its check, the brief drafter and the demo command, with straight connectors and no overlapping labels; the drafter is labelled "drafts the market brief's text" (the owner asked for no reassurance taglines). Then reworked to the C4 notation guide (c4model.com) at the owner's request: typed titles, a key on each view, a description on every element, a verb and [technology] on every line, and only programs and data stores in the container view

## 7. Pre-publication

- [x] 7.1 Scan every blob in the Git history for secrets (blobs exported with `git rev-list --objects --all` and `git cat-file`, scanned by detect-secrets) and record the command and result. Done on 2026-10-15: 808 blobs, no secret; recorded in `docs/reviews/2026-10-15-phase-8-demo.md`
- [x] 7.2 Survey tracked files and history for figures derived from collected data, and record the result (D26). Done on 2026-10-15: no live price, cost, exposure or SKU-level figure; recorded in the review record
- [x] 7.3 Neutralise personal details in the current, non-archived files (D23): PROJECT.md, HANDOFF.md, and `source_kit` in `source-manifest.json` (the digests and the provenance test unchanged). Done on 2026-10-15: the HANDOFF user path and `source_kit`; the owner's name stays
- [x] 7.4 Write the exact publishing list for the operator (D5, D26, D41). Done on 2026-10-15, in the review record. The owner had already made the repository public; PROJECT.md §6 records it

## 8. Verification and review

- [x] 8.1 Run the compute-cost-risk-monitor-market-review read-through of the brief, bottom line, README, methodology and deck (PROJECT.md §3)
- [x] 8.2 Manual check, synthetic only:
  - the demo from a fresh clone at a short path, with `--serve`;
  - the dashboard labels at 1920×1080;
  - the brief command with and without `--draft` refused on collected prices.
- [x] 8.3 Run the gate and `uv audit`
- [x] 8.4 Write `docs/reviews/<date>-phase-8-demo.md` (done: `docs/reviews/2026-10-15-phase-8-demo.md`):
  - the grilling summary;
  - the mock;
  - the drafter run and its cost;
  - the read-through and the manual check;
  - the pre-publication record ("Pre-publication record");
  - what was cut, if anything.
- [x] 8.5 Run `/code-review` on the PR, fix findings in new commits or answer them, and record the outcome in the PR body. Done on 2026-10-15: 15 findings; all fixed with tests (design D47), the brief re-drafted once (prompt v3, about USD 0.05), and the outcome recorded in the PR body

## 9. Gate and close

- [x] 9.1 Put the publishing list to the operator and record the decision in PROJECT.md §6 (D5). On approval, the owner uploads the video unlisted and its link enters the README. Done on 2026-10-15: the owner approved the list; PROJECT.md §6 records it. At the owner's request the video is in the repository (PR #16) rather than uploaded unlisted, and the README links it
- [ ] 9.2 Update HANDOFF for the checkpoint after the merge, including the visibility change the operator approved. Archive the change and mark Phase 8 Done
