## ADDED Requirements

### Requirement: Synthetic demo history
The repository SHALL commit two more synthetic Azure snapshot files, observed at 2026-09-28
09:00 UTC and 2026-10-05 09:00 UTC, that come before `azure_demo.json` (2026-10-12 09:00 UTC)
and leave it unchanged. Ingested and normalized in date order into one database, the three
SHALL hold at least:
- one price change between 2026-10-05 and 2026-10-12: the US East H100 ×8 pay-as-you-go listing
  (`Standard_ND96isr_H100_v5`) goes from 88 to 96 USD per VM-hour;
- one listing present on 2026-09-28 and 2026-10-05 and missing on 2026-10-12, which is
  "absent once (unconfirmed)";
- one listing present only on 2026-09-28, which is "not listed" since 2026-10-05;
- no Spot price above the same size's pay-as-you-go price in its region, in any snapshot.

Every item outside these cases SHALL match `azure_demo.json`. The fixtures README SHALL list each
case and its known answers, worked out by hand before the test is written. `azure_history`
SHALL stay the end-to-end test fixture.

#### Scenario: Demo history known answers
- **WHEN** the three demo snapshots are ingested and normalized in date order into an empty database
- **THEN** the history as of the 2026-10-12 snapshot shows the US East H100 ×8 pay-as-you-go change from 11.0000 to 12.0000 USD/GPU-h, one listing absent once and one not listed since 2026-10-05, and every count equals the fixtures README

#### Scenario: Latest snapshot unchanged
- **WHEN** the dashboard reads the demo database
- **THEN** its latest snapshot is the 2026-10-12 run built from the unchanged `azure_demo.json`, so the "Demo file covers the dashboard cases" checks still hold

#### Scenario: No Spot above pay-as-you-go
- **WHEN** any of the three demo snapshots is normalized
- **THEN** no Spot USD/GPU-hour is above the same size's pay-as-you-go USD/GPU-hour in the same region
