"""Ingest labelled synthetic marketplace snapshots as synthetic runs (design D8, D22).

Each snapshot file becomes one succeeded `synthetic-marketplace` run labelled
`synthetic`, with one raw response for the file (its SHA-256) and one observation per
offer. Synthetic runs go to their own database, never the live one.

    uv run python -m compute_cost_risk_monitor.synthetic FILE [FILE ...] [--db PATH]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

from compute_cost_risk_monitor import collect, db

SOURCE = "synthetic-marketplace"
LABEL = "synthetic"
REPO = collect.REPO
MONITOR_DB = collect.DEFAULT_DB
DEFAULT_DB = REPO / "data" / "synthetic.duckdb"
RENTAL_TYPES = ("on_demand", "spot", "reservation", "savings_plan", "dev_test", "other")
_TEXT = ("offer_id", "machine_id", "gpu_name", "region", "rental_type")


class SyntheticError(ValueError):
    """A snapshot file breaks a rule; nothing was written."""


def _positive(value: object) -> bool:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    )


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
    if not isinstance(gpus, int) or isinstance(gpus, bool) or gpus <= 0:
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


def parse_snapshot(body: bytes) -> tuple[datetime, list[dict[str, Any]]]:
    """The snapshot's time and offers; SyntheticError unless valid and synthetic."""
    try:
        document = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise SyntheticError(f"not JSON: {error}") from None
    if not isinstance(document, dict) or document.get("_label") != LABEL:
        raise SyntheticError('refused: the file is not labelled "_label": "synthetic"')
    try:
        observed = datetime.fromisoformat(str(document.get("observed_at")))
    except ValueError:
        raise SyntheticError("observed_at must be an ISO time") from None
    if observed.tzinfo is None:
        raise SyntheticError("observed_at must carry a time zone")
    offers = document.get("offers")
    if not isinstance(offers, list) or not offers:
        raise SyntheticError("offers must be a non-empty list")
    checked = [_offer(index, offer) for index, offer in enumerate(offers)]
    ids = [offer["offer_id"] for offer in checked]
    duplicates = sorted({oid for oid in ids if ids.count(oid) > 1})
    if duplicates:
        raise SyntheticError(f"offer ID listed twice: {', '.join(duplicates)}")
    return observed, checked


def _display_path(path: Path, repo: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return path.name


def ingest_snapshot(
    connection: duckdb.DuckDBPyConnection, path: Path, repo: Path = REPO
) -> str:
    """Store one snapshot as a synthetic run in one transaction; return its run ID."""
    body = path.read_bytes()
    observed, offers = parse_snapshot(body)
    digest = hashlib.sha256(body).hexdigest()
    run_id = f"synthetic-{observed.strftime('%Y%m%dT%H%M%SZ')}-{digest[:6]}"
    db.create_schema(connection)
    exists = connection.execute(
        "SELECT count(*) FROM collection_run WHERE run_id = ?", [run_id]
    ).fetchone()
    if exists and exists[0]:
        raise SyntheticError(f"run {run_id} is already stored")
    version = connection.execute("SELECT max(version) FROM schema_version").fetchone()
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
                version[0] if version else None,
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


def main(argv: Sequence[str] | None = None) -> int:
    """Ingest each file; 0 on success, 2 when a file or the database is refused."""
    parser = argparse.ArgumentParser(
        prog="python -m compute_cost_risk_monitor.synthetic",
        description="Store labelled synthetic marketplace snapshots as synthetic runs.",
    )
    parser.add_argument("files", nargs="+", type=Path, help="snapshot JSON files")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="DuckDB file")
    args = parser.parse_args(argv)
    if args.db.resolve() == MONITOR_DB.resolve():
        print(f"refused: synthetic runs never go to {MONITOR_DB}", file=sys.stderr)
        return 2
    connection = db.connect(args.db)
    try:
        for path in args.files:
            try:
                run_id = ingest_snapshot(connection, path)
            except (OSError, SyntheticError) as error:
                print(f"refused: {path.name}: {error}", file=sys.stderr)
                return 2
            print(f"stored {run_id} (synthetic) from {path.name}")
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
