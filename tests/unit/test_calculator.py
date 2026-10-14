"""Workload cost, scenarios, fallback and headroom against hand-worked answers.

Groups are built directly with invented round prices (synthetic). Every expected figure
below was worked out by hand; the PROJECT example 32 x 720 x $0.50 = $11,520 holds
whatever the starting price.
"""

import math
from datetime import UTC, datetime

import pytest

from compute_cost_risk_monitor import calculator as calc
from compute_cost_risk_monitor.calculator import Custom, Refused, Workload
from compute_cost_risk_monitor.groups import GroupKey, Member, RegionGroup, Snapshot
from compute_cost_risk_monitor.scenarios import PERCENT, USD

DAY = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)
SNAP = Snapshot("azure-retail", "run-1", DAY, "synthetic")
H100 = "Standard_ND96isr_H100_v5"
EXCLUSIONS = "Excludes disks and storage."


def group(
    rental: str = "on_demand",
    *sizes: tuple[str, float],
    count: int = 8,
    region: str = "westeurope",
    snapshot: Snapshot = SNAP,
) -> RegionGroup:
    """A region group whose members cost `per_gpu` USD/GPU-hour each (synthetic)."""
    members = [
        Member(
            name,
            per_gpu,
            f"m|{name}|{region}|{rental}",
            DAY,
            price=per_gpu * count,
            currency="USD",
            price_unit="1 Hour",
            run_id=snapshot.run_id,
        )
        for name, per_gpu in (sizes or ((H100, 2.5),))
    ]
    key = GroupKey("H100 NVLink 80GB", count, region, rental)
    return RegionGroup(key, snapshot, members, EXCLUSIONS)


def rows(result: calc.Result) -> dict[str, calc.Row]:
    return {row.id: row for row in result.rows}


# --- inputs ---


def test_whole_vms_accepted() -> None:
    work = calc.workload(32, 720, None, 8)
    assert work == Workload(32, 720.0, None)
    assert calc.cost(calc.start(group()), work).vms == 4


@pytest.mark.parametrize(
    ("gpus", "per_vm", "message"),
    [
        (30, 8, "30 GPUs is not a whole number of 8-GPU VMs: use 24 or 32."),
        (3, 2, "3 GPUs is not a whole number of 2-GPU VMs: use 2 or 4."),
        (
            99_999,
            8,
            "99,999 GPUs is not a whole number of 8-GPU VMs: use 99,992 or 100,000.",
        ),
        (4, 8, "GPUs must be at least one VM (8 GPUs)."),
        (0, 1, "GPUs must be at least one VM (1 GPU)."),
        (-8, 8, "at least one VM"),
        (100_008, 8, "GPUs must be at most 100,000."),
    ],
)
def test_gpu_counts_refused_with_the_nearest_valid_counts(
    gpus: int, per_vm: int, message: str
) -> None:
    with pytest.raises(Refused, match=message.replace("(", r"\(").replace(")", r"\)")):
        calc.workload(gpus, 720, None, per_vm)


def test_nearest_counts_stay_within_bounds() -> None:
    assert calc.nearest(30, 8) == [24, 32]
    assert calc.nearest(99_999, 8) == [99_992, 100_000]
    assert calc.nearest(99_999, 7) == [99_995]  # 100,002 would exceed the maximum
    assert calc.nearest(3, 8) == [8]  # zero GPUs is no workload


@pytest.mark.parametrize("gpus", [None, 32.0, True, "32"])
def test_gpus_must_be_a_whole_number(gpus: object) -> None:
    with pytest.raises(Refused, match="whole number"):
        calc.workload(gpus, 720, None, 8)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "hours", [None, 0, -1, math.nan, math.inf, 8_784.5, 0.009, 5e-324]
)
def test_impossible_hours_refused(hours: float | None) -> None:
    # Below 0.01 h a budget's headroom can overflow (found by Hypothesis, Phase 6).
    with pytest.raises(Refused, match="Hours must be at least 0.01 and at most 8,784"):
        calc.workload(8, hours, None, 8)


