## ADDED Requirements

### Requirement: One-command demo build
`python -m compute_cost_risk_monitor.demo` SHALL build the synthetic demo database from the
committed fixture files in a fixed order: the three Azure demo snapshots by date, then the three
synthetic marketplace snapshots. It SHALL:
- build into a new temporary file in `data/`, using the existing synthetic and normalize
  commands;
- stop with the failing command's exit code, leaving the existing demo database untouched, when
  either fails;
- replace `data/synthetic.duckdb` with the new file only when both succeed;
- print counts and paths only.

It SHALL refuse, with exit code 2, any target that resolves to `data/monitor.duckdb`, and SHALL
never open that file. A database held open by the dashboard SHALL produce the dashboard's IN USE
wording rather than a partial file.

#### Scenario: Fresh build
- **WHEN** the command runs in a clone with no `data/` folder
- **THEN** it creates `data/synthetic.duckdb` holding three `azure-retail` runs and three marketplace runs, all labelled `synthetic` and normalized

#### Scenario: Rebuild replaces
- **WHEN** the command runs twice
- **THEN** the second run succeeds and the database holds the same runs, not duplicates

#### Scenario: Collected database refused
- **WHEN** the target resolves to `data/monitor.duckdb`
- **THEN** the command exits 2 and that file is not opened

### Requirement: Demo serve option
With `--serve`, the command SHALL start the dashboard with the same interpreter
(`python -m streamlit run src/compute_cost_risk_monitor/app.py`) after a successful build, and
SHALL not start it after a failed one.

#### Scenario: Serve after build
- **WHEN** the command runs with `--serve` and the build succeeds
- **THEN** it starts the dashboard process with the package's app path
