"""The workload view model and its independent check, on the synthetic demo database.

Prices are the demo file's invented ones (synthetic): H100 x8 is 96 USD per VM-hour in
eastus (12.0 USD/GPU-hour) on pay-as-you-go and Spot alike, 100 in westeurope (12.5) on
pay-as-you-go and 40 (5.0) on Spot, and 48 (6.0) on Spot in uksouth, which has no
pay-as-you-go listing. Every expected figure below was worked out by hand.
"""

import dataclasses
import math
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import duckdb
import pytest

from compute_cost_risk_monitor import calculator as calc
from compute_cost_risk_monitor import (
    dashboard,
    groups,
    normalize,
    synthetic,
    workload_check,
)
from compute_cost_risk_monitor.calculator import Custom, Workload
from compute_cost_risk_monitor.groups import GroupKey, RegionGroup
from compute_cost_risk_monitor.scenarios import JUDGEMENT, NOT_A_FORECAST, PERCENT, USD
from seed import database
from support import FIXTURES

AS_OF = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
H100 = "H100 NVLink 80GB"
KNOWN = Workload(32, 720.0)  # PROJECT's example workload


@pytest.fixture(scope="module")
def found() -> Iterator[list[RegionGroup]]:
    connection: duckdb.DuckDBPyConnection = database()
    synthetic.ingest_file(connection, FIXTURES / "azure_demo.json")
    normalize.normalize_pending(connection, AS_OF)
    (snap,) = groups.snapshots(connection, "azure-retail")
    yield groups.region_groups(connection, snap)
    connection.close()


def pick(
    found: list[RegionGroup], variant: str, count: int, region: str, rental: str
) -> RegionGroup:
    group = dashboard.find_group(found, GroupKey(variant, count, region, rental))
    assert group is not None
    return group


def result(
    found: list[RegionGroup],
    region: str = "eastus",
    rental: str = "on_demand",
    work: Workload = KNOWN,
    change: Custom | None = None,
    limit: float | None = None,
) -> calc.Result:
    begin = calc.start(pick(found, H100, 8, region, rental))
    return calc.calculate(begin, work, found, change, limit)


# --- the independent check over real calculator output ---

CASES = [
    ("eastus", "on_demand", Workload(32, 720.0), None, None),
    ("eastus", "on_demand", Workload(8, 0.5, 150.0), Custom(PERCENT, -99.9), 1.0),
    ("eastus", "spot", Workload(16, 100.0), Custom(USD, 0.25), 5_000.0),
    ("westeurope", "spot", Workload(800, 8_784.0, 1e6), Custom(PERCENT, 1_000), 1e10),
    ("uksouth", "spot", Workload(8, 24.0), Custom(USD, -6.0), None),
    ("westeurope", "on_demand", Workload(100_000, 8_784.0), Custom(USD, -12.4999), 1.0),
]


@pytest.mark.parametrize(("region", "rental", "work", "change", "limit"), CASES)
def test_calculator_output_passes_the_independent_check(
    found: list[RegionGroup],
    region: str,
    rental: str,
    work: Workload,
    change: Custom | None,
    limit: float | None,
) -> None:
    shown = result(found, region, rental, work, change, limit)
    assert dashboard.check(shown.start, shown, work, change, limit, found) == []


@pytest.mark.parametrize(
    "change",
    [
        Custom(PERCENT, -99.99999),
        Custom(PERCENT, -99.99999999999999),
        Custom(PERCENT, 999.99999),
        Custom(USD, -11.9999999999),
    ],
)
def test_extreme_custom_changes_pass_on_many_prices(
    found: list[RegionGroup], change: Custom
) -> None:
    """Valid input never blanks the page: the check and the calculator price a scenario
    with the same formulas, at tolerances scaled to each figure."""
    group = pick(found, H100, 8, "eastus", "on_demand")
    member = group.members[0]
    failures = 0
    for step in range(400):
        per_gpu = 0.05 + step * 0.0317  # invented prices across two decades
        priced = dataclasses.replace(
            member, usd_per_gpu_hour=per_gpu, price=per_gpu * 8
        )
        trial = dataclasses.replace(group, members=[priced])
        begin = calc.start(trial)
        for work in (Workload(8, 0.5), Workload(100_000, 8_784.0, 1e7)):
            shown = calc.calculate(begin, work, [trial], change, 1.0)
            failures += bool(dashboard.check(begin, shown, work, change, 1.0, [trial]))
    assert failures == 0


def test_tampered_exposure_is_caught(found: list[RegionGroup]) -> None:
    shown = result(found)
    rows = list(shown.rows)
    rows[2] = dataclasses.replace(rows[2], exposure=11_520.01)
    tampered = dataclasses.replace(shown, rows=tuple(rows))
    failed = dashboard.check(
        shown.start, tampered, Workload(32, 720.0), None, None, found
    )
    assert "example-050 exposure" in failed


