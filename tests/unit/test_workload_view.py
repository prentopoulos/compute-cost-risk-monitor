"""The workload view model and its independent check, on the synthetic demo database.

Prices are the demo file's invented ones (synthetic): H100 x8 is 96 USD per VM-hour in
eastus (12.0 USD/GPU-hour) on pay-as-you-go and Spot alike, 100 in westeurope (12.5) on
pay-as-you-go and 40 (5.0) on Spot, and 48 (6.0) on Spot in uksouth, which has no
pay-as-you-go listing. Every expected figure below was worked out by hand.
"""

import dataclasses
from collections.abc import Iterator
from datetime import UTC, datetime

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
from compute_cost_risk_monitor.scenarios import JUDGEMENT, PERCENT, USD
from seed import Price, azure_run, database
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


# --- known figures on the demo (phase-7 D6, D7, D9, D32-D39) ---

# The footer's first line on the demo, worked out by hand (Phase 8 D30).
TAG = (
    "EXCL. disks and storage · egress · public IPs · licences · taxes · negotiated"
    " discounts · reservations and savings plans · Spot eviction risk · capacity and"
    " quota"
)
EXCLUSIONS = (
    "Excludes disks and storage, egress, public IPs, licences, taxes, negotiated"
    " discounts, reservations and savings plans, Spot eviction risk, capacity and"
    " quota."
)


def test_key_figures_on_the_demo(found: list[RegionGroup]) -> None:
    shown = result(found)
    assert dashboard.workload_figures(shown.start, shown, False) == [
        ("Cost, USD", "276,480.00"),  # 32 x 720 x 12.0
        ("USD/GPU-h · PAYG", "12.0000"),
        ("VMs", "4 × ND96isr H100 v5"),
        ("GPUs × h", "32 × 720"),
    ]
    budgeted = result(found, limit=11_520.0)
    assert dashboard.workload_figures(budgeted.start, budgeted, True)[-1] == (
        "Headroom, USD/GPU-h",
        "+0.5000 (4.2%)",
    )
    spot = result(found, "eastus", "spot", limit=11_520.0)
    figures = dict(dashboard.workload_figures(spot.start, spot, True))
    assert figures["USD/GPU-h · SPOT"] == "12.0000"
    assert figures["Headroom, USD/GPU-h"] == "+0.5000 (4.2%) †"  # 12.5 > 12.0


def test_key_figures_withheld_show_only_labels(found: list[RegionGroup]) -> None:
    begin = result(found).start
    assert dashboard.workload_figures(begin, None, True) == [
        ("Cost, USD", "—"),
        ("USD/GPU-h · PAYG", "—"),
        ("VMs", "—"),
        ("GPUs × h", "—"),
        ("Headroom, USD/GPU-h", "—"),
    ]
    assert len(dashboard.workload_figures(begin, None, False)) == 4


def test_cost_table_on_the_demo(found: list[RegionGroup]) -> None:
    table = dashboard.cost_table(result(found))
    assert list(table.columns) == ["", "USD/VM-h", "VM-h", "USD"]
    assert table.values.tolist() == [
        ["Compute", "96.00", "2,880", "276,480.00"],
        ["Storage", "", "", "—"],
        ["Total", "", "", "276,480.00"],
    ]
    stored = dashboard.cost_table(result(found, work=Workload(8, 100.0, 150.0)))
    assert stored.values.tolist() == [
        ["Compute", "96.00", "100", "9,600.00"],
        ["Storage", "", "", "150.00"],
        ["Total", "", "", "9,750.00"],
    ]
    html = dashboard.cost_styles(result(found)).to_html()
    assert "font-weight: 700" in html  # the total
    assert "text-align: right !important" in html


