"""The local Streamlit dashboard (Phase 4 design D3-D6, D13, D15, D28).

    uv run streamlit run src/compute_cost_risk_monitor/app.py

Launch it from the repository root so `.streamlit/config.toml` applies: no usage
statistics, and the server listens on 127.0.0.1 only. Each page run opens the chosen
database read-only, reads what it shows, and closes the connection before drawing, so
collect and normalize are never blocked. Every figure comes from `dashboard`, which only
arranges Phase 3 outputs.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from compute_cost_risk_monitor import dashboard
from compute_cost_risk_monitor.dashboard import SourceView
from compute_cost_risk_monitor.groups import GroupKey

Choice = tuple[str, int, str, str]  # variant, GPU count, rental type, region


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
        views = dashboard.load_all(connection, dataset.path, as_of)
    except dashboard.Problem as problem:
        st.warning(str(problem))
        return
    finally:
        connection.close()
    view = views[source]
    _header(view, dataset.path, as_of)
    choice = _filters(view)
    groups_tab, browser_tab, quality_tab = st.tabs(
        ["Comparable groups", "Group browser", "Data quality"]
    )
    with groups_tab:
        _groups(view, choice)
    with browser_tab:
        _browser(view, choice)
    with quality_tab:
        for each in views.values():
            _panel(each, dataset.path, as_of)


if __name__ == "__main__":
    # The only clock read (D15): the page's as-of time for the stale flag.
    main(dashboard.KNOWN, datetime.now(UTC))
