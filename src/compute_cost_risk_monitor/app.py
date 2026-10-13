"""The local Streamlit dashboard (Phase 4 design D3-D6, D13, D15, D28, D31;
phase-5-calculator D17, D24-D27).

    uv run streamlit run src/compute_cost_risk_monitor/app.py

`.streamlit/config.toml` beside this script applies from any folder: no usage
statistics, and the server listens on 127.0.0.1 only. Each page run opens the chosen
database read-only, reads what it shows, and closes the connection before drawing. While
it reads, a collect or normalize started in another process fails instead of waiting,
so rerun it. Every figure comes from `dashboard`, which only arranges Phase 3 outputs
and the workload calculator's, and every workload figure passes the independent check
before it is drawn.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

from compute_cost_risk_monitor import calculator, dashboard, scenarios
from compute_cost_risk_monitor.dashboard import SourceView
from compute_cost_risk_monitor.groups import GroupKey

Choice = tuple[str, int, str, str]  # variant, GPU count, rental type, region
VIEWS = ("Comparable groups", "Workload cost", "Group browser", "Data quality")


def _table(frame: pd.DataFrame) -> None:
    formats = {
        name: st.column_config.NumberColumn(format=fmt)
        for name, fmt in dashboard.FORMATS.items()
        if name in frame.columns
    }
    st.dataframe(frame, hide_index=True, column_config=formats)


def _filters(view: SourceView) -> Choice | None:
    """Cascading choices in the sidebar, offering only groups that exist."""
    found = view.region_groups
    if not found:
        return None
    side = st.sidebar
    variant = side.selectbox("GPU variant", dashboard.variants(found))
    count = side.selectbox(
        "GPU count", dashboard.gpu_counts(found, variant), format_func=dashboard.gpus
    )
    rental = side.selectbox(
        "Rental type",
        dashboard.rental_types(found, variant, count),
        format_func=dashboard.rental_name,
    )
    region = side.selectbox("Region", dashboard.regions(found, variant, count, rental))
    return variant, count, rental, region


def _header(view: SourceView, path: Path, as_of: datetime) -> None:
    snapshot = view.snapshot
    if snapshot is None or view.stale_after_days is None:
        st.info(dashboard.NO_SNAPSHOT)
        return
    line = dashboard.framing(snapshot, view.report.stale, as_of, view.stale_after_days)
    if view.report.stale:
        st.warning(line)
    else:
        st.markdown(line)
    if view.mixed:
        st.warning(dashboard.MIXED.format(labels=", ".join(view.labels)))
    if view.withheld:
        st.error(
            dashboard.NOT_NORMALIZED.format(count=view.report.not_normalized, path=path)
        )


def _groups(view: SourceView, choice: Choice | None) -> None:
    if view.snapshot is None:
        st.info(dashboard.NO_SNAPSHOT)
        return
    if view.withheld:
        st.info("The group views are withheld until this snapshot is normalized.")
        return
    if choice is None:
        st.info("This snapshot holds no comparable groups.")
        return
    variant, count, rental, region = choice
    group = dashboard.find_group(
        view.region_groups, GroupKey(variant, count, region, rental)
    )
    if group is None:  # the filters only offer existing groups
        return
    caption = dashboard.group_caption(group)
    st.subheader("Region group")
    if group.labels:
        st.markdown(dashboard.labels_text(group.labels))
    _table(dashboard.members_frame(group))
    st.caption(caption)
    if view.source == dashboard.AZURE and len(group.members) > 1:
        st.caption(dashboard.MULTI_SIZE)
    if group.stats is not None:  # marketplace: one price per machine
        _table(dashboard.stats_frame(group.stats, "Machines"))
        st.caption(caption)
    with st.expander("Source records"):
        _table(dashboard.provenance_frame(group))
        st.caption(caption)
    summary = dashboard.find_summary(view.summaries, variant, count, rental)
    if summary is None:
        return
    summary_caption = dashboard.summary_caption(summary)
    st.subheader("Across regions")
    st.markdown(dashboard.labels_text(summary.labels))
    st.caption(dashboard.LOWEST)
    _table(dashboard.summary_frame(summary))
    st.caption(summary_caption)
    _table(dashboard.stats_frame(summary.stats, "Regions"))
    st.caption(summary_caption)
    st.altair_chart(dashboard.summary_chart(summary), width="stretch")
    st.caption(summary_caption)


def _workload_inputs(
    per_vm: int,
) -> tuple[int | None, float | None, float | None, str, float | None, float | None]:
    """Workload, custom scenario and budget inputs, kept across tabs (D17, D24-D26)."""
    left, middle, right = st.columns(3)
    gpus = left.number_input(
        "GPUs (whole VMs)",
        min_value=per_vm,
        max_value=calculator.MAX_GPUS,
        value=dashboard.default_gpus(per_vm),
        step=per_vm,
        key="gpus",
        persist_state="session",
    )
    hours = middle.number_input(
        "Hours in the period",
        min_value=0.0,
        max_value=calculator.MAX_HOURS,
        value=calculator.DEFAULT_HOURS,
        step=1.0,
        key="hours",
        help=dashboard.HOURS_HELP,
        persist_state="session",
    )
    storage = right.number_input(
        "Storage for the period (USD, optional)",
        min_value=0.0,
        max_value=calculator.MAX_STORAGE,
        value=None,
        step=100.0,
        key="storage",
        placeholder="not included",
        persist_state="session",
    )
    left, middle, right = st.columns(3)
    label = left.radio(
        "Custom scenario",
        list(dashboard.CUSTOM_KINDS),
        horizontal=True,
        key="custom_kind",
        persist_state="session",
    )
    kind = dashboard.CUSTOM_KINDS[label]
    if kind == scenarios.PERCENT:
        change = middle.number_input(
            "Custom change (% of starting price)",
            min_value=calculator.MIN_CUSTOM_PERCENT,
            max_value=calculator.MAX_CUSTOM_PERCENT,
            value=None,
            step=5.0,
            key="custom_percent",
            placeholder="none",
            persist_state="session",
        )
    else:
        change = middle.number_input(
            "Custom change (USD per GPU-hour)",
            min_value=-calculator.MAX_CUSTOM_USD,
            max_value=calculator.MAX_CUSTOM_USD,
            value=None,
            step=0.1,
            format="%.4f",
            key="custom_usd",
            placeholder="none",
            persist_state="session",
        )
    budget = right.number_input(
        "Budget for headroom (USD, optional)",
        min_value=0.0,
        max_value=calculator.MAX_BUDGET,
        value=None,
        step=1_000.0,
        key="budget",
        placeholder="none",
        persist_state="session",
    )
    return gpus, hours, storage, kind, change, budget


def _workload(view: SourceView, choice: Choice | None) -> None:
    if view.source != dashboard.AZURE:
        st.info(dashboard.MARKETPLACE_NOTE)
        return
    if view.snapshot is None:
        st.info(dashboard.NO_SNAPSHOT)
        return
    if view.withheld:
        st.info(dashboard.WITHHELD_WORKLOAD)
        return
    if choice is None:
        st.info("This snapshot holds no comparable groups.")
        return
    variant, count, rental, region = choice
    group = dashboard.find_group(
        view.region_groups, GroupKey(variant, count, region, rental)
    )
    if group is None:  # the filters only offer existing groups
        return
    st.subheader("Workload cost")
    st.markdown(dashboard.WORKLOAD_INTRO)
    size = None
    if len(group.members) > 1:
        size = st.selectbox(
            "Size",
            dashboard.sizes(group),
            key=dashboard.size_key(group.key),
            persist_state="session",
        )
    begin = calculator.start(group, size)
    st.markdown(dashboard.start_text(begin))
    gpus, hours, storage, kind, entered, budget = _workload_inputs(count)
    try:
        work = calculator.workload(gpus, hours, storage, count)
        change = calculator.custom(kind, entered)
        limit = calculator.budget(budget)
    except calculator.Refused as refused:
        st.warning(str(refused))
        return
    result = calculator.calculate(begin, work, view.region_groups, change, limit)
    failed = dashboard.check(result, work, change, limit, view.region_groups)
    if failed:
        st.error(dashboard.CHECK_FAILED.format(checks=", ".join(failed)))
        return
    caption = dashboard.workload_caption(result)
    st.markdown(dashboard.vms_text(work, begin))
    _table(dashboard.cost_frame(result))
    st.caption(caption)
    st.subheader("Scenarios")
    st.markdown(f"**{scenarios.NOT_A_FORECAST}** · {result.version}")
    scenario_caption = dashboard.scenario_caption(result)
    _table(dashboard.scenario_frame(result))
    st.caption(scenario_caption)
    st.altair_chart(dashboard.exposure_chart(result), width="stretch")
    st.caption(scenario_caption)
    st.subheader("Budget headroom")
    text = dashboard.headroom_text(result)
    if text is None:
        st.caption(dashboard.BUDGET_HINT)
    else:
        st.markdown(text)
        st.caption(caption)


def _browser(view: SourceView, choice: Choice | None) -> None:
    snapshot = view.snapshot
    if snapshot is None or not view.region_groups:
        st.info("No groups to list.")
        return
    narrow = choice is not None and st.toggle("Only the chosen GPU variant")
    variant = choice[0] if narrow and choice is not None else None
    _table(dashboard.browser_frame(view.region_groups, variant=variant))
    st.caption(f"{dashboard.plain_caption(snapshot)} · {dashboard.BROWSER}")


def _panel(view: SourceView, path: Path, as_of: datetime) -> None:
    shown = dashboard.panel(view, as_of)
    st.subheader(dashboard.SOURCE_NAMES[view.source])
    if shown.snapshot is None:
        st.info(dashboard.NO_SNAPSHOT)
        return
    if view.withheld:
        st.error(
            dashboard.NOT_NORMALIZED.format(count=view.report.not_normalized, path=path)
        )
    _table(shown.checks)
    st.caption(shown.caption)
    if shown.unmapped_sizes:
        st.markdown(
            "Sizes not in the map: "
            + ", ".join(f"`{size}`" for size in shown.unmapped_sizes)
        )
    with st.expander("More counts"):
        _table(shown.secondary)
        st.caption(shown.caption)


def main(known: Sequence[tuple[str, Path]], as_of: datetime) -> None:
    """Draw the page for the databases in `known` that exist, as of a given time."""
    st.set_page_config(page_title=dashboard.TITLE, layout="wide")
    st.title(dashboard.TITLE)
    found = dashboard.datasets(known)
    if not found:
        st.info(dashboard.NO_DATABASE)
        return
    names = [dataset.label for dataset in found]
    dataset = found[names.index(st.sidebar.radio("Dataset", names))]
    source = st.sidebar.radio(
        "Source",
        list(dashboard.SOURCE_NAMES),
        format_func=dashboard.SOURCE_NAMES.__getitem__,
    )
    try:
        connection = dashboard.open_read_only(dataset.path)
    except dashboard.Problem as problem:
        st.warning(str(problem))
        return
    try:
        views = dashboard.load_all(connection, dataset.path, as_of, source)
    except dashboard.Problem as problem:
        st.warning(str(problem))
        return
    except duckdb.Error as error:  # shown, not a traceback
        st.error(f"Cannot read {dataset.path}: {error}")
        return
    finally:
        connection.close()
    view = views[source]
    _header(view, dataset.path, as_of)
    choice = _filters(view)
    # Lazy tabs: only the open tab is drawn, so no table is laid out while hidden.
    groups_tab, workload_tab, browser_tab, quality_tab = st.tabs(
        list(VIEWS), key="view", on_change="rerun"
    )
    if groups_tab.open:
        with groups_tab:
            _groups(view, choice)
    if workload_tab.open:
        with workload_tab:
            _workload(view, choice)
    if browser_tab.open:
        with browser_tab:
            _browser(view, choice)
    if quality_tab.open:
        with quality_tab:
            for each in views.values():
                _panel(each, dataset.path, as_of)


if __name__ == "__main__":
    # The only clock read (D15): the page's as-of time for the stale flag.
    main(dashboard.KNOWN, datetime.now(UTC))