@pytest.mark.parametrize("hours", [0.01, 0.5, 8_784])
def test_fractional_and_maximum_hours_accepted(hours: float) -> None:
    assert calc.workload(8, hours, None, 8).hours == hours


@pytest.mark.parametrize("storage", [-1, math.inf, math.nan, 10_000_000.01])
def test_impossible_storage_refused(storage: float) -> None:
    with pytest.raises(Refused, match="Storage must be from USD 0 to 10,000,000"):
        calc.workload(8, 100, storage, 8)


def test_storage_zero_is_entered_and_none_is_not() -> None:
    assert calc.workload(8, 100, 0, 8).storage == 0.0
    assert calc.workload(8, 100, None, 8).storage is None


def test_gpus_per_vm_must_be_positive() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        calc.workload(8, 100, None, 0)


@pytest.mark.parametrize(
    ("kind", "magnitude", "expected"),
    [
        (PERCENT, None, None),
        (PERCENT, -99.9, Custom(PERCENT, -99.9)),
        (PERCENT, 1_000, Custom(PERCENT, 1_000.0)),
        (USD, -1_000, Custom(USD, -1_000.0)),
        (USD, 1_000, Custom(USD, 1_000.0)),
    ],
)
def test_custom_changes_within_bounds(
    kind: str, magnitude: float | None, expected: Custom | None
) -> None:
    assert calc.custom(kind, magnitude) == expected


@pytest.mark.parametrize(
    ("kind", "magnitude", "message"),
    [
        (PERCENT, -100, "above −100% and at most 1,000%"),
        (PERCENT, 1_000.1, "above −100% and at most 1,000%"),
        (PERCENT, math.nan, "above −100% and at most 1,000%"),
        (USD, 1_000.01, "from −1,000 to 1,000 USD per GPU-hour"),
        (USD, -math.inf, "from −1,000 to 1,000 USD per GPU-hour"),
    ],
)
def test_custom_changes_out_of_bounds_refused(
    kind: str, magnitude: float, message: str
) -> None:
    with pytest.raises(Refused, match=message):
        calc.custom(kind, magnitude)


def test_unknown_custom_kind_is_a_programming_error() -> None:
    with pytest.raises(ValueError, match="unknown scenario kind"):
        calc.custom("ratio", 2.0)


def test_budget_inputs() -> None:
    assert calc.budget(None) is None
    assert calc.budget(10_000_000_000) == 10_000_000_000.0
    with pytest.raises(Refused, match="enter an amount above zero"):
        calc.budget(0)
    with pytest.raises(Refused, match="enter an amount above zero"):
        calc.budget(-5)
    with pytest.raises(Refused, match="must be a number"):
        calc.budget(math.nan)
    # Below a cent the headroom can underflow to zero (found by Hypothesis, Phase 6).
    with pytest.raises(Refused, match=r"at least USD 0\.01"):
        calc.budget(5e-324)
    assert calc.budget(0.01) == 0.01
    with pytest.raises(Refused, match="at most USD 10,000,000,000"):
        calc.budget(10_000_000_001)


# --- starting price and cost ---


def test_lowest_member_by_default_and_a_picked_member_otherwise() -> None:
    found = group("on_demand", ("Standard_B", 0.6), ("Standard_A", 0.5))
    lowest = calc.start(found)
    assert (lowest.member.name, lowest.usd_per_gpu_hour, lowest.lowest) == (
        "Standard_A",
        0.5,
        True,
    )
    picked = calc.start(found, "Standard_B")
    assert (picked.member.name, picked.usd_per_gpu_hour, picked.lowest) == (
        "Standard_B",
        0.6,
        False,
    )
    assert picked.member.price == pytest.approx(4.8)  # its published VM-hour price