def test_unchecked_labels_and_storage_are_now_caught(found: list[RegionGroup]) -> None:
    work = Workload(32, 720.0, 500.0)
    shown = result(found, work=work)
    rows = list(shown.rows)
    rows[0] = dataclasses.replace(rows[0], effect=calc.ADDITIONAL, above_payg=99.0)
    cost = dataclasses.replace(shown.cost, storage=9_999.0)
    tampered = dataclasses.replace(shown, rows=tuple(rows), cost=cost)
    failed = dashboard.check(shown.start, tampered, work, None, None, found)
    assert {"decline-25 effect", "decline-25 note", "storage"} <= set(failed)


def test_a_result_priced_from_another_member_is_caught(
    found: list[RegionGroup],
) -> None:
    t4 = pick(found, "T4 16GB", 1, "eastus", "on_demand")
    picked = calc.start(t4, "Standard_NC8as_T4_v3")
    work = Workload(8, 10.0)
    other = calc.calculate(calc.start(t4), work, found)  # priced from the lowest
    failed = dashboard.check(picked, other, work, None, None, found)
    assert "starting member" in failed
    assert "starting price" in failed


def test_dropped_headroom_and_custom_row_are_caught(found: list[RegionGroup]) -> None:
    work, change = Workload(32, 720.0), Custom(PERCENT, 10.0)
    shown = result(found, change=change, limit=11_520.0)
    dropped = dataclasses.replace(shown, rows=shown.rows[:-1], headroom=None)
    failed = dashboard.check(shown.start, dropped, work, change, 11_520.0, found)
    assert "scenario rows" in failed
    assert "headroom" in failed


def test_a_missed_pay_as_you_go_listing_is_caught(found: list[RegionGroup]) -> None:
    # The calculator is given no pay-as-you-go group, but the page's groups hold one.
    spot = pick(found, H100, 8, "westeurope", "spot")
    work = Workload(8, 10.0)
    blind = calc.calculate(calc.start(spot), work, [spot])
    assert blind.rows[-1].effect == calc.NO_PAYG
    failed = dashboard.check(blind.start, blind, work, None, None, found)
    assert "fallback missing" in failed


def test_missing_published_price_fails_the_check(found: list[RegionGroup]) -> None:
    shown = result(found)
    member = dataclasses.replace(shown.start.member, price=None)
    begin = dataclasses.replace(shown.start, member=member)
    broken = dataclasses.replace(shown, start=begin)
    failed = dashboard.check(begin, broken, Workload(32, 720.0), None, None, found)
    assert failed == ["published price missing"]


# --- known figures on the demo ---


def test_known_workload_on_the_demo(found: list[RegionGroup]) -> None:
    shown = result(found)
    cost = dashboard.cost_frame(shown)
    assert list(cost.columns) == ["Item", "Basis", dashboard.AMOUNT]
    assert list(cost["Item"]) == ["Compute", "Storage", "Total"]
    assert cost[dashboard.AMOUNT][0] == 276_480.0  # 32 x 720 x 12.0
    assert math.isnan(cost[dashboard.AMOUNT][1])
    assert cost["Basis"][0] == ("32 GPUs (4 VMs) × 720 h × USD 12.0000/GPU-hour")
    assert cost["Basis"][1] == "not included"
    assert dashboard.vms_text(shown) == "32 GPUs = 4 VMs of 8 GPUs"
    one = result(found, work=Workload(8, 10.0))
    assert dashboard.vms_text(one) == "8 GPUs = 1 VM of 8 GPUs"
    assert dashboard.cost_frame(one)["Basis"][0].startswith("8 GPUs (1 VM) × 10 h")
    frame = dashboard.scenario_frame(shown)
    assert list(frame.columns) == dashboard.SCENARIO_COLUMNS
    assert list(frame.columns)[:3] == ["Scenario", "Effect", dashboard.EXPOSURE]
    assert list(frame.columns)[-1] == "Narrative"
    assert frame["Scenario"][0] == dashboard.STARTING
    assert frame["Effect"][0] == dashboard.BASELINE
    example = frame[frame["Scenario"] == "PROJECT example +$0.50/GPU-hour"].iloc[0]
    assert example[dashboard.EXPOSURE] == 11_520.0
    assert example["Effect"] == calc.ADDITIONAL


def test_storage_entered_is_added_and_labelled(found: list[RegionGroup]) -> None:
    shown = result(found, work=Workload(8, 100.0, 150.0))
    cost = dashboard.cost_frame(shown)
    assert list(cost[dashboard.AMOUNT]) == [9_600.0, 150.0, 9_750.0]
    assert cost["Basis"][1] == "entered by you, not an Azure list price"
    caption = dashboard.workload_caption(shown)
    assert "Storage: USD 150.00 entered by you for this period" in caption
    assert dashboard.STORAGE_NONE not in caption


