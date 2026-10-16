"""The synthetic demo history: two earlier snapshots in front of azure_demo.json.

Phase 8 design D7. The files in tests/fixtures/synthetic/azure_demo_history are
synthetic: Azure-shaped items with invented prices. Every expected number is the
hand-worked answer in tests/fixtures/synthetic/README.md, never a value read back from
the code under test.
"""

import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import duckdb
import pytest

from compute_cost_risk_monitor import (
    checks,
    groups,
    history,
    normalize,
    quality,
    synthetic,
)
from compute_cost_risk_monitor.groups import GroupKey, Snapshot
from seed import database
from support import FIXTURES

DEMO = FIXTURES / "azure_demo.json"
FILES = [*sorted((FIXTURES / "azure_demo_history").glob("snapshot-*.json")), DEMO]
NOW = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
THIRD = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)  # azure_demo.json's start
H100, A100, T4 = (
    "Standard_ND96isr_H100_v5",
    "Standard_NC24ads_A100_v4",
    "Standard_NC8as_T4_v3",
)
SOURCE = "azure-retail"


@pytest.fixture(scope="module")
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    connection = database()
    for path in FILES:
        assert synthetic.ingest_file(connection, path)[0] == SOURCE
    normalize.normalize_pending(connection, NOW)
    yield connection
    connection.close()


@pytest.fixture(scope="module")
def snaps(con: duckdb.DuckDBPyConnection) -> list[Snapshot]:
    return groups.snapshots(con, SOURCE)


def prices(
    con: duckdb.DuckDBPyConnection, snap: Snapshot
) -> dict[tuple[str, str, str], float]:
    """USD/GPU-hour of each compared listing, keyed (size, region, rental)."""
    return {
        (m.name, g.key.region, g.key.rental_type): m.usd_per_gpu_hour
        for g in groups.region_groups(con, snap)
        for m in g.members
    }


def test_three_snapshots_in_date_order(
    con: duckdb.DuckDBPyConnection, snaps: list[Snapshot]
) -> None:
    assert len(FILES) == 3
    assert [s.started_at for s in snaps] == [
        datetime(2026, 9, 28, 9, 0, tzinfo=UTC),
        datetime(2026, 10, 5, 9, 0, tzinfo=UTC),
        THIRD,
    ]
    assert {s.data_label for s in snaps} == {"synthetic"}
    stored = con.execute(
        "SELECT s.observations_stored, s.rejected"
        " FROM collection_run r JOIN collection_run_summary s USING (run_id)"
        " ORDER BY r.started_at"
    ).fetchall()
    assert stored == [(16, 0), (15, 0), (14, 0)]


def test_latest_snapshot_is_the_unchanged_demo_file(
    con: duckdb.DuckDBPyConnection, snaps: list[Snapshot]
) -> None:
    (digest,) = con.execute(
        "SELECT sha256 FROM raw_response WHERE run_id = ?", [snaps[2].run_id]
    ).fetchone() or (None,)
    assert digest == hashlib.sha256(DEMO.read_bytes()).hexdigest()


def test_independent_checks_pass(con: duckdb.DuckDBPyConnection) -> None:
    verdicts = checks.run(con, "groups-v1")
    assert all(v.passed for v in verdicts), [v.failures for v in verdicts]


def test_compared_rows_and_changed_prices(
    con: duckdb.DuckDBPyConnection, snaps: list[Snapshot]
) -> None:
    first, second, third = (prices(con, s) for s in snaps)
    assert (len(first), len(second), len(third)) == (14, 13, 12)
    for earlier in (first, second):
        assert earlier[(H100, "eastus", "on_demand")] == 11.0
        assert earlier[(H100, "eastus", "spot")] == 11.0
        assert earlier[(A100, "westeurope", "on_demand")] == 4.0
    assert first[(T4, "westeurope", "on_demand")] == 0.9
    assert (T4, "westeurope", "on_demand") not in second
    assert third[(H100, "eastus", "on_demand")] == 12.0
    assert third[(H100, "eastus", "spot")] == 12.0
    assert (A100, "westeurope", "on_demand") not in third


def test_history_as_of_the_demo_snapshot(
    con: duckdb.DuckDBPyConnection, snaps: list[Snapshot]
) -> None:
    first, second, third = snaps
    assert history.changes(con, first, second) == []
    found = history.changes(con, second, third)
    assert len(found) == 2
    assert {c.after.group for c in found} == {
        GroupKey("H100 NVLink 80GB", 8, "eastus", "on_demand"),
        GroupKey("H100 NVLink 80GB", 8, "eastus", "spot"),
    }
    for change in found:
        assert (change.before.price, change.after.price) == (88.0, 96.0)
        assert (change.before.usd_per_gpu_hour, change.after.usd_per_gpu_hour) == (
            11.0,
            12.0,
        )
    absent = {a.listing: a for a in history.absences(con, SOURCE)}
    assert set(absent) == {
        (A100, "westeurope", "on_demand", "linux"),
        (T4, "westeurope", "on_demand", "linux"),
    }
    a100 = absent[(A100, "westeurope", "on_demand", "linux")]
    assert (a100.status, a100.since, a100.last_seen) == (
        history.ABSENT_ONCE,
        third,
        second,
    )
    t4 = absent[(T4, "westeurope", "on_demand", "linux")]
    assert (t4.status, t4.since, t4.last_seen) == (history.NOT_LISTED, second, first)


def test_no_spot_above_pay_as_you_go(
    con: duckdb.DuckDBPyConnection, snaps: list[Snapshot]
) -> None:
    for snap in snaps:
        listed = prices(con, snap)
        for (size, region, rental), spot in listed.items():
            payg = listed.get((size, region, "on_demand"))
            if rental == "spot" and payg is not None:
                assert spot <= payg, (snap.started_at, size, region)


def test_quality_report_for_the_demo_snapshot(con: duckdb.DuckDBPyConnection) -> None:
    report = quality.build(con, SOURCE, NOW)
    assert report.snapshot is not None and report.snapshot.started_at == THIRD
    assert report.observations == 14
    assert report.by_status == {"normalized": 12, "unmapped_sku": 1, "windows": 1}
    assert report.unmapped_sizes == ["Standard_ND96is_MI300X_v5"]
    assert (report.region_groups, report.single_price_groups) == (11, 10)
    assert (report.summaries, report.thin) == (4, 3)
    assert (report.changes, report.absent_once, report.not_listed) == (2, 1, 1)
    assert report.rejected == {} and (report.out_of_scope, report.repeats) == (0, 0)
    assert report.not_normalized == 0


@pytest.mark.parametrize(
    ("after", "stale"),
    [(timedelta(days=7), False), (timedelta(days=7, seconds=1), True)],
)
def test_stale_after_seven_days(
    con: duckdb.DuckDBPyConnection, after: timedelta, stale: bool
) -> None:
    assert quality.build(con, SOURCE, THIRD + after).stale is stale