def test_ties_go_to_the_first_size_name() -> None:
    found = group("on_demand", ("Standard_Z", 0.5), ("Standard_A", 0.5))
    assert calc.start(found).member.name == "Standard_A"
    assert calc.start(found, "Standard_Z").lowest is False


def test_unknown_size_and_empty_group_are_programming_errors() -> None:
    with pytest.raises(ValueError, match="not a member"):
        calc.start(group(), "Standard_X")
    empty = group()
    empty.members = []
    with pytest.raises(ValueError, match="at least one member"):
        calc.start(empty)


def test_known_cost_without_and_with_storage() -> None:
    begin = calc.start(group())  # 2.5 USD/GPU-hour, 8 GPUs per VM
    without = calc.cost(begin, Workload(8, 100.0))
    assert (without.vms, without.compute, without.storage, without.total) == (
        1,
        2_000.0,
        None,
        2_000.0,
    )
    stored = calc.cost(begin, Workload(8, 100.0, 150.0))
    assert (stored.compute, stored.storage, stored.total) == (2_000.0, 150.0, 2_150.0)


# --- scenarios ---


@pytest.mark.parametrize("per_gpu", [0.1, 2.5, 12.291267, 98.0])
def test_project_example_whatever_the_starting_price(per_gpu: float) -> None:
    begin = calc.start(group("on_demand", (H100, per_gpu)))
    result = calc.calculate(begin, Workload(32, 720.0), [begin.group])
    example = rows(result)["example-050"]
    assert example.exposure == 11_520.0
    assert example.effect == calc.ADDITIONAL
    assert example.change == 0.5


def test_known_scenario_rows() -> None:
    begin = calc.start(group())  # 2.5 USD/GPU-hour
    result = calc.calculate(begin, Workload(8, 100.0), [begin.group])
    found = rows(result)
    assert list(found) == ["decline-25", "increase-25", "example-050", "spike-100"]
    decline = found["decline-25"]
    assert decline.price == pytest.approx(1.875)
    assert decline.change == pytest.approx(-0.625)
    assert decline.change_pct == pytest.approx(-25.0)
    assert decline.cost == pytest.approx(1_500.0)
    assert decline.exposure == pytest.approx(-500.0)
    assert decline.effect == calc.LOWER
    assert found["increase-25"].exposure == pytest.approx(500.0)
    assert found["example-050"].change_pct == pytest.approx(20.0)
    spike = found["spike-100"]
    assert (spike.price, spike.cost, spike.exposure) == pytest.approx(
        (5.0, 4_000.0, 2_000.0)
    )
    assert result.version == "scenarios-v1"
    assert all(row.above_payg is None for row in result.rows)


def test_storage_is_unchanged_across_scenarios() -> None:
    begin = calc.start(group())
    result = calc.calculate(begin, Workload(8, 100.0, 150.0), [begin.group])
    decline = rows(result)["decline-25"]
    assert decline.cost == pytest.approx(1_650.0)
    assert decline.exposure == pytest.approx(-500.0)


def test_custom_row_comes_last_and_a_price_at_or_below_zero_is_refused() -> None:
    begin = calc.start(group("on_demand", (H100, 0.40)))
    result = calc.calculate(begin, Workload(8, 100.0), [begin.group], Custom(USD, -0.5))
    custom = result.rows[-1]
    assert custom.id == calc.CUSTOM
    assert custom.name == (
        "Custom: −0.5 USD/GPU-hour (entered by you, not part of scenarios-v1)"
    )
    assert custom.effect == calc.ZERO_OR_BELOW
    assert not custom.computed
    assert (custom.price, custom.cost, custom.exposure) == (None, None, None)


def test_a_custom_change_of_zero_reads_no_change() -> None:
    begin = calc.start(group())
    result = calc.calculate(
        begin, Workload(8, 100.0), [begin.group], Custom(PERCENT, 0)
    )
    assert result.rows[-1].exposure == 0.0
    assert result.rows[-1].effect == calc.NO_CHANGE
    assert result.rows[-1].name.startswith("Custom: +0%")