def test_workload_caption_carries_key_snapshot_label_and_assumptions(
    found: list[RegionGroup],
) -> None:
    caption = dashboard.workload_caption(result(found))
    for text in (
        "Group: H100 NVLink 80GB · 8 GPUs · eastus · pay-as-you-go",
        "snapshot 2026-10-12 09:00 UTC",
        "data label: synthetic",
        "Excludes disks and storage",
        dashboard.STORAGE_NONE,
        dashboard.BILLING,
        dashboard.HOURS_NOTE,
    ):
        assert text in caption
    assert dashboard.SPOT_LINE not in caption


def test_spot_captions_add_the_spot_line_and_the_crossing(
    found: list[RegionGroup],
) -> None:
    shown = result(found, "westeurope", "spot")
    assert dashboard.SPOT_LINE in dashboard.workload_caption(shown)
    caption = dashboard.scenario_caption(shown)
    for text in ("scenarios-v1", NOT_A_FORECAST, JUDGEMENT, dashboard.CROSSES_RENTAL):
        assert text in caption
    payg = pick(found, H100, 8, "westeurope", "on_demand").members[0]
    assert caption.endswith(
        "H100 NVLink 80GB · 8 GPUs · westeurope · Spot →"
        " H100 NVLink 80GB · 8 GPUs · westeurope · pay-as-you-go"
        f" (Standard_ND96isr_H100_v5, item key {payg.item_key})"
    )
    assert "(not listed in this snapshot)" not in caption
    unlisted = dashboard.scenario_caption(result(found, "uksouth", "spot"))
    assert unlisted.endswith(
        "H100 NVLink 80GB · 8 GPUs · uksouth · pay-as-you-go"
        " (not listed in this snapshot)"
    )
    plain = dashboard.scenario_caption(result(found))
    assert dashboard.CROSSES_RENTAL not in plain
    assert NOT_A_FORECAST in plain


def test_fallback_rows_on_the_demo(found: list[RegionGroup]) -> None:
    priced = dashboard.scenario_frame(result(found, "westeurope", "spot"))
    fallback = priced.iloc[-1]
    assert fallback["Scenario"] == calc.FALLBACK_NAME
    assert fallback[dashboard.EXPOSURE] == pytest.approx(32 * 720 * 7.5)
    assert fallback["Note"] == dashboard.CROSSES_RENTAL
    equal = dashboard.scenario_frame(result(found, "eastus", "spot")).iloc[-1]
    assert (equal[dashboard.EXPOSURE], equal["Effect"]) == (0.0, calc.NO_CHANGE)
    unlisted = dashboard.scenario_frame(result(found, "uksouth", "spot")).iloc[-1]
    assert unlisted["Effect"] == calc.NO_PAYG
    assert math.isnan(unlisted[dashboard.EXPOSURE])
    assert math.isnan(unlisted[dashboard.SCENARIO_USD])


def test_note_above_pay_as_you_go_on_the_demo(found: list[RegionGroup]) -> None:
    frame = dashboard.scenario_frame(result(found, "eastus", "spot"))
    increase = frame[frame["Scenario"] == "Increase +25%"].iloc[0]
    assert increase["Note"] == dashboard.ABOVE_PAYG.format(price="12.0000")
    assert increase[dashboard.EXPOSURE] == pytest.approx(32 * 720 * 3.0)
    decline = frame[frame["Scenario"] == "Decline −25%"].iloc[0]
    assert decline["Note"] == ""
    below = dashboard.scenario_frame(result(found, "westeurope", "spot"))
    assert set(below["Note"][1:5]) == {""}  # 5.0 doubled stays below 12.5


def test_refused_custom_row_shows_no_figure(found: list[RegionGroup]) -> None:
    frame = dashboard.scenario_frame(
        result(found, "uksouth", "spot", change=Custom(USD, -6.0))
    )
    custom = frame.iloc[-1]
    assert custom["Effect"] == calc.ZERO_OR_BELOW
    assert math.isnan(custom[dashboard.EXPOSURE])
    assert custom["Scenario"].startswith("Custom: −6 USD/GPU-hour")


def test_headroom_text(found: list[RegionGroup]) -> None:
    shown = result(found, limit=11_520.0)
    assert dashboard.headroom_text(shown) == (
        "A rise of USD 0.5000 per GPU-hour (4.2% of starting price) would use up"
        " USD 11,520.00 over 32 GPUs × 720 h. Storage unchanged. Scenario calculation,"
        " not a forecast."
    )
    assert dashboard.headroom_text(result(found)) is None
    tiny = result(found, work=Workload(100_000, 8_784.0), limit=1.0)
    text = dashboard.headroom_text(tiny)
    assert text is not None
    assert text.startswith("A rise of USD 1.14e-09 per GPU-hour (9.49e-09% of")
    spot = result(found, "eastus", "spot", limit=11_520.0)
    text = dashboard.headroom_text(spot)
    assert text is not None and dashboard.ABOVE_PAYG.format(price="12.0000") in text


