## ADDED Requirements

### Requirement: Synthetic command checks every file first
`uv run python -m compute_cost_risk_monitor.synthetic FILE ... [--db PATH]` SHALL read and check
every file before it opens the database. The checks cover:
- the synthetic label;
- the `observed_at` time, which must convert to UTC;
- the shape: marketplace offers or one Azure-shaped page;
- the file's own rules, which for an Azure-shaped file include at least one item passing the
  live row rules;
- that no two files in the command share a source and an observation time.

When any file is refused by these checks, the command SHALL exit with code 2 and name that file
and its reason, with "refused" said once. It SHALL write nothing and SHALL create no database
file. A database that cannot be opened or created, including when its folder cannot be made,
SHALL be refused with exit code 2. Refusals that depend on the database, such as a run already
stored, come after the database is opened.

#### Scenario: Refused file creates no database
- **WHEN** the command is given a valid snapshot file and an unlabelled one, with a database path that does not exist yet
- **THEN** it exits with code 2, names the unlabelled file, stores neither file, and no database file exists afterwards

#### Scenario: Refused file leaves an existing database unchanged
- **WHEN** the command is given an Azure-shaped file none of whose items passes the row rules, with an existing database
- **THEN** it exits with code 2 and the database holds the same runs as before

#### Scenario: Refusal said once
- **WHEN** a file is refused because it lacks `"_label": "synthetic"`
- **THEN** the message reads `refused: <file name>: <reason>`, with the word "refused" once

#### Scenario: Same snapshot twice in one command
- **WHEN** the command is given the same snapshot file twice, with a database path that does not exist yet
- **THEN** it refuses the second copy as observed at the same time as the first, exits with code 2, and no database file exists afterwards

#### Scenario: Database folder that cannot be made
- **WHEN** the `--db` path's parent is a file
- **THEN** the command refuses with "cannot open" and exit code 2, not a traceback
