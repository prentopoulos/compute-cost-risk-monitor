"""Synthetic marketplace ingest and normalization, against hand-worked answers.

The snapshot files under tests/fixtures/synthetic/marketplace are synthetic: a fictional
provider with invented machines and prices.
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

from compute_cost_risk_monitor import checks, normalize, synthetic
from seed import database
from support import FIXTURES

SNAPSHOTS = sorted((FIXTURES / "marketplace").glob("snapshot-*.json"))
NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


@pytest.fixture
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    connection = database()
    yield connection
    connection.close()


def document(path: Path = SNAPSHOTS[0]) -> dict[str, Any]:
    value: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return value


def write(tmp_path: Path, doc: dict[str, Any], name: str = "s.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def one(con: duckdb.DuckDBPyConnection, sql: str, *params: object) -> Any:
    row = con.execute(sql, list(params)).fetchone()
    assert row is not None
    return row[0]


def test_snapshot_stored_as_synthetic(con: duckdb.DuckDBPyConnection) -> None:
    run_id = synthetic.ingest_snapshot(con, SNAPSHOTS[0])
    assert run_id.startswith("synthetic-20261001T120000Z-")
    run = con.execute(
        "SELECT source, data_label, status, started_at FROM collection_run"
    ).fetchall()
    assert run == [
        (
            "synthetic-marketplace",
            "synthetic",
            "succeeded",
            datetime(2026, 10, 1, 12, tzinfo=UTC),
        )
    ]
    assert one(con, "SELECT count(*) FROM price_observation") == 12
    assert one(con, "SELECT count(*) FROM marketplace_offer") == 12
    path, digest, length = con.execute(
        "SELECT file_path, sha256, byte_length FROM raw_response"
    ).fetchall()[0]
    body = SNAPSHOTS[0].read_bytes()
    assert path == "tests/fixtures/synthetic/marketplace/snapshot-1.json"
    assert (digest, length) == (hashlib.sha256(body).hexdigest(), len(body))
    assert one(con, "SELECT observations_stored FROM collection_run_summary") == 12


def test_unlabelled_file_refused(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    doc = document()
    del doc["_label"]
    with pytest.raises(synthetic.SyntheticError, match="not labelled"):
        synthetic.ingest_snapshot(con, write(tmp_path, doc))
    assert one(con, "SELECT count(*) FROM collection_run") == 0


def test_duplicate_offer_refused(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    doc = document()
    doc["offers"].append(copy.deepcopy(doc["offers"][0]))
    with pytest.raises(synthetic.SyntheticError, match="S-101"):
        synthetic.ingest_snapshot(con, write(tmp_path, doc))
    assert one(con, "SELECT count(*) FROM price_observation") == 0


@pytest.mark.parametrize(
    ("change", "why"),
    [
        ({"num_gpus": 0}, "num_gpus"),
        ({"num_gpus": True}, "num_gpus"),
        ({"usd_per_hour": 0}, "usd_per_hour"),
        ({"usd_per_hour": "2.0"}, "usd_per_hour"),
        ({"gpu_vram_gb": -1}, "gpu_vram_gb"),
        ({"country_code": "usa"}, "country_code"),
        ({"rental_type": "bid"}, "rental type"),
        ({"machine_id": ""}, "machine_id"),
    ],
)
def test_bad_offers_refused(
    tmp_path: Path, con: duckdb.DuckDBPyConnection, change: dict[str, Any], why: str
) -> None:
    doc = document()
    doc["offers"][0].update(change)
    with pytest.raises(synthetic.SyntheticError, match=why):
        synthetic.ingest_snapshot(con, write(tmp_path, doc))


@pytest.mark.parametrize(
    ("body", "why"),
    [
        (b"\xff", "not JSON"),
        (b"[]", "not labelled"),
        (b'{"_label": "synthetic", "observed_at": "soon", "offers": []}', "ISO time"),
        (b'{"_label": "synthetic", "observed_at": "2026-10-01T12:00:00"}', "time zone"),
        (b'{"_label": "synthetic", "observed_at": "2026-10-01T12:00Z"}', "offers"),
        (
            b'{"_label": "synthetic", "observed_at": "2026-10-01T12:00Z",'
            b' "offers": [1]}',
            "not an object",
        ),
    ],
)
def test_bad_files_refused(body: bytes, why: str) -> None:
    with pytest.raises(synthetic.SyntheticError, match=why):
        synthetic.parse_snapshot(body)


def test_same_snapshot_twice_refused(con: duckdb.DuckDBPyConnection) -> None:
    synthetic.ingest_snapshot(con, SNAPSHOTS[0])
    with pytest.raises(synthetic.SyntheticError, match="already stored"):
        synthetic.ingest_snapshot(con, SNAPSHOTS[0])


def test_file_outside_repo_keeps_only_its_name(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    path = write(tmp_path, document(), "outside.json")
    synthetic.ingest_snapshot(con, path, repo=tmp_path / "repo")
    assert one(con, "SELECT file_path FROM raw_response") == "outside.json"


def test_normalize_known_answers(con: duckdb.DuckDBPyConnection) -> None:
    for path in SNAPSHOTS:
        synthetic.ingest_snapshot(con, path)
    result = normalize.normalize_pending(con, NOW)
    # Day 1: 12 offers, day 2: 9, day 3: 11. Per day, the reservation is not compared,
    # and the unknown name and the 40 GB "A100 SXM" are unmapped.
    assert result.written == 32
    assert result.by_status == {
        "normalized": 23,
        "unmapped_gpu_name": 6,
        "rental_type_not_compared": 3,
    }
    assert result.unmapped_sizes == []
    two_gpu = con.execute(
        "SELECT usd_per_gpu_hour, gpu_model, gpu_count FROM normalized_price"
        " WHERE item_key = 'S-107' ORDER BY retrieved_at LIMIT 1"
    ).fetchone()
    assert two_gpu == (2.0, "H100 NVLink 80GB", 2.0)
    assert all(v.passed for v in checks.run(con, "groups-v1"))


def test_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "synthetic.duckdb"
    assert synthetic.main([*map(str, SNAPSHOTS), "--db", str(target)]) == 0
    assert capsys.readouterr().out.count("(synthetic)") == 3
    assert synthetic.main([str(SNAPSHOTS[0]), "--db", str(target)]) == 2
    assert "already stored" in capsys.readouterr().err


def test_command_never_writes_the_live_database(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert synthetic.main([str(SNAPSHOTS[0]), "--db", str(synthetic.MONITOR_DB)]) == 2
    assert "never go to" in capsys.readouterr().err
    assert synthetic.DEFAULT_DB.name == "synthetic.duckdb"
