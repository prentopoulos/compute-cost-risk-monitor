"""Workload cost, labelled exposure scenarios and budget headroom (phase-5-calculator).

Pure and deterministic: no Streamlit and no database. It starts from one member of one
region group, as Phase 3 computed it, and never rounds (design D3, D5, D7, D9, D11,
D13-D16, D21, D24, D25). `workload_check`, which imports nothing from here, re-derives
every figure before the page shows one (D19). Exposure is a scenario calculation, not a
forecast, and cost covers only the list price and any storage amount the user enters.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from compute_cost_risk_monitor.groups import GroupKey, Member, RegionGroup, Snapshot
from compute_cost_risk_monitor.scenarios import (
    PERCENT,
    SCENARIOS_V1,
    USD,
    VERSION,
    Kind,
)

MAX_GPUS = 100_000
MAX_HOURS = 8_784.0  # 366 days x 24 hours
MAX_STORAGE = 10_000_000.0
MAX_BUDGET = 10_000_000_000.0
MIN_CUSTOM_PERCENT = -100.0  # exclusive: -100% would take any price to zero
MAX_CUSTOM_PERCENT = 1_000.0
MAX_CUSTOM_USD = 1_000.0  # either way, in USD per GPU-hour
DEFAULT_GPUS = 32  # whole VMs at 1, 2, 4 and 8 GPUs per VM (D26)
DEFAULT_HOURS = 720.0
SPOT = "spot"
ON_DEMAND = "on_demand"

ADDITIONAL = "additional expense"
LOWER = "lower expense"
NO_CHANGE = "no change"
ZERO_OR_BELOW = "not computed: the price would be zero or below"
NO_PAYG = "not computed: no pay-as-you-go listing for this size in this region"

FALLBACK = "fallback"
CUSTOM = "custom"
FALLBACK_NAME = "Spot to pay-as-you-go fallback"
FALLBACK_NARRATIVE = (
    "Spot capacity is lost and the workload moves to the same size at its pay-as-you-go"
    " list price in the same region, as Microsoft advises when capacity is needed right"
    " away after an eviction."
)
CUSTOM_NARRATIVE = "A change entered by you."


class Refused(ValueError):
    """An input the calculator will not compute with; the message says which and why."""


@dataclass(frozen=True)
class Workload:
    gpus: int
    hours: float
    storage: float | None = None  # USD for the period, entered by the user


@dataclass(frozen=True)
class Custom:
    kind: Kind
    magnitude: float


@dataclass(frozen=True)
class Start:
    """The member every figure is priced from, and whether it is its group's lowest."""

    group: RegionGroup
    member: Member
    lowest: bool

    @property
    def key(self) -> GroupKey:
        return self.group.key

    @property
    def snapshot(self) -> Snapshot:
        return self.group.snapshot

    @property
    def gpus_per_vm(self) -> int:
        return self.group.key.gpu_count

    @property
    def usd_per_gpu_hour(self) -> float:
        return self.member.usd_per_gpu_hour

    @property
    def spot(self) -> bool:
        return self.group.key.rental_type == SPOT


@dataclass(frozen=True)
class Cost:
    vms: int
    compute: float
    storage: float | None
    total: float


@dataclass(frozen=True)
class Row:
    """One scenario: its figures, or none at all with the reason in `effect`."""

    id: str
    name: str
    narrative: str
    kind: str  # PERCENT, USD or FALLBACK
    magnitude: float | None  # None for the fallback, which is priced from a listing
    price: float | None = None  # scenario USD/GPU-hour
    change: float | None = None  # USD/GPU-hour
    change_pct: float | None = None  # % of the starting price
    cost: float | None = None  # scenario cost for the workload, storage unchanged
    exposure: float | None = None  # scenario cost minus the starting cost
    effect: str = ""
    above_payg: float | None = None  # the pay-as-you-go USD/GPU-hour a Spot row exceeds

    @property
    def computed(self) -> bool:
        return self.exposure is not None


@dataclass(frozen=True)
class Headroom:
    budget: float
    rise: float  # USD per GPU-hour that would use up the budget
    rise_pct: float
    above_payg: float | None = None


@dataclass(frozen=True)
class Result:
    start: Start
    workload: Workload
    cost: Cost
    rows: tuple[Row, ...]
    version: str
    payg_key: GroupKey | None = (
        None  # for a Spot start, the key the fallback crosses to
    )
    payg: Member | None = None  # the same size on pay-as-you-go, when listed
    custom: Custom | None = None
    headroom: Headroom | None = None


