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
from compute_cost_risk_monitor.scenarios import LADDER_V1
from compute_cost_risk_monitor.workload_check import (
    ADDITIONAL,
    LOWER,
    NO_CHANGE,
    Figures,
    Inputs,
    LadderFigures,
    LadderRowFigures,
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


def ladder_for(inputs: Inputs) -> LadderFigures:
    """A correct ladder for these inputs, in USD/GPU-hour rather than the check's
    VM-hour form, so a test of the scenario rows fails only on what it tampers with.
    The ladder tests below pin it to hand-worked cells."""
    per_vm = inputs.gpus_per_vm
    start = inputs.vm_price / per_vm
    payg = None if inputs.payg_vm_price is None else inputs.payg_vm_price / per_vm
    defined = {n for n in (8, 16, 32, 64, 128) if n % per_vm == 0}
    columns = tuple(sorted(defined | {inputs.gpus}))

    def row(ident: str, price: float, refusal: str, mark: bool) -> LadderRowFigures:
        if price <= 0:
            return LadderRowFigures(ident, None, refusal)
        above = (
            payg if mark and inputs.spot and payg is not None and price > payg else None
        )
        cells = tuple(n * inputs.hours * (price - start) for n in columns)
        return LadderRowFigures(ident, cells, "", above)

    def moved(kind: str, magnitude: float) -> float:
        return start * (1 + magnitude / 100) if kind == "percent" else start + magnitude

    rows = [row(s.id, moved(s.kind, s.magnitude), REFUSED, True) for s in LADDER_V1]
    if inputs.spot:
        rows.append(row("fallback", payg or 0.0, UNLISTED, False))
    if inputs.custom is not None:
        rows.append(row("custom", moved(*inputs.custom), REFUSED, True))
    return LadderFigures(columns, inputs.gpus, tuple(rows))


def fit(inputs: Inputs, figures: Figures) -> Figures:
    """These figures with the correct ladder for these inputs."""
    return dataclasses.replace(figures, ladder=ladder_for(inputs))


FIGURES = Figures(
    KEY, 2.5, 1, 2_000.0, None, 2_000.0, ROWS, None, None, None, ladder_for(INPUTS)
)


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
    figures = Figures(
        KEY, 12.0, 1, 960.0, storage, total, rows, None, None, None, ladder_for(inputs)
    )
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
    base = fit(inputs, FIGURES)
    assert check(inputs, dataclasses.replace(base, rows=(*ROWS, refused))) == []
    shown = RowFigures("custom", -0.5, -3.0, -120.0, -400.0, -2_400.0, None, LOWER)
    failed = check(inputs, dataclasses.replace(base, rows=(*ROWS, shown)))
    assert "custom refused" in failed
    unlabelled = dataclasses.replace(refused, effect=LOWER)
    failed = check(inputs, dataclasses.replace(base, rows=(*ROWS, unlabelled)))
    assert failed == ["custom effect"]
    noted = dataclasses.replace(refused, above_payg=4.0)
    failed = check(inputs, dataclasses.replace(base, rows=(*ROWS, noted)))
    assert failed == ["custom note"]


def test_a_price_within_rounding_of_zero_may_be_refused_or_shown() -> None:
    # -2.5 USD/GPU-hour on 2.5 is exactly zero here, and within rounding of it for a
    # calculator whose stored starting price differs in the last place.
    inputs = dataclasses.replace(INPUTS, custom=("usd", -2.5))
    refused = RowFigures("custom", None, None, None, None, None, None, REFUSED)
    base = fit(inputs, FIGURES)
    assert check(inputs, dataclasses.replace(base, rows=(*ROWS, refused))) == []


def test_unknown_row_is_a_failed_definition() -> None:
    odd = RowFigures("mystery", 3.0, 0.5, 20.0, 2_400.0, 400.0, None, ADDITIONAL)
    failed = check(INPUTS, dataclasses.replace(FIGURES, rows=(*ROWS, odd)))
    assert "mystery definition" in failed
    assert "scenario rows" in failed


def test_custom_change_of_an_unknown_kind_is_a_failed_definition() -> None:
    inputs = dataclasses.replace(INPUTS, custom=("per-day", 0.5))
    row = RowFigures("custom", 3.0, 0.5, 20.0, 2_400.0, 400.0, None, ADDITIONAL)
    failed = check(inputs, dataclasses.replace(fit(inputs, FIGURES), rows=(*ROWS, row)))
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
SPOT_FIGURES = Figures(
    KEY, 1.0, 1, 80.0, None, 80.0, SPOT_ROWS, None, None, None, ladder_for(SPOT)
)


def test_spot_fallback_passes_and_tampering_is_caught() -> None:
    assert check(SPOT, SPOT_FIGURES) == []
    assert "fallback exposure" in check(SPOT, with_row(SPOT_FIGURES, 4, exposure=239.0))
    assert "fallback note" in check(SPOT, with_row(SPOT_FIGURES, 4, above_payg=4.0))


def test_missing_fallback_must_not_be_filled_in() -> None:
    unlisted = dataclasses.replace(SPOT, payg_vm_price=None)
    empty = RowFigures("fallback", None, None, None, None, None, None, UNLISTED)
    assert (
        check(unlisted, fit(unlisted, with_row(SPOT_FIGURES, 4, **vars(empty)))) == []
    )
    assert "fallback refused" in check(unlisted, SPOT_FIGURES)


def test_note_must_appear_exactly_above_pay_as_you_go() -> None:
    # Pay-as-you-go at 1.5 USD/GPU-hour: the example (1.5) is at the boundary, and the
    # spike (2.0) is above it.
    inputs = dataclasses.replace(SPOT, payg_vm_price=12.0)
    rows = (*SPOT_ROWS[:3], dataclasses.replace(SPOT_ROWS[3], above_payg=1.5))
    fallback = RowFigures("fallback", 1.5, 0.5, 50.0, 120.0, 40.0, None, ADDITIONAL)
    figures = fit(inputs, dataclasses.replace(SPOT_FIGURES, rows=(*rows, fallback)))
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
    figures = fit(inputs, dataclasses.replace(SPOT_FIGURES, rows=(*rows, fallback)))
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
    figures = Figures(
        KEY, 2.5, 4, 57_600.0, None, 57_600.0, rows, 0.5, 20.0, None, ladder_for(inputs)
    )
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


# --- the scenario ladder ladder-v1 (phase-7 D20) ---


def ladder_row(figures: Figures, row_id: str) -> LadderRowFigures:
    return next(row for row in figures.ladder.rows if row.id == row_id)


def with_ladder_row(figures: Figures, row_id: str, **changes: object) -> Figures:
    rows = tuple(
        dataclasses.replace(row, **changes) if row.id == row_id else row  # type: ignore[arg-type]
        for row in figures.ladder.rows
    )
    ladder = dataclasses.replace(figures.ladder, rows=rows)
    return dataclasses.replace(figures, ladder=ladder)


def cells_of(figures: Figures, row_id: str) -> tuple[float, ...]:
    cells = ladder_row(figures, row_id).cells
    assert cells is not None
    return cells


def test_known_ladder_cells_pass() -> None:
    # 2.5 USD/GPU-hour for 100 hours: +25% is 0.625 a GPU-hour, so 500 at 8 GPUs.
    assert FIGURES.ladder.columns == (8, 16, 32, 64, 128)
    assert FIGURES.ladder.entered == 8
    assert cells_of(FIGURES, "up-25") == (500.0, 1_000.0, 2_000.0, 4_000.0, 8_000.0)
    assert cells_of(FIGURES, "down-50")[0] == -1_000.0
    assert cells_of(FIGURES, "flat-050")[-1] == 6_400.0
    assert check(INPUTS, FIGURES) == []


def test_tampered_ladder_cell_is_named_by_row_and_column() -> None:
    cells = list(cells_of(FIGURES, "up-25"))
    cells[2] += 0.01
    tampered = with_ladder_row(FIGURES, "up-25", cells=tuple(cells))
    assert check(INPUTS, tampered) == ["ladder up-25 32"]


@pytest.mark.parametrize(
    ("columns", "entered"),
    [
        ((8, 16, 32, 64), 8),  # a column dropped
        ((8, 12, 16, 32, 64, 128), 8),  # 12 is not a whole number of 8-GPU VMs
        ((8, 16, 32, 64, 128), 16),  # the wrong column marked as entered
    ],
)
def test_ladder_columns_checked(columns: tuple[int, ...], entered: int) -> None:
    ladder = dataclasses.replace(FIGURES.ladder, columns=columns, entered=entered)
    assert check(INPUTS, dataclasses.replace(FIGURES, ladder=ladder)) == [
        "ladder columns"
    ]


def test_ladder_rows_checked() -> None:
    rows = FIGURES.ladder.rows
    for wrong in (rows[:-1], tuple(reversed(rows))):
        ladder = dataclasses.replace(FIGURES.ladder, rows=wrong)
        assert check(INPUTS, dataclasses.replace(FIGURES, ladder=ladder)) == [
            "ladder rows"
        ]


def test_a_priced_ladder_row_must_show_its_cells() -> None:
    failed = check(INPUTS, with_ladder_row(FIGURES, "up-25", cells=None))
    assert failed == ["ladder up-25 missing", "ladder up-25 refusal"]


def test_ladder_cells_fill_every_column_and_carry_no_refusal() -> None:
    short = with_ladder_row(FIGURES, "up-25", cells=cells_of(FIGURES, "up-25")[:4])
    assert check(INPUTS, short) == ["ladder up-25 cells"]
    labelled = with_ladder_row(FIGURES, "up-25", refusal=REFUSED)
    assert check(INPUTS, labelled) == ["ladder up-25 refused"]


def test_non_finite_ladder_cell_caught() -> None:
    cells = (math.inf, *cells_of(FIGURES, "up-10")[1:])
    failed = check(INPUTS, with_ladder_row(FIGURES, "up-10", cells=cells))
    assert failed == ["finite: ladder up-10 8"]


def test_refused_custom_ladder_row() -> None:
    # A custom change of -3 USD/GPU-hour takes 2.5 below zero.
    inputs = dataclasses.replace(INPUTS, custom=("usd", -3.0))
    refused = RowFigures("custom", None, None, None, None, None, None, REFUSED)
    figures = dataclasses.replace(fit(inputs, FIGURES), rows=(*ROWS, refused))
    assert ladder_row(figures, "custom").cells is None
    assert check(inputs, figures) == []
    shown = with_ladder_row(figures, "custom", cells=(-2_400.0,) * 5, refusal="")
    assert check(inputs, shown) == ["ladder custom refused"]
    assert check(inputs, with_ladder_row(figures, "custom", above_payg=4.0)) == [
        "ladder custom note"
    ]
    assert check(inputs, with_ladder_row(figures, "custom", refusal="")) == [
        "ladder custom refusal"
    ]


def test_fallback_ladder_row_priced_from_pay_as_you_go_and_never_marked() -> None:
    # 8 GPUs x 10 hours x (4.0 - 1.0) USD/GPU-hour.
    assert cells_of(SPOT_FIGURES, "fallback")[0] == 240.0
    assert check(SPOT, SPOT_FIGURES) == []
    marked = with_ladder_row(SPOT_FIGURES, "fallback", above_payg=4.0)
    assert check(SPOT, marked) == ["ladder fallback note"]


def test_unlisted_fallback_ladder_row_must_not_be_filled_in() -> None:
    unlisted = dataclasses.replace(SPOT, payg_vm_price=None)
    empty = RowFigures("fallback", None, None, None, None, None, None, UNLISTED)
    figures = fit(unlisted, with_row(SPOT_FIGURES, 4, **vars(empty)))
    assert ladder_row(figures, "fallback").refusal == UNLISTED
    assert check(unlisted, figures) == []
    filled = with_ladder_row(figures, "fallback", cells=(240.0,) * 5, refusal="")
    assert check(unlisted, filled) == ["ladder fallback refused"]


def test_spot_ladder_marks_exactly_above_pay_as_you_go() -> None:
    # Pay-as-you-go at 1.5 USD/GPU-hour: +100% (2.0) is above it; +50% and +0.50 USD
    # (1.5) are at the boundary, where either is accepted.
    inputs = dataclasses.replace(SPOT, payg_vm_price=12.0)
    figures = fit(inputs, SPOT_FIGURES)
    assert ladder_row(figures, "up-100").above_payg == 1.5

    def ladder_failures(shown: Figures) -> list[str]:
        return [f for f in check(inputs, shown) if f.startswith("ladder")]

    assert ladder_failures(figures) == []
    unmarked = with_ladder_row(figures, "up-100", above_payg=None)
    assert ladder_failures(unmarked) == ["ladder up-100 note"]
    wrong = with_ladder_row(figures, "up-25", above_payg=1.5)
    assert ladder_failures(wrong) == ["ladder up-25 note"]
