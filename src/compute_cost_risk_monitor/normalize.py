"""Normalize stored observations to USD per GPU-hour, or exclude each one with a reason.

Every observation gets exactly one normalized_price row per rule version (design D12).
A compared row carries USD/GPU-hour = price ÷ GPU count, with its GPU variant and count.
Every other row keeps the first reason that matches, in the rule set's order (D4, D5,
D13, D22, D24). The classifiers are pure; normalize_pending writes in one transaction.

    uv run python -m compute_cost_risk_monitor.normalize [--db PATH]

The command prints counts, never prices (D17).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import duckdb

from compute_cost_risk_monitor import checks, db, gpu_map, rules
from compute_cost_risk_monitor.collect import DEFAULT_DB

AZURE = "azure-retail"
MARKETPLACE = "synthetic-marketplace"


@dataclass(frozen=True)
class Outcome:
    """One observation's normalized_price row, apart from its keys."""

    excluded_reason: str | None
    usd_per_gpu_hour: float | None
    gpu_model: str | None
    gpu_count: float | None
    arm_sku_name: str | None  # the map row used, when the size is mapped (Azure only)


@dataclass(frozen=True)
class AzureObservation:
    arm_sku_name: str | None
    region: str
    rental_type: str
    price: float  # USD per VM for the price unit
    price_unit: str
    product_name: str | None
    snapshot_date: date  # UTC date the run started (D21)


@dataclass(frozen=True)
class MarketplaceObservation:
    rental_type: str
    price: float  # USD per offer-hour
    gpu_name_listed: str
    num_gpus: int
    gpu_vram_gb: float | None


def is_windows(product_name: str | None, params: Mapping[str, Any]) -> bool:
    """Windows when the product name's last word is a Windows suffix (D13)."""
    words = (product_name or "").split()
    return bool(words) and words[-1] in params["windows_product_suffixes"]


def retirement_date(size: str, region: str, params: Mapping[str, Any]) -> date | None:
    """Retirement date for a size in a region; None if not retired (D5, D24)."""
    for entry in params["retirements"]:
        if size in entry["sizes"]:
            day = entry["region_extensions"].get(region, entry["retired_on"])
            return date.fromisoformat(day)
    return None


def _first_reason(
    order: Sequence[str], tests: Mapping[str, Callable[[], bool]]
) -> str | None:
    # The rule set fixes the order; a reason the code does not know is an error.
    for reason in order:
        if tests[reason]():
            return reason
    return None


def classify_azure(
    observation: AzureObservation,
    mapping: Mapping[str, gpu_map.MapRow],
    params: Mapping[str, Any],
) -> Outcome:
    """Normalize one Azure observation, or exclude it with the first matching reason."""
    obs = observation
    mapped = mapping.get(obs.arm_sku_name) if obs.arm_sku_name else None
    retired = retirement_date(obs.arm_sku_name or "", obs.region, params)
    tests: dict[str, Callable[[], bool]] = {
        "rental_type_not_compared": lambda: (
            obs.rental_type not in params["compared_rental_types"]
        ),
        "government_cloud": lambda: obs.region.startswith(
            tuple(params["government_region_prefixes"])
        ),
        "windows": lambda: is_windows(obs.product_name, params),
        "unit_not_hourly": lambda: obs.price_unit != params["hourly_unit"],
        "unmapped_sku": lambda: mapped is None,
        "fractional_gpu": lambda: mapped is not None and not mapped.whole,
        "retired_size": lambda: retired is not None and retired <= obs.snapshot_date,
    }
    reason = _first_reason(params["exclusion_order"], tests)
    if mapped is None:
        return Outcome(reason, None, None, None, None)
    count = float(mapped.gpu_count)
    price = None if reason else obs.price / count
    return Outcome(reason, price, mapped.gpu_model, count, mapped.arm_sku_name)


def classify_marketplace(
    observation: MarketplaceObservation, params: Mapping[str, Any]
) -> Outcome:
    """Normalize one synthetic marketplace offer, or exclude it (D8, D22)."""
    obs = observation
    entry = params["marketplace_gpu_names"].get(obs.gpu_name_listed)
    known = entry is not None and obs.gpu_vram_gb == entry["vram_gb"]
    tests: dict[str, Callable[[], bool]] = {
        "rental_type_not_compared": lambda: (
            obs.rental_type not in params["compared_rental_types"]
        ),
        "unmapped_gpu_name": lambda: not known,
    }
    reason = _first_reason(params["marketplace_exclusion_order"], tests)
    model = entry["variant"] if known and entry is not None else None
    count = float(obs.num_gpus)
    price = None if reason else obs.price / count
    return Outcome(reason, price, model, count, None)


