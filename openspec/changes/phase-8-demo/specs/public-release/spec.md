## ADDED Requirements

### Requirement: README matches the brief
The README SHALL open with the bottom line from the committed synthetic brief, labelled
synthetic. A repository test SHALL check that every figure in the README's bottom line equals the
matching fact in `docs/brief/facts.json` at its displayed decimals.

#### Scenario: README figure drifts
- **WHEN** a README bottom-line figure differs from the committed fact set
- **THEN** the repository test fails and names the figure

### Requirement: Licence and credits
The repository SHALL hold an MIT `LICENSE`. The README SHALL name it, and SHALL list the
third-party material that keeps its own licence: the Microsoft Learn-derived GPU map (CC BY 4.0,
with its attribution file) and the vendored grilling skill (MIT, with its own `LICENSE`). Every
local link in the README SHALL resolve.

#### Scenario: Licence and links present
- **WHEN** the repository tests run
- **THEN** `LICENSE` is MIT, the README names it and both third-party licences, and every relative README link resolves to a tracked file

### Requirement: Pre-publication record
Before the repository is made public, the Phase 8 review record SHALL hold:
- a secret scan over every blob in the Git history, with its command and result;
- a survey of figures derived from collected data in tracked files and history, with the result
  that no live Azure price, cost, exposure or SKU-level price figure appears;
- the personal details neutralised in the current files;
- the exact publishing list put to the operator, with the wording "No live Azure price, cost,
  exposure or SKU-level price figure appears. Aggregate counts and coarse distributions from the
  one local snapshot appear in design and review records."

The repository's visibility SHALL change only after PROJECT.md §6 records the operator's
publishing decision, with its date and scope.

#### Scenario: Gate before visibility
- **WHEN** the repository is made public
- **THEN** PROJECT.md §6 already records the operator's publishing decision, and the review record holds the scan, the survey and the publishing list it approved
