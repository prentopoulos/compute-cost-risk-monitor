"""Build the synthetic demo database in one command (Phase 8 design D39).

    uv run --locked python -m compute_cost_risk_monitor.demo [--serve]

It stores the committed synthetic snapshots in a new file beside the demo database,
using the synthetic and normalize commands, and replaces `data/synthetic.duckdb` only
when both succeed. A rerun rebuilds cleanly, and a failure leaves the old demo
untouched. It never opens the database of collected prices. `--serve` then starts the
dashboard. It prints counts and paths, never a price.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import uuid
from collections.abc import Callable, Sequence
from pathlib import Path

from compute_cost_risk_monitor import normalize, synthetic

REPO = synthetic.REPO
MONITOR_DB = synthetic.MONITOR_DB
DEFAULT_DB = synthetic.DEFAULT_DB
FIXTURES = REPO / "tests" / "fixtures" / "synthetic"
# The order matters: Azure snapshots by date, so azure_demo.json is the latest.
FILES = (
    FIXTURES / "azure_demo_history" / "snapshot-1.json",
    FIXTURES / "azure_demo_history" / "snapshot-2.json",
    FIXTURES / "azure_demo.json",
    FIXTURES / "marketplace" / "snapshot-1.json",
    FIXTURES / "marketplace" / "snapshot-2.json",
    FIXTURES / "marketplace" / "snapshot-3.json",
)
APP = Path(__file__).resolve().parent / "app.py"
IN_USE = (
    "IN USE: {target} is open in another process, probably the dashboard."
    " Stop it and rerun."
)

Command = Callable[[Sequence[str]], int]
Launcher = Callable[[Sequence[str]], int]


def _launch(command: Sequence[str]) -> int:
    return subprocess.run(list(command), check=False).returncode  # noqa: S603


def _remove(path: Path) -> None:
    for leftover in (path, path.with_name(path.name + ".wal")):
        leftover.unlink(missing_ok=True)


def build(
    target: Path = DEFAULT_DB,
    files: Sequence[Path] = FILES,
    *,
    store: Command = synthetic.main,
    normalize_db: Command = normalize.main,
) -> int:
    """Build the demo into `target`: 0 when built, otherwise the failing step's code."""
    if target.resolve() == MONITOR_DB.resolve():
        print(f"refused: the demo never goes to {MONITOR_DB}", file=sys.stderr)
        return 2
    target.parent.mkdir(parents=True, exist_ok=True)
    building = target.with_name(f".{target.name}.{uuid.uuid4().hex[:8]}.building")
    try:
        code = store([*(str(path) for path in files), "--db", str(building)])
        if code:
            return code
        code = normalize_db(["--db", str(building)])
        if code:
            return code
        try:
            os.replace(building, target)
        except PermissionError:
            print(IN_USE.format(target=target), file=sys.stderr)
            return 2
    finally:
        _remove(building)
    print(f"built {target}")
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    store: Command = synthetic.main,
    normalize_db: Command = normalize.main,
    launch: Launcher = _launch,
) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m compute_cost_risk_monitor.demo",
        description="Build the synthetic demo database from the committed fixtures.",
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="DuckDB file")
    parser.add_argument(
        "--serve", action="store_true", help="start the dashboard after the build"
    )
    args = parser.parse_args(argv)
    code = build(args.db, store=store, normalize_db=normalize_db)
    if code or not args.serve:
        return code
    return launch([sys.executable, "-m", "streamlit", "run", str(APP)])


if __name__ == "__main__":
    sys.exit(main())
