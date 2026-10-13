"""AppTest flows through the dashboard on synthetic databases (Phase 4 design D19).

Every database here is a temporary file built from the synthetic fixtures, closed before
the page opens it. The as-of time is fixed, so the stale flag never depends on the date.
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from compute_cost_risk_monitor import dashboard, db, groups, normalize, synthetic
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
    for index, value in enumerate([variant, count, rental, region]):
        at.sidebar.selectbox[index].set_value(value)
        at.run()
    assert not at.exception


def captions(block: Any) -> list[str]:
    return [c.value for c in block.caption]


def figure_captions(block: Any) -> list[str]:
    return [text for text in captions(block) if EXCLUDES in text]


# --- datasets and states ---


def test_no_database_names_the_commands(tmp_path: Path) -> None:
    at = page([(dashboard.LIVE_DATASET, tmp_path / "absent.duckdb")])
    assert [i.value for i in at.info] == [dashboard.NO_DATABASE]
    assert not at.dataframe


def test_only_existing_databases_offered(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    assert at.sidebar.radio[0].options == [dashboard.SYNTHETIC_DATASET]
    assert at.title[0].value == dashboard.TITLE


def test_live_database_is_the_default(
    tmp_path: Path, demo: list[tuple[str, Path]]
) -> None:
    build(tmp_path / "monitor.duckdb", [DEMO])
    at = page(demo)
    assert at.sidebar.radio[0].options == [
        dashboard.LIVE_DATASET,
        dashboard.SYNTHETIC_DATASET,
    ]
    assert at.sidebar.radio[0].value == dashboard.LIVE_DATASET
    # The label comes from the run, never from the file: this "live" file is synthetic.
    framing = [m.value for m in at.markdown if m.value.startswith("Synthetic data")]
    assert framing == [
        "Synthetic data: invented prices for demonstration, not Azure list prices"
        " · snapshot 2026-10-12 09:00 UTC"
    ]


def test_no_rule_set_says_run_normalize_first(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.duckdb"
    connection = db.connect(path)
    synthetic.ingest_file(connection, DEMO)
    connection.close()
    at = page([(dashboard.SYNTHETIC_DATASET, path)])
    assert "run normalize first" in at.warning[0].value
    assert not at.dataframe


def test_not_normalized_banner_withholds_groups(tmp_path: Path) -> None:
    path = build(tmp_path / "synthetic.duckdb", [DEMO])
    connection = db.connect(path)
    azure_run(connection, "later", [Price()], started=DAY + timedelta(days=1))
    connection.close()
    at = page([(dashboard.SYNTHETIC_DATASET, path)])
    banners = [e.value for e in at.error]
    assert banners and banners[0].startswith("NOT NORMALIZED: 1 observations")
    assert not at.sidebar.selectbox
    assert "withheld" in at.tabs[0].info[0].value


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
        "mixes data labels" in w.value and "(live, synthetic)" in w.value
        for w in at.warning
    )


def test_stale_framing_as_of_an_injected_time(demo: list[tuple[str, Path]]) -> None:
    at = page(demo, as_of=AS_OF + timedelta(days=8))
    assert at.warning[0].value.endswith(
        " · STALE (older than 7 days as of 2026-10-20 12:00 UTC)"
    )


def test_marketplace_without_a_run_says_no_snapshot(tmp_path: Path) -> None:
    path = build(tmp_path / "synthetic.duckdb", [DEMO])
    at = page([(dashboard.SYNTHETIC_DATASET, path)])
    at.sidebar.radio[1].set_value(dashboard.MARKETPLACE)
    at.run()
    assert dashboard.NO_SNAPSHOT in [i.value for i in at.info]
    quality = at.tabs[2]
    assert dashboard.NO_SNAPSHOT in [i.value for i in quality.info]


def test_connection_closed_after_the_run(demo: list[tuple[str, Path]]) -> None:
    page(demo)
    writer = db.connect(demo[1][1])
    writer.execute("CHECKPOINT")
    writer.close()


# --- filters and views ---


def test_filters_cascade_over_existing_groups(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    labels = [s.label for s in at.sidebar.selectbox]
    assert labels == ["GPU variant", "GPU count", "Rental type", "Region"]
    assert at.sidebar.selectbox[0].options == ["A100 PCIe 80GB", H100, "T4 16GB"]
    at.sidebar.selectbox[0].set_value("A100 PCIe 80GB")
    at.run()
    assert at.sidebar.selectbox[1].options == ["1 GPU"]
    assert at.sidebar.selectbox[2].options == ["pay-as-you-go"]
    at.sidebar.selectbox[0].set_value(H100)
    at.run()
    assert at.sidebar.selectbox[2].options == ["pay-as-you-go", "Spot"]


def test_region_group_view(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    choose(at, "T4 16GB", 1, "on_demand", "eastus")
    tab = at.tabs[0]
    members = tab.dataframe[0].value
    assert members["Size"].tolist() == ["Standard_NC4as_T4_v3", "Standard_NC8as_T4_v3"]
    assert members[dashboard.PUBLISHED].tolist() == [0.6, 0.8]
    assert members["Unit"].tolist() == ["1 Hour", "1 Hour"]
    assert dashboard.MULTI_SIZE in captions(tab)
    (records,) = tab.expander
    assert records.label == "Source records"
    provenance = records.dataframe[0].value
    assert set(provenance["Raw response"]) == {
        "tests/fixtures/synthetic/azure_demo.json"
    }
    assert provenance["SHA-256"].str.fullmatch("[0-9a-f]{64}").all()


def test_single_list_price_labelled(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    choose(at, "T4 16GB", 1, "on_demand", "westeurope")
    assert f"`{groups.SINGLE}`" in [m.value for m in at.tabs[0].markdown]


def test_cross_region_view_and_chart(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    choose(at, H100, 8, "on_demand", "eastus")
    tab = at.tabs[0]
    summary = tab.dataframe[2].value  # members, provenance, then the summary
    assert summary["Region"].tolist() == [
        "eastus",
        "southcentralus",
        "swedencentral",
        "westeurope",
        "westus3",
    ]
    stats = tab.dataframe[3].value.to_dict("records")
    assert stats == [{"Regions": 5, "Minimum": 12.0, "Median": 13.0, "Maximum": 15.0}]
    assert dashboard.LOWEST in captions(tab)
    assert len(tab.get("vega_lite_chart")) == 1
    assert f"`{groups.THIN}`" not in " ".join(m.value for m in tab.markdown)


def test_every_figure_is_captioned(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    choose(at, H100, 8, "spot", "eastus")
    tab = at.tabs[0]
    shown = figure_captions(tab)
    charts = tab.get("vega_lite_chart")
    assert len(shown) == len(tab.dataframe) + len(charts)
    for text in shown:
        assert "snapshot 2026-10-12 09:00 UTC, run synthetic-" in text
        assert "data label: synthetic" in text
    assert any(t.startswith("Group: H100 NVLink 80GB · 8 GPUs · eastus") for t in shown)
    assert any(t.startswith("Crosses regions: H100 NVLink 80GB") for t in shown)
    assert f"`{groups.THIN}`" in " ".join(m.value for m in tab.markdown)


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
    at.sidebar.radio[1].set_value(dashboard.MARKETPLACE)
    at.run()
    key = flagged.key
    choose(at, key.variant, key.gpu_count, key.rental_type, key.region)
    tab = at.tabs[0]
    offers = tab.dataframe[0].value
    assert offers.loc[offers["Flags"] == groups.DUPLICATE, "Machine"].tolist() == [
        "M-01"
    ]
    machines = tab.dataframe[1].value
    assert machines["Machines"].tolist() == [offers["Machine"].nunique()]
    assert f"`{groups.SYNTHETIC}`" in " ".join(m.value for m in tab.markdown)
    assert not tab.get("vega_lite_chart")


def test_group_browser_has_no_prices(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    tab = at.tabs[1]
    frame = tab.dataframe[0].value
    assert "USD" not in " ".join(frame.columns)
    assert "price" not in " ".join(frame.columns).lower()
    every = len(frame)
    assert dashboard.BROWSER in captions(tab)[0]
    tab.toggle[0].set_value(True)
    at.run()
    narrowed = at.tabs[1].dataframe[0].value
    assert set(narrowed["Variant"]) == {"A100 PCIe 80GB"}
    assert len(narrowed) < every


def test_quality_panel(demo: list[tuple[str, Path]]) -> None:
    at = page(demo)
    tab = at.tabs[2]
    assert [s.value for s in tab.subheader] == [
        "Azure retail list prices",
        "Synthetic marketplace",
    ]
    checks = dict(tab.dataframe[0].value.values.tolist())
    assert (
        checks["Unmapped"] == "sizes not in the map 1; rows excluded as unmapped_sku 1"
    )
    assert "Sizes not in the map: `Standard_ND96is_MI300X_v5`" in [
        m.value for m in tab.markdown
    ]
    marketplace = dict(tab.dataframe[2].value.values.tolist())
    assert marketplace["Stale"].startswith("yes ")
    for text in captions(tab):
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
    assert at.title[0].value == dashboard.TITLE
    assert at.sidebar.radio[0].options == [dashboard.SYNTHETIC_DATASET]
