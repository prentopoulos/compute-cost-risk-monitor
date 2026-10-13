"""The independent checks: pass on honest rows, and catch each kind of planted damage.

Rows are synthetic. Each test normalizes a small run, damages one stored row the way a
bug would, and expects exactly the matching check to fail.
"""

from collections.abc import Iterator
from datetime import UTC, datetime

import duckdb
import pytest

from compute_cost_risk_monitor import checks, gpu_map, normalize, rules, synthetic
from seed import Price, azure_run, database
from support import FIXTURES

NOW = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
NORMAL = Price(meter="a", price=80.0)
FRACTIONAL = Price("Standard_NV18ads_A10_v5", meter="b", price=1.0)
UNMAPPED = Price("Standard_ND96is_noIB_H100_v5", meter="c")
SNAPSHOT = FIXTURES / "marketplace" / "snapshot-1.json"


@pytest.fixture
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    connection = database()
    azure_run(connection, "run-1", [NORMAL, FRACTIONAL, UNMAPPED])
    normalize.normalize_pending(connection, NOW)
    yield connection
    connection.close()


def failing(con: duckdb.DuckDBPyConnection) -> dict[str, list[str]]:
    return {v.name: v.failures for v in checks.run(con, "groups-v1") if not v.passed}


def test_honest_rows_pass(con: duckdb.DuckDBPyConnection) -> None:
    verdicts = checks.run(con, "groups-v1")
    assert [v.name for v in verdicts] == [c.__name__ for c in checks.CHECKS]
    assert all(v.passed for v in verdicts)
    assert {v.name: v.checked for v in verdicts}["one_row_per_observation"] == 3


def test_tampered_price_caught(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        "UPDATE normalized_price SET usd_per_gpu_hour = usd_per_gpu_hour * 1.001"
        " WHERE item_key = ?",
        [NORMAL.key()],
    )
    assert failing(con) == {"multiply_back": [f"azure-retail {NORMAL.key()}"]}


