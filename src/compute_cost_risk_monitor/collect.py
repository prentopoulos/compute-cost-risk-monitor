"""Collect one live run of Azure Retail Prices, then ingest it.

    uv run python -m compute_cost_risk_monitor.collect
    uv run python -m compute_cost_risk_monitor.collect --ingest-run RUN_ID

A fetch is always labelled live; no option sets the label. A live fetch is refused
within 24 hours of the previous one (the live-data gate's "at most one a day", design D1
and D25). The command prints counts, never prices.
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from importlib import metadata
from pathlib import Path

from compute_cost_risk_monitor import azure_retail as az
from compute_cost_risk_monitor import db, fetch, ingest, raw_store

DEFAULT_DB = Path("data/monitor.duckdb")
DEFAULT_RAW = Path("data/raw")
LIVE = "live"
GUARD = timedelta(hours=24)
REPO = Path(__file__).resolve().parents[2]


def package_version() -> str:
    return metadata.version("compute-cost-risk-monitor")


def user_agent() -> str:
    return f"compute-cost-risk-monitor/{package_version()} (Python-urllib)"


def dependency_versions() -> dict[str, str]:
    versions = {"python": platform.python_version()}
    for package in ("compute-cost-risk-monitor", "duckdb", "pandas", "pytz"):
        versions[package] = metadata.version(package)
    return versions


def code_version(repo: Path = REPO) -> str | None:
    """The Git commit, marked -dirty when tracked files have uncommitted changes."""
    git = shutil.which("git")
    if git is None:
        return None
    head = subprocess.run(  # noqa: S603 (fixed arguments, no shell)
        [git, "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if head.returncode != 0:
        return None
    changes = subprocess.run(  # noqa: S603
        [git, "status", "--porcelain", "--untracked-files=no"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    dirty = "-dirty" if changes.stdout.strip() else ""
    return head.stdout.strip() + dirty


def recent_live_run(raw_root: Path, now: datetime) -> tuple[str, datetime] | None:
    """The latest live run started less than 24 hours before `now`, read from disk."""
    latest: tuple[str, datetime] | None = None
    for path in (raw_root / az.SOURCE).glob("*/*/*/*.run.json"):
        manifest = json.loads(path.read_text(encoding="ascii"))
        if manifest.get("data_label") != LIVE:
            continue
        started = datetime.fromisoformat(manifest["started_at"])
        if now - started < GUARD and (latest is None or started > latest[1]):
            latest = (str(manifest["run_id"]), started)
    return latest


def report(result: ingest.IngestResult, db_path: Path) -> None:
    counts = result.summary
    print(f"run {result.run_id} ({result.data_label}): {result.status}")
    print(f"  stop reason: {result.stop_reason}")
    print(
        f"  requests {counts.requests}, pages parsed {counts.pages_parsed},"
        f" failed {counts.failed_requests}, throttled {counts.throttled}"
    )
    print(
        f"  items {counts.items_seen}: stored {counts.observations_stored},"
        f" repeats {counts.repeats}, out of scope {counts.out_of_scope},"
        f" rejected {counts.rejected}"
    )
    for (kind, reason), count in sorted(result.tallies.items()):
        print(f"  {kind} {reason}: {count}")
    print(f"  database: {db_path}")


def _ingest(db_path: Path, raw_root: Path, run_id: str) -> ingest.IngestResult:
    connection = db.connect(db_path)
    try:
        return ingest.ingest_run(connection, raw_root, run_id)
    finally:
        connection.close()


def system_clock() -> fetch.Clock:
    return fetch.Clock(lambda: datetime.now(UTC), time.monotonic, time.sleep)


def main(
    argv: Sequence[str] | None = None,
    *,
    fetcher: fetch.Fetcher | None = None,
    clock: fetch.Clock | None = None,
    data_label: str = LIVE,
) -> int:
    """Run the command; tests inject a fake fetcher, clock and synthetic label."""
    parser = argparse.ArgumentParser(
        prog="python -m compute_cost_risk_monitor.collect",
        description="Fetch one live run of Azure Retail Prices, then ingest it.",
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="DuckDB file")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW, help="raw files")
    parser.add_argument(
        "--ingest-run", metavar="RUN_ID", help="ingest a kept run without the network"
    )
    args = parser.parse_args(argv)

    if args.ingest_run:
        try:
            result = _ingest(
                args.db, args.raw_dir, raw_store.check_run_id(args.ingest_run)
            )
        except (ValueError, raw_store.IntegrityError, ingest.AlreadyIngested) as error:
            print(f"refused: {error}", file=sys.stderr)
            return 2
        report(result, args.db)
        return 0 if result.status == "succeeded" else 1

    clock = clock or system_clock()
    recent = recent_live_run(args.raw_dir, clock.now())
    if recent is not None:
        run_id, started = recent
        print(
            f"refused: live run {run_id} started {started.isoformat()};"
            f" the next live fetch is allowed after {(started + GUARD).isoformat()}",
            file=sys.stderr,
        )
        return 2

    run = fetch.fetch_run(
        args.raw_dir,
        fetcher or fetch.UrllibFetcher(user_agent()),
        clock,
        data_label=data_label,
        code_version=code_version(),
        dependency_versions=dependency_versions(),
        user_agent=user_agent(),
    )
    try:
        result = _ingest(args.db, args.raw_dir, run.run_id)
    except Exception as error:
        print(
            f"fetched run {run.run_id} ({run.stop_reason}) but ingest failed: {error}."
            f" Its files are kept; retry with --ingest-run {run.run_id}",
            file=sys.stderr,
        )
        return 1
    report(result, args.db)
    return 0 if result.status == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