_AZURE_PENDING = """
SELECT p.item_key, p.retrieved_at, p.region, p.rental_type, p.price, p.price_unit,
       a.arm_sku_name, a.product_name, r.started_at
FROM price_observation p
JOIN azure_retail_price a USING (source, item_key, retrieved_at)
JOIN raw_response rr ON rr.response_id = p.response_id
JOIN collection_run r ON r.run_id = rr.run_id
WHERE p.source = 'azure-retail' AND NOT EXISTS (
    SELECT 1 FROM normalized_price n
    WHERE n.source = p.source AND n.item_key = p.item_key
      AND n.retrieved_at = p.retrieved_at AND n.rule_version = ?)
ORDER BY p.item_key, p.retrieved_at
"""

_MARKETPLACE_PENDING = """
SELECT p.item_key, p.retrieved_at, p.region, p.rental_type, p.price,
       m.gpu_name_listed, m.num_gpus, m.gpu_vram_gb
FROM price_observation p
JOIN marketplace_offer m USING (source, item_key, retrieved_at)
WHERE p.source = 'synthetic-marketplace' AND NOT EXISTS (
    SELECT 1 FROM normalized_price n
    WHERE n.source = p.source AND n.item_key = p.item_key
      AND n.retrieved_at = p.retrieved_at AND n.rule_version = ?)
ORDER BY p.item_key, p.retrieved_at
"""


@dataclass
class NormalizeResult:
    rule_version: str
    written: int
    rules_written: bool
    map_rows_written: int
    by_status: dict[str, int]  # "normalized" or a reason, over all rows of the version
    unmapped_sizes: list[str]  # Azure sizes not in the map, over all observations


def _rows(
    connection: duckdb.DuckDBPyConnection,
    params: Mapping[str, Any],
    mapping: Mapping[str, gpu_map.MapRow],
) -> list[tuple[str, str, datetime, str, str, Outcome]]:
    version = params["rule_version"]
    found: list[tuple[str, str, datetime, str, str, Outcome]] = []
    for row in connection.execute(_AZURE_PENDING, [version]).fetchall():
        key, at, region, rental, price, unit, size, product, started = row
        observation = AzureObservation(
            size, region, rental, price, unit, product, started.astimezone(UTC).date()
        )
        outcome = classify_azure(observation, mapping, params)
        found.append((AZURE, key, at, region, rental, outcome))
    for row in connection.execute(_MARKETPLACE_PENDING, [version]).fetchall():
        key, at, region, rental, price, name, gpus, vram = row
        offer = MarketplaceObservation(rental, price, name, gpus, vram)
        found.append(
            (MARKETPLACE, key, at, region, rental, classify_marketplace(offer, params))
        )
    return found


def _write(
    connection: duckdb.DuckDBPyConnection,
    params: Mapping[str, Any],
    rows: list[tuple[str, str, datetime, str, str, Outcome]],
) -> None:
    outcomes = [row[5] for row in rows]
    n = len(rows)
    db.insert_frame(
        connection,
        "normalized_price",
        db.frame(
            {
                "source": (db.TEXT, [row[0] for row in rows]),
                "item_key": (db.TEXT, [row[1] for row in rows]),
                "retrieved_at": ("timestamp", [row[2] for row in rows]),
                "rule_version": (db.TEXT, [params["rule_version"]] * n),
                "region": (db.TEXT, [row[3] for row in rows]),
                "rental_type": (db.TEXT, [row[4] for row in rows]),
                "usd_per_gpu_hour": ("Float64", [o.usd_per_gpu_hour for o in outcomes]),
                "gpu_model": (db.TEXT, [o.gpu_model for o in outcomes]),
                "gpu_count": ("Float64", [o.gpu_count for o in outcomes]),
                "mapping_version": (
                    db.TEXT,
                    [
                        params["map_version"] if o.arm_sku_name else None
                        for o in outcomes
                    ],
                ),
                "arm_sku_name": (db.TEXT, [o.arm_sku_name for o in outcomes]),
                "exclusions": (db.TEXT, [params["exclusions"]] * n),
                "excluded_reason": (db.TEXT, [o.excluded_reason for o in outcomes]),
            }
        ),
    )


