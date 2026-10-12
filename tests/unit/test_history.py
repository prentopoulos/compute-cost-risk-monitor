"""Price changes, absences and "not listed" across consecutive synthetic snapshots.

Answers come from the fixture design in tests/fixtures/synthetic/README.md and from the
seeded Azure runs below, all synthetic.
"""

from datetime import UTC, datetime, timedelta

import duckdb

from compute_cost_risk_monitor import groups, history, normalize, synthetic
from seed import DAY, Price, azure_run, database
from support import FIXTURES

NOW = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
SNAPSHOTS = sorted((FIXTURES / "marketplace").glob("snapshot-*.json"))


def marketplace(days: int) -> duckdb.DuckDBPyConnection:
    con = database()
    for path in SNAPSHOTS[:days]:
        synthetic.ingest_snapshot(con, path)
    normalize.normalize_pending(con, NOW)
    return con


def test_marketplace_changes_follow_the_machine() -> None:
    con = marketplace(3)
    s1, s2, s3 = groups.snapshots(con, "synthetic-marketplace")
    found = history.changes(con, s1, s2)
    # M-01 is re-listed as S-201 (2.0 -> 2.1); M-03 changes (2.6 -> 2.5).
    assert [(c.before.price, c.after.price) for c in found] == [(2.0, 2.1), (2.6, 2.5)]
    relisted = found[0]
    assert (relisted.before.item_key, relisted.after.item_key) == ("S-101", "S-201")
    assert relisted.after.group == groups.GroupKey(
        "H100 NVLink 80GB", 1, "north-america", "on_demand"
    )
    assert history.changes(con, s2, s3) == []


def test_absent_once_then_not_listed() -> None:
    two = history.absences(marketplace(2), "synthetic-marketplace")
    assert {(a.listing[0], a.status) for a in two} == {
        ("M-04", history.ABSENT_ONCE),
        ("M-11", history.ABSENT_ONCE),
    }
    con = marketplace(3)
    three = history.absences(con, "synthetic-marketplace")
    # M-04 is missing twice; M-11 is back under a new offer ID, so it is not absent.
    (gone,) = three
    _, s2, _ = groups.snapshots(con, "synthetic-marketplace")
    assert (gone.listing[0], gone.status, gone.since) == (
        "M-04",
        history.NOT_LISTED,
        s2,
    )


def test_azure_changes_skip_partial_runs_and_ignore_rekeys() -> None:
    con = database()
    kept = Price(meter="same", price=80.0)
    rekeyed_before = Price("Standard_NC4as_T4_v3", meter="old", price=1.0)
    rekeyed_after = Price("Standard_NC4as_T4_v3", meter="new", price=1.0)
    dropped = Price("Standard_NC8as_T4_v3", meter="drop", price=1.0)
    azure_run(con, "d1", [kept, rekeyed_before, dropped], started=DAY)
    # A partial run neither proves presence nor absence.
    azure_run(con, "d2", [], started=DAY + timedelta(days=1), status="partial")
    azure_run(
        con,
        "d3",
        [Price(meter="same", price=88.0), rekeyed_after],
        started=DAY + timedelta(days=2),
    )
    normalize.normalize_pending(con, NOW)
    first, last = groups.snapshots(con, "azure-retail")
    (change,) = history.changes(con, first, last)
    assert (change.price_key, change.before.price, change.after.price) == (
        kept.key(),
        80.0,
        88.0,
    )
    assert (change.before.usd_per_gpu_hour, change.after.usd_per_gpu_hour) == (10, 11)
    (absent,) = history.absences(con, "azure-retail")
    assert absent.listing == (
        "Standard_NC8as_T4_v3",
        "westeurope",
        "on_demand",
        "linux",
    )
    assert absent.status == history.ABSENT_ONCE


def test_reappearance_clears_and_os_is_part_of_the_listing() -> None:
    con = database()
    linux = Price(meter="l")
    windows = Price(meter="w", product="Virtual Machines NDsr H100 v5 Series Windows")
    azure_run(con, "d1", [linux, windows], started=DAY)
    azure_run(con, "d2", [windows], started=DAY + timedelta(days=1))
    azure_run(con, "d3", [linux, windows], started=DAY + timedelta(days=2))
    normalize.normalize_pending(con, NOW)
    assert history.absences(con, "azure-retail") == []
    azure_run(con, "d4", [linux], started=DAY + timedelta(days=3))
    azure_run(con, "d5", [linux], started=DAY + timedelta(days=4))
    normalize.normalize_pending(con, NOW)
    (gone,) = history.absences(con, "azure-retail")
    assert gone.listing[3] == "windows" and gone.status == history.NOT_LISTED
    assert gone.since.run_id == "d4" and gone.last_seen.run_id == "d3"
