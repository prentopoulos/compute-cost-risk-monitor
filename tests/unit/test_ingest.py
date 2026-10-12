"""Ingest builds a run's records from its kept files, checked against known answers.

Every run here is synthetic: scripted responses go through the real fetch loop, then
ingest, and the results are checked independently of the code that produced them.
"""

import gzip
import hashlib
import json
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import duckdb
import pytest

from compute_cost_risk_monitor import azure_retail as az
from compute_cost_risk_monitor import db, fetch, ingest, raw_store
from support import collect, item, next_link, ok, page_bytes, status

# Items for the three-page run. A and C share a meter but not a size.
A = item()
B = item(
    meterId="00000000-0000-0000-0000-00000000000b",
    skuId="SYNTH0001/000B",
    meterName="NC40ads H100 v5 Spot",
    skuName="NC40ads H100 v5 Spot",
    retailPrice=2.5,
    unitPrice=2.5,
)
NP = item(armSkuName="Standard_NP20s", meterName="NP20s", skuName="NP20s")
ZERO = item(meterId="00000000-0000-0000-0000-00000000000f", retailPrice=0.0)
R = item(
    type="Reservation",
    reservationTerm="1 Year",
    retailPrice=25007.0,
    unitPrice=25007.0,
    skuId="SYNTH0001/000R",
)
C = item(armSkuName="Standard_NC40ads_H100_v5_Alt")
D = {
    key: value
    for key, value in item(
        meterId="00000000-0000-0000-0000-00000000000d", skuId="SYNTH0002/000D"
    ).items()
    if key not in {"unitPrice", "effectiveStartDate", "location", "productName"}
}
B_LATER = {**B, "retailPrice": 2.75, "unitPrice": 2.75}
E = item(
    meterId="00000000-0000-0000-0000-00000000000e",
    type="DevTestConsumption",
    skuId="SYNTH0001/000E",
)


def three_pages() -> list[fetch.Response | BaseException]:
    return [
        ok(page_bytes([A, B, NP, ZERO, R], next_link(1000))),
        status(429, "Too Many Requests", ("Retry-After", "3")),
        ok(page_bytes([A, C, D], next_link(2000))),
        ok(page_bytes([B_LATER, E])),
    ]


@pytest.fixture
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    connection = db.connect()
    yield connection
    connection.close()


def run_and_ingest(
    raw_root: Path,
    con: duckdb.DuckDBPyConnection,
    responses: Sequence[fetch.Response | BaseException],
) -> ingest.IngestResult:
    result, _, _ = collect(raw_root, responses)
    return ingest.ingest_run(con, raw_root, result.run_id)


def one(con: duckdb.DuckDBPyConnection, sql: str) -> Any:
    row = con.execute(sql).fetchone()
    assert row is not None
    return row[0] if len(row) == 1 else row


