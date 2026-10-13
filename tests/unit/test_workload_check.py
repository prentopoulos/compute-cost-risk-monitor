"""The independent check of workload figures (phase-5-calculator D19).

Inputs and figures are written out by hand here, with invented round prices (synthetic),
so the check is tested without the calculator. The round trip from the calculator
through the page's figures is tested in test_workload_view.
"""

import ast
import dataclasses
import math
from pathlib import Path

import pytest

from compute_cost_risk_monitor import workload_check
from compute_cost_risk_monitor.workload_check import (
    ADDITIONAL,
    LOWER,
    NO_CHANGE,
    Figures,
    Inputs,
    RowFigures,
    check,
)

KEY = "m|Standard_ND96isr_H100_v5|westeurope|on_demand"
REFUSED = "not computed: the price would be zero or below"
UNLISTED = "not computed: no pay-as-you-go listing for this size in this region"

# 8 GPUs (one 8-GPU VM at USD 20 per VM-hour, so 2.5 USD/GPU-hour) for 100 hours.
INPUTS = Inputs(
    gpus=8,
    hours=100.0,
    storage=None,
    item_key=KEY,
    vm_price=20.0,
    gpus_per_vm=8,
    spot=False,
    payg_vm_price=None,
    custom=None,
    budget=None,
)
ROWS = (
    RowFigures("decline-25", 1.875, -0.625, -25.0, 1_500.0, -500.0, None, LOWER),
    RowFigures("increase-25", 3.125, 0.625, 25.0, 2_500.0, 500.0, None, ADDITIONAL),
    RowFigures("example-050", 3.0, 0.5, 20.0, 2_400.0, 400.0, None, ADDITIONAL),
    RowFigures("spike-100", 5.0, 2.5, 100.0, 4_000.0, 2_000.0, None, ADDITIONAL),
)
FIGURES = Figures(KEY, 2.5, 1, 2_000.0, None, 2_000.0, ROWS, None, None, None)


def with_row(figures: Figures, index: int, **changes: object) -> Figures:
    rows = list(figures.rows)
    rows[index] = dataclasses.replace(rows[index], **changes)  # type: ignore[arg-type]
    return dataclasses.replace(figures, rows=tuple(rows))


def test_correct_figures_pass() -> None:
    assert check(INPUTS, FIGURES) == []


@pytest.mark.parametrize(
    ("changes", "failure"),
    [
        ({"item_key": "m|another size"}, "starting member"),
        ({"start": 2.6}, "starting price"),
        ({"vms": 2}, "VM count"),
        ({"compute": 2_000.01}, "compute cost"),
        ({"storage": 150.0}, "storage"),
        ({"total": 2_000.01}, "total"),
        ({"rows": ROWS[:3]}, "scenario rows"),
        ({"rows": tuple(reversed(ROWS))}, "scenario rows"),
        ({"headroom_above_payg": 3.0}, "headroom without a budget"),
    ],
)
def test_tampered_totals_caught(changes: dict[str, object], failure: str) -> None:
    tampered = dataclasses.replace(FIGURES, **changes)  # type: ignore[arg-type]
    assert failure in check(INPUTS, tampered)


@pytest.mark.parametrize(
    ("field", "value", "failure"),
    [
        ("exposure", -499.99, "decline-25 exposure"),
        ("exposure", -499.99, "decline-25 exposure against costs"),
        ("price", 1.88, "decline-25 price"),
        ("change", -0.62, "decline-25 change"),
        ("change_pct", -24.9, "decline-25 change %"),
        ("cost", 1_500.01, "decline-25 cost"),
        ("exposure", None, "decline-25 missing"),
        ("effect", ADDITIONAL, "decline-25 effect"),
        ("above_payg", 99.0, "decline-25 note"),  # no note on a pay-as-you-go start
    ],
)
def test_tampered_row_caught_and_named(field: str, value: object, failure: str) -> None:
    assert failure in check(INPUTS, with_row(FIGURES, 0, **{field: value}))


def test_non_finite_figure_caught() -> None:
    failed = check(INPUTS, with_row(FIGURES, 1, exposure=math.nan))
    assert failed == ["finite: increase-25 exposure"]


def test_storage_is_added_to_every_cost() -> None:
    inputs = dataclasses.replace(INPUTS, storage=150.0)
    rows = tuple(dataclasses.replace(r, cost=(r.cost or 0) + 150.0) for r in ROWS)
    figures = dataclasses.replace(FIGURES, storage=150.0, total=2_150.0, rows=rows)
    assert check(inputs, figures) == []
    failed = check(inputs, FIGURES)
    assert "storage" in failed and "total" in failed


