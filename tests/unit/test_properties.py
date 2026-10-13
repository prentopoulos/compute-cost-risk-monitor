"""Properties of the calculations over generated inputs (Phase 6 design D4).

Every price here is generated: synthetic, never an Azure list price. The properties come
from the specs (cost = GPUs x hours x USD/GPU-hour; exposure = GPUs x hours x change;
USD/GPU-hour x GPU count = the published price; "lowest listed" never depends on row
order). The known-answer tests stay the primary evidence; these search for inputs that
break the rules. Examples are fixed by the `gate` profile in tests/conftest.py.
"""

import math
from datetime import UTC, date, datetime

from hypothesis import given
from hypothesis import strategies as st

from compute_cost_risk_monitor import calculator as calc
from compute_cost_risk_monitor import dashboard, gpu_map, groups, normalize, rules
from compute_cost_risk_monitor.calculator import Custom, Workload
from compute_cost_risk_monitor.groups import GroupKey, Member, RegionGroup, Snapshot
from compute_cost_risk_monitor.scenarios import PERCENT, USD

T = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)
SNAPSHOT = Snapshot("azure-retail", "run-p", T, "synthetic")
SIZE = "Standard_P_synthetic"  # an invented size name
MAP = gpu_map.load()
WHOLE_SIZES = sorted(name for name, row in MAP.items() if row.whole)

# Published VM-hour prices: finite and positive, across eight decades.
vm_prices = st.floats(min_value=1e-4, max_value=1e4)
gpus_per_vm = st.sampled_from([1, 2, 4, 8])
# The validators' whole domain. Before Phase 6 it reached down to 5e-324 h and USD,
# where the headroom overflowed or underflowed and the check withheld valid figures
# (design D23).
hours = st.floats(min_value=calc.MIN_HOURS, max_value=calc.MAX_HOURS)
storage = st.none() | st.floats(min_value=0, max_value=calc.MAX_STORAGE)
changes = (
    st.none()
    | st.builds(
        Custom,
        st.just(PERCENT),
        st.floats(
            min_value=calc.MIN_CUSTOM_PERCENT,
            max_value=calc.MAX_CUSTOM_PERCENT,
            exclude_min=True,
        ),
    )
    | st.builds(
        Custom,
        st.just(USD),
        st.floats(min_value=-calc.MAX_CUSTOM_USD, max_value=calc.MAX_CUSTOM_USD),
    )
)
budgets = st.none() | st.floats(min_value=calc.MIN_BUDGET, max_value=calc.MAX_BUDGET)


def group(per_vm: int, rental: str, vm_price: float) -> RegionGroup:
    member = Member(
        SIZE,
        vm_price / per_vm,
        f"{SIZE}|{rental}",
        T,
        price=vm_price,
        currency="USD",
        price_unit="1 Hour",
        run_id=SNAPSHOT.run_id,
    )
    key = GroupKey("Synthetic GPU", per_vm, "region-p", rental)
    return RegionGroup(key, SNAPSHOT, [member], rules.GROUPS_V1["exclusions"])


