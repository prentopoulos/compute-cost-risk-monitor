"""The independent checks: pass on honest rows, and catch each kind of planted damage.

Rows are synthetic. Each test normalizes a small run, damages one stored row the way a
bug would, and expects exactly the matching check to fail.
"""

from collections.abc import Iterator
from datetime import UTC, datetime

import duckdb
import pytest

from compute_cost_risk_monitor import checks, normalize
from seed import Price, azure_run, database

NOW = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
NORMAL = Price(meter="a", price=80.0)
FRACTIONAL = Price("Standard_NV18ads_A10_v5", meter="b", price=1.0)
UNMAPPED = Price("Standard_ND96is_noIB_H100_v5", meter="c")


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
    assert set(found) == {"reason_or_price"}
    assert len(found["reason_or_price"]) == 2


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
        "compared_rows_follow_rules": [f"azure-retail {NORMAL.key()}: Windows product"]
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
