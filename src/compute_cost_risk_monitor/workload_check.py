"""Independent check of workload figures before the page shows them (phase-5 D19).

This module imports no calculator code. It takes plain values: the inputs, the starting
member's published VM-hour price and GPUs per VM, and for a Spot start the same size's
pay-as-you-go VM-hour price. It re-derives every figure the page would show from those
and the scenario definitions in `scenarios`, in a different form from the calculator
(VM-hour prices, VMs and costs rather than USD/GPU-hour changes). Failures name the
check and the row, never a price.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields

from compute_cost_risk_monitor.scenarios import PERCENT, SCENARIOS_V1, USD

REL_TOL = 1e-9
FALLBACK = "fallback"
CUSTOM = "custom"


@dataclass(frozen=True)
class Inputs:
    gpus: int
    hours: float
    storage: float | None
    vm_price: float  # the starting member's published USD per VM per hour
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


@dataclass(frozen=True)
class Figures:
    start: float  # USD/GPU-hour
    vms: int
    compute: float
    total: float
    rows: tuple[RowFigures, ...]
    headroom: float | None
    headroom_pct: float | None
    headroom_above_payg: float | None


def _close(actual: float | None, expected: float, scale: float = 0.0) -> bool:
    """Equal to REL_TOL, relative to the larger of the two or to `scale`.

    A difference of two costs is checked relative to the costs, since their rounding
    error is relative to them and not to the difference.
    """
    if actual is None:
        return False
    return math.isclose(actual, expected, rel_tol=REL_TOL, abs_tol=REL_TOL * abs(scale))


def _numbers(figures: Figures) -> list[tuple[str, float]]:
    found: list[tuple[str, float]] = []
    for name in ("start", "compute", "total", "headroom", "headroom_pct"):
        value = getattr(figures, name)
        if value is not None:
            found.append((name, value))
    for row in figures.rows:
        for each in fields(RowFigures):
            value = getattr(row, each.name)
            if each.name != "id" and value is not None:
                found.append((f"{row.id} {each.name}", value))
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


def _note(
    failed: list[str],
    name: str,
    price: float,
    shown: float | None,
    payg: float | None,
    spot: bool,
) -> None:
    """The above-pay-as-you-go note is present exactly when a Spot price exceeds it."""
    if not spot or payg is None or _close(price, payg):
        return  # at the boundary either way is acceptable
    expected = payg if price > payg else None
    if (shown is None) != (expected is None) or (
        expected is not None and not _close(shown, expected)
    ):
        failed.append(name)


def _row(failed: list[str], inputs: Inputs, row: RowFigures, figures: Figures) -> None:
    per_vm = inputs.gpus_per_vm
    start = inputs.vm_price / per_vm
    payg = None if inputs.payg_vm_price is None else inputs.payg_vm_price / per_vm
    gpu_hours = inputs.gpus * inputs.hours
    if row.id == FALLBACK:
        price = payg
    else:
        definition = _definition(inputs, row.id)
        if definition is None:
            failed.append(f"{row.id} definition")
            return
        kind, magnitude = definition
        if kind == PERCENT:
            price = start * (1 + magnitude / 100)
        elif kind == USD:
            price = start + magnitude
        else:
            failed.append(f"{row.id} definition")
            return
    shown = (row.price, row.change, row.change_pct, row.cost, row.exposure)
    if price is None or not price > 0:
        if any(value is not None for value in shown):
            failed.append(f"{row.id} refused")
        return
    if any(value is None for value in shown):
        failed.append(f"{row.id} missing")
        return
    storage = inputs.storage or 0.0
    cost = gpu_hours * price + storage
    largest = max(abs(cost), abs(figures.total))
    checks = [
        ("price", _close(row.price, price)),
        ("change", _close(row.change, price - start, max(price, start))),
        (
            "change %",
            _close(row.change_pct, (price - start) / start * 100, price / start * 100),
        ),
        ("cost", _close(row.cost, cost)),
        ("exposure", _close(row.exposure, gpu_hours * (price - start), largest)),
        (
            "exposure against costs",
            _close(row.exposure, (row.cost or 0.0) - figures.total, largest),
        ),
    ]
    failed.extend(f"{row.id} {name}" for name, ok in checks if not ok)
    if row.id != FALLBACK:
        _note(failed, f"{row.id} note", price, row.above_payg, payg, inputs.spot)


def check(inputs: Inputs, figures: Figures) -> list[str]:
    """The names of the checks that fail; an empty list means every figure holds."""
    failed = [f"finite: {n}" for n, v in _numbers(figures) if not math.isfinite(v)]
    if failed:
        return failed
    per_vm = inputs.gpus_per_vm
    start = inputs.vm_price / per_vm
    storage = inputs.storage or 0.0
    if not _close(figures.start, start):
        failed.append("starting price")
    if figures.vms * per_vm != inputs.gpus:
        failed.append("VM count")
    compute = inputs.vm_price * figures.vms * inputs.hours
    if not _close(figures.compute, compute):
        failed.append("compute cost")
    if not _close(figures.total, compute + storage, compute + storage):
        failed.append("total")
    if [row.id for row in figures.rows] != _expected_ids(inputs):
        failed.append("scenario rows")
    for row in figures.rows:
        _row(failed, inputs, row, figures)
    if inputs.budget is None:
        if figures.headroom is not None or figures.headroom_pct is not None:
            failed.append("headroom without a budget")
    else:
        rise = figures.headroom
        if rise is None or not _close(inputs.gpus * inputs.hours * rise, inputs.budget):
            failed.append("headroom")
        elif not _close(figures.headroom_pct, rise / start * 100):
            failed.append("headroom %")
        else:
            payg = (
                None if inputs.payg_vm_price is None else inputs.payg_vm_price / per_vm
            )
            _note(
                failed,
                "headroom note",
                start + rise,
                figures.headroom_above_payg,
                payg,
                inputs.spot,
            )
    return failed