def test_a_large_storage_amount_never_hides_a_cent() -> None:
    # 8 GPUs x 10 h at 12 USD/GPU-hour (96 per VM-hour) with USD 10,000,000 of storage.
    storage = 10_000_000.0
    inputs = dataclasses.replace(INPUTS, hours=10.0, vm_price=96.0, storage=storage)
    gpu_hours = 80.0

    def row(ident: str, price: float, change: float, effect: str) -> RowFigures:
        return RowFigures(
            ident,
            price,
            change,
            change / 12.0 * 100,
            gpu_hours * price + storage,
            gpu_hours * change,
            None,
            effect,
        )

    rows = (
        row("decline-25", 9.0, -3.0, LOWER),
        row("increase-25", 15.0, 3.0, ADDITIONAL),
        row("example-050", 12.5, 0.5, ADDITIONAL),
        row("spike-100", 24.0, 12.0, ADDITIONAL),
    )
    total = gpu_hours * 12.0 + storage
    figures = Figures(KEY, 12.0, 1, 960.0, storage, total, rows, None, None, None)
    assert check(inputs, figures) == []
    example = rows[2]
    tampered = with_row(
        figures,
        2,
        exposure=(example.exposure or 0) + 0.01,
        cost=(example.cost or 0) + 0.01,
    )
    failed = check(inputs, tampered)
    assert "example-050 exposure" in failed
    assert "example-050 cost" in failed


def test_refused_row_must_carry_no_figure_and_say_so() -> None:
    # A custom change of -3 USD/GPU-hour takes 2.5 below zero.
    inputs = dataclasses.replace(INPUTS, custom=("usd", -3.0))
    refused = RowFigures("custom", None, None, None, None, None, None, REFUSED)
    assert check(inputs, dataclasses.replace(FIGURES, rows=(*ROWS, refused))) == []
    shown = RowFigures("custom", -0.5, -3.0, -120.0, -400.0, -2_400.0, None, LOWER)
    failed = check(inputs, dataclasses.replace(FIGURES, rows=(*ROWS, shown)))
    assert "custom refused" in failed
    unlabelled = dataclasses.replace(refused, effect=LOWER)
    failed = check(inputs, dataclasses.replace(FIGURES, rows=(*ROWS, unlabelled)))
    assert failed == ["custom effect"]
    noted = dataclasses.replace(refused, above_payg=4.0)
    failed = check(inputs, dataclasses.replace(FIGURES, rows=(*ROWS, noted)))
    assert failed == ["custom note"]


def test_a_price_within_rounding_of_zero_may_be_refused_or_shown() -> None:
    # -2.5 USD/GPU-hour on 2.5 is exactly zero here, and within rounding of it for a
    # calculator whose stored starting price differs in the last place.
    inputs = dataclasses.replace(INPUTS, custom=("usd", -2.5))
    refused = RowFigures("custom", None, None, None, None, None, None, REFUSED)
    assert check(inputs, dataclasses.replace(FIGURES, rows=(*ROWS, refused))) == []


def test_unknown_row_is_a_failed_definition() -> None:
    odd = RowFigures("mystery", 3.0, 0.5, 20.0, 2_400.0, 400.0, None, ADDITIONAL)
    failed = check(INPUTS, dataclasses.replace(FIGURES, rows=(*ROWS, odd)))
    assert "mystery definition" in failed
    assert "scenario rows" in failed


def test_custom_change_of_an_unknown_kind_is_a_failed_definition() -> None:
    inputs = dataclasses.replace(INPUTS, custom=("per-day", 0.5))
    row = RowFigures("custom", 3.0, 0.5, 20.0, 2_400.0, 400.0, None, ADDITIONAL)
    failed = check(inputs, dataclasses.replace(FIGURES, rows=(*ROWS, row)))
    assert failed == ["custom definition"]


