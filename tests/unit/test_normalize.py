"""Normalization: known answers per reason, the database step and the command.

Every price here is synthetic (round invented numbers). Sizes are real Azure names so
the packaged Learn map applies. Answers are worked out by hand, not by the code under
test.
"""

from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import duckdb
import pytest

from compute_cost_risk_monitor import checks, db, gpu_map, ingest, normalize, rules
from seed import DAY, Price, azure_run, database
from support import collect, item, ok, page_bytes

NOW = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
MAP = gpu_map.load()
P = rules.GROUPS_V1


TODAY = DAY.date()


def classify(price: Price, day: date = TODAY) -> normalize.Outcome:
    observation = normalize.AzureObservation(
        price.size,
        price.region,
        price.rental,
        price.price,
        price.unit,
        price.product,
        day,
    )
    return normalize.classify_azure(observation, MAP, P)


@pytest.fixture
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    connection = database()
    yield connection
    connection.close()


# Known answers: (case, observation, reason, USD/GPU-hour, GPU count)
CASES: list[tuple[str, Price, str | None, float | None, float | None]] = [
    ("normal 8-GPU", Price(price=80.0), None, 10.0, 8.0),
    ("normal Spot", Price(rental="spot", price=24.0), None, 3.0, 8.0),
    (
        "Linux suffix",
        Price(
            "Standard_NC24ads_A100_v4", product="NCads A100 v4 Series Linux", price=4.0
        ),
        None,
        4.0,
        1.0,
    ),
    (
        "missing product name counts as Linux",
        Price("Standard_NC48ads_A100_v4", product=None, price=8.0),
        None,
        4.0,
        2.0,
    ),
    (
        "rental type before everything",
        Price("Standard_ND96is_noIB_H100_v5", rental="dev_test", product="X Windows"),
        "rental_type_not_compared",
        None,
        None,
    ),
    (
        "reservation",
        Price(rental="reservation", unit="1 Year term"),
        "rental_type_not_compared",
        None,
        8.0,
    ),
    ("low priority", Price(rental="other"), "rental_type_not_compared", None, 8.0),
    (
        "government region",
        Price(region="usgovvirginia", rental="spot"),
        "government_cloud",
        None,
        8.0,
    ),
    ("DoD region", Price(region="usdodeast"), "government_cloud", None, 8.0),
    (
        "Windows",
        Price(product="Virtual Machines NDsr H100 v5 Series Windows"),
        "windows",
        None,
        8.0,
    ),
    (
        "Win",
        Price("Standard_NCC40ads_H100_v5", product="Virtual Machines NCCadsv5 Srs Win"),
        "windows",
        None,
        1.0,
    ),
    ("not hourly", Price(unit="1/Month"), "unit_not_hourly", None, 8.0),
    (
        "unmapped",
        Price("Standard_ND96is_noIB_H100_v5"),
        "unmapped_sku",
        None,
        None,
    ),
    ("fractional", Price("Standard_NV18ads_A10_v5"), "fractional_gpu", None, 0.5),
    ("retired", Price("Standard_NC24s_v3"), "retired_size", None, 4.0),
    (
        "retired fractional is fractional",
        Price("Standard_NV16as_v4"),
        "fractional_gpu",
        None,
        0.5,
    ),
]


@pytest.mark.parametrize(
    ("case", "price", "reason", "per_gpu", "count"), CASES, ids=[c[0] for c in CASES]
)
def test_known_answers(
    case: str,
    price: Price,
    reason: str | None,
    per_gpu: float | None,
    count: float | None,
) -> None:
    outcome = classify(price)
    assert outcome.excluded_reason == reason
    assert outcome.usd_per_gpu_hour == per_gpu
    assert outcome.gpu_count == count
    # A mapped size names its map row even when excluded (design D12).
    assert (outcome.arm_sku_name is not None) == (price.size in MAP)


def test_variant_label_from_the_map() -> None:
    outcome = classify(Price("Standard_NCC40ads_H100_v5", price=5.0))
    assert outcome.gpu_model == "H100 NVL 94GB confidential"
    assert outcome.usd_per_gpu_hour == 5.0


