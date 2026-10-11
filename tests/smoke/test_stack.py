"""Smoke tests: the decided stack imports and works together.

Synthetic data only; no network or credentials.
"""

import importlib
from pathlib import Path

import duckdb
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest


@pytest.mark.parametrize(
    "module", ["pandas", "duckdb", "streamlit", "compute_cost_risk_monitor"]
)
def test_imports(module: str) -> None:
    assert importlib.import_module(module) is not None


def test_package_is_installed_from_src() -> None:
    import compute_cost_risk_monitor

    assert compute_cost_risk_monitor.__file__ is not None
    assert Path(compute_cost_risk_monitor.__file__).parent.parent.name == "src"


def test_pandas_duckdb_round_trip_keeps_values_and_dtypes() -> None:
    frame = pd.DataFrame(
        {
            "offer_id": pd.array([1, 2, 3], dtype="int64"),
            "usd_per_gpu_hour": [0.5, 1.25, 2.0],
            "gpu": ["H100", "A100", "RTX 4090"],
            "retrieved_at": pd.to_datetime(
                [
                    "2026-10-11T00:00:00Z",
                    "2026-10-11T01:00:00Z",
                    "2026-10-11T02:00:00Z",
                ]
            ),
        }
    )
    con = duckdb.connect(":memory:")
    # DuckDB returns TIMESTAMPTZ in the session time zone (default: the machine's).
    con.execute("SET TimeZone = 'UTC'")
    con.register("offers", frame)

    result = con.execute("SELECT * FROM offers ORDER BY offer_id").df()

    assert result.dtypes.to_dict() == {
        "offer_id": "int64",
        "usd_per_gpu_hour": "float64",
        "gpu": pd.StringDtype(na_value=float("nan")),
        "retrieved_at": "datetime64[us, UTC]",
    }
    pd.testing.assert_frame_equal(result, frame)


def _trivial_app() -> None:
    import streamlit as st

    st.write("smoke")


def test_streamlit_script_runs_headlessly() -> None:
    at = AppTest.from_function(_trivial_app).run(timeout=30)

    assert not at.exception
    assert [element.value for element in at.markdown] == ["smoke"]
