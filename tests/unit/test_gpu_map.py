"""The GPU size map and the frozen rule set: loading, validation and write-once storage.

The packaged map is Microsoft Learn content (CC BY 4.0); the other map texts here are
synthetic, written to break one rule each.
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from fractions import Fraction

import duckdb
import pytest

from compute_cost_risk_monitor import db, gpu_map, rules

HEADER = ",".join(gpu_map.COLUMNS)
URL = "https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/x"
NOTE = "Learn updated 2026-07-28; retrieved 2026-10-12"
NOW = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)


def row(
    size: str = "Standard_NC40ads_H100_v5",
    label: str = "H100 NVL 94GB",
    form: str = "NVL",
    vram: str = "94",
    count: str = "1",
    url: str = URL,
    notes: str = NOTE,
) -> str:
    return ",".join([size, label, form, vram, count, url, notes])


def text(*rows: str) -> str:
    return "\n".join(["# synthetic map for tests", HEADER, *rows]) + "\n"


@pytest.fixture
def connection() -> Iterator[duckdb.DuckDBPyConnection]:
    con = db.connect()
    db.create_schema(con)
    yield con
    con.close()


def test_packaged_map_loads_with_known_coverage() -> None:
    rows = gpu_map.load()
    assert len(rows) == 51
    assert sum(r.whole for r in rows.values()) == 35
    assert all(
        r.source_url.startswith("https://learn.microsoft.com/") for r in rows.values()
    )
    assert rows["Standard_ND96isr_H100_v5"].gpu_model == "H100 NVLink 80GB"
    assert rows["Standard_ND96isr_H100_v5"].gpu_count == 8
    assert rows["Standard_NCC40ads_H100_v5"].gpu_model == "H100 NVL 94GB confidential"
    assert rows["Standard_ND128isr_NDR_GB200_v6"].gpu_count == 4


def test_packaged_map_leaves_inexact_names_unmapped() -> None:
    rows = gpu_map.load()
    # Learn spells these differently or not at all (design D9).
    for name in (
        "Standard_NC6_Promo",
        "Standard_NG32adms_V620",
        "Standard_ND96is_noIB_H100_v5",
        "Standard_NC32lds_xl_RTXPRO6000BSE_v6",
    ):
        assert name not in rows


def test_fraction_parsed() -> None:
    rows = gpu_map.parse(text(row(count="1/4")))
    mapped = rows["Standard_NC40ads_H100_v5"]
    assert mapped.gpu_count == Fraction(1, 4)
    assert not mapped.whole
    assert mapped.stored()[4] == 0.25


@pytest.mark.parametrize(
    ("bad", "why"),
    [
        (row(count="0"), "GPU count"),
        (row(count="-1"), "GPU count"),
        (row(count="1/0"), "GPU count"),
        (row(vram="0"), "memory"),
        (row(vram="nan"), "memory"),
        (row(vram="lots"), "memory"),
        (row(url="https://example.com/sizes"), "learn.microsoft.com"),
        (row(url="http://learn.microsoft.com/x"), "learn.microsoft.com"),
        (row(label="H100 94 GB"), "label"),
        (row(label="H100 NVL 80GB"), "label"),
        (row(form="SXM"), "form factor"),
        (row(notes="no date"), "retrieval date"),
        (row(size="Standard_E4s_v5"), "ARM name"),
        (row(size=" Standard_NC40ads_H100_v5"), "ARM name"),
    ],
)
def test_bad_rows_refused(bad: str, why: str) -> None:
    with pytest.raises(gpu_map.MapError, match=why):
        gpu_map.parse(text(bad))


def test_duplicate_size_refused() -> None:
    with pytest.raises(gpu_map.MapError, match="listed twice"):
        gpu_map.parse(text(row(), row()))


def test_bad_header_and_shape_refused() -> None:
    with pytest.raises(gpu_map.MapError, match="header"):
        gpu_map.parse("a,b\n1,2\n")
    with pytest.raises(gpu_map.MapError, match="empty"):
        gpu_map.parse("# only a comment\n")
    with pytest.raises(gpu_map.MapError, match="too many fields"):
        gpu_map.parse(text(row() + ",extra"))
    with pytest.raises(gpu_map.MapError, match="missing column"):
        gpu_map.parse(text("Standard_NC40ads_H100_v5,H100 NVL 94GB"))


def test_map_stored_once(connection: duckdb.DuckDBPyConnection) -> None:
    rows = gpu_map.load()
    assert gpu_map.store(connection, rows) == 51
    assert gpu_map.store(connection, rows) == 0
    count = connection.execute("SELECT count(*) FROM gpu_sku_map").fetchone()
    assert count == (51,)


def test_changed_map_refused(connection: duckdb.DuckDBPyConnection) -> None:
    rows = gpu_map.parse(text(row()))
    gpu_map.store(connection, rows)
    changed = gpu_map.parse(text(row(count="2")))
    with pytest.raises(rules.FrozenMismatch, match="Standard_NC40ads_H100_v5"):
        gpu_map.store(connection, changed)
    extra = gpu_map.parse(text(row(), row(size="Standard_NC80adis_H100_v5")))
    with pytest.raises(rules.FrozenMismatch, match="Standard_NC80adis_H100_v5"):
        gpu_map.store(connection, extra)


def test_rule_set_stored_once(connection: duckdb.DuckDBPyConnection) -> None:
    assert rules.store(connection, NOW) is True
    assert rules.store(connection, NOW) is False
    assert rules.stored(connection, rules.RULE_VERSION) == rules.GROUPS_V1


def test_changed_rule_set_refused(connection: duckdb.DuckDBPyConnection) -> None:
    rules.store(connection, NOW)
    changed = {**rules.GROUPS_V1, "stale_after_days": 14}
    with pytest.raises(rules.FrozenMismatch, match="groups-v1"):
        rules.store(connection, NOW, changed)


def test_unknown_rule_version(connection: duckdb.DuckDBPyConnection) -> None:
    with pytest.raises(KeyError):
        rules.stored(connection, "groups-v9")


def test_rules_name_the_map_and_cover_the_retired_mapped_sizes() -> None:
    params = rules.GROUPS_V1
    assert params["map_version"] == gpu_map.MAP_VERSION
    mapped = gpu_map.load()
    retired = {size for entry in params["retirements"] for size in entry["sizes"]}
    # Every mapped size Learn calls retired has a retirement entry.
    noted = {name for name, r in mapped.items() if "series retired" in r.notes}
    assert noted <= retired
    for entry in params["retirements"]:
        assert entry["source_url"].startswith("https://learn.microsoft.com/")
        datetime.fromisoformat(entry["retired_on"])