def test_grid_on_the_demo(found: list[RegionGroup]) -> None:
    shown = result(found)
    frame = dashboard.grid_frame(shown.ladder)
    assert list(frame.columns) == ["Δ price \\ GPUs", "8", "16", "32", "64", "128"]
    rows = {row[0]: row[1:] for row in frame.values.tolist()}
    assert list(rows) == [
        "−50%",
        "−25%",
        "−10%",
        "+10%",
        "+25%",
        "+50%",
        "+100%",
        "+0.50 USD/GPU-h",
    ]
    assert rows["+25%"][2] == "+69,120"  # 32 x 720 x 3.0
    assert rows["−50%"][2] == "−138,240"
    assert rows["+0.50 USD/GPU-h"] == [
        "+2,880",
        "+5,760",
        "+11,520",
        "+23,040",
        "+46,080",
    ]
    assert dashboard.grid_title(KNOWN) == (
        ":gray[**SCENARIO GRID** ·] **Δ cost, USD · 720 h**"  # D7's title
        " :gray[· **NOT A FORECAST**]"  # Phase 8 D30
    )


def _rem(css: str) -> float:
    return float(css.split("min-width: ")[1].split("rem")[0])


def test_tables_fill_the_mock_column() -> None:
    # Mock v3: one column about 950 px wide, COST 540 px; the rem is 14 px (D49). A
    # sixth column for an entered count shares the same width (D50).
    label = _rem(dashboard.LABEL_CELL)
    grid_px = (label + 5 * _rem(dashboard.grid_cell_css(5))) * 14
    six_px = (label + 6 * _rem(dashboard.grid_cell_css(6))) * 14
    cost_px = (label + 3 * _rem(dashboard.COST_CELL)) * 14
    assert 940 <= grid_px <= 960
    assert six_px <= 960
    assert 535 <= cost_px <= 545


def test_six_columns_keep_the_rules_and_the_width(found: list[RegionGroup]) -> None:
    ladder = result(found, work=Workload(24, 720.0)).ladder
    assert ladder.columns == (8, 16, 24, 32, 64, 128)
    styles = dashboard.grid_styles(ladder)
    by_row = {row.id: list(styles.iloc[i]) for i, row in enumerate(ladder.rows)}
    assert "border-top: 2px" in by_row["up-10"][0]
    assert "border-top: 1px" in by_row["flat-050"][0]
    assert "min-width: 9.58rem" in by_row["up-25"][1]


def test_grid_colours_rules_and_the_entered_column(found: list[RegionGroup]) -> None:
    ladder = result(found).ladder
    styles = dashboard.grid_styles(ladder)
    by_row = {row.id: list(styles.iloc[i]) for i, row in enumerate(ladder.rows)}
    colours = dashboard.COLOURS
    assert f"color: {colours['green']}" in by_row["down-50"][1]
    assert f"color: {colours['red']}" in by_row["up-25"][1]
    assert f"border-top: 2px solid {colours['zero']}" in by_row["up-10"][0]
    assert "border-top: 1px" in by_row["flat-050"][0]
    assert "border-top" not in by_row["up-25"][0]
    entered = by_row["up-25"][3]  # the 32-GPU column
    assert f"background-color: {colours['shade']}" in entered
    assert "font-weight: 700" in entered
    assert "background-color" not in by_row["up-25"][2]
    html = dashboard.grid(ladder).to_html()
    assert "th.col3 {" in html  # the entered column's header
    assert colours["accent"] in html


def test_grid_cells() -> None:
    assert dashboard.grid_cell(27_648.4) == "+27,648"
    assert dashboard.grid_cell(-13_824.0) == "−13,824"
    assert dashboard.grid_cell(0.0) == "0"
    assert dashboard.grid_cell(-0.004) == "−0.004"  # never shown as 0
    # Positional, never exponent form, at 3 significant digits (Phase 8 D14).
    assert dashboard.grid_cell(0.000000006) == "+0.000000006"
    assert dashboard.grid_cell(-0.000012345) == "−0.0000123"
    assert dashboard.grid_cell(0.1235) == "+0.124"  # half up
    assert dashboard.grid_cell(0.0012) == "+0.0012"
    # Whole USD round half up, not to even (D50).
    assert [dashboard.grid_cell(v) for v in (0.5, 2.5, 3.5, -2.5, 27_648.5)] == [
        "+1",
        "+3",
        "+4",
        "−3",
        "+27,649",
    ]