# --- inputs (D13-D15, D21, D24, D25) ---


def _finite(value: float) -> bool:
    return isinstance(value, int | float) and math.isfinite(value)


def _amount(value: float) -> str:
    return f"{value:,.4f}".rstrip("0").rstrip(".")


def nearest(gpus: int, gpus_per_vm: int) -> list[int]:
    """The valid GPU counts either side of a count that is not a whole number of VMs."""
    lower = gpus // gpus_per_vm * gpus_per_vm
    return [n for n in (lower, lower + gpus_per_vm) if gpus_per_vm <= n <= MAX_GPUS]


def workload(
    gpus: int | None, hours: float | None, storage: float | None, gpus_per_vm: int
) -> Workload:
    """A valid workload of whole VMs, or Refused naming the input; never rounded."""
    if gpus_per_vm < 1:
        raise ValueError(f"GPUs per VM must be at least 1, not {gpus_per_vm}")
    if gpus is None or isinstance(gpus, bool) or not isinstance(gpus, int):
        raise Refused("Enter the number of GPUs as a whole number.")
    if gpus < gpus_per_vm:
        unit = "GPU" if gpus_per_vm == 1 else "GPUs"
        raise Refused(f"GPUs must be at least one VM ({gpus_per_vm} {unit}).")
    if gpus > MAX_GPUS:
        raise Refused(f"GPUs must be at most {MAX_GPUS:,}.")
    if gpus % gpus_per_vm:
        options = " or ".join(f"{n:,}" for n in nearest(gpus, gpus_per_vm))
        raise Refused(
            f"{gpus} GPUs is not a whole number of {gpus_per_vm}-GPU VMs:"
            f" use {options}."
        )
    if hours is None or not _finite(hours) or not 0 < hours <= MAX_HOURS:
        raise Refused(f"Hours must be above 0 and at most {MAX_HOURS:,.0f}.")
    if storage is not None and (
        not _finite(storage) or not 0 <= storage <= MAX_STORAGE
    ):
        raise Refused(f"Storage must be from USD 0 to {MAX_STORAGE:,.0f}.")
    return Workload(gpus, float(hours), None if storage is None else float(storage))


def custom(kind: str, magnitude: float | None) -> Custom | None:
    """The user's custom change, None when empty, or Refused when out of bounds."""
    if magnitude is None:
        return None
    if kind == PERCENT:
        if not _finite(magnitude) or not (
            MIN_CUSTOM_PERCENT < magnitude <= MAX_CUSTOM_PERCENT
        ):
            raise Refused("Custom change must be above −100% and at most 1,000%.")
        return Custom(PERCENT, float(magnitude))
    if kind == USD:
        if not _finite(magnitude) or not abs(magnitude) <= MAX_CUSTOM_USD:
            raise Refused(
                "Custom change must be from −1,000 to 1,000 USD per GPU-hour."
            )
        return Custom(USD, float(magnitude))
    raise ValueError(f"unknown scenario kind {kind!r}")


def budget(value: float | None) -> float | None:
    """A budget for headroom, None when empty, or Refused."""
    if value is None:
        return None
    if not _finite(value):
        raise Refused("Budget must be a number.")
    if value <= 0:
        raise Refused("Budget: enter an amount above zero.")
    if value > MAX_BUDGET:
        raise Refused(f"Budget must be at most USD {MAX_BUDGET:,.0f}.")
    return float(value)


# --- starting price and cost (D3, D13) ---


def lowest(group: RegionGroup) -> Member:
    """The group's lowest listed member; ties go to the lexically first size."""
    return min(group.members, key=lambda m: (m.usd_per_gpu_hour, m.name))


def start(group: RegionGroup, size: str | None = None) -> Start:
    """The picked size of a group, or its lowest listed member when none is picked."""
    if not group.members:
        raise ValueError("a region group has at least one member")
    low = lowest(group)
    if size is None:
        return Start(group, low, True)
    member = next((m for m in group.members if m.name == size), None)
    if member is None:
        raise ValueError(f"{size} is not a member of this group")
    return Start(group, member, member.item_key == low.item_key)


