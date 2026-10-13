"""End to end: three dated synthetic snapshots through every stage (Phase 6 design D17).

The files in tests/fixtures/synthetic/azure_history are synthetic: Azure-shaped items
with invented prices. They go through the live row rules (synthetic ingest), normalize,
the independent checks, the quality report, groups, history, the calculator and the
workload check. Every expected number is the hand-worked answer in
tests/fixtures/synthetic/README.md, never a value read back from the code under test.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import duckdb
import pytest

from compute_cost_risk_monitor import (
    calculator,
    checks,
    dashboard,
    groups,
    history,
    normalize,
    quality,
    synthetic,
)
from compute_cost_risk_monitor.groups import GroupKey, RegionGroup, Snapshot
from seed import database
from support import FIXTURES

FILES = sorted((FIXTURES / "azure_history").glob("snapshot-*.json"))
NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
THIRD = datetime(2026, 9, 15, 9, 0, tzinfo=UTC)  # snapshot 3's start
H100, T4 = "H100 NVLink 80GB", "T4 16GB"
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


def prices(con: duckdb.DuckDBPyConnection, snap: Snapshot) -> dict[str, float]:
    """USD/GPU-hour of each compared listing, keyed "size region rental"."""
    return {
        f"{m.name} {g.key.region} {g.key.rental_type}": m.usd_per_gpu_hour
        for g in groups.region_groups(con, snap)
        for m in g.members
    }


def test_three_synthetic_snapshots_stored(
    con: duckdb.DuckDBPyConnection, snaps: list[Snapshot]
) -> None:
    assert len(FILES) == 3
    assert [s.started_at for s in snaps] == [
        datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
        datetime(2026, 9, 8, 9, 0, tzinfo=UTC),
        THIRD,
    ]
    assert {s.data_label for s in snaps} == {"synthetic"}
    stored = con.execute(
        "SELECT r.started_at, s.observations_stored, s.rejected"
        " FROM collection_run r JOIN collection_run_summary s USING (run_id)"
        " ORDER BY r.started_at"
    ).fetchall()
    assert [(n, rejected) for _, n, rejected in stored] == [(6, 0), (4, 0), (4, 0)]


def test_independent_checks_pass(con: duckdb.DuckDBPyConnection) -> None:
    verdicts = checks.run(con, "groups-v1")
    assert all(v.passed for v in verdicts), [v.failures for v in verdicts]


def test_units_and_usd_per_gpu_hour(
    con: duckdb.DuckDBPyConnection, snaps: list[Snapshot]
) -> None:
    h100, t4 = "Standard_ND96isr_H100_v5", "Standard_NC4as_T4_v3"
    assert prices(con, snaps[0]) == {
        f"{h100} eastus on_demand": 12.0,
        f"{h100} westeurope on_demand": 12.5,
        f"{t4} eastus on_demand": 0.6,
        f"{t4} westeurope on_demand": 0.7,
        f"{h100} eastus spot": 5.0,
    }
    assert prices(con, snaps[1]) == {
        f"{h100} eastus on_demand": 12.0,
        f"{h100} westeurope on_demand": 12.5,
        f"{h100} eastus spot": 5.0,
    }
    assert prices(con, snaps[2]) == {
        f"{h100} eastus on_demand": 13.0,
        f"{t4} westeurope on_demand": 0.75,
        f"{h100} eastus spot": 5.0,
    }
    # F's "1/Day" price is excluded every time and never converted to hours.
    excluded = con.execute(
        "SELECT count(*), count(DISTINCT p.price_unit), min(n.usd_per_gpu_hour)"
        " FROM normalized_price n JOIN price_observation p USING (source, item_key,"
        " retrieved_at) WHERE n.excluded_reason = 'unit_not_hourly'"
    ).fetchone()
    assert excluded == (3, 1, None)


def test_history_as_of_the_third_snapshot(
    con: duckdb.DuckDBPyConnection, snaps: list[Snapshot]
) -> None:
    first, second, third = snaps
    assert history.changes(con, first, second) == []
    (change,) = history.changes(con, second, third)
    assert (change.before.price, change.after.price) == (96.0, 104.0)
    assert (change.before.usd_per_gpu_hour, change.after.usd_per_gpu_hour) == (
        12.0,
        13.0,
    )
    assert change.after.group == GroupKey(H100, 8, "eastus", "on_demand")
    found = {a.listing: a for a in history.absences(con, SOURCE)}
    assert set(found) == {
        ("Standard_ND96isr_H100_v5", "westeurope", "on_demand", "linux"),
        ("Standard_NC4as_T4_v3", "eastus", "on_demand", "linux"),
    }
    b = found[("Standard_ND96isr_H100_v5", "westeurope", "on_demand", "linux")]
    assert (b.status, b.since, b.last_seen) == (history.ABSENT_ONCE, third, second)
    c = found[("Standard_NC4as_T4_v3", "eastus", "on_demand", "linux")]
    assert (c.status, c.since, c.last_seen) == (history.NOT_LISTED, second, first)


def test_quality_report_for_the_third_snapshot(con: duckdb.DuckDBPyConnection) -> None:
    report = quality.build(con, SOURCE, THIRD + timedelta(days=2))
    assert report.snapshot is not None and report.snapshot.started_at == THIRD
    assert report.observations == 4
    assert report.by_status == {"normalized": 3, "unit_not_hourly": 1}
    assert (report.region_groups, report.single_price_groups) == (3, 3)
    assert (report.summaries, report.thin) == (3, 3)
    assert (report.changes, report.absent_once, report.not_listed) == (1, 1, 1)
    assert report.unmapped_sizes == [] and report.rejected == {}
    assert (report.out_of_scope, report.repeats) == (0, 0)
    assert report.not_normalized == 0


@pytest.mark.parametrize(
    ("after", "stale"),
    [
        (timedelta(days=2), False),
        (timedelta(days=7), False),
        (timedelta(days=7, seconds=1), True),
    ],
)
def test_stale_as_of(
    con: duckdb.DuckDBPyConnection, after: timedelta, stale: bool
) -> None:
    assert quality.build(con, SOURCE, THIRD + after).stale is stale


def third_groups(
    con: duckdb.DuckDBPyConnection, snaps: list[Snapshot]
) -> list[RegionGroup]:
    return groups.region_groups(con, snaps[2])


def run(
    found: list[RegionGroup], rental: str, limit: float | None = None
) -> calculator.Result:
    group = dashboard.find_group(found, GroupKey(H100, 8, "eastus", rental))
    assert group is not None
    begin = calculator.start(group)
    work = calculator.workload(32, 720.0, None, 8)
    result = calculator.calculate(begin, work, found, None, limit)
    assert dashboard.check(begin, result, work, None, limit, found) == []
    return result


def figures(result: calculator.Result) -> dict[str, tuple[float | None, ...]]:
    return {row.id: (row.price, row.cost, row.exposure) for row in result.rows}


def test_workload_on_the_third_snapshot(
    con: duckdb.DuckDBPyConnection, snaps: list[Snapshot]
) -> None:
    result = run(third_groups(con, snaps), "on_demand", limit=11_520.0)
    assert result.start.usd_per_gpu_hour == 13.0
    assert (result.cost.vms, result.cost.compute, result.cost.total) == (
        4,
        299_520.0,
        299_520.0,
    )
    assert figures(result) == pytest.approx(
        {
            "decline-25": (9.75, 224_640.0, -74_880.0),
            "increase-25": (16.25, 374_400.0, 74_880.0),
            "example-050": (13.5, 311_040.0, 11_520.0),
            "spike-100": (26.0, 599_040.0, 299_520.0),
        },
        rel=1e-12,
    )
    assert result.rows[0].effect == calculator.LOWER
    assert result.headroom is not None
    assert result.headroom.rise == pytest.approx(0.5, rel=1e-12)


def test_spot_workload_and_fallback(
    con: duckdb.DuckDBPyConnection, snaps: list[Snapshot]
) -> None:
    result = run(third_groups(con, snaps), "spot")
    assert result.start.usd_per_gpu_hour == 5.0
    assert result.cost.total == 115_200.0
    assert figures(result) == pytest.approx(
        {
            "decline-25": (3.75, 86_400.0, -28_800.0),
            "increase-25": (6.25, 144_000.0, 28_800.0),
            "example-050": (5.5, 126_720.0, 11_520.0),
            "spike-100": (10.0, 230_400.0, 115_200.0),
            "fallback": (13.0, 299_520.0, 184_320.0),
        },
        rel=1e-12,
    )
    assert all(row.above_payg is None for row in result.rows)