def test_missing_row_caught(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("DELETE FROM normalized_price WHERE item_key = ?", [UNMAPPED.key()])
    found = failing(con)
    assert set(found) == {"one_row_per_observation", "totals_reconcile"}
    assert found["one_row_per_observation"] == [
        f"azure-retail {UNMAPPED.key()}: 0 rows"
    ]


def test_wrong_gpu_count_caught(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        "UPDATE normalized_price SET gpu_count = 4, usd_per_gpu_hour = 20"
        " WHERE item_key = ?",
        [NORMAL.key()],
    )
    assert set(failing(con)) == {"gpu_fields_match"}


def test_unknown_reason_and_text_caught(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        "UPDATE normalized_price SET excluded_reason = 'looks_expensive'"
        " WHERE item_key = ?",
        [FRACTIONAL.key()],
    )
    con.execute(
        "UPDATE normalized_price SET exclusions = 'none' WHERE item_key = ?",
        [UNMAPPED.key()],
    )
    found = failing(con)
    # The text change and the unknown reason both fail reason_or_price; the unknown
    # reason also disagrees with the re-derived one.
    assert set(found) == {"reason_or_price", "reasons_rederived"}
    assert len(found["reason_or_price"]) == 2
    assert found["reasons_rederived"] == [
        f"azure-retail {FRACTIONAL.key()}: reason looks_expensive,"
        " rules give fractional_gpu"
    ]


def test_unmapped_row_with_gpu_fields_caught(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        "UPDATE normalized_price SET gpu_model = 'H100 NVLink 80GB', gpu_count = 8"
        " WHERE item_key = ?",
        [UNMAPPED.key()],
    )
    assert set(failing(con)) == {"gpu_fields_match"}


def test_compared_row_breaking_rules_caught(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        "UPDATE azure_retail_price SET product_name = 'Virtual Machines X Windows'"
        " WHERE item_key = ?",
        [NORMAL.key()],
    )
    assert failing(con) == {
        "reasons_rederived": [
            f"azure-retail {NORMAL.key()}: reason None, rules give windows"
        ],
        "compared_rows_follow_rules": [f"azure-retail {NORMAL.key()}: Windows product"],
    }


def test_broken_totals_caught(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        "UPDATE collection_run_summary SET observations_stored = 4, items_seen = 4"
        " WHERE run_id = 'run-1'"
    )
    assert failing(con) == {"totals_reconcile": ["run run-1: summary says 4, found 3"]}


def test_failures_list_is_capped() -> None:
    verdict = checks.Verdict("x", 10)
    for n in range(8):
        verdict.fail(str(n))
    assert verdict.failed == 8 and len(verdict.failures) == checks.SHOWN
    assert not verdict.passed


def test_missing_rule_set(con: duckdb.DuckDBPyConnection) -> None:
    with pytest.raises(KeyError, match="groups-v9"):
        checks.run(con, "groups-v9")


def test_checker_catches_a_classifier_that_ignores_the_rules() -> None:
    # Store the real rules under a test version, then write rows from a classifier that
    # ignores most of them: the checker, reading the stored rules, must catch each one.
    con = database()
    bad = [
        Price(meter="r", rental="reservation", unit="1 Year term"),
        Price(meter="g", region="usgovarizona"),
        Price(meter="u", unit="1/Month"),
        Price(meter="w", product="Virtual Machines NDsr H100 v5 Series Windows"),
        Price("Standard_NV18ads_A10_v5", meter="f"),
    ]
    azure_run(con, "run-1", bad)
    strict = {**rules.GROUPS_V1, "rule_version": "groups-test"}
    lax = {
        **strict,
        "compared_rental_types": ["on_demand", "spot", "reservation"],
        "exclusion_order": ["unmapped_sku"],
    }
    mapping = gpu_map.load()
    rules.store(con, NOW, strict)
    gpu_map.store(con, mapping)
    normalize._write(con, lax, normalize._rows(con, lax, mapping))
    found = failing_for(con, "groups-test")
    # Excluded-looking rows are now "compared"; the rule checks see why.
    assert set(found) == {"reasons_rederived", "compared_rows_follow_rules"}
    assert len(found["reasons_rederived"]) == 5
    reasons = sorted(f.split(": ", 1)[1] for f in found["compared_rows_follow_rules"])
    assert reasons == [
        "GPU count is not whole",
        "Windows product",
        "government region usgovarizona",
        "rental type reservation is not compared",
        "unit is not hourly",
    ]


def test_map_version_and_offer_mismatches_caught() -> None:
    con = database()
    azure_run(con, "run-1", [NORMAL])
    normalize.normalize_pending(con, NOW)
    con.execute(
        "INSERT INTO gpu_sku_map SELECT 'gpu-map-v0', arm_sku_name, gpu_model,"
        " gpu_form_factor, gpu_vram_gb, gpu_count, source_url, notes FROM gpu_sku_map"
    )
    con.execute("UPDATE normalized_price SET mapping_version = 'gpu-map-v0'")
    assert failing(con) == {
        "gpu_fields_match": [
            f"azure-retail {NORMAL.key()}: does not use the map row for"
            " Standard_ND96isr_H100_v5"
        ]
    }
    market = database()
    synthetic.ingest_snapshot(market, SNAPSHOT)
    normalize.normalize_pending(market, NOW)
    market.execute(
        "UPDATE normalized_price SET gpu_model = 'H100 PCIe 80GB'"
        " WHERE item_key = 'S-101'"
    )
    assert failing(market) == {
        "gpu_fields_match": [
            "synthetic-marketplace S-101: GPU fields differ from the offer"
        ]
    }


def failing_for(con: duckdb.DuckDBPyConnection, version: str) -> dict[str, list[str]]:
    return {v.name: v.failures for v in checks.run(con, version) if not v.passed}


def test_wrong_map_row_caught() -> None:
    # A classifier that picks another size's map row; every figure still
    # multiplies back.
    con = database()
    azure_run(con, "run-1", [NORMAL])
    normalize.normalize_pending(con, NOW)
    con.execute(
        "UPDATE normalized_price SET arm_sku_name = 'Standard_NC24s_v3',"
        " gpu_model = 'V100 16GB', gpu_count = 4, usd_per_gpu_hour = 20"
    )
    found = failing(con)
    assert found["gpu_fields_match"] == [
        f"azure-retail {NORMAL.key()}: does not use the map row for"
        " Standard_ND96isr_H100_v5"
    ]
    assert "multiply_back" not in found


def test_mapped_size_marked_unmapped_caught() -> None:
    con = database()
    azure_run(con, "run-1", [NORMAL])
    normalize.normalize_pending(con, NOW)
    con.execute(
        "UPDATE normalized_price SET excluded_reason = 'unmapped_sku',"
        " usd_per_gpu_hour = NULL, gpu_model = NULL, gpu_count = NULL,"
        " mapping_version = NULL, arm_sku_name = NULL"
    )
    found = failing(con)
    assert set(found) == {"gpu_fields_match", "reasons_rederived"}
    assert found["reasons_rederived"] == [
        f"azure-retail {NORMAL.key()}: reason unmapped_sku, rules give None"
    ]


def test_retired_size_compared_caught() -> None:
    # A classifier that ignores retirements: only the re-derived reason sees it.
    con = database()
    retired = Price("Standard_NC24s_v3", meter="r", price=12.0)
    azure_run(con, "run-1", [retired])
    strict = {**rules.GROUPS_V1, "rule_version": "groups-test"}
    lax = {
        **strict,
        "exclusion_order": [
            r for r in strict["exclusion_order"] if r != "retired_size"
        ],
    }
    mapping = gpu_map.load()
    rules.store(con, NOW, strict)
    gpu_map.store(con, mapping)
    normalize._write(con, lax, normalize._rows(con, lax, mapping))
    assert failing_for(con, "groups-test") == {
        "reasons_rederived": [
            f"azure-retail {retired.key()}: reason None, rules give retired_size"
        ]
    }


def test_wrong_source_and_wrong_order_reasons_caught() -> None:
    con = database()
    gov_windows = Price(
        meter="gw", region="usgovvirginia", product="Virtual Machines X Windows"
    )
    azure_run(con, "run-1", [UNMAPPED, gov_windows])
    normalize.normalize_pending(con, NOW)
    con.execute(
        "UPDATE normalized_price SET excluded_reason = 'unmapped_gpu_name'"
        " WHERE item_key = ?",
        [UNMAPPED.key()],
    )
    con.execute(
        "UPDATE normalized_price SET excluded_reason = 'windows' WHERE item_key = ?",
        [gov_windows.key()],
    )
    found = failing(con)
    assert found["reason_or_price"] == [
        f"azure-retail {UNMAPPED.key()}: reason unmapped_gpu_name is not one of its"
        " source's"
    ]
    assert sorted(found["reasons_rederived"]) == sorted(
        [
            f"azure-retail {UNMAPPED.key()}: reason unmapped_gpu_name, rules give"
            " unmapped_sku",
            f"azure-retail {gov_windows.key()}: reason windows, rules give"
            " government_cloud",
        ]
    )


def test_checker_refuses_a_reason_it_cannot_test() -> None:
    con = database()
    azure_run(con, "run-1", [NORMAL])
    params = {
        **rules.GROUPS_V1,
        "rule_version": "groups-test",
        "exclusion_order": ["looks_odd", *rules.GROUPS_V1["exclusion_order"]],
    }
    mapping = gpu_map.load()
    rules.store(con, NOW, params)
    gpu_map.store(con, mapping)
    safe = {**params, "exclusion_order": rules.GROUPS_V1["exclusion_order"]}
    normalize._write(con, safe, normalize._rows(con, safe, mapping))
    assert failing_for(con, "groups-test")["reasons_rederived"] == [
        f"azure-retail {NORMAL.key()}: the checker cannot test looks_odd"
    ]
