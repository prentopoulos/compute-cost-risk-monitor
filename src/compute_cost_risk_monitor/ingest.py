"""Build a run's database records from its retained files, in one transaction.

Ingest reads only the files raw_store kept: never memory, never the network. It checks
every body against its sidecar before parsing, then writes the run, its summary and
tallies, every raw response, the observations with their Azure detail, and the
repeats. If anything fails, nothing of the run is written and the files stay (design
D7-D10, D27).
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

from compute_cost_risk_monitor import azure_retail as az
from compute_cost_risk_monitor import db, raw_store
from compute_cost_risk_monitor.db import TEXT

# Module names, so a test can make one insert fail.
_frame = db.frame
_insert = db.insert_frame


class AlreadyIngested(Exception):
    """The database already holds this run."""


@dataclass
class Summary:
    requests: int = 0
    pages_parsed: int = 0
    failed_requests: int = 0
    throttled: int = 0
    items_seen: int = 0
    observations_stored: int = 0
    repeats: int = 0
    out_of_scope: int = 0
    rejected: int = 0


@dataclass
class IngestResult:
    run_id: str
    data_label: str
    status: str
    stop_reason: str
    summary: Summary
    tallies: dict[tuple[str, str], int] = field(default_factory=dict)


def _time(value: object) -> datetime | None:
    return None if value is None else datetime.fromisoformat(str(value))


def run_status(stop_reason: str, pages_parsed: int) -> str:
    """succeeded only when paging ended normally; otherwise partial or failed (D7)."""
    if stop_reason == "completed" and pages_parsed > 0:
        return "succeeded"
    return "partial" if pages_parsed > 0 else "failed"


def ingest_run(
    connection: duckdb.DuckDBPyConnection,
    raw_root: Path,
    run_id: str,
    source: str = az.SOURCE,
) -> IngestResult:
    files = raw_store.read_run(raw_root, source, run_id)
    db.create_schema(connection)
    already = connection.execute(
        "SELECT count(*) FROM collection_run WHERE run_id = ?", [run_id]
    ).fetchone()
    if already and already[0]:
        raise AlreadyIngested(f"run {run_id} is already in the database")

    summary = Summary()
    tallies: Counter[tuple[str, str]] = Counter()
    responses: list[dict[str, Any]] = []
    kept: dict[str, tuple[az.Row, object, datetime]] = {}
    observations: list[tuple[az.Row, datetime, str]] = []
    repeats: list[dict[str, Any]] = []

    for sidecar in files.sidecars:
        # Every body is checked before any is parsed; a mismatch stops the ingest.
        body = raw_store.read_body(raw_root, sidecar)
        response_id = f"{run_id}-{sidecar['seq']:04d}"
        status, error = sidecar["http_status"], sidecar["error"]
        received_at = _time(sidecar["received_at"])
        page = az.parse_page(body) if status == 200 and error is None else None
        summary.requests += 1
        if status == 429:
            summary.throttled += 1
        if page is None:
            summary.failed_requests += 1
            if status == 200 and error is None:
                parse_status, error = "failed", "not a valid page"
            elif status is not None and error is None:
                parse_status, error = "not_parsed", f"HTTP {status} {sidecar['reason']}"
            else:
                parse_status = "failed" if status == 200 else "not_parsed"
        else:
            parse_status = "parsed"
            summary.pages_parsed += 1
        responses.append(
            {
                "response_id": response_id,
                "seq": sidecar["seq"],
                "file_path": sidecar["file"],
                "sha256": sidecar["sha256"],
                "byte_length": sidecar["byte_length"],
                "request_url": sidecar["url"],
                "http_status": status,
                "requested_at": _time(sidecar["requested_at"]),
                "received_at": received_at,
                "item_count": None if page is None else len(page.items),
                "parse_status": parse_status,
                "error": error,
            }
        )
        if page is None or received_at is None:
            continue
        link = page.next_link
        if isinstance(link, str) and link and az.missing_params(link):
            tallies[("flagged", "next_link_missing_params")] += 1
        for index, item in enumerate(page.items):
            summary.items_seen += 1
            verdict = az.classify(item)
            if verdict.outcome == "out_of_scope":
                summary.out_of_scope += 1
                continue
            if verdict.row is None:
                summary.rejected += 1
                tallies[("rejected", verdict.reason or "unknown")] += 1
                continue
            row = verdict.row
            first = kept.get(row.item_key)
            if first is not None:
                first_row, first_item, first_time = first
                summary.repeats += 1
                repeats.append(
                    {
                        "response_id": response_id,
                        "item_index": index,
                        "item_key": row.item_key,
                        "first_retrieved_at": first_time,
                        "same_price": row.retail_price == first_row.retail_price,
                        "same_fields": item == first_item,
                    }
                )
                continue
            kept[row.item_key] = (row, item, received_at)
            observations.append((row, received_at, response_id))
            summary.observations_stored += 1
            for flag in row.flags:
                tallies[("flagged", flag)] += 1

    meters = Counter(row.meter_key for row, _, _ in observations)
    shared = sum(count - 1 for count in meters.values() if count > 1)
    if shared:
        tallies[("flagged", "shared_meter_key")] += shared
    if files.orphan_bodies:
        tallies[("flagged", "orphan_body_file")] += len(files.orphan_bodies)

    end = files.end
    stop_reason = str(end["stop_reason"]) if end else "no_end_manifest"
    detail = str(end.get("detail", "")) if end else "the run stopped before it finished"
    status = run_status(stop_reason, summary.pages_parsed)
    manifest = files.manifest
    schema_version = max(db.applied_versions(connection))

    connection.begin()
    try:
        connection.execute(
            "INSERT INTO collection_run (run_id, source, data_label, started_at,"
            " finished_at, status, code_version, schema_version, dependency_versions,"
            " request_params, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                run_id,
                source,
                manifest["data_label"],
                _time(manifest["started_at"]),
                _time(end["finished_at"]) if end else None,
                status,
                manifest.get("code_version"),
                schema_version,
                json.dumps(manifest.get("dependency_versions", {})),
                json.dumps(manifest.get("request_params", {})),
                f"{stop_reason}: {detail}" if detail else stop_reason,
            ],
        )
        connection.execute(
            "INSERT INTO collection_run_summary VALUES"
            " (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                run_id,
                source,
                summary.requests,
                summary.pages_parsed,
                summary.failed_requests,
                summary.throttled,
                summary.items_seen,
                summary.observations_stored,
                summary.repeats,
                summary.out_of_scope,
                summary.rejected,
                stop_reason,
            ],
        )
        for (kind, reason), count in sorted(tallies.items()):
            connection.execute(
                "INSERT INTO collection_run_tally VALUES (?, ?, ?, ?, ?)",
                [run_id, source, kind, reason, count],
            )
        _write_rows(connection, run_id, source, responses, observations, repeats)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return IngestResult(
        run_id, str(manifest["data_label"]), status, stop_reason, summary, dict(tallies)
    )


def _write_rows(
    connection: duckdb.DuckDBPyConnection,
    run_id: str,
    source: str,
    responses: list[dict[str, Any]],
    observations: list[tuple[az.Row, datetime, str]],
    repeats: list[dict[str, Any]],
) -> None:
    def column(rows: list[dict[str, Any]], name: str) -> list[Any]:
        return [row[name] for row in rows]

    n = len(responses)
    _insert(
        connection,
        "raw_response",
        _frame(
            {
                "response_id": (TEXT, column(responses, "response_id")),
                "run_id": (TEXT, [run_id] * n),
                "source": (TEXT, [source] * n),
                "seq": ("Int64", column(responses, "seq")),
                "file_path": (TEXT, column(responses, "file_path")),
                "sha256": (TEXT, column(responses, "sha256")),
                "byte_length": ("Int64", column(responses, "byte_length")),
                "request_url": (TEXT, column(responses, "request_url")),
                "http_status": ("Int64", column(responses, "http_status")),
                "requested_at": ("timestamp", column(responses, "requested_at")),
                "received_at": ("timestamp", column(responses, "received_at")),
                "item_count": ("Int64", column(responses, "item_count")),
                "parse_status": (TEXT, column(responses, "parse_status")),
                "error": (TEXT, column(responses, "error")),
            }
        ),
    )
    rows = [row for row, _, _ in observations]
    times = [moment for _, moment, _ in observations]
    keys = [row.item_key for row in rows]
    m = len(rows)
    _insert(
        connection,
        "price_observation",
        _frame(
            {
                "source": (TEXT, [source] * m),
                "item_key": (TEXT, keys),
                "retrieved_at": ("timestamp", times),
                "response_id": (TEXT, [response for _, _, response in observations]),
                "rental_type": (TEXT, [row.rental_type for row in rows]),
                "region": (TEXT, [row.arm_region_name for row in rows]),
                "price": ("Float64", [row.retail_price for row in rows]),
                "currency": (TEXT, ["USD"] * m),
                "price_unit": (TEXT, [row.price_unit for row in rows]),
                # GPU fields come from the Phase 3 mapping; unknown until then.
                "gpu_model": (TEXT, [None] * m),
                "gpu_count": ("Float64", [None] * m),
            }
        ),
    )
    detail: dict[str, tuple[str, list[Any]]] = {
        "source": (TEXT, [source] * m),
        "item_key": (TEXT, keys),
        "retrieved_at": ("timestamp", times),
    }
    for name, dtype in (
        ("meter_id", TEXT),
        ("sku_id", TEXT),
        ("arm_sku_name", TEXT),
        ("arm_region_name", TEXT),
        ("location", TEXT),
        ("price_type", TEXT),
        ("retail_price", "Float64"),
        ("unit_price", "Float64"),
        ("unit_of_measure", TEXT),
        ("effective_start_date", "timestamp"),
        ("product_id", TEXT),
        ("product_name", TEXT),
        ("sku_name", TEXT),
        ("meter_name", TEXT),
        ("service_name", TEXT),
        ("service_family", TEXT),
        ("is_primary_meter_region", "boolean"),
        ("reservation_term", TEXT),
        ("tier_minimum_units", "Float64"),
        ("savings_plan", TEXT),
    ):
        detail[name] = (dtype, [getattr(row, name) for row in rows])
    _insert(connection, "azure_retail_price", _frame(detail))
    r = len(repeats)
    _insert(
        connection,
        "observation_repeat",
        _frame(
            {
                "response_id": (TEXT, column(repeats, "response_id")),
                "item_index": ("Int64", column(repeats, "item_index")),
                "source": (TEXT, [source] * r),
                "item_key": (TEXT, column(repeats, "item_key")),
                "first_retrieved_at": (
                    "timestamp",
                    column(repeats, "first_retrieved_at"),
                ),
                "same_price": ("boolean", column(repeats, "same_price")),
                "same_fields": ("boolean", column(repeats, "same_fields")),
            }
        ),
    )
