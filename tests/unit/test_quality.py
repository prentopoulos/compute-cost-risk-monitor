"""The counts-only quality report: freshness, reconciliation, flags and rendering.

All runs are synthetic; expected counts are worked out from the seeded rows by hand.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb
import pytest

from compute_cost_risk_monitor import db, normalize, quality, synthetic
from seed import DAY, Price, azure_run, database
from support import FIXTURES

NOW = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
SNAPSHOT = FIXTURES / "marketplace" / "snapshot-1.json"
PRICES = [
    Price(meter="a", price=80.0),
    Price(meter="b", price=96.0, product=None),
    Price(meter="c", product="Virtual Machines NDsr H100 v5 Series Windows"),
    Price(meter="d", rental="reservation", unit="1 Year term"),
    Price("Standard_ND96is_noIB_H100_v5", meter="e"),
    Price("Standard_NV18ads_A10_v5", meter="f"),
    Price(meter="g", product="Virtual Machines Win Thing Series"),
]


def seeded() -> quality.QualityReport:
    con = database()
    azure_run(
        con,
        "run-1",
        PRICES,
        tallies={("rejected", "missing_field"): 2, ("flagged", "shared_meter_key"): 1},
        repeats=1,
    )
    normalize.normalize_pending(con, NOW)
    return quality.build(con, "azure-retail", DAY + timedelta(days=2))


def test_counts_reconcile() -> None:
    report = seeded()
    assert report.observations == 7
    assert report.by_status == {
        "normalized": 3,
        "windows": 1,
        "rental_type_not_compared": 1,
        "unmapped_sku": 1,
        "fractional_gpu": 1,
    }
    assert sum(report.by_status.values()) == report.observations
    assert report.unmapped_sizes == ["Standard_ND96is_noIB_H100_v5"]
    assert report.rejected == {"missing_field": 2}
    assert report.duplicates == {"repeats": 1, "shared_meter_key": 1}
    # Seeded rows have a location but no effective start date; one has no product name.
    assert report.missing_fields == {
        "location": 0,
        "product_name": 1,
        "effective_start_date": 3,
    }
    assert report.os_ambiguous == 1
    assert (report.region_groups, report.single_price_groups) == (1, 0)
    assert (report.summaries, report.thin) == (1, 1)
    assert report.changes is None and report.not_listed == 0


def test_fresh_and_stale() -> None:
    con = database()
    azure_run(con, "run-1", [Price()])
    normalize.normalize_pending(con, NOW)
    fresh = quality.build(con, "azure-retail", DAY + timedelta(days=2))
    stale = quality.build(con, "azure-retail", DAY + timedelta(days=8))
    assert fresh.stale is False and stale.stale is True
    assert "STALE" in quality.render(stale) and "not stale" in quality.render(fresh)


def test_exactly_seven_days_is_not_stale() -> None:
    con = database()
    azure_run(con, "run-1", [Price()])  # started at DAY
    normalize.normalize_pending(con, NOW)
    week = DAY + timedelta(days=7)
    assert quality.build(con, "azure-retail", week).stale is False
    later = week + timedelta(seconds=1)
    assert quality.build(con, "azure-retail", later).stale is True


@pytest.mark.parametrize("status", ["partial", "failed"])
def test_staleness_comes_from_the_latest_succeeded_run(status: str) -> None:
    con = database()
    azure_run(con, "old", [Price()])  # succeeded, started at DAY
    azure_run(con, "newer", [], started=DAY + timedelta(days=7), status=status)
    normalize.normalize_pending(con, NOW)
    report = quality.build(con, "azure-retail", DAY + timedelta(days=8))
    assert report.snapshot is not None and report.snapshot.run_id == "old"
    assert report.stale is True


def test_snapshot_dated_after_the_as_of_time_is_not_stale() -> None:
    con = database()
    azure_run(con, "ahead", [Price()])  # started at DAY
    normalize.normalize_pending(con, NOW)
    report = quality.build(con, "azure-retail", DAY - timedelta(days=30))
    assert report.stale is False
    assert "not stale" in quality.render(report)
    assert report.snapshot is not None and report.snapshot.run_id == "ahead"


def test_no_snapshot_is_not_zero_prices() -> None:
    con = database()
    azure_run(con, "run-1", [], status="failed")
    report = quality.build(con, "azure-retail", NOW)
    assert report.snapshot is None and report.stale is None
    assert quality.render(report) == "azure-retail: no snapshot (no succeeded run)"


def test_render_holds_no_prices() -> None:
    text = quality.render(seeded())
    for value in ("80.0", "96.0", "10.0", "12.0"):
        assert value not in text
    assert "observations 7" in text and "normalized: 3" in text


def test_marketplace_report() -> None:
    con = database()
    for path in sorted((FIXTURES / "marketplace").glob("snapshot-*.json")):
        synthetic.ingest_snapshot(con, path)
    normalize.normalize_pending(con, NOW)
    report = quality.build(
        con, "synthetic-marketplace", datetime(2026, 10, 4, tzinfo=UTC)
    )
    assert report.observations == 11
    assert report.duplicates == {"machine_duplicate": 0}
    assert report.thin == 2  # H100 x2 (one machine) and RTX 4090 Spot (two)
    assert (report.changes, report.absent_once, report.not_listed) == (0, 0, 1)


def test_marketplace_counts_its_own_missing_fields(tmp_path: Path) -> None:
    doc = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    doc["offers"] = [o for o in doc["offers"] if o["offer_id"] in ("S-101", "S-103")]
    del doc["offers"][0]["country_code"]
    path = tmp_path / "s.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    con = database()
    synthetic.ingest_snapshot(con, path, repo=tmp_path)
    normalize.normalize_pending(con, NOW)
    report = quality.build(con, "synthetic-marketplace", NOW)
    assert report.missing_fields == {"country_code": 1}


def test_passed_region_groups_are_used() -> None:
    con = database()
    azure_run(con, "run-1", PRICES)
    normalize.normalize_pending(con, NOW)
    report = quality.build(con, "azure-retail", NOW, region_groups=[])
    assert (report.region_groups, report.summaries) == (0, 0)


def test_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "monitor.duckdb"
    assert quality.main(["--db", str(path)]) == 2
    con = db.connect(path)
    db.create_schema(con)
    azure_run(con, "run-1", [Price()])
    con.close()
    assert quality.main(["--db", str(path)]) == 2  # not normalized yet
    assert "run normalize first" in capsys.readouterr().err
    assert normalize.main(["--db", str(path)], now=NOW) == 0
    assert (
        quality.main(["--db", str(path), "--as-of", "2026-10-13T00:00:00+00:00"]) == 0
    )
    out = capsys.readouterr().out
    assert "synthetic-marketplace: no snapshot" in out and "not stale" in out
    assert quality.main(["--db", str(path), "--as-of", "2026-10-13T00:00:00"]) == 2


def test_command_prints_the_as_of_time_in_utc(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "monitor.duckdb"
    con = db.connect(path)
    db.create_schema(con)
    azure_run(con, "run-1", [Price()])  # started 2026-10-12 09:00 UTC
    con.close()
    assert normalize.main(["--db", str(path)], now=NOW) == 0
    capsys.readouterr()
    # 05:00 at -04:00 is 09:00 UTC: exactly 7 days, so not stale; a second later, stale.
    assert (
        quality.main(["--db", str(path), "--as-of", "2026-10-19T05:00:00-04:00"]) == 0
    )
    out = capsys.readouterr().out
    assert "not stale as of 2026-10-19T09:00:00+00:00" in out
    assert (
        quality.main(["--db", str(path), "--as-of", "2026-10-19T05:00:01-04:00"]) == 0
    )
    assert "STALE as of 2026-10-19T09:00:01+00:00" in capsys.readouterr().out


def test_snapshot_not_yet_normalized_is_flagged() -> None:
    con = database()
    azure_run(con, "run-1", [Price()])
    normalize.normalize_pending(con, NOW)
    # A newer run arrives after the last normalize.
    azure_run(
        con, "run-2", [Price(), Price(meter="b")], started=DAY + timedelta(days=1)
    )
    report = quality.build(con, "azure-retail", DAY + timedelta(days=2))
    assert (report.observations, report.not_normalized) == (2, 2)
    assert "NOT NORMALIZED: 2 observations" in quality.render(report)


def test_render_names_unmapped_sizes() -> None:
    text = quality.render(seeded())
    assert "sizes not in the map: 1 (Standard_ND96is_noIB_H100_v5)" in text


def test_command_refuses_a_database_it_cannot_open(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "monitor.duckdb"
    path.write_bytes(b"")

    def locked(*_: object) -> None:
        raise duckdb.IOException("file is locked (simulated)")

    monkeypatch.setattr(db, "connect", locked)
    assert quality.main(["--db", str(path)]) == 2
    assert "cannot open" in capsys.readouterr().err


def test_run_without_a_summary_counts_are_unknown() -> None:
    con = database()
    azure_run(con, "run-1", [Price()])
    con.execute("DELETE FROM collection_run_summary WHERE run_id = 'run-1'")
    normalize.normalize_pending(con, NOW)
    report = quality.build(con, "azure-retail", DAY + timedelta(days=1))
    assert (report.out_of_scope, report.repeats, report.rejected_total) == (
        None,
        None,
        None,
    )
    text = quality.render(report)
    assert (
        "run records: out of scope unknown (no run summary),"
        " repeats unknown (no run summary), rejected unknown (no run summary)"
    ) in text
    assert (
        "duplicates: repeats unknown (no run summary),"
        " shared_meter_key unknown (no run summary)"
    ) in text


def test_tallies_without_a_summary_stay_known() -> None:
    # A tally row records a count above zero, so it stands without the summary; the
    # totals it cannot prove (zeros, the rejected total) stay unknown.
    con = database()
    tallies = {("rejected", "missing_field"): 2, ("flagged", "shared_meter_key"): 1}
    azure_run(con, "run-1", [Price()], tallies=tallies)
    con.execute("DELETE FROM collection_run_summary WHERE run_id = 'run-1'")
    normalize.normalize_pending(con, NOW)
    report = quality.build(con, "azure-retail", DAY + timedelta(days=1))
    assert report.rejected == {"missing_field": 2}
    assert report.rejected_total is None
    assert report.duplicates == {"repeats": None, "shared_meter_key": 1}
    text = quality.render(report)
    assert "rejected unknown (no run summary)" in text
    assert "    rejected missing_field: 2" in text