# Spot: one 8-GPU VM at USD 8 per VM-hour (1.0 USD/GPU-hour) for 10 hours; the same
# size on pay-as-you-go at USD 32 per VM-hour (4.0 USD/GPU-hour).
SPOT = dataclasses.replace(
    INPUTS, hours=10.0, vm_price=8.0, spot=True, payg_vm_price=32.0
)
SPOT_ROWS = (
    RowFigures("decline-25", 0.75, -0.25, -25.0, 60.0, -20.0, None, LOWER),
    RowFigures("increase-25", 1.25, 0.25, 25.0, 100.0, 20.0, None, ADDITIONAL),
    RowFigures("example-050", 1.5, 0.5, 50.0, 120.0, 40.0, None, ADDITIONAL),
    RowFigures("spike-100", 2.0, 1.0, 100.0, 160.0, 80.0, None, ADDITIONAL),
    RowFigures("fallback", 4.0, 3.0, 300.0, 320.0, 240.0, None, ADDITIONAL),
)
SPOT_FIGURES = Figures(KEY, 1.0, 1, 80.0, None, 80.0, SPOT_ROWS, None, None, None)


def test_spot_fallback_passes_and_tampering_is_caught() -> None:
    assert check(SPOT, SPOT_FIGURES) == []
    assert "fallback exposure" in check(SPOT, with_row(SPOT_FIGURES, 4, exposure=239.0))
    assert "fallback note" in check(SPOT, with_row(SPOT_FIGURES, 4, above_payg=4.0))


def test_missing_fallback_must_not_be_filled_in() -> None:
    unlisted = dataclasses.replace(SPOT, payg_vm_price=None)
    empty = RowFigures("fallback", None, None, None, None, None, None, UNLISTED)
    assert check(unlisted, with_row(SPOT_FIGURES, 4, **vars(empty))) == []
    assert "fallback refused" in check(unlisted, SPOT_FIGURES)


def test_note_must_appear_exactly_above_pay_as_you_go() -> None:
    # Pay-as-you-go at 1.5 USD/GPU-hour: the example (1.5) is at the boundary, and the
    # spike (2.0) is above it.
    inputs = dataclasses.replace(SPOT, payg_vm_price=12.0)
    rows = (*SPOT_ROWS[:3], dataclasses.replace(SPOT_ROWS[3], above_payg=1.5))
    fallback = RowFigures("fallback", 1.5, 0.5, 50.0, 120.0, 40.0, None, ADDITIONAL)
    figures = dataclasses.replace(SPOT_FIGURES, rows=(*rows, fallback))
    assert check(inputs, figures) == []
    assert "spike-100 note" in check(inputs, with_row(figures, 3, above_payg=None))
    assert "decline-25 note" in check(inputs, with_row(figures, 0, above_payg=1.5))


def test_equal_spot_and_pay_as_you_go_read_no_change() -> None:
    inputs = dataclasses.replace(SPOT, payg_vm_price=8.0)
    fallback = RowFigures("fallback", 1.0, 0.0, 0.0, 80.0, 0.0, None, NO_CHANGE)
    rows = tuple(
        dataclasses.replace(r, above_payg=1.0) if (r.price or 0) > 1.0 else r
        for r in SPOT_ROWS[:4]
    )
    figures = dataclasses.replace(SPOT_FIGURES, rows=(*rows, fallback))
    assert check(inputs, figures) == []
    wrong = with_row(figures, 4, effect=ADDITIONAL)
    assert "fallback effect" in check(inputs, wrong)


def test_headroom_checked() -> None:
    inputs = dataclasses.replace(INPUTS, gpus=32, hours=720.0, budget=11_520.0)
    rows = tuple(
        dataclasses.replace(
            r,
            cost=32 * 720 * (r.price or 0),
            exposure=32 * 720 * (r.change or 0),
        )
        for r in ROWS
    )
    figures = Figures(KEY, 2.5, 4, 57_600.0, None, 57_600.0, rows, 0.5, 20.0, None)
    assert check(inputs, figures) == []
    assert "headroom" in check(inputs, dataclasses.replace(figures, headroom=0.51))
    assert "headroom %" in check(
        inputs, dataclasses.replace(figures, headroom_pct=21.0)
    )
    assert "headroom %" in check(
        inputs, dataclasses.replace(figures, headroom_pct=None)
    )
    assert "headroom note" in check(
        inputs, dataclasses.replace(figures, headroom_above_payg=3.0)
    )
    assert "headroom without a budget" in check(
        dataclasses.replace(inputs, budget=None), figures
    )


def test_check_imports_no_calculator_code() -> None:
    source = Path(workload_check.__file__).read_text(encoding="utf-8")
    imported: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
            imported.extend(f"{node.module}.{alias.name}" for alias in node.names)
    assert imported
    assert not any("calculator" in name for name in imported)
    assert "compute_cost_risk_monitor.scenarios" in imported