def cost(begin: Start, work: Workload) -> Cost:
    compute = work.gpus * work.hours * begin.usd_per_gpu_hour
    total = compute if work.storage is None else compute + work.storage
    return Cost(work.gpus // begin.gpus_per_vm, compute, work.storage, total)


# --- scenarios (D5-D7, D11, D16) ---


def _effect(exposure: float) -> str:
    if exposure > 0:
        return ADDITIONAL
    if exposure < 0:
        return LOWER
    return NO_CHANGE


def _row(
    begin: Start,
    work: Workload,
    head: tuple[str, str, str, str, float | None],
    change: float,
    payg: float | None,
) -> Row:
    """Price one scenario from its USD/GPU-hour change; refuse a price at or below 0."""
    price = begin.usd_per_gpu_hour + change
    if not price > 0:
        return Row(*head, effect=ZERO_OR_BELOW)
    exposure = work.gpus * work.hours * change
    scenario = work.gpus * work.hours * price
    if work.storage is not None:
        scenario += work.storage
    above = payg if begin.spot and payg is not None and price > payg else None
    return Row(
        *head,
        price=price,
        change=change,
        change_pct=change / begin.usd_per_gpu_hour * 100,
        cost=scenario,
        exposure=exposure,
        effect=_effect(exposure),
        above_payg=above,
    )


def _change(begin: Start, kind: str, magnitude: float) -> float:
    if kind == PERCENT:
        return begin.usd_per_gpu_hour * magnitude / 100
    return magnitude


def custom_name(change: Custom) -> str:
    sign = "+" if change.magnitude >= 0 else "−"
    amount = _amount(abs(change.magnitude))
    unit = "%" if change.kind == PERCENT else " USD/GPU-hour"
    return f"Custom: {sign}{amount}{unit} (entered by you, not part of {VERSION})"


def pay_as_you_go(
    begin: Start, found: Sequence[RegionGroup]
) -> tuple[GroupKey, Member | None]:
    """For a Spot start: the pay-as-you-go key and the same size listed under it."""
    key = GroupKey(begin.key.variant, begin.key.gpu_count, begin.key.region, ON_DEMAND)
    group = next(
        (
            g
            for g in found
            if g.key == key and g.snapshot.run_id == begin.snapshot.run_id
        ),
        None,
    )
    if group is None:
        return key, None
    return key, next((m for m in group.members if m.name == begin.member.name), None)


def calculate(
    begin: Start,
    work: Workload,
    found: Sequence[RegionGroup],
    change: Custom | None = None,
    limit: float | None = None,
) -> Result:
    """Cost, every scenario row and headroom for one workload at one starting price.

    `found` holds the snapshot's region groups, where a Spot start finds its size on
    pay-as-you-go. The fallback row follows the presets, and the custom row comes last.
    """
    if work.gpus % begin.gpus_per_vm:
        raise ValueError("the workload is not a whole number of this group's VMs")
    payg_key: GroupKey | None = None
    payg: Member | None = None
    if begin.spot:
        payg_key, payg = pay_as_you_go(begin, found)
    payg_price = None if payg is None else payg.usd_per_gpu_hour
    rows = [
        _row(
            begin,
            work,
            (s.id, s.name, s.narrative, s.kind, s.magnitude),
            _change(begin, s.kind, s.magnitude),
            payg_price,
        )
        for s in SCENARIOS_V1
    ]
    if begin.spot:
        head = (FALLBACK, FALLBACK_NAME, FALLBACK_NARRATIVE, FALLBACK, None)
        if payg_price is None:
            rows.append(Row(*head, effect=NO_PAYG))
        else:
            rows.append(
                _row(begin, work, head, payg_price - begin.usd_per_gpu_hour, None)
            )
    if change is not None:
        rows.append(
            _row(
                begin,
                work,
                (
                    CUSTOM,
                    custom_name(change),
                    CUSTOM_NARRATIVE,
                    change.kind,
                    change.magnitude,
                ),
                _change(begin, change.kind, change.magnitude),
                payg_price,
            )
        )
    room = None
    if limit is not None:
        rise = limit / (work.gpus * work.hours)
        above = (
            payg_price
            if begin.spot
            and payg_price is not None
            and begin.usd_per_gpu_hour + rise > payg_price
            else None
        )
        room = Headroom(limit, rise, rise / begin.usd_per_gpu_hour * 100, above)
    return Result(
        begin,
        work,
        cost(begin, work),
        tuple(rows),
        VERSION,
        payg_key,
        payg,
        change,
        room,
    )
