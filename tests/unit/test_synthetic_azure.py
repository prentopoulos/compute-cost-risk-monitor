"""Synthetic Azure-shaped snapshots stored as synthetic runs (Phase 4 design D7, D29).

Every file here is synthetic: Azure-shaped items with invented prices, built from the
base item in tests/fixtures/synthetic/azure_items.json.
"""

import copy
import hashlib
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pytest

from compute_cost_risk_monitor import checks, groups, normalize, synthetic
from seed import database
from support import BASE_ITEM, FIXTURES

OBSERVED = "2026-10-12T09:00:00+00:00"
NOW = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)


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


def test_file_with_nothing_stored_refused(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    rejected = item(isPrimaryMeterRegion=False)
    outside = item(
        meterId="00000000-0000-0000-0000-000000000009", armSkuName="Standard_D2s_v5"
    )
    path = write(tmp_path, page([rejected, outside]))
    with pytest.raises(synthetic.SyntheticError, match="1 out of scope, 1 rejected"):
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


def test_demo_file_covers_the_dashboard_cases(
    con: duckdb.DuckDBPyConnection,
) -> None:
    synthetic.ingest_azure_snapshot(con, FIXTURES / "azure_demo.json")
    normalize.normalize_pending(con, NOW)
    assert all(v.passed for v in checks.run(con, "groups-v1"))
    (snap,) = groups.snapshots(con, "azure-retail")
    assert snap.data_label == "synthetic"
    found = {
        (g.key.variant, g.key.gpu_count, g.key.region, g.key.rental_type): g
        for g in groups.region_groups(con, snap)
    }
    assert len(found[("T4 16GB", 1, "eastus", "on_demand")].members) == 2
    assert groups.SINGLE in found[("T4 16GB", 1, "westeurope", "on_demand")].labels
    thin = {
        (s.variant, s.rental_type): groups.THIN in s.labels
        for s in groups.summaries(con, snap)
    }
    assert thin[("H100 NVLink 80GB", "on_demand")] is False
    assert thin[("H100 NVLink 80GB", "spot")] is True
    spot = found[("H100 NVLink 80GB", 8, "eastus", "spot")].members[0]
    listed = found[("H100 NVLink 80GB", 8, "eastus", "on_demand")].members[0]
    assert spot.price == listed.price
    # A Spot size with no pay-as-you-go listing in its region (Phase 5 D12).
    unlisted = found[("H100 NVLink 80GB", 8, "uksouth", "spot")].members[0]
    assert unlisted.name == listed.name
    assert ("H100 NVLink 80GB", 8, "uksouth", "on_demand") not in found
    assert [
        len(s.contributions)
        for s in groups.summaries(con, snap)
        if (s.variant, s.rental_type) == ("H100 NVLink 80GB", "spot")
    ] == [3]
    reasons = dict(
        con.execute(
            "SELECT excluded_reason, count(*) FROM normalized_price"
            " WHERE excluded_reason IS NOT NULL GROUP BY 1"
        ).fetchall()
    )
    assert reasons == {"unmapped_sku": 1, "windows": 1}


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