@st.composite
def workloads(draw: st.DrawFn, per_vm: int) -> Workload:
    vms = draw(st.integers(min_value=1, max_value=calc.MAX_GPUS // per_vm))
    return calc.workload(vms * per_vm, draw(hours), draw(storage), per_vm)


# --- the never-cut pair (D6) ---


@given(
    per_vm=gpus_per_vm,
    vm_price=vm_prices,
    spot=st.booleans(),
    payg=st.none() | vm_prices,
    change=changes,
    limit=budgets,
    data=st.data(),
)
def test_calculator_and_independent_check_agree(
    per_vm: int,
    vm_price: float,
    spot: bool,
    payg: float | None,
    change: Custom | None,
    limit: float | None,
    data: st.DataObject,
) -> None:
    """Valid input never fails the check, so the page never blanks a valid workload."""
    found = [group(per_vm, calc.SPOT if spot else calc.ON_DEMAND, vm_price)]
    if spot and payg is not None:
        found.append(group(per_vm, calc.ON_DEMAND, payg))
    work = data.draw(workloads(per_vm))
    begin = calc.start(found[0])
    result = calc.calculate(begin, work, found, change, limit)
    assert dashboard.check(begin, result, work, change, limit, found) == []


@given(
    size=st.sampled_from(WHOLE_SIZES), price=st.floats(min_value=1e-6, max_value=1e6)
)
def test_usd_per_gpu_hour_times_gpus_gives_back_the_price(
    size: str, price: float
) -> None:
    observation = normalize.AzureObservation(
        size, "westeurope", "on_demand", price, "1 Hour", None, date(2020, 1, 1)
    )
    outcome = normalize.classify_azure(observation, MAP, rules.GROUPS_V1)
    assert outcome.excluded_reason is None
    assert outcome.usd_per_gpu_hour is not None and outcome.gpu_count is not None
    back = outcome.usd_per_gpu_hour * outcome.gpu_count
    assert math.isclose(back, price, rel_tol=1e-9)


# --- the rest (D4) ---


@given(per_vm=gpus_per_vm, vm_price=vm_prices, data=st.data())
def test_cost_is_linear_in_gpus_and_hours(
    per_vm: int, vm_price: float, data: st.DataObject
) -> None:
    begin = calc.start(group(per_vm, calc.ON_DEMAND, vm_price))
    vms = data.draw(st.integers(min_value=1, max_value=calc.MAX_GPUS // per_vm // 2))
    span = data.draw(st.floats(min_value=calc.MIN_HOURS, max_value=calc.MAX_HOURS / 2))
    base = calc.cost(begin, Workload(vms * per_vm, span)).compute
    more_gpus = calc.cost(begin, Workload(2 * vms * per_vm, span)).compute
    more_hours = calc.cost(begin, Workload(vms * per_vm, 2 * span)).compute
    assert math.isclose(more_gpus, 2 * base, rel_tol=1e-12)
    assert math.isclose(more_hours, 2 * base, rel_tol=1e-12)
    expected = vms * per_vm * span * begin.usd_per_gpu_hour
    assert math.isclose(base, expected, rel_tol=1e-12)


@given(per_vm=gpus_per_vm, vm_price=vm_prices, change=changes, data=st.data())
def test_exposure_is_the_cost_difference_and_follows_the_change(
    per_vm: int, vm_price: float, change: Custom | None, data: st.DataObject
) -> None:
    found = [group(per_vm, calc.ON_DEMAND, vm_price)]
    work = data.draw(workloads(per_vm))
    result = calc.calculate(calc.start(found[0]), work, found, change, None)
    for row in result.rows:
        if not row.computed:
            assert row.price is None and row.effect.startswith("not computed")
            continue
        assert row.exposure is not None and row.cost is not None
        assert row.change is not None and row.price is not None and row.price > 0
        scale = work.gpus * work.hours * max(row.price, result.start.usd_per_gpu_hour)
        # A storage amount adds its own rounding to both costs, so their difference is
        # only good to a few units in the last place of the larger cost.
        rounding = 4 * math.ulp(max(abs(row.cost), abs(result.cost.total)))
        assert math.isclose(
            row.exposure,
            row.cost - result.cost.total,
            abs_tol=1e-9 * scale + rounding,
        )
        if (
            abs(row.exposure) > 1e-9 * scale
        ):  # beyond rounding, the sign is the change's
            assert (row.exposure > 0) == (row.change > 0)
        effect = {1: calc.ADDITIONAL, -1: calc.LOWER, 0: calc.NO_CHANGE}
        assert row.effect == effect[(row.exposure > 0) - (row.exposure < 0)]


prices = st.floats(min_value=1e-4, max_value=1e4)


@st.composite
def member_lists(draw: st.DrawFn) -> list[Member]:
    names = draw(
        st.lists(
            st.from_regex(r"Standard_[A-Z][0-9]{1,3}", fullmatch=True),
            min_size=1,
            max_size=8,
            unique=True,
        )
    )
    # Ties are drawn on purpose: equal prices must still give one answer.
    values = draw(
        st.lists(
            st.sampled_from([1.0, 2.5]) | prices,
            min_size=len(names),
            max_size=len(names),
        )
    )
    return [Member(n, v, f"k|{n}", T) for n, v in zip(names, values, strict=True)]


@given(members=member_lists(), data=st.data())
def test_lowest_and_statistics_do_not_depend_on_row_order(
    members: list[Member], data: st.DataObject
) -> None:
    shuffled = data.draw(st.permutations(members))
    assert groups.lowest(shuffled) == groups.lowest(members)
    values = [m.usd_per_gpu_hour for m in members]
    assert groups.stats([m.usd_per_gpu_hour for m in shuffled]) == groups.stats(values)
    low = groups.lowest(members)
    assert all(groups.price_order(low) <= groups.price_order(m) for m in members)
