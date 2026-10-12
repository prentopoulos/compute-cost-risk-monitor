"""Schema version 1 enforces the evidence rules at the storage boundary.

All rows are synthetic. The small loaders below are test scaffolding, not the Phase 2
parser.
"""

import json
import math
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import pytest

from compute_cost_risk_monitor import db

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic"
T0 = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
SHA = "0" * 64
TABLES = {
    "schema_version",
    "collection_run",
    "raw_response",
    "price_observation",
    "azure_retail_price",
    "marketplace_offer",
    "gpu_sku_map",
    "rule_set",
    "normalized_price",
}


@pytest.fixture
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    connection = db.connect()
    db.create_schema(connection)
    yield connection
    connection.close()


def add_run(
    con: duckdb.DuckDBPyConnection,
    run_id: str = "run-1",
    source: str = "azure-retail",
    label: str = "synthetic",
) -> None:
    con.execute(
        "INSERT INTO collection_run (run_id, source, data_label, started_at, status,"
        " schema_version) VALUES (?, ?, ?, ?, 'succeeded', 1)",
        [run_id, source, label, T0],
    )


def add_response(
    con: duckdb.DuckDBPyConnection,
    response_id: str = "resp-1",
    run_id: str = "run-1",
    seq: int = 0,
    sha256: str | None = SHA,
) -> None:
    con.execute(
        "INSERT INTO raw_response (response_id, run_id, seq, file_path, sha256,"
        " byte_length, request_url, http_status, requested_at, item_count,"
        " parse_status)"
        " VALUES (?, ?, ?, 'data/raw/synthetic.json.gz', ?, 10, 'https://example.test',"
        " 200, ?, 1, 'parsed')",
        [response_id, run_id, seq, sha256, T0],
    )


def observation(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "source": "azure-retail",
        "item_key": "item-1",
        "retrieved_at": T0,
        "response_id": "resp-1",
        "rental_type": "on_demand",
        "region": "eastus",
        "price": 7.0,
        "currency": "USD",
        "price_unit": "1 Hour",
        "gpu_model": "H100 NVL",
        "gpu_count": 1.0,
    }
    row.update(overrides)
    return row


def add_observation(con: duckdb.DuckDBPyConnection, **overrides: Any) -> None:
    row = observation(**overrides)
    columns = ", ".join(row)
    marks = ", ".join("?" for _ in row)
    # Column names come from the fixed dict above, never from input.
    sql = f"INSERT INTO price_observation ({columns}) VALUES ({marks})"  # noqa: S608
    con.execute(sql, list(row.values()))