def test_custom_percent_name() -> None:
    assert calc.custom_name(Custom(PERCENT, 10.0)) == (
        "Custom: +10% (entered by you, not part of scenarios-v1)"
    )


@pytest.mark.parametrize(
    ("change", "shown"),
    [
        (Custom(PERCENT, 0.00001), "Custom: +1e-05%"),
        (Custom(USD, -0.00004), "Custom: −4e-05 USD/GPU-hour"),
        (Custom(USD, 1_000.0), "Custom: +1,000 USD/GPU-hour"),
        # Four decimals would round these to a boundary the move is not at (D50).
        (Custom(PERCENT, -99.99999), "Custom: −99.99999%"),
        (Custom(USD, -11.99999), "Custom: −11.99999 USD/GPU-hour"),
    ],
)
def test_a_small_custom_change_is_never_named_zero(change: Custom, shown: str) -> None:
    assert calc.custom_name(change).startswith(shown + " (")


def test_percentage_and_usd_scenarios_use_one_formula_each() -> None:
    assert calc.priced(2.5, PERCENT, -25.0) == (2.5 * 0.75, 2.5 * 0.75 - 2.5)
    assert calc.priced(0.1, USD, 0.5) == (0.1 + 0.5, 0.5)  # the change stays exact


def test_calculate_refuses_a_workload_that_is_not_whole_vms() -> None:
    begin = calc.start(group())
    with pytest.raises(ValueError, match="whole number"):
        calc.calculate(begin, Workload(12, 100.0), [begin.group])


# --- Spot to pay-as-you-go fallback and the note ---


def spot_case(
    spot: float, payg: float | None, payg_size: str = H100
) -> tuple[calc.Start, list[RegionGroup]]:
    spot_group = group("spot", (H100, spot))
    found = [spot_group]
    if payg is not None:
        found.append(group("on_demand", (payg_size, payg)))
    return calc.start(spot_group), found


def test_fallback_priced_from_the_same_size_on_pay_as_you_go() -> None:
    begin, found = spot_case(1.0, 4.0)
    result = calc.calculate(begin, Workload(8, 10.0), found)
    fallback = rows(result)[calc.FALLBACK]
    assert fallback.exposure == pytest.approx(240.0)
    assert fallback.price == 4.0
    assert fallback.effect == calc.ADDITIONAL
    assert fallback.name == "Spot to pay-as-you-go fallback"
    assert result.payg_key == GroupKey("H100 NVLink 80GB", 8, "westeurope", "on_demand")
    assert result.payg is not None and result.payg.name == H100
    assert [row.id for row in result.rows][-1] == calc.FALLBACK


def test_fallback_with_equal_prices_reads_no_change() -> None:
    begin, found = spot_case(2.0, 2.0)
    fallback = rows(calc.calculate(begin, Workload(8, 10.0), found))[calc.FALLBACK]
    assert fallback.exposure == 0.0
    assert fallback.effect == calc.NO_CHANGE


@pytest.mark.parametrize(
    ("payg", "payg_size"), [(None, H100), (4.0, "Standard_ND96amsr_A100_v4")]
)
def test_fallback_not_computed_without_the_size_on_pay_as_you_go(
    payg: float | None, payg_size: str
) -> None:
    begin, found = spot_case(1.0, payg, payg_size)
    result = calc.calculate(begin, Workload(8, 10.0), found)
    fallback = rows(result)[calc.FALLBACK]
    assert fallback.effect == calc.NO_PAYG
    assert not fallback.computed and fallback.price is None
    assert result.payg is None
    assert result.payg_key is not None  # the key is still named
    assert all(row.above_payg is None for row in result.rows)


