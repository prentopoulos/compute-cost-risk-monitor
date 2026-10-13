"""The dashboard's view model against hand-worked answers (Phase 4 design).

All data is synthetic: the Azure demo snapshot and the marketplace snapshots under
tests/fixtures/synthetic, plus seeded Azure runs with invented round prices.
"""

import hashlib
import subprocess
import sys
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import pytest

from compute_cost_risk_monitor import (
    dashboard,
    db,
    groups,
    normalize,
    quality,
    synthetic,
)
from compute_cost_risk_monitor.groups import GroupKey, Snapshot
from seed import DAY, Price, azure_run, database
from support import FIXTURES

AS_OF = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
DEMO = FIXTURES / "azure_demo.json"
SNAPSHOTS = sorted((FIXTURES / "marketplace").glob("snapshot-*.json"))
H100 = "H100 NVLink 80GB"
PRICE_WORDS = ("USD", "price", "Minimum", "Median", "Maximum")


def demo_database(connection: duckdb.DuckDBPyConnection) -> None:
    for path in [DEMO, *SNAPSHOTS]:
        synthetic.ingest_file(connection, path)
    normalize.normalize_pending(connection, AS_OF)


@pytest.fixture
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    connection = database()
    demo_database(connection)
    yield connection
    connection.close()


@pytest.fixture
def views(con: duckdb.DuckDBPyConnection) -> dict[str, dashboard.SourceView]:
    return dashboard.load_all(con, Path("synthetic.duckdb"), AS_OF)


def azure(views: dict[str, dashboard.SourceView]) -> dashboard.SourceView:
    return views[dashboard.AZURE]


def group(view: dashboard.SourceView, *key: Any) -> groups.RegionGroup:
    found = dashboard.find_group(view.region_groups, GroupKey(*key))
    assert found is not None
    return found


# --- datasets and database states ---


def test_only_existing_databases_offered_live_first(tmp_path: Path) -> None:
    live, fake = tmp_path / "monitor.duckdb", tmp_path / "synthetic.duckdb"
    known = [(dashboard.LIVE_DATASET, live), (dashboard.SYNTHETIC_DATASET, fake)]
    assert dashboard.datasets(known) == []
    fake.touch()
    assert [d.label for d in dashboard.datasets(known)] == [dashboard.SYNTHETIC_DATASET]
    live.touch()
    assert [d.path for d in dashboard.datasets(known)] == [live, fake]


def test_missing_database_names_the_commands(tmp_path: Path) -> None:
    with pytest.raises(dashboard.Problem, match="compute_cost_risk_monitor.collect"):
        dashboard.open_read_only(tmp_path / "absent.duckdb")


