"""Ingest labelled synthetic snapshots as synthetic runs (Phase 3 D8, D22; Phase 4 D7).

Two kinds of file, told apart by shape:
- a marketplace snapshot (`offers`) becomes one `synthetic-marketplace` run, with one
  observation per offer;
- an Azure-shaped snapshot (one API page: `Items`) becomes one `azure-retail` run, its
  items passing the same row rules as live ingest.

Each run is labelled `synthetic` and `succeeded`, with one raw response for the file
(its SHA-256). Synthetic runs go to their own database, never the live one.

    uv run python -m compute_cost_risk_monitor.synthetic FILE [FILE ...] [--db PATH]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from compute_cost_risk_monitor import azure_retail, collect, db, ingest

SOURCE = "synthetic-marketplace"
AZURE_SOURCE = azure_retail.SOURCE
LABEL = "synthetic"
REPO = collect.REPO
MONITOR_DB = collect.DEFAULT_DB
DEFAULT_DB = REPO / "data" / "synthetic.duckdb"
RENTAL_TYPES = ("on_demand", "spot", "reservation", "savings_plan", "dev_test", "other")
_TEXT = ("offer_id", "machine_id", "gpu_name", "region", "rental_type")
MAX_GPUS = 2**31 - 1  # the stored column is a 32-bit integer


class SyntheticError(ValueError):
    """A snapshot file breaks a rule; nothing was written."""


def _positive(value: object) -> bool:
    if not isinstance(value, int | float) or isinstance(value, bool):
        return False
    try:
        number = float(value)
    except OverflowError:  # an integer too large for a float
        return False
    return math.isfinite(number) and number > 0


def _offer(index: int, offer: object) -> dict[str, Any]:
    def fail(why: str) -> SyntheticError:
        return SyntheticError(f"offer {index}: {why}")

    if not isinstance(offer, dict):
        raise fail("not an object")
    for name in _TEXT:
        if not isinstance(offer.get(name), str) or not offer[name]:
            raise fail(f"{name} must be non-empty text")
    if offer["rental_type"] not in RENTAL_TYPES:
        raise fail(f"unknown rental type {offer['rental_type']}")
    gpus = offer.get("num_gpus")
    if not isinstance(gpus, int) or isinstance(gpus, bool) or not 0 < gpus <= MAX_GPUS:
        raise fail("num_gpus must be a whole number above zero")
    if not _positive(offer.get("usd_per_hour")):
        raise fail("usd_per_hour must be a finite number above zero")
    vram = offer.get("gpu_vram_gb")
    if vram is not None and not _positive(vram):
        raise fail("gpu_vram_gb must be above zero when given")
    country = offer.get("country_code")
    if country is not None and not (
        isinstance(country, str) and len(country) == 2 and country.isupper()
    ):
        raise fail("country_code must be two capital letters when given")
    return offer


def _labelled(body: bytes) -> tuple[dict[str, Any], datetime]:
    """The document and its time; SyntheticError unless JSON, synthetic and timed."""
    try:
        document = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise SyntheticError(f"not JSON: {error}") from None
    if not isinstance(document, dict) or document.get("_label") != LABEL:
        raise SyntheticError('the file is not labelled "_label": "synthetic"')
    try:
        observed = datetime.fromisoformat(str(document.get("observed_at")))
    except ValueError:
        raise SyntheticError("observed_at must be an ISO time") from None
    if observed.tzinfo is None:
        raise SyntheticError("observed_at must carry a time zone")
    return document, observed


def kind(body: bytes) -> str:
    """The source a synthetic file feeds, from its shape; SyntheticError if neither."""
    document, _ = _labelled(body)
    if "Items" in document:
        return AZURE_SOURCE
    if "offers" in document:
        return SOURCE
    raise SyntheticError("neither an Azure page (Items) nor a marketplace snapshot")


def parse_snapshot(body: bytes) -> tuple[datetime, list[dict[str, Any]]]:
    """The snapshot's time and offers; SyntheticError unless valid and synthetic."""
    document, observed = _labelled(body)
    offers = document.get("offers")
    if not isinstance(offers, list) or not offers:
        raise SyntheticError("offers must be a non-empty list")
    checked = [_offer(index, offer) for index, offer in enumerate(offers)]
    counts = Counter(offer["offer_id"] for offer in checked)
    duplicates = sorted(oid for oid, n in counts.items() if n > 1)
    if duplicates:
        raise SyntheticError(f"offer ID listed twice: {', '.join(duplicates)}")
    return observed, checked