def test_fallback_ignores_a_pay_as_you_go_group_from_another_snapshot() -> None:
    spot_group = group("spot", (H100, 1.0))
    other = group(
        "on_demand",
        (H100, 4.0),
        snapshot=Snapshot("azure-retail", "run-0", DAY, "synthetic"),
    )
    result = calc.calculate(
        calc.start(spot_group), Workload(8, 10.0), [spot_group, other]
    )
    assert rows(result)[calc.FALLBACK].effect == calc.NO_PAYG


def test_no_fallback_for_a_pay_as_you_go_start() -> None:
    begin = calc.start(group())
    result = calc.calculate(begin, Workload(8, 10.0), [begin.group])
    assert calc.FALLBACK not in rows(result)
    assert result.payg_key is None


def test_note_on_a_spot_row_above_pay_as_you_go_and_not_below() -> None:
    begin, found = spot_case(2.0, 2.0)
    equal = rows(calc.calculate(begin, Workload(8, 10.0), found))
    assert equal["increase-25"].above_payg == 2.0
    assert equal["increase-25"].exposure == pytest.approx(40.0)  # arithmetic kept
    assert equal["decline-25"].above_payg is None
    assert equal[calc.FALLBACK].above_payg is None
    begin, found = spot_case(0.6, 2.0)  # 30% of pay-as-you-go
    below = rows(calc.calculate(begin, Workload(8, 10.0), found))
    assert below["spike-100"].above_payg is None


def test_note_on_a_custom_row_and_on_headroom() -> None:
    begin, found = spot_case(1.0, 1.5)
    result = calc.calculate(
        begin, Workload(8, 10.0), found, Custom(PERCENT, 60.0), limit=80.0
    )
    assert result.rows[-1].above_payg == 1.5
    assert result.headroom is not None
    assert result.headroom.rise == pytest.approx(1.0)
    assert result.headroom.above_payg == 1.5


# --- budget headroom ---


def test_known_headroom() -> None:
    begin = calc.start(group("on_demand", (H100, 2.0)))
    result = calc.calculate(begin, Workload(32, 720.0), [begin.group], limit=11_520.0)
    assert result.headroom is not None
    assert result.headroom.rise == pytest.approx(0.5)
    assert result.headroom.rise_pct == pytest.approx(25.0)
    assert result.headroom.above_payg is None


def test_no_headroom_without_a_budget() -> None:
    begin = calc.start(group())
    assert calc.calculate(begin, Workload(8, 10.0), [begin.group]).headroom is None


# --- scenario ladder ladder-v1 (phase-7 D7) ---


def ladder_rows(result: calc.Result) -> dict[str, calc.LadderRow]:
    return {row.id: row for row in result.ladder.rows}


def cell(result: calc.Result, row_id: str, gpus: int) -> float:
    row = ladder_rows(result)[row_id]
    assert row.cells is not None
    return row.cells[result.ladder.columns.index(gpus)]


def test_known_ladder_cells() -> None:
    begin = calc.start(group())  # 2.5 USD/GPU-hour
    result = calc.calculate(begin, Workload(32, 720.0), [begin.group])
    ladder = result.ladder
    assert ladder.version == "ladder-v1"
    assert ladder.columns == (8, 16, 32, 64, 128)
    assert ladder.entered == 32
    assert cell(result, "up-25", 32) == pytest.approx(14_400.0)
    assert cell(result, "down-50", 32) == pytest.approx(-28_800.0)
    assert cell(result, "up-100", 32) == pytest.approx(57_600.0)
    assert cell(result, "flat-050", 32) == pytest.approx(11_520.0)
    assert cell(result, "up-10", 8) == pytest.approx(1_440.0)
    assert [row.id for row in ladder.rows] == [
        "down-50",
        "down-25",
        "down-10",
        "up-10",
        "up-25",
        "up-50",
        "up-100",
        "flat-050",
    ]
    assert all(row.refusal == "" and row.above_payg is None for row in ladder.rows)