def test_grid_rows_for_spot_groups(found: list[RegionGroup]) -> None:
    priced = dashboard.grid_frame(result(found, "westeurope", "spot").ladder)
    fallback = priced.values.tolist()[-1]
    assert fallback[0] == "Spot → PAYG *"
    assert fallback[3] == "+172,800"  # 32 x 720 x (12.5 - 5.0)
    unlisted = dashboard.grid_frame(result(found, "uksouth", "spot").ladder)
    assert unlisted.values.tolist()[-1] == ["Spot → PAYG *"] + ["n/a"] * 5
    equal = result(found, "eastus", "spot")
    labels = list(dashboard.grid_frame(equal.ladder)[dashboard.GRID_CORNER])
    assert labels[:3] == ["−50%", "−25%", "−10%"]
    assert labels[3:8] == [  # above 12.0, the same size's pay-as-you-go price
        "+10% †",
        "+25% †",
        "+50% †",
        "+100% †",
        "+0.50 USD/GPU-h †",
    ]
    assert labels[-1] == "Spot → PAYG *"
    styles = dashboard.grid_styles(result(found, "uksouth", "spot").ladder)
    assert f"color: {dashboard.COLOURS['muted']}" in str(styles.iloc[-1, 3])


def test_refused_custom_row_shows_na(found: list[RegionGroup]) -> None:
    shown = result(found, "uksouth", "spot", change=Custom(USD, -6.0))
    last = dashboard.grid_frame(shown.ladder).values.tolist()[-1]
    assert last == ["Custom −6 USD/GPU-h"] + ["n/a"] * 5
    assert dashboard.footer(shown)[-1] == dashboard.ZERO_CLAUSE


def test_footer_clauses(found: list[RegionGroup]) -> None:
    # One line per clause, each starting with its mark (D49).
    assert dashboard.footer(result(found)) == [TAG]
    stored = dashboard.footer(result(found, work=Workload(32, 720.0, 5_000.0)))
    assert stored[1:] == ["Total includes USD 5,000.00 storage entered by you."]
    unlisted = dashboard.footer(result(found, "uksouth", "spot"))
    assert unlisted[1:] == [
        "* Crosses rental types (Spot → pay-as-you-go): same size, same region."
        " Not computed: no pay-as-you-go listing for this size in this region."
    ]
    priced = dashboard.footer(result(found, "westeurope", "spot"))
    assert priced[1:] == [dashboard.CROSSING_CLAUSE]  # computed, and no † row
    marked = dashboard.footer(result(found, "eastus", "spot"))
    assert marked[1:] == [
        dashboard.CROSSING_CLAUSE,
        "† Above this size's pay-as-you-go list price (USD 12.0000/GPU-h): the"
        " arithmetic, not what Azure would bill.",
    ]
    # No grid row reaches 12.5 there, but a rise of USD 200,000 / (32 x 720) does.
    roomy = result(found, "westeurope", "spot", limit=200_000.0)
    assert roomy.headroom is not None and roomy.headroom.above_payg == 12.5
    assert all(row.above_payg is None for row in roomy.ladder.rows)
    assert dashboard.footer(roomy)[-1].endswith(
        " Above this size's pay-as-you-go list price (USD 12.5000/GPU-h): the"
        " arithmetic, not what Azure would bill."
    )
    # On the page: muted lines with hard breaks between them.
    assert dashboard.footer_text(result(found, "eastus", "spot")) == "  \n".join(
        f":gray[{line}]" for line in marked
    )


def test_exclusions_tag_keeps_every_item() -> None:
    assert dashboard.exclusions_tag(EXCLUSIONS) == TAG
    assert TAG.count(" · ") == 8  # nine items, none dropped
    # Text of another shape is shown whole rather than cut (Phase 8 D30).
    assert dashboard.exclusions_tag("Storage excluded") == "Storage excluded"
    assert dashboard.exclusions_tag("Excludes egress") == "Excludes egress"