def test_retired_by_snapshot_date() -> None:
    size = Price("Standard_NC24s_v3", price=12.0)
    assert classify(size, date(2025, 9, 29)).usd_per_gpu_hour == 3.0
    assert classify(size, date(2025, 9, 30)).excluded_reason == "retired_size"


def test_regional_extension() -> None:
    uae = Price("Standard_NV12s_v3", region="uaenorth", price=2.0)
    europe = Price("Standard_NV12s_v3", region="westeurope", price=2.0)
    assert classify(uae).excluded_reason is None
    assert classify(europe).excluded_reason == "retired_size"
    assert classify(uae, date(2027, 1, 31)).excluded_reason == "retired_size"


def test_unknown_reason_in_rules_is_an_error() -> None:
    params = {**P, "exclusion_order": ["cheap_looking", *P["exclusion_order"]]}
    observation = normalize.AzureObservation(
        "Standard_ND96isr_H100_v5",
        "westeurope",
        "on_demand",
        80.0,
        "1 Hour",
        None,
        DAY.date(),
    )
    with pytest.raises(KeyError, match="cheap_looking"):
        normalize.classify_azure(observation, MAP, params)


@pytest.mark.parametrize(
    ("offer", "reason", "per_gpu", "model"),
    [
        (("on_demand", 4.0, "H100 SXM", 2, 80.0), None, 2.0, "H100 NVLink 80GB"),
        (("spot", 0.3, "RTX 4090", 1, 24.0), None, 0.3, "RTX 4090 24GB"),
        (("on_demand", 4.0, "Mystery 9000", 1, 80.0), "unmapped_gpu_name", None, None),
        (("on_demand", 4.0, "A100 SXM", 1, 40.0), "unmapped_gpu_name", None, None),
        (("on_demand", 4.0, "A100 SXM", 1, None), "unmapped_gpu_name", None, None),
        (
            ("reservation", 4.0, "H100 SXM", 1, 80.0),
            "rental_type_not_compared",
            None,
            "H100 NVLink 80GB",
        ),
    ],
)
def test_marketplace_known_answers(
    offer: tuple[str, float, str, int, float | None],
    reason: str | None,
    per_gpu: float | None,
    model: str | None,
) -> None:
    outcome = normalize.classify_marketplace(
        normalize.MarketplaceObservation(*offer), P
    )
    assert outcome.excluded_reason == reason
    assert outcome.usd_per_gpu_hour == per_gpu
    assert outcome.gpu_model == model
    assert outcome.gpu_count == float(offer[3])
    assert outcome.arm_sku_name is None


def rows(con: duckdb.DuckDBPyConnection) -> dict[str, tuple[Any, ...]]:
    found = con.execute(
        "SELECT item_key, excluded_reason, usd_per_gpu_hour, gpu_model, gpu_count,"
        " mapping_version, arm_sku_name, exclusions FROM normalized_price"
    ).fetchall()
    return {row[0]: row[1:] for row in found}


def test_database_step_writes_one_row_each(con: duckdb.DuckDBPyConnection) -> None:
    prices = [case[1] for case in CASES[:3]] + [Price("Standard_ND96is_noIB_H100_v5")]
    prices = [Price(**{**p.__dict__, "meter": f"m{i}"}) for i, p in enumerate(prices)]
    azure_run(con, "run-1", prices)
    result = normalize.normalize_pending(con, NOW)
    assert result.written == 4
    assert result.rules_written and result.map_rows_written == 51
    assert result.by_status == {"normalized": 3, "unmapped_sku": 1}
    assert result.unmapped_sizes == ["Standard_ND96is_noIB_H100_v5"]
    stored = rows(con)
    normal = stored[prices[0].key()]
    assert normal[:6] == (
        None,
        10.0,
        "H100 NVLink 80GB",
        8.0,
        "gpu-map-v1",
        "Standard_ND96isr_H100_v5",
    )
    assert normal[6] == P["exclusions"]
    assert stored[prices[3].key()][:6] == ("unmapped_sku", None, None, None, None, None)
    assert all(v.passed for v in checks.run(con, "groups-v1"))


