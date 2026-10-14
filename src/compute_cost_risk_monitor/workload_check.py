"""Independent check of workload figures before the page shows them (phase-5 D19).

This module imports no calculator code. It takes plain values: the inputs, the member
the page picked (its item key, published VM-hour price and GPUs per VM), and for a Spot
start the same size's pay-as-you-go VM-hour price. It re-derives every figure and label
the page would show from those and the scenario definitions in `scenarios`, in a
different form from the calculator: VM-hour prices, VMs and costs rather than stored
USD/GPU-hour. Failures name the check and the row, never a price.

Tolerances are relative to each figure's own scale (GPU-hours times the larger of the
two prices). Adding a storage amount only adds that sum's rounding, so a large storage
entry never hides a cent-level error in a cost or an exposure.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields

from compute_cost_risk_monitor.scenarios import (
    LADDER_GPUS,
    LADDER_V1,
    PERCENT,
    SCENARIOS_V1,
    USD,
)

REL_TOL = 1e-9
FALLBACK = "fallback"
CUSTOM = "custom"
# The effect words the page shows, kept here so the check does not read them from the
# calculator; test_workload_view asserts the two agree.
ADDITIONAL = "additional expense"
LOWER = "lower expense"
NO_CHANGE = "no change"
NOT_COMPUTED = "not computed"


@dataclass(frozen=True)
class Inputs:
    gpus: int
    hours: float
    storage: float | None
    item_key: str  # the member the page picked
    vm_price: float  # its published USD per VM per hour
    gpus_per_vm: int
    spot: bool
    payg_vm_price: float | None  # a Spot start's size on pay-as-you-go, when listed
    custom: tuple[str, float] | None  # kind and magnitude
    budget: float | None


@dataclass(frozen=True)
class RowFigures:
    id: str
    price: float | None
    change: float | None
    change_pct: float | None
    cost: float | None
    exposure: float | None
    above_payg: float | None
    effect: str = ""


@dataclass(frozen=True)
class LadderRowFigures:
    id: str
    cells: tuple[float, ...] | None  # one per column; None when the row is refused
    refusal: str = ""
    above_payg: float | None = None


@dataclass(frozen=True)
class LadderFigures:
    columns: tuple[int, ...]
    entered: int
    rows: tuple[LadderRowFigures, ...]


@dataclass(frozen=True)
class Figures:
    item_key: str  # the member the figures were priced from
    start: float  # USD/GPU-hour
    vms: int
    compute: float
    storage: float | None
    total: float
    rows: tuple[RowFigures, ...]
    headroom: float | None
    headroom_pct: float | None
    headroom_above_payg: float | None
    ladder: LadderFigures


def _close(
    actual: float | None,
    expected: float,
    scale: float | None = None,
    slack: float = 0.0,
) -> bool:
    """Equal to REL_TOL of the values themselves, or of `scale` when given, plus `slack`
    for a sum's rounding. A cost that adds storage, or a difference of two costs, is
    checked against the scale of what was priced, never of the storage amount."""
    if actual is None:
        return False
    if scale is None:
        return math.isclose(actual, expected, rel_tol=REL_TOL)
    return abs(actual - expected) <= REL_TOL * abs(scale) + slack


def _slack(*values: float) -> float:
    """The rounding of a sum or difference of these values: a few units in the last
    place of the largest."""
    return 4 * math.ulp(max(abs(v) for v in values))


def _numbers(figures: Figures) -> list[tuple[str, float]]:
    found: list[tuple[str, float]] = []
    names = ("start", "compute", "storage", "total", "headroom", "headroom_pct")
    for name in names:
        value = getattr(figures, name)
        if value is not None:
            found.append((name, value))
    for row in figures.rows:
        for each in fields(RowFigures):
            value = getattr(row, each.name)
            if each.name not in ("id", "effect") and value is not None:
                found.append((f"{row.id} {each.name}", value))
    for step in figures.ladder.rows:
        for column, cell in zip(figures.ladder.columns, step.cells or (), strict=False):
            found.append((f"ladder {step.id} {column}", cell))
        if step.above_payg is not None:
            found.append((f"ladder {step.id} note", step.above_payg))
    return found


def _definition(inputs: Inputs, row_id: str) -> tuple[str, float] | None:
    for scenario in SCENARIOS_V1:
        if scenario.id == row_id:
            return scenario.kind, scenario.magnitude
    if row_id == CUSTOM:
        return inputs.custom
    return None


def _expected_ids(inputs: Inputs) -> list[str]:
    ids = [s.id for s in SCENARIOS_V1]
    if inputs.spot:
        ids.append(FALLBACK)
    if inputs.custom is not None:
        ids.append(CUSTOM)
    return ids


def _effect(exposure: float) -> str:
    if exposure > 0:
        return ADDITIONAL
    if exposure < 0:
        return LOWER
    return NO_CHANGE


def _note(
    failed: list[str],
    name: str,
    price: float,
    shown: float | None,
    payg: float | None,
    spot: bool,
) -> None:
    """The above-pay-as-you-go note is present exactly when a Spot price exceeds it."""
    if not spot or payg is None:
        if shown is not None:
            failed.append(name)
        return
    if _close(price, payg, payg):
        return  # at the boundary either way is acceptable
    expected = payg if price > payg else None
    if (shown is None) != (expected is None) or (
        expected is not None and not _close(shown, expected)
    ):
        failed.append(name)


Priced = tuple[float, float] | None


def _priced(
    inputs: Inputs, row: RowFigures, start: float, payg: float | None
) -> Priced | str:
    """The row's price and change, None when nothing prices it, or an error name.

    The same two formulas as the calculator: a percentage multiplies the starting price;
    a USD scenario's change is its magnitude exactly.
    """
    if row.id == FALLBACK:
        return None if payg is None else (payg, payg - start)
    definition = _definition(inputs, row.id)
    if definition is None:
        return f"{row.id} definition"
    kind, magnitude = definition
    if kind == PERCENT:
        price = start * (1 + magnitude / 100)
        return price, price - start
    if kind == USD:
        return start + magnitude, magnitude
    return f"{row.id} definition"


def _row(failed: list[str], inputs: Inputs, row: RowFigures, figures: Figures) -> None:
    per_vm = inputs.gpus_per_vm
    start = inputs.vm_price / per_vm
    payg = None if inputs.payg_vm_price is None else inputs.payg_vm_price / per_vm
    gpu_hours = inputs.gpus * inputs.hours
    found = _priced(inputs, row, start, payg)
    if isinstance(found, str):
        failed.append(found)
        return
    shown = (row.price, row.change, row.change_pct, row.cost, row.exposure)
    # A price within rounding of zero may be refused or shown; any other may not.
    near_zero = found is not None and abs(found[0]) <= REL_TOL * start
    priceable = found is not None and found[0] > 0 and not near_zero
    if all(value is None for value in shown):
        if priceable:
            failed.append(f"{row.id} missing")
        if row.above_payg is not None:
            failed.append(f"{row.id} note")
        if not row.effect.startswith(NOT_COMPUTED):
            failed.append(f"{row.id} effect")
        return
    if any(value is None for value in shown):
        failed.append(f"{row.id} missing")
        return
    if found is None or (found[0] <= 0 and not near_zero):
        failed.append(f"{row.id} refused")
        return
    price, change = found
    storage = inputs.storage or 0.0
    larger = max(abs(price), start)
    scale = gpu_hours * larger
    cost = gpu_hours * price + storage
    shown_cost = row.cost or 0.0
    checks = [
        ("price", _close(row.price, price, larger)),
        ("change", _close(row.change, change, larger)),
        (
            "change %",
            _close(row.change_pct, change / start * 100, larger / start * 100),
        ),
        ("cost", _close(row.cost, cost, scale, _slack(cost, storage))),
        ("exposure", _close(row.exposure, gpu_hours * change, scale)),
        (
            "exposure against costs",
            _close(
                row.exposure,
                shown_cost - figures.total,
                scale,
                _slack(shown_cost, figures.total),
            ),
        ),
        ("effect", row.effect == _effect(row.exposure or 0.0)),
    ]
    failed.extend(f"{row.id} {name}" for name, ok in checks if not ok)
    if row.id == FALLBACK:
        if row.above_payg is not None:
            failed.append(f"{row.id} note")
    else:
        _note(failed, f"{row.id} note", price, row.above_payg, payg, inputs.spot)


def _headroom(
    failed: list[str], inputs: Inputs, figures: Figures, start: float
) -> None:
    shown = (figures.headroom, figures.headroom_pct, figures.headroom_above_payg)
    if inputs.budget is None:
        if any(value is not None for value in shown):
            failed.append("headroom without a budget")
        return
    rise = figures.headroom
    if rise is None or not _close(inputs.gpus * inputs.hours * rise, inputs.budget):
        failed.append("headroom")
        return
    if not _close(figures.headroom_pct, rise / start * 100):
        failed.append("headroom %")
    per_vm = inputs.gpus_per_vm
    payg = None if inputs.payg_vm_price is None else inputs.payg_vm_price / per_vm
    _note(
        failed,
        "headroom note",
        start + rise,
        figures.headroom_above_payg,
        payg,
        inputs.spot,
    )


def _ladder(failed: list[str], inputs: Inputs, ladder: LadderFigures) -> None:
    """Every ladder row, column, cell, refusal and mark, from VM-hour prices.

    A cell is VMs x hours x the change in VM-hour price: a percentage of the published
    VM-hour price, or a USD step's magnitude per GPU-hour times GPUs per VM.
    """
    per_vm = inputs.gpus_per_vm
    columns = tuple(sorted({n for n in LADDER_GPUS if n % per_vm == 0} | {inputs.gpus}))
    if ladder.columns != columns or ladder.entered != inputs.gpus:
        failed.append("ladder columns")
        return
    expected = [s.id for s in LADDER_V1]
    definitions: dict[str, tuple[str, float]] = {
        s.id: (s.kind, s.magnitude) for s in LADDER_V1
    }
    if inputs.spot:
        expected.append(FALLBACK)
    if inputs.custom is not None:
        expected.append(CUSTOM)
        definitions[CUSTOM] = inputs.custom
    if [row.id for row in ladder.rows] != expected:
        failed.append("ladder rows")
        return
    vm = inputs.vm_price
    payg_vm = inputs.payg_vm_price
    payg = None if payg_vm is None else payg_vm / per_vm
    for row in ladder.rows:
        name = f"ladder {row.id}"
        found: tuple[float, float] | None  # VM-hour price and its change
        if row.id == FALLBACK:
            found = None if payg_vm is None else (payg_vm, payg_vm - vm)
        else:
            kind, magnitude = definitions[row.id]
            delta = vm * magnitude / 100 if kind == PERCENT else magnitude * per_vm
            found = (vm + delta, delta)
        # A price within rounding of zero may be refused or shown; any other may not.
        near_zero = found is not None and abs(found[0]) <= REL_TOL * vm
        priceable = found is not None and found[0] > 0 and not near_zero
        if row.cells is None:
            if priceable:
                failed.append(f"{name} missing")
            if not row.refusal.startswith(NOT_COMPUTED):
                failed.append(f"{name} refusal")
            if row.above_payg is not None:
                failed.append(f"{name} note")
            continue
        if found is None or (found[0] <= 0 and not near_zero) or row.refusal:
            failed.append(f"{name} refused")
            continue
        if len(row.cells) != len(columns):
            failed.append(f"{name} cells")
            continue
        price, delta = found
        larger = max(abs(price), vm)
        for column, cell in zip(columns, row.cells, strict=True):
            vms = column / per_vm
            scale = vms * inputs.hours * larger
            if not _close(cell, vms * inputs.hours * delta, scale):
                failed.append(f"{name} {column}")
        if row.id == FALLBACK:
            if row.above_payg is not None:
                failed.append(f"{name} note")
        else:
            _note(
                failed,
                f"{name} note",
                price / per_vm,
                row.above_payg,
                payg,
                inputs.spot,
            )


def check(inputs: Inputs, figures: Figures) -> list[str]:
    """The names of the checks that fail; an empty list means every figure holds."""
    failed = [f"finite: {n}" for n, v in _numbers(figures) if not math.isfinite(v)]
    if failed:
        return failed
    start = inputs.vm_price / inputs.gpus_per_vm
    storage = inputs.storage or 0.0
    if figures.item_key != inputs.item_key:
        failed.append("starting member")
    if not _close(figures.start, start, start):
        failed.append("starting price")
    if figures.vms * inputs.gpus_per_vm != inputs.gpus:
        failed.append("VM count")
    compute = inputs.vm_price * figures.vms * inputs.hours
    if not _close(figures.compute, compute):
        failed.append("compute cost")
    if figures.storage != inputs.storage:
        failed.append("storage")
    if not _close(figures.total, compute + storage, compute, _slack(compute, storage)):
        failed.append("total")
    if [row.id for row in figures.rows] != _expected_ids(inputs):
        failed.append("scenario rows")
    for row in figures.rows:
        _row(failed, inputs, row, figures)
    _headroom(failed, inputs, figures, start)
    _ladder(failed, inputs, figures.ladder)
    return failed