def test_database_held_by_a_writer_is_in_use(tmp_path: Path) -> None:
    path = tmp_path / "held.duckdb"
    db.connect(path).close()
    holder = subprocess.Popen(  # noqa: S603 - a fixed command on a test file
        [
            sys.executable,
            "-c",
            "import sys, duckdb; c = duckdb.connect(sys.argv[1]); print('held',"
            " flush=True); sys.stdin.read()",
            str(path),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout is not None
        assert holder.stdout.readline().strip() == "held"
        with pytest.raises(dashboard.Problem, match="in use"):
            dashboard.open_read_only(path)
    finally:
        holder.communicate("", timeout=30)
    dashboard.open_read_only(path).close()


def test_unreadable_file_is_not_called_in_use(tmp_path: Path) -> None:
    path = tmp_path / "broken.duckdb"
    path.write_text("not a database", encoding="utf-8")
    with pytest.raises(dashboard.Problem) as caught:
        dashboard.open_read_only(path)
    assert str(caught.value).startswith(f"Cannot open {path}")
    assert dashboard.IN_USE not in str(caught.value)


def test_database_without_tables_names_the_commands(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.duckdb"
    db.connect(path).close()  # what a refused synthetic command leaves behind
    connection = dashboard.open_read_only(path)
    try:
        with pytest.raises(dashboard.Problem, match="holds no tables yet"):
            dashboard.load_all(connection, path, AS_OF)
    finally:
        connection.close()


def test_commands_quote_the_path() -> None:
    connection = database()
    azure_run(connection, "run-1", [Price()])
    path = Path("C:/Market Projects/Compute Cost & Risk Monitor/data/monitor.duckdb")
    with pytest.raises(dashboard.Problem) as caught:
        dashboard.load(connection, path, dashboard.AZURE, AS_OF)
    assert f'--db "{path}"' in str(caught.value)
    assert f'--db "{path}"' in dashboard.NOT_NORMALIZED.format(count=1, path=path)


def test_other_key_errors_are_not_called_a_missing_rule_set(
    con: duckdb.DuckDBPyConnection, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*args: object, **kwargs: object) -> None:
        raise KeyError("thin_below_machines")

    monkeypatch.setattr(quality, "build", broken)
    with pytest.raises(KeyError, match="thin_below_machines"):
        dashboard.load(con, Path("x.duckdb"), dashboard.AZURE, AS_OF)


def test_groups_load_for_the_selected_source_only(
    con: duckdb.DuckDBPyConnection,
) -> None:
    views = dashboard.load_all(con, Path("x.duckdb"), AS_OF, dashboard.MARKETPLACE)
    assert views[dashboard.MARKETPLACE].region_groups
    assert views[dashboard.AZURE].region_groups == []
    assert views[dashboard.AZURE].report.region_groups > 0  # its report is complete


def test_read_only_connection_lets_a_writer_in_after_close(tmp_path: Path) -> None:
    path = tmp_path / "demo.duckdb"
    writer = db.connect(path)
    db.create_schema(writer)
    writer.close()
    reader = dashboard.open_read_only(path)
    reader.close()
    db.connect(path).close()


def test_no_rule_set_says_run_normalize_first() -> None:
    connection = database()
    azure_run(connection, "run-1", [Price()])
    with pytest.raises(dashboard.Problem, match="run normalize first"):
        dashboard.load(connection, Path("x.duckdb"), dashboard.AZURE, AS_OF)


def test_not_normalized_snapshot_withholds_the_groups() -> None:
    connection = database()
    azure_run(connection, "run-1", [Price()])
    normalize.normalize_pending(connection, AS_OF)
    azure_run(connection, "run-2", [Price()], started=DAY + timedelta(days=1))
    view = dashboard.load(connection, Path("x.duckdb"), dashboard.AZURE, AS_OF)
    assert view.withheld
    assert view.report.not_normalized == 1
    assert view.region_groups == []
    assert view.summaries == []


def test_source_without_a_run_has_no_snapshot() -> None:
    connection = database()
    azure_run(connection, "run-1", [Price()])
    normalize.normalize_pending(connection, AS_OF)
    view = dashboard.load(connection, Path("x.duckdb"), dashboard.MARKETPLACE, AS_OF)
    assert view.snapshot is None
    shown = dashboard.panel(view, AS_OF)
    assert dashboard.NO_SNAPSHOT in shown.caption
    assert shown.checks.empty


def test_mixed_labels_detected() -> None:
    connection = database()
    connection.execute(
        "INSERT INTO collection_run VALUES ('live-0', 'azure-retail', 'live', ?, ?,"
        " 'succeeded', 'test', 1, NULL, NULL, NULL)",
        [DAY - timedelta(days=1), DAY - timedelta(days=1)],
    )
    azure_run(connection, "run-1", [Price()])
    normalize.normalize_pending(connection, AS_OF)
    view = dashboard.load(connection, Path("x.duckdb"), dashboard.AZURE, AS_OF)
    assert view.labels == ("live", "synthetic")
    assert view.mixed


def test_demo_labels_are_not_mixed(views: dict[str, dashboard.SourceView]) -> None:
    assert not azure(views).mixed
    assert views[dashboard.MARKETPLACE].labels == ("synthetic",)


# --- filters and browser ---


def test_filters_offer_only_existing_groups(
    views: dict[str, dashboard.SourceView],
) -> None:
    found = azure(views).region_groups
    assert dashboard.variants(found) == ["A100 PCIe 80GB", H100, "T4 16GB"]
    assert dashboard.gpu_counts(found, "A100 PCIe 80GB") == [1]
    assert dashboard.rental_types(found, "A100 PCIe 80GB", 1) == ["on_demand"]
    assert dashboard.rental_types(found, H100, 8) == ["on_demand", "spot"]
    assert dashboard.regions(found, H100, 8, "spot") == ["eastus", "westeurope"]
    assert dashboard.regions(found, H100, 8, "on_demand") == [
        "eastus",
        "southcentralus",
        "swedencentral",
        "westeurope",
        "westus3",
    ]


def test_browser_has_keys_counts_and_labels_but_no_prices(
    views: dict[str, dashboard.SourceView],
) -> None:
    frame = dashboard.browser_frame(azure(views).region_groups)
    assert list(frame.columns) == [
        "Variant",
        "GPUs",
        "Region",
        "Rental type",
        "Members",
        "Labels",
    ]
    assert not any(word in " ".join(frame.columns) for word in PRICE_WORDS)
    assert len(frame) == len(azure(views).region_groups)
    # Key order, as the columns read: variant, GPU count, region, rental type.
    shown = frame[["Variant", "GPUs", "Region", "Rental type"]].values.tolist()
    by_key = sorted(
        (g.key.variant, g.key.gpu_count, g.key.region, g.key.rental_type)
        for g in azure(views).region_groups
    )
    assert shown == [
        [variant, count, region, dashboard.rental_name(rental)]
        for variant, count, region, rental in by_key
    ]
    t4 = dashboard.browser_frame(azure(views).region_groups, variant="T4 16GB")
    assert t4[["Region", "Members", "Labels"]].values.tolist() == [
        ["eastus", 2, ""],
        ["westeurope", 1, groups.SINGLE],
    ]


# --- group views, captions and formats ---


def test_region_group_lists_every_member(
    views: dict[str, dashboard.SourceView],
) -> None:
    t4 = group(azure(views), "T4 16GB", 1, "eastus", "on_demand")
    frame = dashboard.members_frame(t4)
    assert list(frame.columns) == [
        "Size",
        dashboard.USD,
        dashboard.PUBLISHED,
        "Currency",
        "Unit",
        "Retrieved",
    ]
    assert frame.values.tolist() == [
        ["Standard_NC4as_T4_v3", 0.6, 0.6, "USD", "1 Hour", "2026-10-12 09:00 UTC"],
        ["Standard_NC8as_T4_v3", 0.8, 0.8, "USD", "1 Hour", "2026-10-12 09:00 UTC"],
    ]


def test_eight_gpu_member_shows_its_vm_price(
    views: dict[str, dashboard.SourceView],
) -> None:
    h100 = group(azure(views), H100, 8, "eastus", "spot")
    frame = dashboard.members_frame(h100)
    assert frame[[dashboard.USD, dashboard.PUBLISHED]].values.tolist() == [[12.0, 96.0]]
    assert h100.labels == [groups.SINGLE]
    # Spot equal to pay-as-you-go is shown as listed: nothing marks it.
    listed = group(azure(views), H100, 8, "eastus", "on_demand")
    assert h100.members[0].price == listed.members[0].price


def test_source_records_trace_to_the_file(
    views: dict[str, dashboard.SourceView],
) -> None:
    a100 = group(azure(views), "A100 PCIe 80GB", 1, "eastus", "on_demand")
    (row,) = dashboard.provenance_frame(a100).to_dict("records")
    assert row["Raw response"] == "tests/fixtures/synthetic/azure_demo.json"
    assert row["SHA-256"] == hashlib.sha256(DEMO.read_bytes()).hexdigest()
    assert row["Seq"] == 0
    assert row["Data label"] == "synthetic"
    assert row["Run ID"] == a100.snapshot.run_id
    assert row["Item key"].startswith("00000000-0000-0000-0000-")
    assert row["Retrieved (UTC)"] == "2026-10-12T09:00:00+00:00"


def test_group_caption_carries_key_snapshot_label_and_exclusions(
    views: dict[str, dashboard.SourceView],
) -> None:
    t4 = group(azure(views), "T4 16GB", 1, "eastus", "on_demand")
    text = dashboard.group_caption(t4)
    assert "Group: T4 16GB · 1 GPU · eastus · pay-as-you-go" in text
    assert "snapshot 2026-10-12 09:00 UTC" in text
    assert t4.snapshot.run_id in text
    assert "data label: synthetic" in text
    assert text.endswith(t4.exclusions)
    assert t4.exclusions.startswith("Excludes disks")


def test_known_answer_summary() -> None:
    connection = database()
    sizes = [
        Price("Standard_ND96isr_H100_v5", f"r{i}", price=8 * v, meter=f"h{i}")
        for i, v in enumerate([1, 2, 3, 4, 10], 1)
    ]
    azure_run(connection, "run-1", sizes)
    normalize.normalize_pending(connection, AS_OF)
    view = dashboard.load(connection, Path("x.duckdb"), dashboard.AZURE, AS_OF)
    summary = dashboard.find_summary(view.summaries, H100, 8, "on_demand")
    assert summary is not None
    stats = dashboard.stats_frame(summary.stats, "Regions").to_dict("records")
    assert stats == [{"Regions": 5, "Minimum": 1.0, "Median": 3.0, "Maximum": 10.0}]
    assert groups.THIN not in summary.labels
    frame = dashboard.summary_frame(summary)
    assert frame["Region"].tolist() == ["r1", "r2", "r3", "r4", "r5"]
    text = dashboard.summary_caption(summary)
    assert text.startswith("Crosses regions: H100 NVLink 80GB · 8 GPUs · pay-as-you-go")
    assert "data label: synthetic" in text
    assert text.endswith(summary.exclusions)


def test_thin_summary_labelled(views: dict[str, dashboard.SourceView]) -> None:
    spot = dashboard.find_summary(azure(views).summaries, H100, 8, "spot")
    listed = dashboard.find_summary(azure(views).summaries, H100, 8, "on_demand")
    assert spot is not None and listed is not None
    assert groups.THIN in spot.labels
    assert groups.THIN not in listed.labels


def test_marketplace_duplicate_marked() -> None:
    connection = database()
    synthetic.ingest_snapshot(connection, SNAPSHOTS[0])
    normalize.normalize_pending(connection, AS_OF)
    view = dashboard.load(connection, Path("x.duckdb"), dashboard.MARKETPLACE, AS_OF)
    flagged = [
        g
        for g in view.region_groups
        if any(groups.DUPLICATE in m.flags for m in g.members)
    ]
    assert len(flagged) == 1
    frame = dashboard.members_frame(flagged[0])
    assert list(frame.columns) == [
        "Offer",
        "Machine",
        dashboard.USD,
        dashboard.OFFER,
        "Currency",
        "Unit",
        "Retrieved",
        "Flags",
    ]
    duplicates = frame[frame["Flags"] == groups.DUPLICATE]
    assert duplicates["Machine"].tolist() == ["M-01"]
    stats = flagged[0].stats
    assert stats is not None
    machines = set(frame["Machine"])
    assert stats.count == len(machines)
    assert groups.SYNTHETIC in flagged[0].labels


def test_marketplace_browser_counts_machines_and_offers() -> None:
    connection = database()
    synthetic.ingest_snapshot(connection, SNAPSHOTS[0])
    normalize.normalize_pending(connection, AS_OF)
    view = dashboard.load(connection, Path("x.duckdb"), dashboard.MARKETPLACE, AS_OF)
    frame = dashboard.browser_frame(view.region_groups)
    assert list(frame.columns) == [
        "Variant",
        "GPUs",
        "Region",
        "Rental type",
        "Machines",
        "Offers",
        "Labels",
    ]
    (flagged,) = [
        g
        for g in view.region_groups
        if any(groups.DUPLICATE in m.flags for m in g.members)
    ]
    row = frame[
        (frame["Variant"] == flagged.key.variant)
        & (frame["GPUs"] == flagged.key.gpu_count)
        & (frame["Region"] == flagged.key.region)
    ]
    machines = len({m.machine_id for m in flagged.members})
    assert row[["Machines", "Offers"]].values.tolist() == [
        [machines, len(flagged.members)]
    ]
    assert machines < len(flagged.members)


def test_panels_compare_by_identity(views: dict[str, dashboard.SourceView]) -> None:
    first = dashboard.panel(azure(views), AS_OF)
    second = dashboard.panel(azure(views), AS_OF)
    assert first == first
    assert first != second  # no DataFrame truth-value error
    assert first in [first]


def test_framing_lines() -> None:
    live = Snapshot("azure-retail", "run-1", DAY, "live")
    fake = Snapshot("azure-retail", "run-2", DAY, "synthetic")
    assert dashboard.framing(live, False, AS_OF, 7) == (
        "Published Azure retail list prices for GPU VMs · live · snapshot"
        " 2026-10-12 09:00 UTC · local analysis only"
    )
    assert dashboard.framing(fake, False, AS_OF, 7) == (
        "Synthetic data: invented prices for demonstration, not Azure list prices"
        " · snapshot 2026-10-12 09:00 UTC"
    )
    later = DAY + timedelta(days=8)
    assert dashboard.framing(fake, True, later, 7).endswith(
        " · STALE (older than 7 days as of 2026-10-20 09:00 UTC)"
    )


def test_display_formats() -> None:
    assert dashboard.FORMATS[dashboard.USD] % 12.291267 == "12.2913"
    assert dashboard.FORMATS[dashboard.PUBLISHED] == "plain"
    assert all(dashboard.FORMATS[k] == "%.4f" for k in ("Minimum", "Median", "Maximum"))


# --- chart ---


def _layers(chart: Any) -> list[tuple[str, list[dict[str, Any]]]]:
    spec = chart.to_dict()
    found = []
    for layer in spec["layer"]:
        mark = layer["mark"]
        kind = mark if isinstance(mark, str) else mark["type"]
        found.append((kind, spec["datasets"][layer["data"]["name"]]))
    return found


def test_chart_plots_only_listed_regions(
    views: dict[str, dashboard.SourceView],
) -> None:
    spot = dashboard.find_summary(azure(views).summaries, H100, 8, "spot")
    assert spot is not None
    (points_kind, points), (rules_kind, marks) = _layers(dashboard.summary_chart(spot))
    assert (points_kind, rules_kind) == ("point", "rule")
    assert [p["Region"] for p in points] == ["eastus", "westeurope"]
    assert [m[dashboard.USD] for m in marks] == [5.0, 8.5, 12.0]
    assert [m["Statistic"] for m in marks] == ["minimum", dashboard.MEDIAN, "maximum"]
    assert "line" not in str(dashboard.summary_chart(spot).to_dict()["layer"])


# --- quality panel ---


def test_panel_matches_the_report(views: dict[str, dashboard.SourceView]) -> None:
    view = azure(views)
    shown = dashboard.panel(view, AS_OF)
    checks = dict(shown.checks.values.tolist())
    assert shown.unmapped_sizes == ["Standard_ND96is_MI300X_v5"]
    assert checks["Unmapped"] == (
        "sizes not in the map 1; rows excluded as unmapped_sku 1"
    )
    assert checks["Observations not normalized"] == "0"
    assert checks["Thin cross-region summaries"] == str(view.report.thin)
    assert checks["Stale"].startswith("no ")
    assert checks["Duplicates"] == "repeats 0, shared_meter_key 0"
    assert checks["Missing fields among compared rows"] == (
        "location 0, product_name 0, effective_start_date 0"
    )
    secondary = dict(shown.secondary.values.tolist())
    assert secondary["Observations"] == "13"
    assert secondary["Rows: windows"] == "1"
    assert secondary["Changes since the previous snapshot"] == "no previous snapshot"
    assert "data label: synthetic" in shown.caption
    assert "as of 2026-10-12 12:00 UTC" in shown.caption


def test_marketplace_panel_counts_machine_duplicates(
    views: dict[str, dashboard.SourceView],
) -> None:
    view = views[dashboard.MARKETPLACE]
    checks = dict(dashboard.panel(view, AS_OF).checks.values.tolist())
    duplicates = view.report.duplicates[groups.DUPLICATE]
    assert checks["Duplicates"] == f"{groups.DUPLICATE} {duplicates}"
    assert checks["Stale"].startswith("yes ")  # snapshot-3 is 2026-10-03
    assert "Thin groups" in checks