def test_rerun_writes_nothing(con: duckdb.DuckDBPyConnection) -> None:
    azure_run(con, "run-1", [Price()])
    normalize.normalize_pending(con, NOW)
    again = normalize.normalize_pending(con, NOW)
    assert again.written == 0
    assert not again.rules_written and again.map_rows_written == 0
    azure_run(
        con, "run-2", [Price(price=88.0)], started=datetime(2026, 10, 13, tzinfo=UTC)
    )
    assert normalize.normalize_pending(con, NOW).written == 1


def test_error_rolls_everything_back(
    con: duckdb.DuckDBPyConnection, monkeypatch: pytest.MonkeyPatch
) -> None:
    azure_run(con, "run-1", [Price()])

    def broken(*args: object) -> None:
        raise RuntimeError("disk full (simulated)")

    monkeypatch.setattr(normalize, "_write", broken)
    with pytest.raises(RuntimeError, match="simulated"):
        normalize.normalize_pending(con, NOW)
    for table in ("normalized_price", "rule_set", "gpu_sku_map"):
        assert con.execute(f"SELECT count(*) FROM {table}").fetchone() == (0,)  # noqa: S608


def test_changed_rules_refused(con: duckdb.DuckDBPyConnection) -> None:
    azure_run(con, "run-1", [Price()])
    normalize.normalize_pending(con, NOW)
    with pytest.raises(rules.FrozenMismatch):
        normalize.normalize_pending(con, NOW, {**P, "thin_below_regions": 3})
    assert con.execute("SELECT count(*) FROM normalized_price").fetchone() == (1,)


def test_non_primary_never_reaches_normalized(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    # The real fetch loop and ingest, on a synthetic page: ingest rejects the item.
    primary = item(armSkuName="Standard_NC40ads_H100_v5")
    secondary = item(
        meterId="00000000-0000-0000-0000-00000000000e", isPrimaryMeterRegion=False
    )
    result, _, _ = collect(tmp_path, [ok(page_bytes([primary, secondary]))])
    ingested = ingest.ingest_run(con, tmp_path, result.run_id)
    assert ingested.tallies[("rejected", "not_primary_meter")] == 1
    normalized = normalize.normalize_pending(con, NOW)
    assert normalized.written == 1
    assert normalized.by_status == {"normalized": 1}
    assert all(v.passed for v in checks.run(con, "groups-v1"))


def test_command_prints_counts_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "monitor.duckdb"
    con = db.connect(path)
    db.create_schema(con)
    azure_run(
        con,
        "run-1",
        [Price(price=123.25), Price("Standard_NV18ads_A10_v5", meter="m2", price=7.5)],
    )
    con.close()
    assert normalize.main(["--db", str(path)], now=NOW) == 0
    out = capsys.readouterr().out
    assert "normalized: 1" in out and "fractional_gpu: 1" in out
    assert "check multiply_back: pass" in out
    for value in ("123.25", "15.40625", "7.5", "15.0"):
        assert value not in out


def test_command_refuses_missing_db_and_changed_rules(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    assert normalize.main(["--db", str(tmp_path / "none.duckdb")], now=NOW) == 2
    path = tmp_path / "monitor.duckdb"
    con = db.connect(path)
    db.create_schema(con)
    azure_run(con, "run-1", [Price()])
    con.close()
    assert normalize.main(["--db", str(path)], now=NOW) == 0
    monkeypatch.setattr(rules, "GROUPS_V1", {**P, "stale_after_days": 3})
    assert normalize.main(["--db", str(path)], now=NOW) == 2
    assert "refused" in capsys.readouterr().err


def test_command_fails_when_a_check_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "monitor.duckdb"
    con = db.connect(path)
    db.create_schema(con)
    azure_run(con, "run-1", [Price()])
    con.close()
    failing = checks.Verdict("planted", 1, failed=1, failures=["planted failure"])
    monkeypatch.setattr(checks, "run", lambda *_: [failing])
    assert normalize.main(["--db", str(path)], now=NOW) == 1