def test_start_text_names_the_lowest_member_only_when_it_is(
    found: list[RegionGroup],
) -> None:
    t4 = pick(found, "T4 16GB", 1, "eastus", "on_demand")
    assert dashboard.sizes(t4) == ["Standard_NC4as_T4_v3", "Standard_NC8as_T4_v3"]
    lowest = dashboard.start_text(calc.start(t4))
    assert lowest.startswith(
        "Starting price: USD 0.6000/GPU-hour for Standard_NC4as_T4_v3"
        " (lowest listed in this group), from its published price USD 0.6 per VM per"
        " 1 Hour (1 GPU per VM)"
    )
    picked = dashboard.start_text(calc.start(t4, "Standard_NC8as_T4_v3"))
    assert dashboard.LOWEST_MEMBER not in picked
    assert "item key" in picked and "run " in picked


def test_exposure_chart_draws_computed_rows_and_a_zero_rule(
    found: list[RegionGroup],
) -> None:
    shown = result(found, "uksouth", "spot", change=Custom(USD, -6.0))
    spec = dashboard.exposure_chart(shown).to_dict()
    layers: list[tuple[str, list[dict[str, Any]]]] = []
    for layer in spec["layer"]:
        mark = layer["mark"]
        kind = mark if isinstance(mark, str) else mark["type"]
        layers.append((kind, spec["datasets"][layer["data"]["name"]]))
    (bar_kind, bars), (rule_kind, rules) = layers
    assert (bar_kind, rule_kind) == ("bar", "rule")
    assert [b["Scenario"] for b in bars] == [
        "Decline −25%",
        "Increase +25%",
        "PROJECT example +$0.50/GPU-hour",
        "Spike +100% (price doubles)",
    ]  # the unlisted fallback and the refused custom row are absent
    assert bars[2][dashboard.EXPOSURE] == 11_520.0  # 32 GPUs x 720 h x 0.50
    assert rules == [{dashboard.EXPOSURE: 0.0}]
    assert "line" not in str(spec["layer"])


@pytest.mark.parametrize(
    ("per_vm", "default"), [(1, 32), (2, 32), (4, 32), (8, 32), (3, 3), (64, 64)]
)
def test_default_gpus_make_whole_vms(per_vm: int, default: int) -> None:
    assert dashboard.default_gpus(per_vm) == default


def test_size_keys_differ_per_group(found: list[RegionGroup]) -> None:
    keys = {dashboard.size_key(g.key) for g in found}
    assert len(keys) == len(found)


def test_display_formats_and_text() -> None:
    assert dashboard.FORMATS[dashboard.EXPOSURE] == "%,.2f"
    assert dashboard.FORMATS[dashboard.SCENARIO_COST] == "%,.2f"
    assert dashboard.FORMATS[dashboard.AMOUNT] == "%,.2f"
    assert dashboard.FORMATS[dashboard.CHANGE_PCT] == "%.1f"
    assert dashboard.FORMATS[dashboard.CHANGE_USD] == "%.4f"
    assert dashboard.FORMATS[dashboard.SCENARIO_USD] == "%.4f"
    assert dashboard.money(11_520) == "USD 11,520.00"
    assert [dashboard.hours_text(h) for h in (720.0, 0.5, 8_784.0, 0.004)] == [
        "720 h",
        "0.5 h",
        "8,784 h",
        "0.004 h",
    ]
    assert dashboard.hours_text(0.00001) == "1e-05 h"  # never "0 h"
    assert dashboard.fixed(0.0000000011, 4) == "1.1e-09"
    assert dashboard.fixed(0.5, 4) == "0.5000"
    assert dashboard.fixed(0.0, 1) == "0.0"


def test_check_and_calculator_agree_on_effect_words() -> None:
    assert workload_check.ADDITIONAL == calc.ADDITIONAL
    assert workload_check.LOWER == calc.LOWER
    assert workload_check.NO_CHANGE == calc.NO_CHANGE
    assert calc.ZERO_OR_BELOW.startswith(workload_check.NOT_COMPUTED)
    assert calc.NO_PAYG.startswith(workload_check.NOT_COMPUTED)


def test_marketplace_note_points_to_azure() -> None:
    assert "Azure list-price groups" in dashboard.MARKETPLACE_NOTE
    assert "data-quality rules" in dashboard.MARKETPLACE_NOTE