def test_three_page_run_known_answers(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    result = run_and_ingest(tmp_path, con, three_pages())
    assert (result.status, result.stop_reason, result.data_label) == (
        "succeeded",
        "completed",
        "synthetic",
    )
    assert one(
        con,
        "SELECT requests, pages_parsed, failed_requests, throttled, items_seen,"
        " observations_stored, repeats, out_of_scope, rejected, stop_reason"
        " FROM collection_run_summary",
    ) == (4, 3, 1, 1, 10, 6, 2, 1, 1, "completed")
    assert con.execute(
        "SELECT kind, reason, occurrences FROM collection_run_tally ORDER BY ALL"
    ).fetchall() == [
        ("flagged", "shared_meter_key", 1),
        ("rejected", "non_positive_price", 1),
    ]
    rental = con.execute(
        "SELECT a.meter_id, a.arm_sku_name, o.rental_type, o.price, o.price_unit"
        " FROM price_observation o JOIN azure_retail_price a"
        " USING (source, item_key, retrieved_at) ORDER BY ALL"
    ).fetchall()
    short = [
        (m[-1], sku[-3:], kind, price, unit) for m, sku, kind, price, unit in rental
    ]
    assert short == [
        ("1", "_v5", "on_demand", 7.0, "1 Hour"),
        ("1", "_v5", "reservation", 25007.0, "1 Year term"),
        ("1", "Alt", "on_demand", 7.0, "1 Hour"),
        ("b", "_v5", "spot", 2.5, "1 Hour"),
        ("d", "_v5", "on_demand", 7.0, "1 Hour"),
        ("e", "_v5", "dev_test", 7.0, "1 Hour"),
    ]
    assert con.execute(
        "SELECT r.response_id, r.item_index, o.price, r.same_price, r.same_fields"
        " FROM observation_repeat r JOIN price_observation o"
        " ON o.source = r.source AND o.item_key = r.item_key"
        " AND o.retrieved_at = r.first_retrieved_at ORDER BY ALL"
    ).fetchall() == [
        (f"{result.run_id}-0002", 0, 7.0, True, True),
        (f"{result.run_id}-0003", 0, 2.5, False, False),
    ]
    run = one(
        con, "SELECT data_label, status, finished_at IS NOT NULL FROM collection_run"
    )
    assert run == ("synthetic", "succeeded", True)


def test_missing_values_stay_null(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    run_and_ingest(tmp_path, con, three_pages())
    assert one(
        con,
        "SELECT unit_price, effective_start_date, location, product_name, gpu_model,"
        " gpu_count FROM azure_retail_price JOIN price_observation"
        " USING (source, item_key, retrieved_at)"
        " WHERE meter_id LIKE '%d'",
    ) == (None, None, None, None, None, None)
    assert (
        one(con, "SELECT count(*) FROM azure_retail_price WHERE isnan(unit_price)") == 0
    )


def test_every_observation_traces_to_its_kept_bytes(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    # Independent of ingest: re-read each file, re-hash it and find the item in it.
    run_and_ingest(tmp_path, con, three_pages())
    rows = con.execute(
        "SELECT o.item_key, o.price, o.retrieved_at, r.file_path, r.sha256,"
        " r.received_at FROM price_observation o JOIN raw_response r"
        " USING (response_id, source)"
    ).fetchall()
    assert len(rows) == 6
    for key, price, retrieved_at, file_path, sha256, received_at in rows:
        body = gzip.decompress((tmp_path / file_path).read_bytes())
        assert hashlib.sha256(body).hexdigest() == sha256
        assert retrieved_at == received_at
        meter_id, sku_id, *_, sku_name = key.split("|")
        matches = [
            entry
            for entry in json.loads(body)["Items"]
            if entry["meterId"] == meter_id
            and entry["skuId"] == sku_id
            and entry["armSkuName"] == sku_name
        ]
        assert matches and matches[0]["retailPrice"] == price


def test_accounting_identity_holds_in_the_database(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    run_and_ingest(tmp_path, con, three_pages())
    stored = one(con, "SELECT count(*) FROM price_observation")
    repeats = one(con, "SELECT count(*) FROM observation_repeat")
    items = one(con, "SELECT sum(item_count) FROM raw_response")
    rejected = one(
        con, "SELECT sum(occurrences) FROM collection_run_tally WHERE kind = 'rejected'"
    )
    out_of_scope = one(con, "SELECT out_of_scope FROM collection_run_summary")
    assert items == stored + repeats + rejected + out_of_scope == 10


def test_response_rows_record_every_attempt(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    result = run_and_ingest(tmp_path, con, three_pages())
    assert con.execute(
        "SELECT seq, http_status, parse_status, item_count, error FROM raw_response"
        " ORDER BY seq"
    ).fetchall() == [
        (0, 200, "parsed", 5, None),
        (1, 429, "not_parsed", None, "HTTP 429 Too Many Requests"),
        (2, 200, "parsed", 3, None),
        (3, 200, "parsed", 2, None),
    ]
    assert one(con, "SELECT count(DISTINCT run_id) FROM raw_response") == 1
    assert one(con, "SELECT run_id FROM raw_response LIMIT 1") == result.run_id


def test_partial_run_keeps_what_was_parsed(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    responses = [ok(page_bytes([A, B], next_link(1000))), *[status(503)] * 5]
    result = run_and_ingest(tmp_path, con, responses)
    assert (result.status, result.stop_reason) == ("partial", "retries_exhausted")
    assert one(con, "SELECT count(*) FROM price_observation") == 2
    assert one(con, "SELECT count(*) FROM raw_response") == 6
    assert one(con, "SELECT status FROM collection_run") == "partial"


def test_failed_run_is_recorded(tmp_path: Path, con: duckdb.DuckDBPyConnection) -> None:
    result = run_and_ingest(tmp_path, con, [status(503)] * 5)
    assert (result.status, result.summary.pages_parsed) == ("failed", 0)
    assert one(con, "SELECT count(*) FROM price_observation") == 0
    assert con.execute("SELECT DISTINCT parse_status FROM raw_response").fetchall() == [
        ("not_parsed",)
    ]


def test_interrupted_run_is_partial(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    responses: list[fetch.Response | BaseException] = [
        ok(page_bytes([A], next_link(1000))),
        KeyboardInterrupt(),
    ]
    result = run_and_ingest(tmp_path, con, responses)
    assert (result.status, result.stop_reason) == ("partial", "interrupted")


def test_unparseable_and_failed_transport_attempts(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    responses = [
        ok(b"<html>busy</html>"),
        fetch.Response(None, "", [], b"", "TimeoutError: timed out"),
        ok(page_bytes([A])),
    ]
    run_and_ingest(tmp_path, con, responses)
    assert con.execute(
        "SELECT parse_status, http_status, error FROM raw_response ORDER BY seq"
    ).fetchall() == [
        ("failed", 200, "not a valid page"),
        ("not_parsed", None, "TimeoutError: timed out"),
        ("parsed", 200, None),
    ]


def test_crashed_run_restored_under_its_own_id(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    result, _, _ = collect(tmp_path, three_pages())
    # A hard kill leaves no end manifest (simulated by removing it).
    (result.folder / f"{result.run_id}.end.json").unlink()
    restored = ingest.ingest_run(con, tmp_path, result.run_id)
    assert (restored.run_id, restored.stop_reason, restored.status) == (
        result.run_id,
        "no_end_manifest",
        "partial",
    )
    assert one(con, "SELECT data_label, finished_at FROM collection_run") == (
        "synthetic",
        None,
    )


def test_tampered_body_refused_and_nothing_written(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    result, _, _ = collect(tmp_path, three_pages())
    body = result.folder / f"{result.run_id}-0002.json.gz"
    body.unlink()
    body.write_bytes(raw_store.compress(page_bytes([A])))
    with pytest.raises(raw_store.IntegrityError, match="does not match"):
        ingest.ingest_run(con, tmp_path, result.run_id)
    assert one(con, "SELECT count(*) FROM collection_run") == 0


def test_run_ingested_twice_refused(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    result = run_and_ingest(tmp_path, con, three_pages())
    with pytest.raises(ingest.AlreadyIngested):
        ingest.ingest_run(con, tmp_path, result.run_id)
    assert one(con, "SELECT count(*) FROM price_observation") == 6


def test_failed_write_leaves_nothing_behind(
    tmp_path: Path, con: duckdb.DuckDBPyConnection, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, _, _ = collect(tmp_path, three_pages())
    real_insert = ingest._insert

    def failing_insert(
        connection: duckdb.DuckDBPyConnection, table: str, frame: Any
    ) -> None:
        if table == "azure_retail_price":
            raise RuntimeError("disk full (simulated)")
        real_insert(connection, table, frame)

    monkeypatch.setattr(ingest, "_insert", failing_insert)
    with pytest.raises(RuntimeError, match="simulated"):
        ingest.ingest_run(con, tmp_path, result.run_id)
    for table in ("collection_run", "raw_response", "price_observation"):
        assert one(con, f"SELECT count(*) FROM {table}") == 0  # noqa: S608
    assert (result.folder / f"{result.run_id}.end.json").exists()


def test_flags_for_dropped_link_parameters_and_orphans(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    bare = (
        "https://prices.azure.com:443/api/retail/prices"
        "?$filter=serviceName%20eq%20%27Virtual%20Machines%27&$skip=1000"
    )
    result, _, _ = collect(tmp_path, [ok(page_bytes([A], bare)), ok(page_bytes([B]))])
    raw_store.write_once(
        result.folder / f"{result.run_id}-0099.json.gz", raw_store.compress(b"{}")
    )
    restored = ingest.ingest_run(con, tmp_path, result.run_id)
    assert restored.tallies == {
        ("flagged", "next_link_missing_params"): 1,
        ("flagged", "orphan_body_file"): 1,
    }


def test_schema_is_created_on_a_fresh_database(tmp_path: Path) -> None:
    result, _, _ = collect(tmp_path, [ok(page_bytes([A]))])
    connection = db.connect(tmp_path / "fresh.duckdb")
    ingest.ingest_run(connection, tmp_path, result.run_id)
    assert db.applied_versions(connection) == {1, 2}
    connection.close()


def test_run_status_rules() -> None:
    assert ingest.run_status("completed", 3) == "succeeded"
    assert ingest.run_status("completed", 0) == "failed"
    assert ingest.run_status("page_cap", 200) == "partial"
    assert ingest.run_status("no_end_manifest", 0) == "failed"


def test_item_fixture_is_the_shared_base() -> None:
    assert az.classify(A).outcome == "stored"