def _display_path(path: Path, repo: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return path.name


def parse_azure_snapshot(body: bytes) -> tuple[datetime, list[object]]:
    """An Azure-shaped snapshot's time and items; SyntheticError unless valid."""
    document, observed = _labelled(body)
    items = document.get("Items")
    if not isinstance(items, list) or not items:
        raise SyntheticError("Items must be a non-empty list")
    if document.get("NextPageLink"):
        raise SyntheticError("a synthetic Azure snapshot is one page: NextPageLink")
    return observed, items


def _run_id(observed: datetime, body: bytes) -> tuple[str, str]:
    """The run ID and the file's SHA-256."""
    digest = hashlib.sha256(body).hexdigest()
    stamp = observed.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"synthetic-{stamp}-{digest[:6]}", digest


def _new_run(
    connection: duckdb.DuckDBPyConnection, source: str, observed: datetime, body: bytes
) -> tuple[str, str, int | None]:
    """A fresh run ID, the file's SHA-256 and the schema version; refuse repeats."""
    run_id, digest = _run_id(observed, body)
    db.create_schema(connection)
    exists = connection.execute(
        "SELECT count(*) FROM collection_run WHERE run_id = ?", [run_id]
    ).fetchone()
    if exists and exists[0]:
        raise SyntheticError(f"run {run_id} is already stored")
    same_time = connection.execute(
        "SELECT run_id FROM collection_run WHERE source = ? AND started_at = ?",
        [source, observed],
    ).fetchone()
    if same_time:
        raise SyntheticError(
            f"a snapshot observed at {observed.isoformat()} is already stored as run"
            f" {same_time[0]}"
        )
    version = connection.execute("SELECT max(version) FROM schema_version").fetchone()
    return run_id, digest, version[0] if version else None


def _azure_rows(body: bytes) -> tuple[datetime, int, ingest.Items]:
    """An Azure-shaped snapshot's time, item count and rows passing the live row rules.

    SyntheticError unless the file is valid and at least one item passes.
    """
    observed, items = parse_azure_snapshot(body)
    response = f"{_run_id(observed, body)[0]}-0000"
    found = ingest.Items()
    found.summary.requests = found.summary.pages_parsed = 1
    found.add_page(items, response, observed)
    found.flag_shared_meters()
    if not found.observations:
        summary = found.summary
        raise SyntheticError(
            f"no item passed the row rules ({summary.out_of_scope} out of scope,"
            f" {summary.rejected} rejected): nothing to store"
        )
    return observed, len(items), found


def ingest_azure_snapshot(
    connection: duckdb.DuckDBPyConnection,
    path: Path,
    repo: Path = REPO,
    body: bytes | None = None,
) -> str:
    """Store one Azure-shaped snapshot as a synthetic run; return its run ID.

    `body` is the file's bytes when the caller has already read them.
    """
    body = path.read_bytes() if body is None else body
    observed, item_count, found = _azure_rows(body)
    run_id, digest, version = _new_run(connection, AZURE_SOURCE, observed, body)
    response = f"{run_id}-0000"  # the ID the rows were built with in _azure_rows
    shown = _display_path(path, repo)
    connection.begin()
    try:
        connection.execute(
            "INSERT INTO collection_run VALUES (?, ?, ?, ?, ?, 'succeeded', NULL, ?,"
            " NULL, ?, ?)",
            [
                run_id,
                AZURE_SOURCE,
                LABEL,
                observed,
                observed,
                version,
                json.dumps({"file": shown}),
                "synthetic Azure-shaped snapshot; the prices are invented",
            ],
        )
        ingest.write_records(
            connection,
            run_id,
            AZURE_SOURCE,
            found,
            "completed",
            [
                {
                    "response_id": response,
                    "seq": 0,
                    "file_path": shown,
                    "sha256": digest,
                    "byte_length": len(body),
                    "request_url": f"file:{shown}",
                    "http_status": None,
                    "requested_at": observed,
                    "received_at": observed,
                    "item_count": item_count,
                    "parse_status": "parsed",
                    "error": None,
                }
            ],
        )
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    return run_id


def ingest_snapshot(
    connection: duckdb.DuckDBPyConnection,
    path: Path,
    repo: Path = REPO,
    body: bytes | None = None,
) -> str:
    """Store one snapshot as a synthetic run in one transaction; return its run ID.

    `body` is the file's bytes when the caller has already read them.
    """
    body = path.read_bytes() if body is None else body
    observed, offers = parse_snapshot(body)
    run_id, digest, version = _new_run(connection, SOURCE, observed, body)
    shown = _display_path(path, repo)
    response = f"{run_id}-0000"
    n = len(offers)
    connection.begin()
    try:
        connection.execute(
            "INSERT INTO collection_run VALUES (?, ?, ?, ?, ?, 'succeeded', NULL, ?,"
            " NULL, ?, ?)",
            [
                run_id,
                SOURCE,
                LABEL,
                observed,
                observed,
                version,
                json.dumps({"file": shown}),
                "synthetic marketplace snapshot; the provider is fictional",
            ],
        )
        connection.execute(
            "INSERT INTO raw_response VALUES (?, ?, ?, 0, ?, ?, ?, ?, NULL, ?, ?, ?,"
            " 'parsed', NULL)",
            [
                response,
                run_id,
                SOURCE,
                shown,
                digest,
                len(body),
                f"file:{shown}",
                observed,
                observed,
                n,
            ],
        )
        db.insert_frame(
            connection,
            "price_observation",
            db.frame(
                {
                    "source": (db.TEXT, [SOURCE] * n),
                    "item_key": (db.TEXT, [o["offer_id"] for o in offers]),
                    "retrieved_at": ("timestamp", [observed] * n),
                    "response_id": (db.TEXT, [response] * n),
                    "rental_type": (db.TEXT, [o["rental_type"] for o in offers]),
                    "region": (db.TEXT, [o["region"] for o in offers]),
                    "price": ("Float64", [float(o["usd_per_hour"]) for o in offers]),
                    "currency": (db.TEXT, ["USD"] * n),
                    "price_unit": (db.TEXT, ["1 Hour"] * n),
                }
            ),
        )
        db.insert_frame(
            connection,
            "marketplace_offer",
            db.frame(
                {
                    "source": (db.TEXT, [SOURCE] * n),
                    "item_key": (db.TEXT, [o["offer_id"] for o in offers]),
                    "retrieved_at": ("timestamp", [observed] * n),
                    "offer_id": (db.TEXT, [o["offer_id"] for o in offers]),
                    "machine_id": (db.TEXT, [o["machine_id"] for o in offers]),
                    "gpu_name_listed": (db.TEXT, [o["gpu_name"] for o in offers]),
                    "num_gpus": ("Int64", [o["num_gpus"] for o in offers]),
                    "gpu_vram_gb": ("Float64", [o.get("gpu_vram_gb") for o in offers]),
                    "country_code": (db.TEXT, [o.get("country_code") for o in offers]),
                }
            ),
        )
        connection.execute(
            "INSERT INTO collection_run_summary"
            " VALUES (?, ?, 1, 1, 0, 0, ?, ?, 0, 0, 0, 'completed')",
            [run_id, SOURCE, n, n],
        )
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    return run_id


def check(body: bytes) -> str:
    """The source a file feeds, after every check that needs no database.

    SyntheticError when the file is refused: its label, time, shape, offers, or (for an
    Azure-shaped page) no item passing the live row rules.
    """
    source = kind(body)
    if source == AZURE_SOURCE:
        _azure_rows(body)
    else:
        parse_snapshot(body)
    return source


def ingest_file(
    connection: duckdb.DuckDBPyConnection,
    path: Path,
    repo: Path = REPO,
    body: bytes | None = None,
) -> tuple[str, str]:
    """Store a marketplace or Azure-shaped snapshot; return (source, run ID).

    The file is read once, so its kind, digest and rows all come from the same bytes;
    `body` is those bytes when the caller has already read them.
    """
    body = path.read_bytes() if body is None else body
    source = kind(body)
    if source == AZURE_SOURCE:
        return source, ingest_azure_snapshot(connection, path, repo, body)
    return source, ingest_snapshot(connection, path, repo, body)


def main(argv: Sequence[str] | None = None) -> int:
    """Ingest each file; 0 on success, 2 when a file or the database is refused."""
    parser = argparse.ArgumentParser(
        prog="python -m compute_cost_risk_monitor.synthetic",
        description="Store labelled synthetic marketplace or Azure-shaped snapshots"
        " as synthetic runs.",
    )
    parser.add_argument("files", nargs="+", type=Path, help="snapshot JSON files")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="DuckDB file")
    args = parser.parse_args(argv)
    if args.db.resolve() == MONITOR_DB.resolve():
        print(f"refused: synthetic runs never go to {MONITOR_DB}", file=sys.stderr)
        return 2
    # Every file is checked before the database is opened, so a refused file never
    # leaves an empty database behind.
    checked: list[tuple[Path, bytes]] = []
    for path in args.files:
        try:
            body = path.read_bytes()
            check(body)
        except (OSError, SyntheticError) as error:
            print(f"refused: {path.name}: {error}", file=sys.stderr)
            return 2
        checked.append((path, body))
    try:
        connection = db.connect(args.db)
    except duckdb.Error as error:
        print(f"refused: cannot open {args.db}: {error}", file=sys.stderr)
        return 2
    try:
        for path, body in checked:
            try:
                source, run_id = ingest_file(connection, path, body=body)
            except (SyntheticError, duckdb.Error) as error:
                print(f"refused: {path.name}: {error}", file=sys.stderr)
                return 2
            print(f"stored {run_id} (synthetic) for {source} from {path.name}")
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
