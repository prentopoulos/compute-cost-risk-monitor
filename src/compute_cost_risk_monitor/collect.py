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

_CHECKOUT = Path(__file__).resolve().parents[2]
# The repo root when run from a checkout (uv run), so the data folder and the 24-hour
# guard do not depend on the working directory; otherwise the working directory.
REPO = _CHECKOUT if (_CHECKOUT / "pyproject.toml").is_file() else Path.cwd()
DEFAULT_DB = REPO / "data" / "monitor.duckdb"
DEFAULT_RAW = REPO / "data" / "raw"
LIVE = "live"
GUARD = timedelta(hours=24)
# A run without an end manifest may still be fetching until its time cap has passed.
SETTLE = timedelta(seconds=fetch.Limits().max_seconds) + timedelta(minutes=5)


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


def _sent_no_request(folder: Path, run_id: str) -> bool:
    end = folder / f"{run_id}.end.json"
    if not end.exists():
        return False  # still running or killed: count it
    return bool(json.loads(end.read_text(encoding="ascii")).get("requests") == 0)


def recent_live_run(raw_root: Path, now: datetime) -> tuple[str, datetime] | None:
    """The latest live run started less than 24 hours before `now`, read from disk.

    Runs are filed by UTC start date, so only today's and yesterday's folders can hold
    one. A run that ended before sending any request read nothing and is not counted.
    """
    latest: tuple[str, datetime] | None = None
    days = {now.date(), (now - GUARD).date()}
    for path, manifest in raw_store.run_manifests(raw_root, az.SOURCE, days):
        if manifest.get("data_label") != LIVE:
            continue
        started = datetime.fromisoformat(manifest["started_at"])
        if not now - started < GUARD or (latest is not None and started <= latest[1]):
            continue
        if not _sent_no_request(path.parent, str(manifest["run_id"])):
            latest = (str(manifest["run_id"]), started)
    return latest


def still_fetching(raw_root: Path, run_id: str, now: datetime) -> datetime | None:
    """When a run without an end manifest may be ingested, if that is still ahead."""
    files = raw_store.read_run(raw_root, az.SOURCE, run_id)
    if files.end is not None:
        return None
    settled = datetime.fromisoformat(files.manifest["started_at"]) + SETTLE
    return settled if now < settled else None


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

    clock = clock or system_clock()
    if args.ingest_run:
        try:
            run_id = raw_store.check_run_id(args.ingest_run)
            settled = still_fetching(args.raw_dir, run_id, clock.now())
            if settled is not None:
                print(
                    f"refused: run {run_id} has no end manifest and may still be"
                    f" fetching; retry after {settled.isoformat()}",
                    file=sys.stderr,
                )
                return 2
            result = _ingest(args.db, args.raw_dir, run_id)
        except (ValueError, raw_store.IntegrityError, ingest.AlreadyIngested) as error:
            print(f"refused: {error}", file=sys.stderr)
            return 2
        report(result, args.db)
        return 0 if result.status == "succeeded" else 1

    recent = recent_live_run(args.raw_dir, clock.now())
    if recent is not None:
        run_id, started = recent
        print(
            f"refused: live run {run_id} started {started.isoformat()};"
            f" the next live fetch is allowed after {(started + GUARD).isoformat()}",
            file=sys.stderr,
        )
        return 2

    agent = user_agent()
    try:
        run = fetch.fetch_run(
            args.raw_dir,
            fetcher or fetch.UrllibFetcher(agent),
            clock,
            data_label=data_label,
            code_version=code_version(),
            dependency_versions=dependency_versions(),
            user_agent=agent,
        )
    except OSError as error:  # the start or end manifest could not be written
        print(f"run could not be recorded: {error}", file=sys.stderr)
        return 1
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