@pytest.fixture
def ready(con: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyConnection:
    add_run(con)
    add_response(con)
    return con


# --- connection and schema ---


def test_connection_reports_utc(con: duckdb.DuckDBPyConnection) -> None:
    assert con.execute("SELECT current_setting('TimeZone')").fetchone() == ("UTC",)


def test_timestamptz_round_trip_is_utc(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("CREATE TEMP TABLE t (ts TIMESTAMPTZ)")
    con.execute("INSERT INTO t VALUES (?)", [T0])
    row = con.execute("SELECT ts FROM t").fetchone()
    assert row is not None
    assert row[0] == T0
    assert row[0].utcoffset().total_seconds() == 0
    frame = con.execute("SELECT ts FROM t").df()
    assert str(frame["ts"].dtype) == "datetime64[us, UTC]"
    assert frame["ts"].iloc[0] == pd.Timestamp(T0)


def test_create_schema_builds_every_table(con: duckdb.DuckDBPyConnection) -> None:
    tables = {
        row[0]
        for row in con.execute("SELECT table_name FROM duckdb_tables()").fetchall()
    }
    assert tables == TABLES
    assert con.execute("SELECT version FROM schema_version").fetchall() == [(1,)]


def test_create_schema_rerun_is_a_no_op(con: duckdb.DuckDBPyConnection) -> None:
    assert db.create_schema(con) == []
    assert con.execute("SELECT count(*) FROM schema_version").fetchone() == (1,)


# --- collection runs and raw responses ---


def test_unknown_data_label_rejected(con: duckdb.DuckDBPyConnection) -> None:
    with pytest.raises(duckdb.ConstraintException):
        add_run(con, label="stale")


def test_synthetic_marketplace_run_cannot_be_live(
    con: duckdb.DuckDBPyConnection,
) -> None:
    with pytest.raises(duckdb.ConstraintException):
        add_run(con, source="synthetic-marketplace", label="live")


@pytest.mark.parametrize("sha256", [None, "abc", "G" * 64])
def test_raw_response_needs_a_valid_sha256(
    con: duckdb.DuckDBPyConnection, sha256: str | None
) -> None:
    add_run(con)
    with pytest.raises(duckdb.ConstraintException):
        add_response(con, sha256=sha256)


def test_failed_request_is_recorded(con: duckdb.DuckDBPyConnection) -> None:
    add_run(con)
    con.execute(
        "INSERT INTO raw_response (response_id, run_id, seq, file_path, sha256,"
        " byte_length, request_url, http_status, requested_at, item_count,"
        " parse_status, error)"
        " VALUES ('resp-429', 'run-1', 0, 'data/raw/synthetic.json.gz', ?, 29,"
        " 'https://example.test', 429, ?, NULL, 'failed', 'Too Many Requests')",
        [SHA, T0],
    )
    assert con.execute(
        "SELECT http_status, parse_status FROM raw_response"
    ).fetchone() == (
        429,
        "failed",
    )


# --- price observations ---


def test_duplicate_observation_rejected(ready: duckdb.DuckDBPyConnection) -> None:
    add_observation(ready)
    with pytest.raises(duckdb.ConstraintException):
        add_observation(ready, price=8.0)


@pytest.mark.parametrize("price", [0.0, -1.0, math.nan, math.inf])
def test_non_positive_or_non_finite_price_rejected(
    ready: duckdb.DuckDBPyConnection, price: float
) -> None:
    with pytest.raises(duckdb.ConstraintException):
        add_observation(ready, price=price)


@pytest.mark.parametrize(
    "field", ["retrieved_at", "currency", "price_unit", "rental_type", "response_id"]
)
def test_missing_provenance_rejected(
    ready: duckdb.DuckDBPyConnection, field: str
) -> None:
    with pytest.raises(duckdb.ConstraintException):
        add_observation(ready, **{field: None})


def test_unknown_rental_type_rejected(ready: duckdb.DuckDBPyConnection) -> None:
    with pytest.raises(duckdb.ConstraintException):
        add_observation(ready, rental_type="bid")


def test_non_usd_currency_rejected(ready: duckdb.DuckDBPyConnection) -> None:
    with pytest.raises(duckdb.ConstraintException):
        add_observation(ready, currency="EUR")


def test_observation_needs_an_existing_raw_response(
    ready: duckdb.DuckDBPyConnection,
) -> None:
    with pytest.raises(duckdb.ConstraintException):
        add_observation(ready, response_id="no-such-response")


def test_unmapped_observation_keeps_nulls(ready: duckdb.DuckDBPyConnection) -> None:
    add_observation(ready, gpu_model=None, gpu_count=None)
    assert ready.execute(
        "SELECT gpu_model, gpu_count FROM price_observation"
    ).fetchone() == (
        None,
        None,
    )


def test_zero_gpu_count_rejected(ready: duckdb.DuckDBPyConnection) -> None:
    with pytest.raises(duckdb.ConstraintException):
        add_observation(ready, gpu_count=0.0)


# --- detail, rule and derived tables ---


def test_azure_detail_needs_an_observation(ready: duckdb.DuckDBPyConnection) -> None:
    with pytest.raises(duckdb.ConstraintException):
        ready.execute(
            "INSERT INTO azure_retail_price (source, item_key, retrieved_at, meter_id,"
            " sku_id, arm_region_name, price_type, retail_price, unit_of_measure)"
            " VALUES ('azure-retail', 'missing', ?, 'm', 's', 'eastus', 'Consumption',"
            " 7.0, '1 Hour')",
            [T0],
        )


def add_rule(con: duckdb.DuckDBPyConnection, version: str) -> None:
    con.execute(
        "INSERT INTO rule_set VALUES (?, ?, 'synthetic test rules', ?)",
        [version, T0, json.dumps({"stale_after_days": 7})],
    )


def add_normalized(con: duckdb.DuckDBPyConnection, rule_version: str) -> None:
    con.execute(
        "INSERT INTO normalized_price (source, item_key, retrieved_at, rule_version,"
        " usd_per_gpu_hour, gpu_model, gpu_count, region, rental_type, exclusions)"
        " VALUES ('azure-retail', 'item-1', ?, ?, 7.0, 'H100 NVL', 1, 'eastus',"
        " 'on_demand', 'storage, egress, licences, taxes, discounts')",
        [T0, rule_version],
    )


def test_derived_price_needs_a_known_rule_version(
    ready: duckdb.DuckDBPyConnection,
) -> None:
    add_observation(ready)
    with pytest.raises(duckdb.ConstraintException):
        add_normalized(ready, "groups-v1")


def test_one_observation_under_two_rule_versions(
    ready: duckdb.DuckDBPyConnection,
) -> None:
    add_observation(ready)
    add_rule(ready, "groups-v1")
    add_rule(ready, "groups-v2")
    add_normalized(ready, "groups-v1")
    add_normalized(ready, "groups-v2")
    assert ready.execute("SELECT count(*) FROM normalized_price").fetchone() == (2,)


# --- synthetic fixtures end to end ---


def azure_rental_type(item: dict[str, Any]) -> str:
    if item["type"] == "Reservation":
        return "reservation"
    if item["type"] == "Consumption":
        return "spot" if "Spot" in item["meterName"] else "on_demand"
    return "other"


def azure_item_key(item: dict[str, Any]) -> str:
    parts = [
        item["meterId"],
        item["skuId"],
        item["armRegionName"],
        item["type"],
        item.get("reservationTerm") or "",
        str(item["tierMinimumUnits"]),
        item["currencyCode"],
    ]
    return "|".join(parts)


def test_synthetic_azure_page_loads(con: duckdb.DuckDBPyConnection) -> None:
    page = json.loads((FIXTURES / "azure_retail_page.json").read_text(encoding="utf-8"))
    assert page["_label"] == "synthetic"
    add_run(con)
    add_response(con)
    for item in page["Items"]:
        key = azure_item_key(item)
        add_observation(
            con,
            item_key=key,
            rental_type=azure_rental_type(item),
            region=item["armRegionName"],
            price=item["retailPrice"],
            price_unit=item["unitOfMeasure"],
            gpu_model=None,
            gpu_count=None,
        )
        con.execute(
            "INSERT INTO azure_retail_price (source, item_key, retrieved_at, meter_id,"
            " sku_id, arm_sku_name, arm_region_name, location, price_type,"
            " retail_price, unit_price, unit_of_measure, effective_start_date,"
            " product_name, sku_name,"
            " meter_name, service_name, service_family, is_primary_meter_region,"
            " reservation_term, tier_minimum_units) VALUES ('azure-retail', ?, ?, ?, ?,"
            " ?, ?, ?, ?, ?, ?, ?, CAST(? AS TIMESTAMPTZ), ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                key,
                T0,
                item["meterId"],
                item["skuId"],
                item["armSkuName"],
                item["armRegionName"],
                item["location"],
                item["type"],
                item["retailPrice"],
                item["unitPrice"],
                item["unitOfMeasure"],
                item["effectiveStartDate"],
                item["productName"],
                item["skuName"],
                item["meterName"],
                item["serviceName"],
                item["serviceFamily"],
                item["isPrimaryMeterRegion"],
                item.get("reservationTerm"),
                item["tierMinimumUnits"],
            ],
        )
    counts = con.execute(
        "SELECT rental_type, count(*) FROM price_observation GROUP BY ALL ORDER BY ALL"
    ).fetchall()
    assert counts == [("on_demand", 2), ("reservation", 1), ("spot", 1)]
    assert con.execute("SELECT count(*) FROM azure_retail_price").fetchone() == (4,)


def test_synthetic_marketplace_offers_load(con: duckdb.DuckDBPyConnection) -> None:
    data = json.loads(
        (FIXTURES / "marketplace_offers.json").read_text(encoding="utf-8")
    )
    assert data["_label"] == "synthetic"
    add_run(con, run_id="run-m", source="synthetic-marketplace", label="synthetic")
    add_response(con, response_id="resp-m", run_id="run-m")
    for offer in data["offers"]:
        add_observation(
            con,
            source="synthetic-marketplace",
            item_key=offer["offer_id"],
            response_id="resp-m",
            rental_type=offer["rental_type"],
            region=offer["region"],
            price=offer["usd_per_hour"],
            price_unit="1 Hour per offer",
            gpu_model=offer["gpu_name"],
            gpu_count=float(offer["num_gpus"]),
        )
        con.execute(
            "INSERT INTO marketplace_offer"
            " VALUES ('synthetic-marketplace', ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                offer["offer_id"],
                T0,
                offer["offer_id"],
                offer["machine_id"],
                offer["gpu_name"],
                offer["num_gpus"],
                offer["gpu_vram_gb"],
                offer["country_code"],
            ],
        )
    machines = con.execute(
        "SELECT count(DISTINCT machine_id) FROM marketplace_offer"
    ).fetchone()
    assert machines == (3,)