def summarize(
    connection: duckdb.DuckDBPyConnection, rule_version: str
) -> tuple[dict[str, int], list[str]]:
    """Rows by status under a rule version, and Azure sizes the map does not hold."""
    status = connection.execute(
        "SELECT coalesce(excluded_reason, 'normalized'), count(*) FROM normalized_price"
        " WHERE rule_version = ? GROUP BY 1 ORDER BY 1",
        [rule_version],
    ).fetchall()
    unmapped = connection.execute(
        "SELECT DISTINCT a.arm_sku_name FROM normalized_price n"
        " JOIN azure_retail_price a USING (source, item_key, retrieved_at)"
        " WHERE n.rule_version = ? AND n.arm_sku_name IS NULL ORDER BY 1",
        [rule_version],
    ).fetchall()
    return {name: count for name, count in status}, [row[0] for row in unmapped]


def normalize_pending(
    connection: duckdb.DuckDBPyConnection,
    now: datetime,
    params: Mapping[str, Any] | None = None,
    mapping: Mapping[str, gpu_map.MapRow] | None = None,
) -> NormalizeResult:
    """Store the rules and map, then normalize every observation lacking a row.

    Runs in one transaction: on any error, nothing of this call stays.
    """
    params = rules.GROUPS_V1 if params is None else params
    mapping = gpu_map.load() if mapping is None else mapping
    db.create_schema(connection)
    connection.begin()
    try:
        rules_written = rules.store(connection, now, dict(params))
        map_written = gpu_map.store(connection, dict(mapping), params["map_version"])
        rows = _rows(connection, params, mapping)
        _write(connection, params, rows)
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    by_status, unmapped = summarize(connection, params["rule_version"])
    return NormalizeResult(
        params["rule_version"],
        len(rows),
        rules_written,
        map_written,
        by_status,
        unmapped,
    )


def report(result: NormalizeResult, verdicts: list[checks.Verdict]) -> None:
    """Counts only: never a price or USD/GPU-hour value (D17)."""
    total = sum(result.by_status.values())
    print(f"rule set {result.rule_version}: {result.written} new rows, {total} in all")
    if result.rules_written or result.map_rows_written:
        print(
            f"  stored now: rule set {'yes' if result.rules_written else 'no'},"
            f" map rows {result.map_rows_written}"
        )
    for status, count in sorted(result.by_status.items(), key=lambda item: -item[1]):
        print(f"  {status}: {count}")
    print(f"  Azure sizes not in the map: {len(result.unmapped_sizes)}")
    for verdict in verdicts:
        state = "pass" if verdict.passed else "FAIL"
        print(f"check {verdict.name}: {state} ({verdict.checked} rows checked)")
        for failure in verdict.failures:
            print(f"    {failure}")


def main(argv: Sequence[str] | None = None, *, now: datetime | None = None) -> int:
    """Run the command: 0 when checks pass, 1 if a check fails, 2 when refused.

    Refused means nothing was written: a changed frozen row, a bad map file, or a
    database that cannot be opened or written.
    """
    parser = argparse.ArgumentParser(
        prog="python -m compute_cost_risk_monitor.normalize",
        description="Normalize stored prices to USD per GPU-hour under groups-v1.",
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="DuckDB file")
    args = parser.parse_args(argv)
    if not args.db.is_file():
        print(f"refused: no database at {args.db}", file=sys.stderr)
        return 2
    try:
        connection = db.connect(args.db)
    except duckdb.Error as error:
        print(f"refused: cannot open {args.db}: {error}", file=sys.stderr)
        return 2
    try:
        try:
            result = normalize_pending(connection, now or datetime.now(UTC))
        except (rules.FrozenMismatch, gpu_map.MapError, duckdb.Error) as error:
            print(f"refused: {error}", file=sys.stderr)
            return 2
        verdicts = checks.run(connection, result.rule_version)
    finally:
        connection.close()
    report(result, verdicts)
    return 0 if all(verdict.passed for verdict in verdicts) else 1


if __name__ == "__main__":
    sys.exit(main())
