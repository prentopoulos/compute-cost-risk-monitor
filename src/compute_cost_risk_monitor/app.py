"""The local Streamlit dashboard (Phase 4 design D3-D6, D13, D15, D28, D31;
phase-5-calculator D17, D24-D27; phase-7 D6-D10, D16, D25, D27, D33-D46).

    uv run streamlit run src/compute_cost_risk_monitor/app.py

`.streamlit/config.toml` beside this script applies from any folder: no usage
statistics, the server listens on 127.0.0.1 only, and it sets the dark desk theme. Each
page run opens the chosen database read-only, reads what it shows, and closes the
connection before drawing. While it reads, a collect or normalize started in another
process fails instead of waiting, so rerun it. Every figure comes from `dashboard`,
which only arranges Phase 3 outputs and the workload calculator's, and every workload
figure passes the independent check before it is drawn. States are plain status words,
never coloured alert boxes, and explanations live in each tab's Sources section.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

from compute_cost_risk_monitor import calculator, dashboard, scenarios
from compute_cost_risk_monitor.dashboard import KeyFigure, SourceView
from compute_cost_risk_monitor.groups import GroupKey, RegionGroup

Choice = tuple[str, int, str, str]  # variant, GPU count, rental type, region
VIEWS = ("Workload cost", "Comparable groups", "Group browser", "Data quality")
# Everything under the inputs keeps mock v3's single column; the Styler cell widths
# size the grid and COST tables to it (phase-7 D49).
COLUMN_WIDTH = 960


def _status(word: str | None, message: str) -> None:
    """A state in plain words, in text colour; never a coloured alert box (D40, D41)."""
    st.markdown(f"**{word}**  \n{message}" if word else message)


def _table(frame: pd.DataFrame) -> None:
    formats = {
        name: st.column_config.NumberColumn(format=fmt)
        for name, fmt in dashboard.FORMATS.items()
        if name in frame.columns
    }
    st.dataframe(frame, hide_index=True, column_config=formats)


def _figures(figures: Sequence[KeyFigure]) -> None:
    """One row of key figures, packed left: terse label above, value below."""
    columns = st.columns([1.2] * len(figures) + [6 - len(figures)])
    for column, (label, value) in zip(columns, figures, strict=False):
        column.metric(label, value)


def _sources(lines: Sequence[str], group: RegionGroup | None) -> None:
    """The closed Sources section: provenance and every explanation (D9, D27)."""
    with st.expander("Sources"):
        st.markdown("\n".join(f"- {line}" for line in lines))
        if group is not None:
            _table(dashboard.provenance_frame(group))


def _filters(view: SourceView) -> Choice | None:
    """Cascading choices in the sidebar, offering only groups that exist."""
    found = view.region_groups
    if not found:
        return None
    side = st.sidebar
    variant = side.selectbox("GPU", dashboard.variants(found))
    count = side.selectbox("GPUs per VM", dashboard.gpu_counts(found, variant))
    rental = side.selectbox(
        "Pricing",
        dashboard.rental_types(found, variant, count),
        format_func=dashboard.pricing_name,
    )
    region = side.selectbox(
        "Region",
        dashboard.region_choices(view, variant, count, rental),
        format_func=lambda code: dashboard.region_name(view, code),
    )
    return variant, count, rental, region


def _header(view: SourceView, path: Path, as_of: datetime) -> None:
    snapshot = view.snapshot
    days = view.stale_after_days
    st.markdown(dashboard.status_line(snapshot, view.report.stale, as_of, days))
    if snapshot is None:
        _status(dashboard.NO_SNAPSHOT_WORD, dashboard.NO_SNAPSHOT)
        return
    if view.mixed:
        st.markdown(f":orange[{dashboard.MIXED.format(labels=', '.join(view.labels))}]")
    if view.withheld:
        _status(
            None,
            dashboard.NOT_NORMALIZED.format(
                count=view.report.not_normalized, path=path
            ),
        )


def _group(view: SourceView, choice: Choice | None) -> RegionGroup | None:
    """The chosen group, or None after drawing why there is none to show."""
    if view.snapshot is None:
        return None  # the header already says no snapshot
    if view.withheld:
        _status(dashboard.WITHHELD_WORD, dashboard.WITHHELD_WORKLOAD)
        return None
    if choice is None:
        _status(dashboard.NO_GROUPS_WORD, dashboard.NO_GROUPS)
        return None
    variant, count, rental, region = choice
    # The filters only offer existing groups, so this finds one.
    return dashboard.find_group(
        view.region_groups, GroupKey(variant, count, region, rental)
    )


def _groups(view: SourceView, choice: Choice | None) -> None:
    group = _group(view, choice)
    if group is None or choice is None:
        return
    variant, count, rental, _ = choice
    _figures(dashboard.group_figures(group))
    if group.labels:
        st.markdown(dashboard.labels_text(group.labels))
    _table(dashboard.members_frame(group))
    if group.stats is not None:  # marketplace: one price per machine
        _table(dashboard.stats_frame(group.stats, "Machines"))
    st.markdown(f":gray[{group.exclusions}]")
    summary = dashboard.find_summary(view.summaries, variant, count, rental)
    if summary is not None:
        st.markdown(
            ":gray[**ACROSS REGIONS**] " + dashboard.labels_text(summary.labels)
        )
        _table(dashboard.summary_frame(summary, view.region_names))
        _table(dashboard.stats_frame(summary.stats, "Regions"))
        st.altair_chart(
            dashboard.summary_chart(summary, view.region_names), width="stretch"
        )
    _sources(dashboard.group_sources(view, group, summary), group)


def _workload_inputs(
    size_options: list[str] | None, key: GroupKey
) -> tuple[
    str | None, int | None, float | None, float | None, str, float | None, float | None
]:
    """The inputs row, kept across tabs (phase-5 D17, D24-D26; phase-7 D6, D34)."""
    per_vm = key.gpu_count
    widths = [1.4] if size_options else []
    widths += [1, 1, 1, 1.2, 1, 1.5]
    columns = iter(st.columns(widths, vertical_alignment="bottom"))
    size = None
    if size_options:
        size = next(columns).selectbox(
            "Size",
            size_options,
            key=dashboard.size_key(key),
            persist_state="session",
        )
    gpus = next(columns).number_input(
        "GPUs",
        min_value=per_vm,
        max_value=calculator.MAX_GPUS,
        value=dashboard.default_gpus(per_vm),
        step=per_vm,
        key="gpus",
        persist_state="session",
    )
    hours = next(columns).number_input(
        "Hours",
        min_value=0.0,
        max_value=calculator.MAX_HOURS,
        value=calculator.DEFAULT_HOURS,
        step=24.0,
        format="%g",
        key="hours",
        persist_state="session",
    )
    storage = next(columns).number_input(
        "Storage, USD",
        min_value=0.0,
        max_value=calculator.MAX_STORAGE,
        value=None,
        step=100.0,
        key="storage",
        placeholder=dashboard.DASH,
        persist_state="session",
    )
    column = next(columns)  # the custom move, its unit switch above it (D34, D49)
    unit = column.radio(
        "Unit",
        list(dashboard.CUSTOM_KINDS),
        horizontal=True,
        key="custom_kind",
        label_visibility="collapsed",
        persist_state="session",
    )
    kind = dashboard.CUSTOM_KINDS[unit]
    if kind == scenarios.PERCENT:
        change = column.number_input(
            dashboard.CUSTOM_LABELS[kind],
            min_value=calculator.MIN_CUSTOM_PERCENT,
            max_value=calculator.MAX_CUSTOM_PERCENT,
            value=None,
            step=5.0,
            key="custom_percent",
            placeholder=dashboard.DASH,
            persist_state="session",
        )
    else:
        change = column.number_input(
            dashboard.CUSTOM_LABELS[kind],
            min_value=-calculator.MAX_CUSTOM_USD,
            max_value=calculator.MAX_CUSTOM_USD,
            value=None,
            step=0.1,
            format="%.4f",
            key="custom_usd",
            placeholder=dashboard.DASH,
            persist_state="session",
        )
    budget = next(columns).number_input(
        "Contingency, USD",
        min_value=0.0,
        max_value=calculator.MAX_BUDGET,
        value=None,
        step=1_000.0,
        key="budget",
        placeholder=dashboard.DASH,
        persist_state="session",
    )
    return size, gpus, hours, storage, kind, change, budget


def _workload(view: SourceView, choice: Choice | None) -> None:
    if view.source != dashboard.AZURE:
        st.markdown(dashboard.MARKETPLACE_NOTE)
        return
    group = _group(view, choice)
    if group is None:
        return
    figures = st.container()  # drawn once the inputs are read and the check runs
    options = dashboard.sizes(group) if len(group.members) > 1 else None
    size, gpus, hours, storage, kind, entered, budget = _workload_inputs(
        options, group.key
    )
    begin = calculator.start(group, size)
    # Everything under the inputs stays in one column (D6, D49).
    with st.container(width=COLUMN_WIDTH):
        try:
            work = calculator.workload(gpus, hours, storage, group.key.gpu_count)
            change = calculator.custom(kind, entered)
            limit = calculator.budget(budget)
        except calculator.Refused as refused:
            with figures:
                _figures(dashboard.workload_figures(begin, None, budget is not None))
            _status(dashboard.REFUSED, str(refused))
            _sources(dashboard.workload_sources(group, None), group)
            return
        result = calculator.calculate(begin, work, view.region_groups, change, limit)
        failed = dashboard.check(begin, result, work, change, limit, view.region_groups)
        if failed:
            with figures:
                _figures(dashboard.workload_figures(begin, None, limit is not None))
            _status(
                dashboard.CHECK_FAILED_WORD,
                dashboard.CHECK_FAILED.format(checks=", ".join(failed)),
            )
            _sources(dashboard.workload_sources(group, None), group)
            return
        # Every price, the starting one included, appears only after the check passes.
        with figures:
            _figures(dashboard.workload_figures(begin, result, limit is not None))
        st.markdown(dashboard.grid_title(work))
        st.table(dashboard.grid(result.ladder), hide_index=True, border="horizontal")
        st.markdown(dashboard.footer_text(result))
        st.markdown(":gray[**COST**]")
        st.table(
            dashboard.cost_styles(result),
            hide_index=True,
            width="content",
            border="horizontal",
        )
        _sources(dashboard.workload_sources(group, result), group)


def _browser(view: SourceView, choice: Choice | None) -> None:
    snapshot = view.snapshot
    if snapshot is None or not view.region_groups:
        _status(dashboard.NO_GROUPS_WORD, "No groups to list.")
        return
    narrow = choice is not None and st.toggle("Only the chosen GPU")
    variant = choice[0] if narrow and choice is not None else None
    _table(
        dashboard.browser_frame(
            view.region_groups, variant=variant, names=view.region_names
        )
    )
    _sources(dashboard.browser_sources(snapshot), None)


def _panel(view: SourceView, path: Path, as_of: datetime) -> None:
    shown = dashboard.panel(view, as_of)
    st.subheader(dashboard.catalogue_name(view.source, view))
    if shown.snapshot is None:
        _status(dashboard.NO_SNAPSHOT_WORD, dashboard.NO_SNAPSHOT)
        return
    if view.withheld:
        _status(
            None,
            dashboard.NOT_NORMALIZED.format(
                count=view.report.not_normalized, path=path
            ),
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
    found = dashboard.datasets(known)
    if not found:
        st.markdown(f"**{dashboard.TITLE_LINE}**")
        _status(dashboard.NO_DATABASE_WORD, dashboard.NO_DATABASE)
        return
    names = [dataset.label for dataset in found]
    dataset = found[names.index(st.sidebar.selectbox("Dataset", names, key="dataset"))]
    # The catalogue choice from the last run picks which source's groups to read; its
    # names need each source's run label, so it is drawn after the read (D33).
    selected = st.session_state.get("catalogue", dashboard.AZURE)
    try:
        connection = dashboard.open_read_only(dataset.path)
    except dashboard.Problem as problem:
        st.markdown(f"**{dashboard.TITLE_LINE}**")
        _status(problem.word, str(problem))
        return
    try:
        views = dashboard.load_all(connection, dataset.path, as_of, selected)
    except dashboard.Problem as problem:
        st.markdown(f"**{dashboard.TITLE_LINE}**")
        _status(problem.word, str(problem))
        return
    except duckdb.Error as error:  # shown, not a traceback
        st.markdown(f"**{dashboard.TITLE_LINE}**")
        _status("CANNOT READ", f"Cannot read {dataset.path}: {error}")
        return
    finally:
        connection.close()
    source = st.sidebar.selectbox(
        "Catalogue",
        list(dashboard.CATALOGUE),
        key="catalogue",
        format_func=lambda each: dashboard.catalogue_name(each, views[each]),
    )
    view = views[source]
    _header(view, dataset.path, as_of)
    choice = _filters(view)
    # Lazy tabs: only the open tab is drawn, so no table is laid out while hidden.
    workload_tab, groups_tab, browser_tab, quality_tab = st.tabs(
        list(VIEWS), key="view", on_change="rerun"
    )
    if workload_tab.open:
        with workload_tab:
            _workload(view, choice)
    if groups_tab.open:
        with groups_tab:
            _groups(view, choice)
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
