"""Synthetic Azure-shaped snapshots stored as synthetic runs (Phase 4 design D7, D29).

Every file here is synthetic: Azure-shaped items with invented prices, built from the
base item in tests/fixtures/synthetic/azure_items.json.
"""

import copy
import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import duckdb
import pytest

from compute_cost_risk_monitor import synthetic
from seed import database
from support import BASE_ITEM, FIXTURES

OBSERVED = "2026-10-12T09:00:00+00:00"


@pytest.fixture
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    connection = database()
    yield connection
    connection.close()


def item(**changes: Any) -> dict[str, Any]:
    value = copy.deepcopy(BASE_ITEM)
    value.update(changes)
    return value


def page(items: list[dict[str, Any]], **changes: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "_label": "synthetic",
        "observed_at": OBSERVED,
        "Items": items,
        "NextPageLink": None,
    }
    doc.update(changes)
    return doc


def write(tmp_path: Path, doc: dict[str, Any], name: str = "azure.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def one(con: duckdb.DuckDBPyConnection, sql: str) -> Any:
    row = con.execute(sql).fetchone()
    assert row is not None
    return row[0]


TWO = [
    item(),
    item(
        meterId="00000000-0000-0000-0000-000000000002",
        skuId="SYNTH0001/0002",
        armRegionName="westeurope",
        location="EU West",
    ),
]


def test_snapshot_stored_as_a_synthetic_azure_run(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    path = write(tmp_path, page(TWO))
    run_id = synthetic.ingest_azure_snapshot(con, path, repo=tmp_path)
    assert con.execute(
        "SELECT source, data_label, status FROM collection_run"
    ).fetchall() == [("azure-retail", "synthetic", "succeeded")]
    assert one(con, "SELECT count(*) FROM azure_retail_price") == 2
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert con.execute(
        "SELECT DISTINCT rr.run_id, rr.sha256, rr.file_path, rr.request_url"
        " FROM price_observation p JOIN raw_response rr"
        " ON rr.response_id = p.response_id"
    ).fetchall() == [(run_id, digest, "azure.json", "file:azure.json")]
    assert con.execute(
        "SELECT items_seen, observations_stored, repeats, rejected, stop_reason"
        " FROM collection_run_summary"
    ).fetchall() == [(2, 2, 0, 0, "completed")]


def test_same_row_rules_as_live_ingest(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    secondary = item(
        meterId="00000000-0000-0000-0000-000000000003", isPrimaryMeterRegion=False
    )
    path = write(tmp_path, page([*TWO, TWO[0], secondary]))
    synthetic.ingest_azure_snapshot(con, path, repo=tmp_path)
    assert con.execute(
        "SELECT kind, reason, occurrences FROM collection_run_tally"
    ).fetchall() == [("rejected", "not_primary_meter", 1)]
    assert con.execute(
        "SELECT items_seen, observations_stored, repeats, rejected"
        " FROM collection_run_summary"
    ).fetchall() == [(4, 2, 1, 1)]
    assert one(con, "SELECT count(*) FROM observation_repeat") == 1


@pytest.mark.parametrize(
    ("changes", "why"),
    [
        ({"_label": "live"}, "not labelled"),
        ({"observed_at": "yesterday"}, "ISO time"),
        ({"observed_at": "2026-10-12T09:00:00"}, "time zone"),
        ({"Items": []}, "non-empty list"),
        ({"NextPageLink": "https://prices.azure.com/next"}, "one page"),
    ],
)
def test_bad_files_refused(
    tmp_path: Path, con: duckdb.DuckDBPyConnection, changes: dict[str, Any], why: str
) -> None:
    path = write(tmp_path, page(TWO, **changes))
    with pytest.raises(synthetic.SyntheticError, match=why):
        synthetic.ingest_azure_snapshot(con, path, repo=tmp_path)
    assert one(con, "SELECT count(*) FROM collection_run") == 0


def test_same_snapshot_twice_refused(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    path = write(tmp_path, page(TWO))
    synthetic.ingest_azure_snapshot(con, path, repo=tmp_path)
    with pytest.raises(synthetic.SyntheticError, match="already stored"):
        synthetic.ingest_azure_snapshot(con, path, repo=tmp_path)


def test_kind_follows_the_shape(tmp_path: Path) -> None:
    azure = write(tmp_path, page(TWO)).read_bytes()
    assert synthetic.kind(azure) == "azure-retail"
    market = (FIXTURES / "marketplace" / "snapshot-1.json").read_bytes()
    assert synthetic.kind(market) == "synthetic-marketplace"
    neither = json.dumps({"_label": "synthetic", "observed_at": OBSERVED}).encode()
    with pytest.raises(synthetic.SyntheticError, match="neither"):
        synthetic.kind(neither)


def test_command_stores_both_kinds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "synthetic.duckdb"
    files = [write(tmp_path, page(TWO)), FIXTURES / "marketplace" / "snapshot-1.json"]
    assert synthetic.main([*map(str, files), "--db", str(target)]) == 0
    out = capsys.readouterr().out
    assert "for azure-retail" in out
    assert "for synthetic-marketplace" in out


def test_command_refuses_the_live_database_for_azure_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(tmp_path, page(TWO))
    assert synthetic.main([str(path), "--db", str(synthetic.MONITOR_DB)]) == 2
    assert "never go to" in capsys.readouterr().err
