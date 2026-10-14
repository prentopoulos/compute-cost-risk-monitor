"""AppTest flows through the dashboard on synthetic databases (Phase 4 design D19;
Phase 7 design D6-D10, D33-D46).

Every database here is a temporary file built from the synthetic fixtures, closed before
the page opens it. The as-of time is fixed, so the stale flag never depends on the date.
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import pytest
from streamlit.testing.v1 import AppTest

from compute_cost_risk_monitor import (
    dashboard,
    db,
    groups,
    normalize,
    scenarios,
    synthetic,
    workload_check,
)
from seed import DAY, Price, azure_run
from support import FIXTURES

# asyncio on Windows builds its self-pipe from a loopback TCP socket pair, so these
# tests may connect to 127.0.0.1 and nowhere else.
pytestmark = pytest.mark.allow_hosts(["127.0.0.1"])

ROOT = Path(__file__).resolve().parents[2]
AS_OF = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
DEMO = FIXTURES / "azure_demo.json"
SNAPSHOTS = sorted((FIXTURES / "marketplace").glob("snapshot-*.json"))
H100 = "H100 NVLink 80GB"
EXCLUDES = "Excludes disks"
FILTERS = ["GPU", "GPUs per VM", "Pricing", "Region"]


def run_app(known: "Sequence[tuple[str, Path]]", as_of: "datetime") -> None:
    # AppTest runs this body as its own script, so annotations stay unevaluated.
    from compute_cost_risk_monitor import app

    app.main(known, as_of)


def page(known: Sequence[tuple[str, Path]], as_of: datetime = AS_OF) -> AppTest:
    at = AppTest.from_function(
        run_app, kwargs={"known": known, "as_of": as_of}, default_timeout=30
    )
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def build(path: Path, files: Sequence[Path] = (DEMO, *SNAPSHOTS)) -> Path:
    connection = db.connect(path)
    try:
        for file in files:
            synthetic.ingest_file(connection, file)
        normalize.normalize_pending(connection, AS_OF)
    finally:
        connection.close()
    return path


@pytest.fixture
def demo(tmp_path: Path) -> list[tuple[str, Path]]:
    path = build(tmp_path / "synthetic.duckdb")
    return [
        (dashboard.LIVE_DATASET, tmp_path / "monitor.duckdb"),
        (dashboard.SYNTHETIC_DATASET, path),
    ]


def choose(at: AppTest, variant: str, count: int, rental: str, region: str) -> None:
    for label, value in zip(FILTERS, [variant, count, rental, region], strict=True):
        select = next(s for s in at.sidebar.selectbox if s.label == label)
        select.set_value(value)
        at.run()
    assert not at.exception


def show(at: AppTest, view: str) -> None:
    """Open a tab: the tabs are lazy, so only the open one is drawn."""
    at.session_state["view"] = view
    at.run()
    assert not at.exception


def texts(block: Any) -> list[str]:
    return [m.value for m in block.markdown]


def status(word: str, message: str) -> str:
    return f"**{word}**  \n{message}"


def no_alerts(block: Any) -> None:
    """States are plain words, never coloured alert boxes (phase-7 D40, D41)."""
    assert not block.warning and not block.error and not block.info
    assert not block.success


def sources(tab: Any) -> Any:
    (shown,) = [e for e in tab.expander if e.label == "Sources"]
    return shown


def source_text(tab: Any) -> str:
    return " ".join(texts(sources(tab)))


# --- datasets and states ---


def test_no_database_names_the_commands(tmp_path: Path) -> None:
    at = page([(dashboard.LIVE_DATASET, tmp_path / "absent.duckdb")])
    assert texts(at) == [
        f"**{dashboard.TITLE_LINE}**",
        status(dashboard.NO_DATABASE_WORD, dashboard.NO_DATABASE),
    ]
    assert not at.dataframe
    no_alerts(at)


def test_only_existing_databases_offered(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    dataset = at.sidebar.selectbox[0]
    assert dataset.label == "Dataset"
    assert dataset.options == [dashboard.SYNTHETIC_DATASET]
    assert not at.title  # the status line names the page
    assert texts(at)[0] == (
        "**COMPUTE COST & RISK MONITOR**"
        " · :orange[**SYNTHETIC DATA — NOT AZURE LIST PRICES**]"
        " · AS OF 12 OCT 2026 09:00 UTC"
    )
    no_alerts(at)


def test_catalogue_names_follow_the_run_labels(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    catalogue = at.selectbox(key="catalogue")
    assert catalogue.label == "Catalogue"
    assert catalogue.options == ["Azure VMs (synthetic)", "Marketplace (synthetic)"]
    assert catalogue.value == dashboard.AZURE


def test_live_database_is_the_default(
    tmp_path: Path, demo: list[tuple[str, Path]]
) -> None:
    build(tmp_path / "monitor.duckdb", [DEMO])
    at = page(demo)
    assert at.sidebar.selectbox[0].options == [
        dashboard.LIVE_DATASET,
        dashboard.SYNTHETIC_DATASET,
    ]
    assert at.sidebar.selectbox[0].value == dashboard.LIVE_DATASET
    # The label comes from the run, never from the file: this "live" file is synthetic.
    assert ":orange[**SYNTHETIC DATA — NOT AZURE LIST PRICES**]" in texts(at)[0]
    assert at.selectbox(key="catalogue").options[0] == "Azure VMs (synthetic)"


def test_no_rule_set_says_run_normalize_first(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.duckdb"
    connection = db.connect(path)
    synthetic.ingest_file(connection, DEMO)
    connection.close()
    at = page([(dashboard.SYNTHETIC_DATASET, path)])
    (shown,) = [t for t in texts(at) if t.startswith("**NO RULE SET**")]
    assert "run normalize first" in shown
    assert not at.dataframe
    no_alerts(at)


def test_database_without_tables_names_the_commands(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.duckdb"
    db.connect(path).close()
    at = page([(dashboard.SYNTHETIC_DATASET, path)])
    (shown,) = [t for t in texts(at) if t.startswith("**NO TABLES**")]
    assert "holds no tables yet" in shown
    assert not at.dataframe


def test_not_normalized_banner_withholds_groups(tmp_path: Path) -> None:
    path = build(tmp_path / "synthetic.duckdb", [DEMO])
    connection = db.connect(path)
    azure_run(connection, "later", [Price()], started=DAY + timedelta(days=1))
    connection.close()
    at = page([(dashboard.SYNTHETIC_DATASET, path)])
    banners = [t for t in texts(at) if t.startswith("NOT NORMALIZED: 1 observations")]
    assert len(banners) == 1
    assert [s.label for s in at.sidebar.selectbox] == ["Dataset", "Catalogue"]
    assert texts(at.tabs[0]) == [
        status(dashboard.WITHHELD_WORD, dashboard.WITHHELD_WORKLOAD)
    ]
    no_alerts(at)


def test_mixed_labels_warned(tmp_path: Path) -> None:
    path = build(tmp_path / "synthetic.duckdb", [DEMO])
    connection = db.connect(path)
    # A temporary test database: a run labelled live with no rows, to mix labels.
    connection.execute(
        "INSERT INTO collection_run VALUES ('live-0', 'azure-retail', 'live', ?, ?,"
        " 'succeeded', 'test', 1, NULL, NULL, NULL)",
        [DAY - timedelta(days=1), DAY - timedelta(days=1)],
    )
    connection.close()
    at = page([(dashboard.SYNTHETIC_DATASET, path)])
    assert any(
        t.startswith(":orange[")
        and "mixes data labels" in t
        and "(live, synthetic)" in t
        for t in texts(at)
    )


def test_stale_status_as_of_an_injected_time(demo: list[tuple[str, Path]]) -> None:
    at = page(demo, as_of=AS_OF + timedelta(days=8))
    assert texts(at)[0].endswith(
        " · :orange[**STALE — OLDER THAN 7 DAYS AS OF 20 OCT 2026 12:00 UTC**]"
    )


def test_marketplace_without_a_run_says_no_snapshot(tmp_path: Path) -> None:
    path = build(tmp_path / "synthetic.duckdb", [DEMO])
    at = page([(dashboard.SYNTHETIC_DATASET, path)])
    at.selectbox(key="catalogue").set_value(dashboard.MARKETPLACE)
    at.run()
    assert at.selectbox(key="catalogue").options == [
        "Azure VMs (synthetic)",
        "Marketplace",
    ]
    no_snapshot = status(dashboard.NO_SNAPSHOT_WORD, dashboard.NO_SNAPSHOT)
    assert no_snapshot in texts(at)
    show(at, "Data quality")
    assert no_snapshot in texts(at.tabs[3])
    no_alerts(at)


def test_withheld_snapshot_lists_no_groups_and_flags_the_panel(
    tmp_path: Path,
) -> None:
    path = build(tmp_path / "synthetic.duckdb", [DEMO])
    connection = db.connect(path)
    azure_run(connection, "later", [Price()], started=DAY + timedelta(days=1))
    connection.close()
    at = page([(dashboard.SYNTHETIC_DATASET, path)])
    show(at, "Group browser")
    assert texts(at.tabs[2]) == [status(dashboard.NO_GROUPS_WORD, "No groups to list.")]
    assert not at.tabs[2].dataframe
    show(at, "Data quality")
    banners = texts(at.tabs[3])
    assert any(t.startswith("NOT NORMALIZED: 1 observations") for t in banners)
    no_alerts(at)


def test_file_that_is_not_a_database_is_named(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.duckdb"
    path.write_text("plain text, not DuckDB", encoding="utf-8")
    at = page([(dashboard.SYNTHETIC_DATASET, path)])
    (shown,) = [t for t in texts(at) if t.startswith("**CANNOT OPEN**")]
    assert f"Cannot open {path}" in shown
    assert not at.dataframe


def test_read_error_is_shown_not_raised(
    demo: list[tuple[str, Path]], monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing(*_: object, **__: object) -> None:
        raise duckdb.IOException("simulated read failure")

    monkeypatch.setattr(dashboard, "load_all", failing)
    at = page(demo)
    (shown,) = [t for t in texts(at) if t.startswith("**CANNOT READ**")]
    assert "  \nCannot read " in shown
    assert shown.endswith("simulated read failure")
    assert not at.dataframe
    no_alerts(at)


def test_choice_naming_no_group_draws_nothing(
    demo: list[tuple[str, Path]], monkeypatch: pytest.MonkeyPatch
) -> None:
    # The filters only offer existing groups; if a choice ever named none, the
    # workload and group tabs draw nothing rather than a figure for another group.
    monkeypatch.setattr(dashboard, "find_group", lambda *_: None)
    at = page(demo)
    assert not at.tabs[0].metric and not at.tabs[0].table
    show(at, "Comparable groups")
    assert not at.tabs[1].metric and not at.tabs[1].dataframe


def test_connection_closed_after_the_run(demo: list[tuple[str, Path]]) -> None:
    page(demo)
    writer = db.connect(demo[1][1])
    writer.execute("CHECKPOINT")
    writer.close()


# --- filters and the comparable groups tab ---


def test_filters_cascade_over_existing_groups(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    labels = [s.label for s in at.sidebar.selectbox]
    assert labels == ["Dataset", "Catalogue", *FILTERS]
    gpu = at.sidebar.selectbox[2]
    assert gpu.options == ["A100 PCIe 80GB", H100, "T4 16GB"]
    gpu.set_value("A100 PCIe 80GB")
    at.run()
    assert at.sidebar.selectbox[3].options == ["1"]
    assert at.sidebar.selectbox[4].options == ["Pay-as-you-go"]
    at.sidebar.selectbox[2].set_value(H100)
    at.run()
    assert at.sidebar.selectbox[4].options == ["Pay-as-you-go", "Spot"]
    # Regions show their stored names, sorted by name.
    assert at.sidebar.selectbox[5].options == [
        "EU West",
        "Sweden Central",
        "US East",
        "US South Central",
        "US West 3",
    ]


def test_region_group_view(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    choose(at, "T4 16GB", 1, "on_demand", "eastus")
    show(at, "Comparable groups")
    tab = at.tabs[1]
    assert [(m.label, m.value) for m in tab.metric] == [
        ("Lowest, USD/GPU-h · PAYG", "0.6000"),
        ("Size", "NC4as T4 v3"),
        ("Members", "2"),
    ]
    members = tab.dataframe[0].value
    assert members["Size"].tolist() == ["Standard_NC4as_T4_v3", "Standard_NC8as_T4_v3"]
    assert members[dashboard.PUBLISHED].tolist() == [0.6, 0.8]
    assert members["Unit"].tolist() == ["1 Hour", "1 Hour"]
    assert dashboard.MULTI_SIZE in source_text(tab)
    assert dashboard.MULTI_SIZE not in texts(tab)  # explanations live in Sources
    provenance = sources(tab).dataframe[0].value
    assert set(provenance["Raw response"]) == {
        "tests/fixtures/synthetic/azure_demo.json"
    }
    assert provenance["SHA-256"].str.fullmatch("[0-9a-f]{64}").all()


def test_single_list_price_tagged(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    choose(at, "T4 16GB", 1, "on_demand", "westeurope")
    show(at, "Comparable groups")
    assert f"`{groups.SINGLE}`" in texts(at.tabs[1])


def test_cross_region_view_and_chart(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    choose(at, H100, 8, "on_demand", "eastus")
    show(at, "Comparable groups")
    tab = at.tabs[1]
    summary = tab.dataframe[1].value  # members, then the summary and its statistics
    assert summary["Region"].tolist() == [
        "eastus",
        "southcentralus",
        "swedencentral",
        "westeurope",
        "westus3",
    ]
    stats = tab.dataframe[2].value.to_dict("records")
    assert stats == [{"Regions": 5, "Minimum": 12.0, "Median": 13.0, "Maximum": 15.0}]
    assert dashboard.LOWEST in source_text(tab)
    assert len(tab.get("vega_lite_chart")) == 1
    assert f"`{groups.THIN}`" not in " ".join(texts(tab))


def test_one_exclusions_footer_and_the_keys_in_sources(
    demo: list[tuple[str, Path]],
) -> None:
    at = page(demo)
    choose(at, H100, 8, "spot", "eastus")
    show(at, "Comparable groups")
    tab = at.tabs[1]
    assert len([t for t in texts(tab) if EXCLUDES in t]) == 1
    assert not tab.caption
    shown = source_text(tab)
    assert "- Group: H100 NVLink 80GB · 8 GPUs · eastus · Spot" in shown
    assert "Snapshot 2026-10-12 09:00 UTC, run synthetic-" in shown
    assert "data label: synthetic" in shown
    assert "Crosses regions: H100 NVLink 80GB · 8 GPUs · Spot" in shown
    assert f"`{groups.THIN}`" in " ".join(texts(tab))


def test_marketplace_view_marks_duplicates(tmp_path: Path) -> None:
    path = build(tmp_path / "synthetic.duckdb", [SNAPSHOTS[0]])
    connection = db.connect(path, read_only=True)
    view = dashboard.load(connection, path, dashboard.MARKETPLACE, AS_OF)
    connection.close()
    (flagged,) = [
        g
        for g in view.region_groups
        if any(groups.DUPLICATE in m.flags for m in g.members)
    ]
    at = page([(dashboard.SYNTHETIC_DATASET, path)])
    at.selectbox(key="catalogue").set_value(dashboard.MARKETPLACE)
    at.run()
    key = flagged.key
    choose(at, key.variant, key.gpu_count, key.rental_type, key.region)
    show(at, "Comparable groups")
    tab = at.tabs[1]
    offers = tab.dataframe[0].value
    assert offers.loc[offers["Flags"] == groups.DUPLICATE, "Machine"].tolist() == [
        "M-01"
    ]
    machines = tab.dataframe[1].value
    assert machines["Machines"].tolist() == [offers["Machine"].nunique()]
    figures = dict((m.label, m.value) for m in tab.metric)
    assert figures["Machines"] == str(offers["Machine"].nunique())
    assert figures["Offers"] == str(len(offers))
    assert f"`{groups.SYNTHETIC}`" in " ".join(texts(tab))
    assert not tab.get("vega_lite_chart")


def test_only_the_open_tab_is_drawn(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    assert [tab.label for tab in at.tabs] == [
        "Workload cost",
        "Comparable groups",
        "Group browser",
        "Data quality",
    ]
    assert at.tabs[0].table  # the page opens on Workload cost
    assert not at.tabs[1].dataframe
    assert not at.tabs[2].dataframe
    assert not at.tabs[3].dataframe
    show(at, "Group browser")
    assert not at.tabs[0].table
    assert at.tabs[2].dataframe


def test_group_browser_has_no_prices(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    show(at, "Group browser")
    tab = at.tabs[2]
    frame = tab.dataframe[0].value
    assert "USD" not in " ".join(frame.columns)
    assert "price" not in " ".join(frame.columns).lower()
    every = len(frame)
    assert dashboard.BROWSER in source_text(tab)
    tab.toggle[0].set_value(True)
    # AppTest keeps no tab state between runs, so the run reopens the tab.
    show(at, "Group browser")
    narrowed = at.tabs[2].dataframe[0].value
    assert set(narrowed["Variant"]) == {"A100 PCIe 80GB"}
    assert len(narrowed) < every


def test_quality_panel(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    show(at, "Data quality")
    tab = at.tabs[3]
    assert [s.value for s in tab.subheader] == [
        "Azure VMs (synthetic)",
        "Marketplace (synthetic)",
    ]
    checks = dict(tab.dataframe[0].value.values.tolist())
    assert (
        checks["Unmapped"] == "sizes not in the map 1; rows excluded as unmapped_sku 1"
    )
    assert "Sizes not in the map: `Standard_ND96is_MI300X_v5`" in texts(tab)
    marketplace = dict(tab.dataframe[2].value.values.tolist())
    assert marketplace["Stale"].startswith("yes ")
    assert marketplace["Unmapped"] == "rows excluded as unmapped_gpu_name 2"
    for text in [c.value for c in tab.caption]:
        assert "data label: synthetic" in text
        assert "as of 2026-10-12 12:00 UTC" in text


def test_script_runs_from_its_file(
    demo: list[tuple[str, Path]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dashboard, "KNOWN", tuple(demo))
    at = AppTest.from_file(
        str(ROOT / "src" / "compute_cost_risk_monitor" / "app.py"), default_timeout=30
    )
    at.run()
    assert not at.exception
    assert texts(at)[0].startswith("**COMPUTE COST & RISK MONITOR**")
    assert at.sidebar.selectbox[0].options == [dashboard.SYNTHETIC_DATASET]


# --- workload cost (phase-5-calculator; phase-7 D6, D7, D9, D33-D46) ---

WORKLOAD = "Workload cost"


def workload_tab(at: AppTest) -> Any:
    """Open the workload tab; AppTest keeps no tab state, so every run reopens it."""
    show(at, WORKLOAD)
    return at.tabs[0]


def figures(tab: Any) -> list[tuple[str, str]]:
    return [(m.label, m.value) for m in tab.metric]


def grid(tab: Any) -> dict[str, list[str]]:
    """The scenario grid, by row label: its cells from 8 GPUs to 128 GPUs."""
    frame = tab.table[0].value
    return {row[0]: list(row[1:]) for row in frame.values.tolist()}


def cost(tab: Any) -> list[list[str]]:
    return list(tab.table[1].value.values.tolist())


def footer(tab: Any) -> str:
    (shown,) = [t for t in texts(tab) if t.startswith(":gray[Scenario calculation")]
    return str(shown)


DASHES = [
    ("Cost, USD", "—"),
    ("USD/GPU-h · PAYG", "—"),
    ("VMs", "—"),
    ("GPUs × h", "—"),
]


def test_known_workload_on_the_demo(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    choose(at, H100, 8, "on_demand", "eastus")
    tab = workload_tab(at)
    assert at.number_input(key="gpus").value == 32
    assert at.number_input(key="hours").value == 720.0
    assert figures(tab) == [
        ("Cost, USD", "276,480.00"),
        ("USD/GPU-h · PAYG", "12.0000"),
        ("VMs", "4 × ND96isr H100 v5"),
        ("GPUs × h", "32 × 720"),
    ]
    assert ":gray[**SCENARIO GRID**] **Δ cost, USD · 720 h**" in texts(tab)
    cells = grid(tab)
    assert list(cells) == [
        "−50%",
        "−25%",
        "−10%",
        "+10%",
        "+25%",
        "+50%",
        "+100%",
        "+0.50 USD/GPU-h",
    ]
    assert cells["+0.50 USD/GPU-h"][2] == "+11,520"  # PROJECT's example
    assert cells["+100%"][2] == "+276,480"
    assert footer(tab).startswith(
        ":gray[Scenario calculation, not a forecast. Excludes disks"
    )
    assert cost(tab) == [
        ["Compute", "96", "2,880", "276,480.00"],
        ["Storage", "", "", "—"],
        ["Total", "", "", "276,480.00"],
    ]
    shown = source_text(tab)
    for text in (
        "Group: H100 NVLink 80GB · 8 GPUs · eastus · pay-as-you-go",
        dashboard.BILLING,
        dashboard.STORAGE_NONE,
        dashboard.BUDGET_HINT,
        dashboard.WORKLOAD_INTRO,
        f"ladder-v1 and scenarios-v1: {scenarios.JUDGEMENT}",
        "Starting price: USD 12.0000/GPU-hour",
    ):
        assert text in shown
    assert dashboard.WORKLOAD_INTRO not in texts(tab)
    assert not tab.dataframe[1:] and not tab.get("vega_lite_chart")  # no scenario table
    no_alerts(tab)


def test_inputs_kept_across_tabs(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    choose(at, H100, 8, "on_demand", "eastus")
    workload_tab(at)
    at.number_input(key="gpus").set_value(16)
    assert ("VMs", "2 × ND96isr H100 v5") in figures(workload_tab(at))
    show(at, "Group browser")
    assert not at.tabs[0].number_input
    workload_tab(at)
    assert at.number_input(key="gpus").value == 16


def test_a_kept_gpu_count_that_is_not_whole_vms_is_refused(
    demo: list[tuple[str, Path]],
) -> None:
    at = page(demo)
    choose(at, "T4 16GB", 1, "on_demand", "eastus")
    workload_tab(at)
    at.number_input(key="gpus").set_value(12)
    workload_tab(at)
    choose(at, H100, 8, "on_demand", "eastus")
    tab = workload_tab(at)
    assert at.number_input(key="gpus").value == 12
    assert status(
        dashboard.REFUSED, "12 GPUs is not a whole number of 8-GPU VMs: use 8 or 16."
    ) in texts(tab)
    assert figures(tab) == DASHES
    assert not tab.table
    no_alerts(tab)
    # Below the new minimum, Streamlit itself resets the input to its default.
    choose(at, "T4 16GB", 1, "on_demand", "eastus")
    workload_tab(at)
    at.number_input(key="gpus").set_value(3)
    workload_tab(at)
    choose(at, H100, 8, "on_demand", "eastus")
    workload_tab(at)
    assert at.number_input(key="gpus").value == 32


def test_impossible_hours_refused(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    workload_tab(at)
    at.number_input(key="hours").set_value(0.0)
    tab = workload_tab(at)
    assert status(
        dashboard.REFUSED, "Hours must be at least 0.01 and at most 8,784."
    ) in texts(tab)
    assert not tab.table


def test_size_choice(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    choose(at, "T4 16GB", 1, "on_demand", "eastus")
    tab = workload_tab(at)
    (size,) = tab.selectbox
    assert size.options == ["Standard_NC4as_T4_v3", "Standard_NC8as_T4_v3"]
    assert "Standard_NC4as_T4_v3 (lowest listed in this group)" in source_text(tab)
    assert ("VMs", "32 × NC4as T4 v3") in figures(tab)
    size.set_value("Standard_NC8as_T4_v3")
    tab = workload_tab(at)
    assert (
        "Starting price: USD 0.8000/GPU-hour for Standard_NC8as_T4_v3, from"
        in source_text(tab)
    )
    assert ("USD/GPU-h · PAYG", "0.8000") in figures(tab)
    choose(at, H100, 8, "on_demand", "eastus")
    assert not workload_tab(at).selectbox  # one member: no choice to make


def test_custom_move_and_headroom(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    choose(at, H100, 8, "on_demand", "eastus")
    workload_tab(at)
    assert at.number_input(key="custom_percent").label == "Custom, %"
    at.number_input(key="custom_percent").set_value(10.0)
    at.number_input(key="budget").set_value(11_520.0)
    tab = workload_tab(at)
    cells = grid(tab)
    assert list(cells)[-1] == "Custom +10%"
    assert cells["Custom +10%"][2] == "+27,648"  # 32 x 720 x 1.2
    assert figures(tab)[-1] == ("Headroom, USD/GPU-h", "+0.5000 (4.2%)")
    assert (
        "A rise of USD 0.5000 per GPU-hour (4.2% of starting price) would use up"
        " USD 11,520.00 over 32 GPUs × 720 h. Storage unchanged. Scenario"
        " calculation, not a forecast." in source_text(tab)
    )
    # Switching unit never reinterprets the value: the USD input starts empty.
    assert at.radio(key="custom_kind").options == ["%", "USD/GPU-h"]
    at.radio(key="custom_kind").set_value("USD/GPU-h")
    tab = workload_tab(at)
    assert at.number_input(key="custom_usd").value is None
    assert at.number_input(key="custom_usd").label == "Custom, USD/GPU-h"
    assert list(grid(tab))[-1] == "+0.50 USD/GPU-h"
    at.radio(key="custom_kind").set_value("%")
    workload_tab(at)
    assert at.number_input(key="custom_percent").value == 10.0
    at.number_input(key="budget").set_value(0.0)
    tab = workload_tab(at)
    assert status(dashboard.REFUSED, "Budget: enter an amount above zero.") in texts(
        tab
    )
    assert figures(tab) == [*DASHES, ("Headroom, USD/GPU-h", "—")]
    assert "Starting price" not in source_text(tab)  # no price, not even the start
    assert not tab.table


def test_storage_entered(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    choose(at, H100, 8, "on_demand", "eastus")
    workload_tab(at)
    at.number_input(key="storage").set_value(150.0)
    tab = workload_tab(at)
    assert cost(tab)[1:] == [
        ["Storage", "", "", "150.00"],
        ["Total", "", "", "276,630.00"],
    ]
    assert footer(tab).endswith(" Total includes USD 150.00 storage entered by you.]")
    assert "Storage: USD 150.00 entered by you" in source_text(tab)


def test_spot_fallback_not_computed_on_the_demo(
    demo: list[tuple[str, Path]],
) -> None:
    at = page(demo)
    choose(at, H100, 8, "spot", "uksouth")
    tab = workload_tab(at)
    assert ("USD/GPU-h · SPOT", "6.0000") in figures(tab)
    assert grid(tab)["Spot → PAYG *"] == ["n/a"] * 5
    shown = footer(tab)
    assert dashboard.CROSSING_CLAUSE in shown
    assert dashboard.NO_PAYG_CLAUSE in shown
    assert dashboard.SPOT_LINE in source_text(tab)
    assert "(not listed in this snapshot)" in source_text(tab)


def test_spot_rows_above_pay_as_you_go_are_marked(
    demo: list[tuple[str, Path]],
) -> None:
    at = page(demo)
    choose(at, H100, 8, "spot", "eastus")  # Spot equals pay-as-you-go here
    tab = workload_tab(at)
    assert "+25% †" in grid(tab)
    assert "−25%" in grid(tab)
    assert footer(tab).endswith(
        "† Above this size's pay-as-you-go list price (USD 12.0000/GPU-h): the"
        " arithmetic, not what Azure would bill.]"
    )
    assert dashboard.ABOVE_PAYG.format(price="12.0000") in source_text(tab)


def test_marketplace_source_shows_the_note(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    at.selectbox(key="catalogue").set_value(dashboard.MARKETPLACE)
    at.run()
    tab = workload_tab(at)
    assert texts(tab) == [dashboard.MARKETPLACE_NOTE]
    assert not tab.table and not tab.metric


def test_workload_withheld_when_not_normalized(tmp_path: Path) -> None:
    path = build(tmp_path / "synthetic.duckdb", [DEMO])
    connection = db.connect(path)
    azure_run(connection, "later", [Price()], started=DAY + timedelta(days=1))
    connection.close()
    at = page([(dashboard.SYNTHETIC_DATASET, path)])
    tab = workload_tab(at)
    assert texts(tab) == [status(dashboard.WITHHELD_WORD, dashboard.WITHHELD_WORKLOAD)]
    assert not tab.table


def test_failed_check_shows_no_figures(
    demo: list[tuple[str, Path]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(workload_check, "check", lambda inputs, figures: ["total"])
    at = page(demo)
    choose(at, H100, 8, "on_demand", "eastus")
    tab = workload_tab(at)
    assert status(
        dashboard.CHECK_FAILED_WORD,
        "The independent check failed: total. No figures are shown.",
    ) in texts(tab)
    assert figures(tab) == DASHES
    assert "Starting price" not in source_text(tab)
    assert not tab.table
    assert not tab.get("vega_lite_chart")
    no_alerts(tab)


def test_workload_without_an_azure_snapshot(tmp_path: Path) -> None:
    path = build(tmp_path / "synthetic.duckdb", SNAPSHOTS[:1])
    at = page([(dashboard.SYNTHETIC_DATASET, path)])
    assert status(dashboard.NO_SNAPSHOT_WORD, dashboard.NO_SNAPSHOT) in texts(at)
    tab = workload_tab(at)
    assert not tab.table and not tab.metric


def test_workload_without_comparable_groups(tmp_path: Path) -> None:
    path = build(tmp_path / "synthetic.duckdb", SNAPSHOTS[:1])
    connection = db.connect(path)
    unmapped = Price("Standard_ND96is_noIB_H100_v5", meter="unmapped")
    azure_run(connection, "unmapped-only", [unmapped])
    normalize.normalize_pending(connection, AS_OF)
    connection.close()
    tab = workload_tab(page([(dashboard.SYNTHETIC_DATASET, path)]))
    assert texts(tab) == [status(dashboard.NO_GROUPS_WORD, dashboard.NO_GROUPS)]
    assert not tab.table