def test_entered_count_adds_a_column() -> None:
    begin = calc.start(group())
    result = calc.calculate(begin, Workload(24, 720.0), [begin.group])
    assert result.ladder.columns == (8, 16, 24, 32, 64, 128)
    assert result.ladder.entered == 24
    assert cell(result, "up-100", 24) == pytest.approx(24 * 720 * 2.5)


def test_defined_columns_that_are_not_whole_vms_are_left_out() -> None:
    assert calc.ladder_columns(32, 16) == (16, 32, 64, 128)
    assert calc.ladder_columns(256, 8) == (8, 16, 32, 64, 128, 256)


def test_entered_column_matches_scenarios_v1() -> None:
    begin = calc.start(group("on_demand", (H100, 3.7)))
    result = calc.calculate(begin, Workload(40, 333.0), [begin.group])
    exposure = {row.id: row.exposure for row in result.rows}
    pairs = {
        "down-25": "decline-25",
        "up-25": "increase-25",
        "up-100": "spike-100",
        "flat-050": "example-050",
    }
    for step, scenario in pairs.items():
        assert cell(result, step, 40) == pytest.approx(exposure[scenario])


def test_storage_is_not_in_the_ladder() -> None:
    begin = calc.start(group())
    bare = calc.calculate(begin, Workload(32, 720.0), [begin.group])
    stored = calc.calculate(begin, Workload(32, 720.0, 5_000.0), [begin.group])
    assert bare.ladder == stored.ladder


def test_custom_ladder_row_comes_last_and_is_refused_at_or_below_zero() -> None:
    begin = calc.start(group("on_demand", (H100, 0.40)))
    result = calc.calculate(begin, Workload(8, 10.0), [begin.group], Custom(USD, -0.50))
    custom = result.ladder.rows[-1]
    assert custom.id == calc.CUSTOM
    assert custom.label == "Custom −0.5 USD/GPU-h"
    assert custom.cells is None and not custom.computed
    assert custom.refusal == calc.ZERO_OR_BELOW


def test_custom_percent_ladder_row() -> None:
    begin = calc.start(group())
    result = calc.calculate(
        begin, Workload(8, 10.0), [begin.group], Custom(PERCENT, 15.0)
    )
    custom = ladder_rows(result)[calc.CUSTOM]
    assert custom.label == "Custom +15%"
    assert calc.custom_label(Custom(PERCENT, -99.99999)) == "Custom −99.99999%"
    assert cell(result, calc.CUSTOM, 8) == pytest.approx(8 * 10 * 2.5 * 0.15)


def test_fallback_ladder_row_crosses_to_pay_as_you_go() -> None:
    begin, found = spot_case(1.0, 4.0)
    result = calc.calculate(begin, Workload(8, 10.0), found, Custom(PERCENT, 10.0))
    ids = [row.id for row in result.ladder.rows]
    assert ids[-2:] == [calc.FALLBACK, calc.CUSTOM]
    fallback = ladder_rows(result)[calc.FALLBACK]
    assert fallback.label == "Spot → pay-as-you-go"
    assert cell(result, calc.FALLBACK, 8) == pytest.approx(240.0)
    assert fallback.above_payg is None


def test_fallback_ladder_row_not_computed_without_a_listing() -> None:
    begin, found = spot_case(1.0, None)
    result = calc.calculate(begin, Workload(8, 10.0), found)
    fallback = ladder_rows(result)[calc.FALLBACK]
    assert fallback.cells is None
    assert fallback.refusal == calc.NO_PAYG


def test_spot_ladder_rows_above_pay_as_you_go_are_marked() -> None:
    begin, found = spot_case(0.6, 1.0)  # Spot at 60% of pay-as-you-go
    result = calc.calculate(begin, Workload(8, 10.0), found)
    marked = {row.id for row in result.ladder.rows if row.above_payg is not None}
    assert marked == {"up-100", "flat-050"}  # 1.2 and 1.1 against 1.0
    assert ladder_rows(result)["up-100"].above_payg == 1.0
    assert cell(result, "up-100", 8) == pytest.approx(8 * 10 * 0.6)
