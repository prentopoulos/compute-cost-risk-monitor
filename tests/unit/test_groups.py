"""Comparable groups and statistics against hand-worked answers (synthetic prices).

Azure-shaped runs are seeded with invented round prices; the marketplace cases use the
synthetic snapshot fixtures. Every expected figure below was worked out by hand.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import duckdb
import pytest

from compute_cost_risk_monitor import groups, normalize, synthetic
from seed import DAY, Price, azure_run, database
from support import FIXTURES

NOW = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
H100 = "Standard_ND96isr_H100_v5"  # 8 x H100 NVLink 80GB


def t4(size: str, region: str, per_gpu: float, gpus: int = 1) -> Price:
    return Price(size, region, price=per_gpu * gpus, meter=f"{size}-{region}")


AZURE = [
    # H100 x8: one size per region, USD/GPU-hour 1, 2, 3, 4, 10 in five regions.
    *(
        Price(H100, f"r{i}", price=8 * v, meter=f"h{i}")
        for i, v in enumerate([1, 2, 3, 4, 10], 1)
    ),
    # T4 x1: region r1 holds two sizes (3 and 4); four regions in all.
    t4("Standard_NC4as_T4_v3", "r1", 4.0),
    t4("Standard_NC8as_T4_v3", "r1", 3.0),
    t4("Standard_NC4as_T4_v3", "r2", 1.0),
    t4("Standard_NC4as_T4_v3", "r3", 2.0),
    t4("Standard_NC4as_T4_v3", "r4", 4.0),
    # T4 x4 is its own group; an unmapped size never enters a group.
    t4("Standard_NC64as_T4_v3", "r1", 1.5, gpus=4),
    Price("Standard_ND96is_noIB_H100_v5", "r1", meter="unmapped"),
]


@pytest.fixture
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    connection = database()
    azure_run(connection, "run-1", AZURE)
    normalize.normalize_pending(connection, NOW)
    yield connection
    connection.close()


def snapshot(con: duckdb.DuckDBPyConnection) -> groups.Snapshot:
    (only,) = groups.snapshots(con, "azure-retail")
    return only


def test_region_groups(con: duckdb.DuckDBPyConnection) -> None:
    found = {
        (g.key.variant, g.key.gpu_count, g.key.region): g
        for g in groups.region_groups(con, snapshot(con))
    }
    assert len(found) == 10  # 5 H100, 4 T4 x1, 1 T4 x4
    pair = found[("T4 16GB", 1, "r1")]
    assert [(m.name, m.usd_per_gpu_hour) for m in pair.members] == [
        ("Standard_NC8as_T4_v3", 3.0),
        ("Standard_NC4as_T4_v3", 4.0),
    ]
    assert groups.SINGLE not in pair.labels
    assert found[("H100 NVLink 80GB", 8, "r1")].labels == [groups.SINGLE]
    assert found[("T4 16GB", 4, "r1")].members[0].usd_per_gpu_hour == 1.5
    assert all(g.exclusions.startswith("Excludes disks") for g in found.values())
    names = {m.name for g in found.values() for m in g.members}
    assert "Standard_ND96is_noIB_H100_v5" not in names


def test_member_carries_its_published_price_and_provenance() -> None:
    connection = database()
    try:
        a100 = Price("Standard_NC48ads_A100_v4", "r1", price=7.0)  # 2 x A100 PCIe
        azure_run(connection, "run-2", [a100])
        normalize.normalize_pending(connection, NOW)
        (snap,) = groups.snapshots(connection, "azure-retail")
        (group,) = groups.region_groups(connection, snap)
        (member,) = group.members
    finally:
        connection.close()
    assert snap.data_label == "synthetic"
    assert (member.usd_per_gpu_hour, member.price) == (3.5, 7.0)
    assert (member.currency, member.price_unit) == ("USD", "1 Hour")
    assert (member.run_id, member.file_path, member.seq, member.sha256) == (
        "run-2",
        "synthetic.json.gz",
        0,
        "0" * 64,
    )


def test_cross_region_summaries(con: duckdb.DuckDBPyConnection) -> None:
    found = {(s.variant, s.gpu_count): s for s in groups.summaries(con, snapshot(con))}
    assert set(found) == {("H100 NVLink 80GB", 8), ("T4 16GB", 1), ("T4 16GB", 4)}
    h100 = found[("H100 NVLink 80GB", 8)]
    assert h100.stats == groups.Stats(5, 1.0, 3.0, 10.0)
    assert h100.labels == [groups.LOWEST, groups.CROSSES]
    t4_one = found[("T4 16GB", 1)]
    # r1 contributes its lowest member (3.0, NC8as); 1, 2, 3, 4 has median 2.5.
    assert t4_one.stats == groups.Stats(4, 1.0, 2.5, 4.0)
    r1 = next(c for c in t4_one.contributions if c.region == "r1")
    assert r1.member.name == "Standard_NC8as_T4_v3"
    assert groups.THIN in t4_one.labels
    assert groups.THIN in found[("T4 16GB", 4)].labels


def test_ties_go_to_the_first_name() -> None:
    a = groups.Member("Standard_B", 2.0, "kb", DAY)
    b = groups.Member("Standard_A", 2.0, "ka", DAY)
    snap = groups.Snapshot("azure-retail", "run", DAY, "synthetic")
    key = groups.GroupKey("T4 16GB", 1, "r1", "on_demand")
    (summary,) = groups.cross_region([groups.RegionGroup(key, snap, [a, b], "x")], 5)
    assert summary.contributions[0].member.name == "Standard_A"


def test_only_succeeded_runs_are_snapshots() -> None:
    con = database()
    azure_run(con, "ok-1", [Price()], started=DAY)
    azure_run(
        con, "partial", [Price()], started=DAY + timedelta(days=1), status="partial"
    )
    azure_run(con, "ok-2", [Price()], started=DAY + timedelta(days=2))
    assert [s.run_id for s in groups.snapshots(con, "azure-retail")] == ["ok-1", "ok-2"]
    assert groups.snapshots(con, "synthetic-marketplace") == []


def test_marketplace_groups_count_machines() -> None:
    con = database()
    synthetic.ingest_snapshot(con, FIXTURES / "marketplace" / "snapshot-1.json")
    normalize.normalize_pending(con, NOW)
    (snap,) = groups.snapshots(con, "synthetic-marketplace")
    found = {
        (g.key.variant, g.key.gpu_count): g for g in groups.region_groups(con, snap)
    }
    h100 = found[("H100 NVLink 80GB", 1)]
    # M-01 offers 2.0 and 2.2: one machine, its lowest price; five machines in all.
    assert h100.stats == groups.Stats(5, 2.0, 2.6, 3.0)
    flagged = [m.name for m in h100.members if groups.DUPLICATE in m.flags]
    assert flagged == ["S-102"]
    assert h100.labels == [groups.SYNTHETIC]
    assert found[("RTX 4090 24GB", 1)].labels == [groups.SYNTHETIC, groups.THIN]
    assert found[("H100 NVLink 80GB", 2)].stats == groups.Stats(1, 2.0, 2.0, 2.0)
