"""Schema versions 1 and 2 enforce the evidence rules at the storage boundary.

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
    "collection_run_summary",
    "collection_run_tally",
    "observation_repeat",
}
VERSIONS = [(1,), (2,)]


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
    source: str = "azure-retail",
) -> None:
    con.execute(
        "INSERT INTO raw_response (response_id, run_id, source, seq, file_path, sha256,"
        " byte_length, request_url, http_status, requested_at, item_count,"
        " parse_status)"
        " VALUES (?, ?, ?, ?, 'data/raw/synthetic.json.gz', ?, 10,"
        " 'https://example.test', 200, ?, 1, 'parsed')",
        [response_id, run_id, source, seq, sha256, T0],
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


def test_read_only_connection_is_utc_and_cannot_write(tmp_path: Path) -> None:
    path = tmp_path / "monitor.duckdb"
    writer = db.connect(path)
    db.create_schema(writer)
    writer.close()
    reader = db.connect(path, read_only=True)
    try:
        assert reader.execute("SELECT current_setting('TimeZone')").fetchone() == (
            "UTC",
        )
        assert db.applied_versions(reader)
        with pytest.raises(duckdb.InvalidInputException, match="read-only"):
            reader.execute("CREATE TABLE t (x INTEGER)")
    finally:
        reader.close()
    # Once the reader is closed, a writer can open the file again.
    db.connect(path).close()


def test_read_only_connection_refuses_a_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "absent" / "monitor.duckdb"
    with pytest.raises(duckdb.IOException):
        db.connect(path, read_only=True)
    assert not path.parent.exists()


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
    query = "SELECT version FROM schema_version ORDER BY version"
    assert con.execute(query).fetchall() == VERSIONS


def test_create_schema_rerun_is_a_no_op(con: duckdb.DuckDBPyConnection) -> None:
    assert db.create_schema(con) == []
    assert con.execute(
        "SELECT version, count(*) FROM schema_version GROUP BY version ORDER BY version"
    ).fetchall() == [(1, 1), (2, 1)]


def test_upgrade_from_version_1_applies_only_version_2() -> None:
    connection = db.connect()
    version, description, sql = db.migrations()[0]
    assert version == 1
    connection.execute(sql)
    connection.execute(
        "INSERT INTO schema_version VALUES (?, ?, ?)", [version, T0, description]
    )
    add_run(connection)
    assert db.create_schema(connection) == [2]
    assert connection.execute("SELECT run_id FROM collection_run").fetchall() == [
        ("run-1",)
    ]
    connection.close()


def test_duplicate_schema_versions_rejected() -> None:
    files = [("002_a.sql", "SELECT 1"), ("002_b.sql", "SELECT 2")]
    with pytest.raises(ValueError, match="share version 002"):
        db.parse_migrations(files)


def test_parse_migrations_orders_and_ignores_other_files() -> None:
    files = [("010_b.sql", "B"), ("README.md", "x"), ("002_a_b.sql", "A")]
    assert db.parse_migrations(files) == [(2, "a b", "A"), (10, "b", "B")]


def test_temp_schema_version_table_does_not_count_as_applied() -> None:
    connection = db.connect()
    connection.execute("CREATE TEMP TABLE schema_version (version INTEGER)")
    connection.execute("INSERT INTO schema_version VALUES (1)")
    assert db.applied_versions(connection) == set()
    connection.close()


def test_applied_versions_reads_this_database(con: duckdb.DuckDBPyConnection) -> None:
    assert db.applied_versions(con) == {1, 2}


def test_create_schema_refuses_an_open_transaction() -> None:
    connection = db.connect()
    connection.begin()
    with pytest.raises(RuntimeError, match="outside one"):
        db.create_schema(connection)
    connection.close()


# --- collection runs and raw responses ---


def test_run_schema_version_must_exist(con: duckdb.DuckDBPyConnection) -> None:
    with pytest.raises(duckdb.ConstraintException):
        con.execute(
            "INSERT INTO collection_run (run_id, source, data_label, started_at,"
            " status, schema_version) VALUES ('r', 'azure-retail', 'live', ?,"
            " 'succeeded', 99)",
            [T0],
        )


def test_response_source_must_match_its_run(con: duckdb.DuckDBPyConnection) -> None:
    add_run(con, label="live")
    with pytest.raises(duckdb.ConstraintException):
        add_response(con, source="synthetic-marketplace")


def test_observation_source_must_match_its_run(con: duckdb.DuckDBPyConnection) -> None:
    # A live Azure run cannot carry synthetic marketplace prices.
    add_run(con, label="live")
    add_response(con)
    with pytest.raises(duckdb.ConstraintException):
        add_observation(con, source="synthetic-marketplace")


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
        "INSERT INTO raw_response (response_id, run_id, source, seq, file_path,"
        " sha256, byte_length, request_url, http_status, requested_at, item_count,"
        " parse_status, error)"
        " VALUES ('resp-429', 'run-1', 'azure-retail', 0,"
        " 'data/raw/synthetic.json.gz', ?, 29,"
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


def test_azure_detail_must_agree_with_its_observation(
    ready: duckdb.DuckDBPyConnection,
) -> None:
    add_observation(ready)
    with pytest.raises(duckdb.ConstraintException):
        ready.execute(
            "INSERT INTO azure_retail_price (source, item_key, retrieved_at, meter_id,"
            " sku_id, arm_region_name, price_type, retail_price, unit_of_measure)"
            " VALUES ('azure-retail', 'item-1', ?, 'm', 's', 'westus', 'Consumption',"
            " 6.5, '1 Hour')",
            [T0],
        )


@pytest.mark.parametrize(
    ("table", "column", "value"),
    [
        ("gpu_sku_map", "gpu_vram_gb", math.nan),
        ("gpu_sku_map", "gpu_vram_gb", math.inf),
        ("marketplace_offer", "gpu_vram_gb", math.nan),
        ("azure_retail_price", "tier_minimum_units", math.nan),
        ("azure_retail_price", "unit_price", -1.0),
    ],
)
def test_non_finite_or_negative_attributes_rejected(
    ready: duckdb.DuckDBPyConnection, table: str, column: str, value: float
) -> None:
    if table == "gpu_sku_map":
        sql = (
            "INSERT INTO gpu_sku_map (mapping_version, arm_sku_name, gpu_model,"
            " gpu_count, source_url, gpu_vram_gb) VALUES ('m1', 'S', 'H100', 1,"
            " 'https://example.test', ?)"
        )
    elif table == "marketplace_offer":
        add_run(ready, run_id="run-m", source="synthetic-marketplace")
        add_response(
            ready, response_id="resp-m", run_id="run-m", source="synthetic-marketplace"
        )
        add_observation(ready, source="synthetic-marketplace", response_id="resp-m")
        sql = (
            "INSERT INTO marketplace_offer (source, item_key, retrieved_at, offer_id,"
            " machine_id, gpu_name_listed, num_gpus, gpu_vram_gb)"
            " VALUES ('synthetic-marketplace', 'item-1', ?, 'o', 'm', 'H100', 1, ?)"
        )
    else:
        add_observation(ready)
        azure_sql = {
            "tier_minimum_units": (
                "INSERT INTO azure_retail_price (source, item_key, retrieved_at,"
                " meter_id, sku_id, arm_region_name, price_type, retail_price,"
                " unit_of_measure, tier_minimum_units) VALUES ('azure-retail',"
                " 'item-1', ?, 'm', 's', 'eastus', 'Consumption', 7.0, '1 Hour', ?)"
            ),
            "unit_price": (
                "INSERT INTO azure_retail_price (source, item_key, retrieved_at,"
                " meter_id, sku_id, arm_region_name, price_type, retail_price,"
                " unit_of_measure, unit_price) VALUES ('azure-retail', 'item-1', ?,"
                " 'm', 's', 'eastus', 'Consumption', 7.0, '1 Hour', ?)"
            ),
        }
        sql = azure_sql[column]
    params = [value] if table == "gpu_sku_map" else [T0, value]
    with pytest.raises(duckdb.ConstraintException):
        ready.execute(sql, params)


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


def test_excluded_row_is_stored_without_a_price(
    ready: duckdb.DuckDBPyConnection,
) -> None:
    add_observation(ready, gpu_model=None, gpu_count=None)
    add_rule(ready, "groups-v1")
    ready.execute(
        "INSERT INTO normalized_price (source, item_key, retrieved_at, rule_version,"
        " region, rental_type, exclusions, excluded_reason) VALUES ('azure-retail',"
        " 'item-1', ?, 'groups-v1', 'eastus', 'on_demand', 'n/a', 'unmapped SKU')",
        [T0],
    )
    row = ready.execute(
        "SELECT usd_per_gpu_hour, excluded_reason FROM normalized_price"
    ).fetchone()
    assert row == (None, "unmapped SKU")


def test_excluded_row_cannot_carry_a_price(ready: duckdb.DuckDBPyConnection) -> None:
    add_observation(ready)
    add_rule(ready, "groups-v1")
    with pytest.raises(duckdb.ConstraintException):
        ready.execute(
            "INSERT INTO normalized_price (source, item_key, retrieved_at,"
            " rule_version, region, rental_type, usd_per_gpu_hour, gpu_model,"
            " gpu_count, exclusions, excluded_reason) VALUES ('azure-retail',"
            " 'item-1', ?, 'groups-v1', 'eastus', 'on_demand', 7.0, 'H100 NVL', 1,"
            " 'n/a', 'unmapped SKU')",
            [T0],
        )


@pytest.mark.parametrize(
    ("region", "rental_type"), [("westus", "on_demand"), ("eastus", "bogus")]
)
def test_derived_group_key_must_match_its_observation(
    ready: duckdb.DuckDBPyConnection, region: str, rental_type: str
) -> None:
    add_observation(ready)
    add_rule(ready, "groups-v1")
    with pytest.raises(duckdb.ConstraintException):
        ready.execute(
            "INSERT INTO normalized_price (source, item_key, retrieved_at,"
            " rule_version, region, rental_type, usd_per_gpu_hour, gpu_model,"
            " gpu_count, exclusions) VALUES ('azure-retail', 'item-1', ?,"
            " 'groups-v1', ?, ?, 7.0, 'H100 NVL', 1, 'storage')",
            [T0, region, rental_type],
        )


def test_derived_price_must_use_an_existing_mapping(
    ready: duckdb.DuckDBPyConnection,
) -> None:
    add_observation(ready)
    add_rule(ready, "groups-v1")
    with pytest.raises(duckdb.ConstraintException):
        ready.execute(
            "INSERT INTO normalized_price (source, item_key, retrieved_at,"
            " rule_version, region, rental_type, usd_per_gpu_hour, gpu_model,"
            " gpu_count, mapping_version, arm_sku_name, exclusions)"
            " VALUES ('azure-retail', 'item-1', ?, 'groups-v1', 'eastus',"
            " 'on_demand', 7.0, 'H100 NVL', 1, 'nomap', 'Standard_X', 'storage')",
            [T0],
        )


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
    add_response(
        con, response_id="resp-m", run_id="run-m", source="synthetic-marketplace"
    )
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


# --- version 2: insert-only run records ---


def test_referenced_run_cannot_be_updated(ready: duckdb.DuckDBPyConnection) -> None:
    # DuckDB 1.5.6 limit that makes run records write-once. If this starts passing,
    # revisit design D9 of phase-2-collector.
    with pytest.raises(duckdb.ConstraintException, match="foreign key"):
        ready.execute("UPDATE collection_run SET status = 'partial'")


def test_reservation_with_term_unit_accepted(ready: duckdb.DuckDBPyConnection) -> None:
    add_observation(
        ready,
        rental_type="reservation",
        region="westeurope",
        price=25007.0,
        price_unit="1 Year term",
        gpu_model=None,
        gpu_count=None,
    )
    ready.execute(
        "INSERT INTO azure_retail_price (source, item_key, retrieved_at, meter_id,"
        " sku_id, arm_region_name, price_type, retail_price, unit_of_measure,"
        " reservation_term) VALUES ('azure-retail', 'item-1', ?, 'm', 's',"
        " 'westeurope', 'Reservation', 25007.0, '1 Hour', '1 Year')",
        [T0],
    )
    assert ready.execute(
        "SELECT o.price_unit, a.unit_of_measure FROM price_observation o"
        " JOIN azure_retail_price a USING (source, item_key, retrieved_at)"
    ).fetchone() == ("1 Year term", "1 Hour")


def summary(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "run_id": "run-1",
        "source": "azure-retail",
        "requests": 3,
        "pages_parsed": 2,
        "failed_requests": 1,
        "throttled": 1,
        "items_seen": 10,
        "observations_stored": 7,
        "repeats": 1,
        "out_of_scope": 1,
        "rejected": 1,
        "stop_reason": "completed",
    }
    row.update(overrides)
    return row


def add_summary(con: duckdb.DuckDBPyConnection, **overrides: Any) -> None:
    row = summary(**overrides)
    columns = ", ".join(row)
    marks = ", ".join("?" for _ in row)
    # Column names come from the fixed dict above, never from input.
    sql = f"INSERT INTO collection_run_summary ({columns}) VALUES ({marks})"  # noqa: S608
    con.execute(sql, list(row.values()))


def test_summary_accepted(ready: duckdb.DuckDBPyConnection) -> None:
    add_summary(ready)
    assert ready.execute("SELECT count(*) FROM collection_run_summary").fetchone() == (
        1,
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"observations_stored": 6},  # 6 + 1 + 1 + 1 != 10
        {"requests": -1, "pages_parsed": -1, "failed_requests": 0, "throttled": 0},
        {"pages_parsed": 3},  # 3 + 1 != 3 requests
        {"throttled": 2},  # more 429s than failures
        {"stop_reason": ""},
        {"run_id": "no-such-run"},
        {"source": "synthetic-marketplace"},
    ],
)
def test_bad_summary_rejected(
    ready: duckdb.DuckDBPyConnection, overrides: dict[str, Any]
) -> None:
    with pytest.raises(duckdb.ConstraintException):
        add_summary(ready, **overrides)


def add_tally(
    con: duckdb.DuckDBPyConnection, kind: str, reason: str, occurrences: int
) -> None:
    con.execute(
        "INSERT INTO collection_run_tally VALUES ('run-1', 'azure-retail', ?, ?, ?)",
        [kind, reason, occurrences],
    )


def test_tallies_accepted_once_per_reason(ready: duckdb.DuckDBPyConnection) -> None:
    add_tally(ready, "rejected", "non_positive_price", 2)
    add_tally(ready, "flagged", "shared_meter_key", 1)
    with pytest.raises(duckdb.ConstraintException):
        add_tally(ready, "rejected", "non_positive_price", 1)


@pytest.mark.parametrize(
    ("kind", "reason", "occurrences"),
    [("warning", "x", 1), ("rejected", "x", 0), ("rejected", "", 1)],
)
def test_bad_tally_rejected(
    ready: duckdb.DuckDBPyConnection, kind: str, reason: str, occurrences: int
) -> None:
    with pytest.raises(duckdb.ConstraintException):
        add_tally(ready, kind, reason, occurrences)


def add_repeat(
    con: duckdb.DuckDBPyConnection,
    response_id: str = "resp-2",
    item_key: str = "item-1",
    first_retrieved_at: datetime = T0,
) -> None:
    con.execute(
        "INSERT INTO observation_repeat"
        " VALUES (?, 4, 'azure-retail', ?, ?, false, true)",
        [response_id, item_key, first_retrieved_at],
    )


def test_repeat_recorded(ready: duckdb.DuckDBPyConnection) -> None:
    add_observation(ready)
    add_response(ready, response_id="resp-2", seq=1)
    add_repeat(ready)
    assert ready.execute(
        "SELECT response_id, item_index, same_price, same_fields"
        " FROM observation_repeat"
    ).fetchone() == ("resp-2", 4, False, True)


@pytest.mark.parametrize(
    "overrides",
    [
        {"item_key": "no-such-item"},
        {"first_retrieved_at": datetime(2026, 1, 1, tzinfo=UTC)},
        {"response_id": "no-such-response"},
    ],
)
def test_repeat_needs_its_response_and_observation(
    ready: duckdb.DuckDBPyConnection, overrides: dict[str, Any]
) -> None:
    add_observation(ready)
    add_response(ready, response_id="resp-2", seq=1)
    with pytest.raises(duckdb.ConstraintException):
        add_repeat(ready, **overrides)


def test_failed_migration_rolls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = db.connect()
    broken = [(1, "broken", "CREATE TABLE half_done (a INTEGER); NOT VALID SQL")]
    monkeypatch.setattr(db, "migrations", lambda: broken)
    with pytest.raises(duckdb.ParserException):
        db.create_schema(connection)
    tables = connection.execute(
        "SELECT table_name FROM information_schema.tables"
    ).fetchall()
    assert ("half_done",) not in tables
    connection.close()