def test_workload_sources(found: list[RegionGroup]) -> None:
    shown = result(found, limit=11_520.0)
    lines = dashboard.workload_sources(shown.start.group, shown)
    assert lines[0] == "Group: H100 NVLink 80GB · 8 GPUs · eastus · pay-as-you-go"
    assert lines[1].startswith("Snapshot 2026-10-12 09:00 UTC, run ")
    assert lines[1].endswith(" · data label: synthetic")
    assert lines[2] == f"ladder-v1 and scenarios-v1: {JUDGEMENT}"
    for text in (
        dashboard.STORAGE_NONE,
        dashboard.BILLING,
        dashboard.HOURS_NOTE,
        dashboard.WORKLOAD_INTRO,
        dashboard.BUDGET_HINT,
        dashboard.headroom_text(shown),
    ):
        assert text in lines
    assert any(
        line.startswith("Starting price: USD 12.0000/GPU-hour") for line in lines
    )
    assert dashboard.SPOT_LINE not in lines
    assert dashboard.MULTI_SIZE not in lines  # one member: no Size choice
    t4 = pick(found, "T4 16GB", 1, "eastus", "on_demand")
    assert dashboard.MULTI_SIZE in dashboard.workload_sources(t4, None)  # D50
    withheld = dashboard.workload_sources(shown.start.group, None)
    assert not any(
        "Starting price" in line or "USD 0.5000" in line for line in withheld
    )
    assert dashboard.BILLING in withheld


def test_spot_sources_name_both_keys_and_the_full_note(
    found: list[RegionGroup],
) -> None:
    westeurope = result(found, "westeurope", "spot")
    lines = dashboard.workload_sources(westeurope.start.group, westeurope)
    assert dashboard.SPOT_LINE in lines
    payg = pick(found, H100, 8, "westeurope", "on_demand").members[0]
    assert (
        "Spot → PAYG row crosses rental types (Spot → pay-as-you-go):"
        " H100 NVLink 80GB · 8 GPUs · westeurope · Spot →"
        " H100 NVLink 80GB · 8 GPUs · westeurope · pay-as-you-go"
        f" (Standard_ND96isr_H100_v5, item key {payg.item_key})"
    ) in lines
    uksouth = result(found, "uksouth", "spot")
    lines = dashboard.workload_sources(uksouth.start.group, uksouth)
    assert any(line.endswith("(not listed in this snapshot)") for line in lines)
    eastus = result(found, "eastus", "spot")
    lines = dashboard.workload_sources(eastus.start.group, eastus)
    assert dashboard.ABOVE_PAYG.format(price="12.0000") in lines
    assert dashboard.ABOVE_PAYG.endswith(" See the 'Spot → PAYG *' row.")  # D50


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


@pytest.mark.parametrize(
    ("per_vm", "default"), [(1, 32), (2, 32), (4, 32), (8, 32), (3, 3), (64, 64)]
)
def test_default_gpus_make_whole_vms(per_vm: int, default: int) -> None:
    assert dashboard.default_gpus(per_vm) == default


def test_size_keys_differ_per_group(found: list[RegionGroup]) -> None:
    keys = {dashboard.size_key(g.key) for g in found}
    assert len(keys) == len(found)


def test_display_formats_and_text() -> None:
    # Published prices keep every stored decimal, never fewer than two (D32, D49).
    assert [dashboard.at_least_cents(v) for v in (96.0, 0.6, 27.197, 1e-12)] == [
        "96.00",
        "0.60",
        "27.197",
        "1e-12",
    ]
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
    assert dashboard.MARKETPLACE_NOTE == "Workload cost uses the Azure VMs catalogue."


def test_spot_size_missing_from_its_pay_as_you_go_group_is_not_computed() -> None:
    # eastus T4: Spot lists NC4as, pay-as-you-go lists only NC8as. The fallback
    # needs the same size, so it is not computed, and the check agrees.
    con = database()
    azure_run(
        con,
        "r",
        [
            Price("Standard_NC4as_T4_v3", meter="s", region="eastus", rental="spot"),
            Price("Standard_NC8as_T4_v3", meter="p", region="eastus", price=0.8),
        ],
    )
    normalize.normalize_pending(con, AS_OF)
    (snap,) = groups.snapshots(con, "azure-retail")
    found = groups.region_groups(con, snap)
    con.close()
    begin = calc.start(pick(found, "T4 16GB", 1, "eastus", "spot"))
    work = Workload(4, 10.0)
    outcome = calc.calculate(begin, work, found, None, None)
    (fallback,) = [row for row in outcome.rows if row.id == calc.FALLBACK]
    assert not fallback.computed
    assert fallback.effect.startswith("not computed")
    assert dashboard.check(begin, outcome, work, None, None, found) == []
