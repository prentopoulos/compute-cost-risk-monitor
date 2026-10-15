"""View model for the local Streamlit dashboard (Phase 4 design D3, D9, D10, D13, D17,
D23-D26, D31; phase-5-calculator D8, D10, D16, D18, D19, D21, D27).

Plain Python and pandas with no Streamlit import, so every rule here is tested directly.
It only arranges what Phase 3 code computes (region groups, cross-region summaries,
marketplace groups and the quality report) and what `calculator` computes from them, and
formats values for display. Workload figures pass `workload_check` before they are
shown. Nothing is computed from a rounded value, and nothing is written.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import TYPE_CHECKING

import altair as alt
import duckdb
import pandas as pd
from pandas.io.formats.style import Styler

from compute_cost_risk_monitor import (
    azure_retail,
    calculator,
    db,
    groups,
    quality,
    rules,
    scenarios,
    synthetic,
    workload_check,
)
from compute_cost_risk_monitor.calculator import Custom, Result, Start, Workload

if TYPE_CHECKING:
    from pandas.io.formats.style_render import CSSDict
from compute_cost_risk_monitor.collect import DEFAULT_DB as MONITOR_DB
from compute_cost_risk_monitor.groups import (
    CrossRegionSummary,
    GroupKey,
    RegionGroup,
    Snapshot,
    Stats,
)

TITLE = "Compute Cost & Risk Monitor"
TITLE_LINE = "COMPUTE COST & RISK MONITOR"
# Dataset and catalogue names (phase-7 D33, D37): never the word "live".
LIVE_DATASET = "Azure list prices (local only)"
SYNTHETIC_DATASET = "Synthetic demo"
KNOWN: tuple[tuple[str, Path], ...] = (
    (LIVE_DATASET, MONITOR_DB),
    (SYNTHETIC_DATASET, synthetic.DEFAULT_DB),
)
AZURE = azure_retail.SOURCE
MARKETPLACE = synthetic.SOURCE
CATALOGUE = {AZURE: "Azure VMs", MARKETPLACE: "Marketplace"}
RENTAL_NAMES = {"on_demand": "pay-as-you-go", "spot": "Spot"}  # in running text
PRICING_NAMES = {"on_demand": "Pay-as-you-go", "spot": "Spot"}  # the Pricing choice
PRICING_SHORT = {"on_demand": "PAYG", "spot": "SPOT"}  # key-figure labels
# The status line (phase-7 D6, D9, D28, D42).
DATA_SYNTHETIC = "SYNTHETIC DATA — NOT AZURE LIST PRICES"
DATA_PUBLISHED = "AZURE PUBLISHED LIST PRICES"
STALE_LINE = "STALE — OLDER THAN {days} DAYS AS OF {when}"
# Status words for states, drawn in text colour and never as alert boxes (D40, D41).
REFUSED = "REFUSED"
CHECK_FAILED_WORD = "CHECK FAILED"
NO_SNAPSHOT_WORD = "NO SNAPSHOT"
NO_DATABASE_WORD = "NO DATABASE"
WITHHELD_WORD = "WITHHELD"
NO_GROUPS_WORD = "NO GROUPS"
NO_GROUPS = "This snapshot holds no comparable groups."
DASH = "—"  # an empty input, a value not entered, or a figure withheld
NA = "n/a"  # a grid cell that is not computed (D38)

NO_DATABASE = (
    "No database yet. Collect live Azure list prices with"
    " `uv run python -m compute_cost_risk_monitor.collect`, or store the synthetic demo"
    " with `uv run python -m compute_cost_risk_monitor.synthetic"
    " tests/fixtures/synthetic/azure_demo.json"
    " tests/fixtures/synthetic/marketplace/snapshot-1.json` (and the other snapshots),"
    " then run `uv run python -m compute_cost_risk_monitor.normalize --db <database>`."
)
IN_USE = (
    "The database is in use by another process, probably collect or normalize."
    " Rerun when it finishes."
)
# DuckDB's lock errors on Windows and elsewhere; any other open error is shown as is.
LOCK_ERRORS = (
    "being used by another process",
    "Could not set lock",
    "Conflicting lock",
)
EMPTY = (
    "{path} holds no tables yet. Store a run with"
    " `uv run python -m compute_cost_risk_monitor.collect` or"
    " `uv run python -m compute_cost_risk_monitor.synthetic`, then run normalize."
)
# Paths are quoted: the owner's repository path holds spaces and "&".
NO_RULES = (
    "No rule set is stored in {path}: run normalize first"
    ' (`uv run python -m compute_cost_risk_monitor.normalize --db "{path}"`).'
)
NOT_NORMALIZED = (
    "NOT NORMALIZED: {count} observations in the latest snapshot have no row under the"
    " rule set. Run"
    ' `uv run python -m compute_cost_risk_monitor.normalize --db "{path}"`.'
    " The group views are withheld until then."
)
NO_SNAPSHOT = "No snapshot: this source has no succeeded run."
MIXED = (
    "This source mixes data labels across its snapshots ({labels}). Each figure shows"
    " its own snapshot's label."
)
MULTI_SIZE = (
    "Sizes in this group share GPU variant and count but differ in vCPUs, RAM and"
    " local disk, so their per-GPU prices can differ."
)
LOWEST = (
    "Each region contributes its lowest listed size: the cheapest configuration listed"
    " there. The median is a statistic, not a listed price."
)
BROWSER = (
    "Group keys, member counts and labels only: no prices, so nothing is compared."
)
MEDIAN = "median (a statistic, not a listed price)"
# The theme's colours (config.toml [theme]; phase-7 D4, D10, D24, D26). The scenario
# grid and the charts draw with them, and tests/repo/test_streamlit_config.py keeps
# them equal to the config and above the contrast floor.
COLOURS = {
    "background": "#0E1116",
    "panel": "#161B22",
    "text": "#E6E8EB",
    "muted": "#9AA3AE",
    "accent": "#7AA2D6",  # the active tab and the entered grid column only
    "border": "#646E7C",
    "rule": "#2A313C",
    "zero": "#4A5462",  # the grid's rule between price falls and rises
    "shade": "#1F2A3A",  # the entered grid column
    "red": "#EF6B63",  # an added cost
    "green": "#5CC98A",  # a saving
    "amber": "#F2CC60",  # data labels and the stale warning
}
POINT_COLOUR = COLOURS["text"]
RULE_COLOURS = [COLOURS["muted"], COLOURS["text"], COLOURS["muted"]]  # min, median, max

USD = "USD/GPU-h"
PUBLISHED = "Published price"
OFFER = "Offer price"
# Display formats (D9): Streamlit NumberColumn formats, by column name.
FORMATS = {
    USD: "%.4f",
    PUBLISHED: "plain",  # the full stored number, as published
    OFFER: "plain",
    "Minimum": "%.4f",
    "Median": "%.4f",
    "Maximum": "%.4f",
}


class Problem(Exception):
    """The page cannot show figures; the message says why and what to run, under a
    status word (phase-7 D41)."""

    def __init__(self, message: str, word: str) -> None:
        super().__init__(message)
        self.word = word


@dataclass(frozen=True)
class Dataset:
    label: str
    path: Path


def datasets(known: Sequence[tuple[str, Path]] = KNOWN) -> list[Dataset]:
    """The known databases that exist, live first, so the first one is the default."""
    return [Dataset(label, path) for label, path in known if path.is_file()]


def open_read_only(path: Path) -> duckdb.DuckDBPyConnection:
    """A read-only connection; Problem when the file is missing or held by a writer."""
    if not path.is_file():
        raise Problem(NO_DATABASE, NO_DATABASE_WORD)
    try:
        return db.connect(path, read_only=True)
    except duckdb.IOException as error:
        if any(text in str(error) for text in LOCK_ERRORS):
            raise Problem(IN_USE, "IN USE") from error
        raise Problem(f"Cannot open {path}: {error}", "CANNOT OPEN") from error
    except duckdb.Error as error:
        raise Problem(f"Cannot open {path}: {error}", "CANNOT OPEN") from error


@dataclass
class SourceView:
    """What the page shows for one source, read before the connection closes."""

    source: str
    report: quality.QualityReport
    labels: tuple[str, ...] = ()  # data labels of the source's succeeded snapshots
    stale_after_days: int | None = None
    region_groups: list[RegionGroup] = field(default_factory=list)
    summaries: list[CrossRegionSummary] = field(default_factory=list)
    region_names: dict[str, str] = field(default_factory=dict)  # code -> stored name

    @property
    def snapshot(self) -> Snapshot | None:
        return self.report.snapshot

    @property
    def mixed(self) -> bool:
        return len(self.labels) > 1

    @property
    def withheld(self) -> bool:
        """True when the latest snapshot is not fully normalized (D17)."""
        return self.report.not_normalized > 0


def load(
    connection: duckdb.DuckDBPyConnection,
    path: Path,
    source: str,
    as_of: datetime,
    rule_version: str = rules.RULE_VERSION,
    with_groups: bool = True,
) -> SourceView:
    """One source's quality report and, when asked and not withheld, its groups.

    The region groups are built once and shared with the quality report.
    """
    try:
        ordered = groups.snapshots(connection, source)
    except duckdb.CatalogException as error:  # a database file with no tables yet
        raise Problem(EMPTY.format(path=path), "NO TABLES") from error
    labels = tuple(sorted({s.data_label for s in ordered}))
    if not ordered:
        report = quality.build(connection, source, as_of, rule_version)
        return SourceView(source, report, labels)
    try:
        params = rules.stored(connection, rule_version)
    except KeyError as error:  # no rule set stored yet
        raise Problem(NO_RULES.format(path=path), "NO RULE SET") from error
    found = (
        groups.region_groups(connection, ordered[-1], rule_version)
        if with_groups
        else None
    )
    report = quality.build(connection, source, as_of, rule_version, found)
    view = SourceView(source, report, labels, int(params["stale_after_days"]))
    if found is None or view.withheld:
        return view
    view.region_groups = found
    if source == AZURE:
        view.summaries = groups.cross_region(found, params["thin_below_regions"])
        view.region_names = region_names(connection, ordered[-1].run_id)
    return view


def region_names(connection: duckdb.DuckDBPyConnection, run_id: str) -> dict[str, str]:
    """Each Azure region code's stored `location` name in the shown snapshot's run.
    Codes without one, or with a blank one, are absent, so the page shows the code
    (phase-7 D30, D50). Nothing is filled in."""
    rows = connection.execute(
        "SELECT a.arm_region_name, min(a.location) FROM azure_retail_price a"
        " JOIN price_observation p ON p.source = a.source AND p.item_key = a.item_key"
        " AND p.retrieved_at = a.retrieved_at"
        " JOIN raw_response rr ON rr.response_id = p.response_id"
        " WHERE rr.run_id = ? AND trim(a.location) <> ''"
        " GROUP BY a.arm_region_name",
        [run_id],
    ).fetchall()
    return {str(code): str(name) for code, name in rows}


def load_all(
    connection: duckdb.DuckDBPyConnection,
    path: Path,
    as_of: datetime,
    selected: str | None = None,
) -> dict[str, SourceView]:
    """Both sources' reports, with groups for the selected source (all when None)."""
    return {
        source: load(
            connection,
            path,
            source,
            as_of,
            with_groups=selected is None or source == selected,
        )
        for source in CATALOGUE
    }


def catalogue_name(source: str, view: SourceView | None) -> str:
    """The catalogue's name, with " (synthetic)" when its latest succeeded snapshot is
    labelled synthetic. Read from the run, never the file, and never "(live)" (D33)."""
    name = CATALOGUE[source]
    snapshot = None if view is None else view.snapshot
    if snapshot is not None and snapshot.data_label == synthetic.LABEL:
        return f"{name} (synthetic)"
    return name


# --- filters (D1): cascading, offering only groups that exist ---


def variants(found: Sequence[RegionGroup]) -> list[str]:
    return sorted({g.key.variant for g in found})


def gpu_counts(found: Sequence[RegionGroup], variant: str) -> list[int]:
    return sorted({g.key.gpu_count for g in found if g.key.variant == variant})


def rental_types(found: Sequence[RegionGroup], variant: str, count: int) -> list[str]:
    return sorted(
        {
            g.key.rental_type
            for g in found
            if (g.key.variant, g.key.gpu_count) == (variant, count)
        }
    )


def regions(
    found: Sequence[RegionGroup], variant: str, count: int, rental: str
) -> list[str]:
    return sorted(
        {
            g.key.region
            for g in found
            if (g.key.variant, g.key.gpu_count, g.key.rental_type)
            == (variant, count, rental)
        }
    )


def find_group(found: Sequence[RegionGroup], key: GroupKey) -> RegionGroup | None:
    return next((g for g in found if g.key == key), None)


def find_summary(
    found: Sequence[CrossRegionSummary], variant: str, count: int, rental: str
) -> CrossRegionSummary | None:
    return next(
        (
            s
            for s in found
            if (s.variant, s.gpu_count, s.rental_type) == (variant, count, rental)
        ),
        None,
    )


# --- text (D6, D9, D24) ---


def utc(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def gpus(count: int) -> str:
    return f"{count} GPU" if count == 1 else f"{count} GPUs"


def rental_name(rental: str) -> str:
    return RENTAL_NAMES.get(rental, rental)


def key_text(key: GroupKey) -> str:
    return (
        f"{key.variant} · {gpus(key.gpu_count)} · {key.region}"
        f" · {rental_name(key.rental_type)}"
    )


def snapshot_text(snapshot: Snapshot) -> str:
    return (
        f"snapshot {utc(snapshot.started_at)}, run {snapshot.run_id}"
        f" · data label: {snapshot.data_label}"
    )


def plain_caption(snapshot: Snapshot) -> str:
    """The snapshot, its run and its label, as a sentence."""
    return snapshot_text(snapshot)[0].upper() + snapshot_text(snapshot)[1:]


def crosses_regions(summary: CrossRegionSummary) -> str:
    return (
        f"Crosses regions: {summary.variant} · {gpus(summary.gpu_count)}"
        f" · {rental_name(summary.rental_type)}"
    )


def group_sources(
    view: SourceView, group: RegionGroup, summary: CrossRegionSummary | None
) -> list[str]:
    """What the Comparable groups tab's Sources section says, before its source
    records (phase-7 D9, D27): the keys, the snapshot and the explanatory notes."""
    lines = [f"Group: {key_text(group.key)}", plain_caption(group.snapshot)]
    if view.source == AZURE and len(group.members) > 1:
        lines.append(MULTI_SIZE)
    if summary is not None:
        lines += [crosses_regions(summary), LOWEST]
    return lines


def browser_sources(snapshot: Snapshot) -> list[str]:
    return [plain_caption(snapshot), BROWSER]


def stamp(moment: datetime) -> str:
    """A time for the status line: "12 OCT 2026 09:00 UTC"."""
    return moment.astimezone(UTC).strftime("%d %b %Y %H:%M").upper() + " UTC"


def data_label(snapshot: Snapshot) -> str:
    """What the data is, from the run's label: synthetic, or published list prices."""
    if snapshot.data_label == synthetic.LABEL:
        return DATA_SYNTHETIC
    return DATA_PUBLISHED


def status_line(
    snapshot: Snapshot | None,
    stale: bool | None,
    as_of: datetime,
    stale_after_days: int | None,
) -> str:
    """The one line over every tab, as markdown: the title, the data label in amber,
    the snapshot's time, and STALE in amber when it applies (phase-7 D6, D9, D42)."""
    parts = [f"**{TITLE_LINE}**"]
    if snapshot is None:
        return parts[0]
    parts += [
        f":orange[**{data_label(snapshot)}**]",
        f"AS OF {stamp(snapshot.started_at)}",
    ]
    if stale:
        when = STALE_LINE.format(days=stale_after_days, when=stamp(as_of))
        parts.append(f":orange[**{when}**]")
    return " · ".join(parts)


def pricing_name(rental: str) -> str:
    return PRICING_NAMES.get(rental, rental)


def region_name(view: SourceView, code: str) -> str:
    """A region's stored name, or its code when none is stored (phase-7 D30)."""
    return view.region_names.get(code, code)


def region_choices(
    view: SourceView, variant: str, count: int, rental: str
) -> list[str]:
    """The region codes the filters offer, sorted by the name shown for each."""
    codes = regions(view.region_groups, variant, count, rental)
    return sorted(codes, key=lambda code: (placed(region_name(view, code)), code))


def placed(name: str) -> str:
    """The sort key for a shown region: its name, ignoring case, so a code sorts in."""
    return name.casefold()


def short_size(name: str) -> str:
    """An Azure size for a key figure: no `Standard_` prefix, underscores as spaces
    (D46). Any other name, such as a marketplace offer ID, is shown as stored (D50)."""
    if not name.startswith("Standard_"):
        return name
    return name.removeprefix("Standard_").replace("_", " ")


def labels_text(labels: Sequence[str]) -> str:
    """Tags as muted text at body size. Not inline code, which Streamlit fixes at
    0.75em, 10.5 px here, below the 12 px floor (phase-7 D49)."""
    return f":gray[{' · '.join(labels)}]"


# --- tables (D10, D23) ---


def members_frame(group: RegionGroup) -> pd.DataFrame:
    """One row per member: name, USD/GPU-hour, its source price and retrieval time."""
    marketplace = group.snapshot.source == MARKETPLACE
    rows = []
    for m in group.members:
        row: dict[str, object] = {"Offer" if marketplace else "Size": m.name}
        if marketplace:
            row["Machine"] = m.machine_id
        row[USD] = m.usd_per_gpu_hour
        row[OFFER if marketplace else PUBLISHED] = m.price
        row["Currency"] = m.currency
        row["Unit"] = m.price_unit
        row["Retrieved"] = utc(m.retrieved_at)
        if marketplace:
            row["Flags"] = ", ".join(m.flags)
        rows.append(row)
    return pd.DataFrame(rows)


def provenance_frame(group: RegionGroup) -> pd.DataFrame:
    """Where each member's price was recorded (PROJECT §3)."""
    return pd.DataFrame(
        [
            {
                "Name": m.name,
                "Item key": m.item_key,
                "Run ID": m.run_id,
                "Data label": group.snapshot.data_label,
                "Raw response": m.file_path,
                "Seq": m.seq,
                "SHA-256": m.sha256,
                "Retrieved (UTC)": m.retrieved_at.astimezone(UTC).isoformat(),
            }
            for m in group.members
        ]
    )


def summary_frame(
    summary: CrossRegionSummary, names: Mapping[str, str] | None = None
) -> pd.DataFrame:
    """Each region's lowest listed size, by the region's shown name (phase-7 D48).

    `names` maps region codes to stored names; a code without one is shown as is.
    """
    shown = names or {}
    ordered = sorted(
        summary.contributions, key=lambda c: placed(shown.get(c.region, c.region))
    )
    return pd.DataFrame(
        [
            {
                "Region": shown.get(c.region, c.region),
                "Lowest listed size": c.member.name,
                USD: c.member.usd_per_gpu_hour,
            }
            for c in ordered
        ]
    )


def stats_frame(stats: Stats, counted: str) -> pd.DataFrame:
    """Count, minimum, median and maximum; `counted` names what was counted."""
    return pd.DataFrame(
        [
            {
                counted: stats.count,
                "Minimum": stats.minimum,
                "Median": stats.median,
                "Maximum": stats.maximum,
            }
        ]
    )


def browser_frame(
    found: Sequence[RegionGroup],
    variant: str | None = None,
    names: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Group keys with member counts and labels, in key order, with no prices (D4).

    Regions show their stored names and sort by them (phase-7 D48). A marketplace group
    counts its distinct machines and its offers, so a `thin` label (fewer than 5
    machines) matches the count beside it.
    """
    shown = names or {}
    marketplace = any(g.snapshot.source == MARKETPLACE for g in found)
    counts = ["Machines", "Offers"] if marketplace else ["Members"]
    rows = []
    for g in sorted(
        found,
        key=lambda g: (
            g.key.variant,
            g.key.gpu_count,
            placed(shown.get(g.key.region, g.key.region)),
            g.key.rental_type,
        ),
    ):
        if variant is not None and g.key.variant != variant:
            continue
        row: dict[str, object] = {
            "Variant": g.key.variant,
            "GPUs": g.key.gpu_count,
            "Region": shown.get(g.key.region, g.key.region),
            "Rental type": rental_name(g.key.rental_type),
        }
        if marketplace:
            row["Machines"] = g.stats.count if g.stats is not None else 0
            row["Offers"] = len(g.members)
        else:
            row["Members"] = len(g.members)
        row["Labels"] = ", ".join(g.labels)
        rows.append(row)
    columns = ["Variant", "GPUs", "Region", "Rental type", *counts, "Labels"]
    return pd.DataFrame(rows, columns=columns)


# --- chart (D5) ---


def summary_chart(
    summary: CrossRegionSummary, names: Mapping[str, str] | None = None
) -> alt.LayerChart:
    """Each region's lowest listed USD/GPU-hour as a point, with min, median and max.

    Only regions with a listing are plotted, and no line joins the points.
    """
    points = summary_frame(summary, names)
    marks = pd.DataFrame(
        {
            "Statistic": ["minimum", MEDIAN, "maximum"],
            USD: [summary.stats.minimum, summary.stats.median, summary.stats.maximum],
        }
    )
    x = alt.X(
        f"{USD}:Q",
        title=USD,
        scale=alt.Scale(zero=False),
        axis=alt.Axis(format=".4~f", tickCount=8),
    )
    dots = (
        alt.Chart(points)
        .mark_point(filled=True, size=90, color=POINT_COLOUR)
        .encode(
            x=x,
            y=alt.Y("Region:N", sort=None, title=None),
            tooltip=[
                "Region:N",
                "Lowest listed size:N",
                alt.Tooltip(f"{USD}:Q", format=".4f"),
            ],
        )
    )
    lines = (
        alt.Chart(marks)
        .mark_rule(strokeDash=[4, 3], strokeWidth=2)
        .encode(
            x=f"{USD}:Q",
            color=alt.Color(
                "Statistic:N",
                sort=None,
                title=None,
                scale=alt.Scale(domain=list(marks["Statistic"]), range=RULE_COLOURS),
                legend=alt.Legend(orient="bottom", labelLimit=0),
            ),
            tooltip=["Statistic:N", alt.Tooltip(f"{USD}:Q", format=".4f")],
        )
    )
    return alt.LayerChart(layer=[dots, lines])


# --- data-quality panel (D25) ---


@dataclass(frozen=True, eq=False)  # DataFrames have no truth value to compare
class Panel:
    source: str
    snapshot: Snapshot | None
    caption: str
    checks: pd.DataFrame  # the five headline checks plus not normalized
    unmapped_sizes: list[str]
    secondary: pd.DataFrame


def _table(rows: list[tuple[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(
        [(name, str(value)) for name, value in rows], columns=["Check", "Count"]
    )


def panel(view: SourceView, as_of: datetime) -> Panel:
    """Counts only, from the quality report as of the injected time."""
    report = view.report
    name = catalogue_name(view.source, view)
    if report.snapshot is None:
        empty = _table([])
        return Panel(view.source, None, f"{name} · {NO_SNAPSHOT}", empty, [], empty)
    azure = view.source == AZURE
    unmapped_reason = "unmapped_sku" if azure else "unmapped_gpu_name"
    unmapped_rows = report.by_status.get(unmapped_reason, 0)
    days = view.stale_after_days
    checks = _table(
        [
            (
                "Missing fields among compared rows",
                ", ".join(f"{k} {v}" for k, v in report.missing_fields.items()),
            ),
            ("Observations not normalized", report.not_normalized),
            (
                "Duplicates",
                ", ".join(
                    f"{k} {quality.shown(v)}" for k, v in report.duplicates.items()
                ),
            ),
            (
                "Stale",
                f"{'yes' if report.stale else 'no'} (latest snapshot older than"
                f" {days} days as of {utc(as_of)})",
            ),
            (
                "Thin " + ("cross-region summaries" if azure else "groups"),
                report.thin,
            ),
            (
                "Unmapped",
                (
                    f"sizes not in the map {len(report.unmapped_sizes)}; "
                    if azure
                    else ""
                )
                + f"rows excluded as {unmapped_reason} {unmapped_rows}",
            ),
        ]
    )
    secondary_rows: list[tuple[str, object]] = [("Observations", report.observations)]
    secondary_rows += [(f"Rows: {k}", v) for k, v in report.by_status.items()]
    secondary_rows += [
        ("Rejected by the collector", quality.shown(report.rejected_total)),
        *((f"Rejected: {k}", v) for k, v in report.rejected.items()),
        ("Out of scope", quality.shown(report.out_of_scope)),
        ("Region groups", report.region_groups),
    ]
    if azure:
        secondary_rows += [
            ("os_ambiguous", report.os_ambiguous),
            ("Single list price groups", report.single_price_groups),
            ("Cross-region summaries", report.summaries),
        ]
    changes = "no previous snapshot" if report.changes is None else report.changes
    secondary_rows += [
        ("Changes since the previous snapshot", changes),
        ("Absent once (unconfirmed)", report.absent_once),
        ("Not listed", report.not_listed),
    ]
    caption = (
        f"{name} · {snapshot_text(report.snapshot)} · as of {utc(as_of)} · counts only"
    )
    return Panel(
        view.source,
        report.snapshot,
        caption,
        checks,
        list(report.unmapped_sizes),
        _table(secondary_rows),
    )


# --- workload cost (phase-5-calculator D3, D8, D10, D16, D18, D19, D21, D27;
# phase-7 D6, D7, D9, D27, D32-D39) ---

WORKLOAD_INTRO = (
    "How the cost of one workload would change under labelled price changes. These are"
    " scenario calculations from published list prices, not forecasts, market prices or"
    " what a customer would pay."
)
MARKETPLACE_NOTE = "Workload cost uses the Azure VMs catalogue."
WITHHELD_WORKLOAD = (
    "The workload figures are withheld until this snapshot is normalized."
)
WITHHELD_GROUPS = "The group views are withheld until this snapshot is normalized."
HOURS_HELP = "720 h = 30 days; Microsoft's pricing calculator uses 730 h for a month."
HOURS_NOTE = "Costs are for the hours entered, never converted to a month."
STORAGE_ENTERED = (
    "Storage: USD {amount} entered by you for this period, not an Azure list price and"
    " not checked against Azure disk prices. The total adds it; every other exclusion"
    " still applies."
)
STORAGE_NONE = "Storage not included."
BILLING = (
    "Assumes each VM is allocated for exactly the hours entered. Azure bills full"
    " minutes while a VM is allocated, including Stopped (allocated); only Stopped"
    " (deallocated) ends compute billing. Every VM has an OS disk, billed as storage"
    " and not in the GPU price; add it under storage."
)
SPOT_LINE = (
    "Spot: Azure can evict these VMs at any time with 30 seconds' notice and gives no"
    " SLA, and the Spot price is variable. This figure assumes every hour entered runs"
    " at this listed Spot price; evicted hours may not be delivered, and an evicted VM"
    " that is deallocated still bills for its disks."
)
ABOVE_PAYG = (
    "Above this size's pay-as-you-go list price (USD {price}/GPU-hour). With max price"
    " −1 Azure charges at most the pay-as-you-go price; with a lower max price the VM"
    " is evicted. This row shows the scenario's arithmetic, not what Azure would bill."
    " See the 'Spot → PAYG *' row."
)
CROSSES_RENTAL = "crosses rental types (Spot → pay-as-you-go)"
CHECK_FAILED = "The independent check failed: {checks}. No figures are shown."
BUDGET_HINT = (
    "Enter a contingency to see the price rise per GPU-hour that would use it up (a"
    " reverse scenario calculation)."
)
LOWEST_MEMBER = "lowest listed in this group"
# The custom move's unit switch and the input label each unit gets (D34).
CUSTOM_KINDS = {"%": scenarios.PERCENT, "USD/GPU-h": scenarios.USD}
CUSTOM_LABELS = {scenarios.PERCENT: "Custom, %", scenarios.USD: "Custom, USD/GPU-h"}
# Key-figure labels (D6, D33).
COST_LABEL = "Cost, USD"
VMS_LABEL = "VMs"
GPU_HOURS_LABEL = "GPUs × h"
HEADROOM_LABEL = "Headroom, USD/GPU-h"
# The scenario grid (D7, D25, D35, D36, D38).
GRID_TITLE = "SCENARIO GRID"
# Labels every scenario figure on the tab, Headroom included (Phase 8 D30).
GRID_MARK = "NOT A FORECAST"
EXCLUDES = "Excludes "  # how the stored exclusions text opens (groups-v1)
EXCL_TAG = "EXCL."
GRID_CORNER = "Δ price \\ GPUs"
FALLBACK_LABEL = "Spot → PAYG *"
MARKED = " †"
# Footer clauses, each only when it applies (D9, D35, D36, D44).
STORAGE_CLAUSE = "Total includes USD {amount} storage entered by you."
CROSSING_CLAUSE = (
    "* Crosses rental types (Spot → pay-as-you-go): same size, same region."
)
NO_PAYG_CLAUSE = "Not computed: no pay-as-you-go listing for this size in this region."
ZERO_CLAUSE = "Not computed: the price would be zero or below."
MARK_CLAUSE = (
    "† Above this size's pay-as-you-go list price (USD {price}/GPU-h): the"
    " arithmetic, not what Azure would bill."
)


def money(value: float) -> str:
    return f"USD {value:,.2f}"


def per_gpu_hour(value: float) -> str:
    return f"USD {value:.4f}/GPU-hour"


def plain(value: float, places: int) -> str:
    """Up to `places` decimals without trailing zeros, or 3 significant digits when that
    would show a non-zero value as zero."""
    text = f"{value:,.{places}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("0", "-0") and value != 0:
        return f"{value:.3g}"
    return text


def at_least_cents(value: float) -> str:
    """A published price with every stored decimal, and never fewer than two (D32)."""
    text = plain(value, 10)
    if "e" in text:
        return text
    whole, _, cents = text.partition(".")
    return f"{whole}.{cents.ljust(2, '0')}"


def fixed(value: float, places: int) -> str:
    """Exactly `places` decimals, or 3 significant digits when that would show a
    non-zero value as zero."""
    text = f"{value:,.{places}f}"
    if float(text.replace(",", "")) == 0 and value != 0:
        return f"{value:.3g}"
    return text


def hours_text(hours: float) -> str:
    return plain(hours, 4) + " h"


def size_key(key: GroupKey) -> str:
    """The size choice's widget key: one per group, so each keeps its pick (D27)."""
    return "|".join(
        ["size", key.variant, str(key.gpu_count), key.region, key.rental_type]
    )


def sizes(group: RegionGroup) -> list[str]:
    """Member sizes, lowest listed first, so the first is the default."""
    return [m.name for m in sorted(group.members, key=groups.price_order)]


def default_gpus(gpus_per_vm: int) -> int:
    """32 when it makes whole VMs (1, 2, 4 or 8 GPUs per VM), else one VM (D26)."""
    preferred = calculator.DEFAULT_GPUS
    if gpus_per_vm <= preferred and preferred % gpus_per_vm == 0:
        return preferred
    return gpus_per_vm


def start_text(begin: Start) -> str:
    member = begin.member
    lowest = f" ({LOWEST_MEMBER})" if begin.lowest else ""
    return (
        f"Starting price: {per_gpu_hour(begin.usd_per_gpu_hour)} for {member.name}"
        f"{lowest}, from its published price {member.currency} {member.price} per VM"
        f" per {member.price_unit} ({gpus(begin.gpus_per_vm)} per VM) · item key"
        f" {member.item_key} · run {member.run_id}"
    )


def storage_line(work: Workload) -> str:
    if work.storage is None:
        return STORAGE_NONE
    return STORAGE_ENTERED.format(amount=f"{work.storage:,.2f}")


def price_label(rental: str) -> str:
    """The starting price's label, naming the rental type: "USD/GPU-h · PAYG"."""
    return f"USD/GPU-h · {PRICING_SHORT.get(rental, rental.upper())}"


KeyFigure = tuple[str, str]  # label, value


def workload_figures(
    begin: Start, result: Result | None, budget_entered: bool
) -> list[KeyFigure]:
    """The Workload key figures; each shows "—" until the check passes (D6, D33)."""
    labels = [
        COST_LABEL,
        price_label(begin.key.rental_type),
        VMS_LABEL,
        GPU_HOURS_LABEL,
    ]
    if result is None:
        if budget_entered:
            labels.append(HEADROOM_LABEL)
        return [(label, DASH) for label in labels]
    work, cost = result.workload, result.cost
    values = [
        f"{cost.total:,.2f}",
        fixed(begin.usd_per_gpu_hour, 4),
        f"{cost.vms:,} × {short_size(begin.member.name)}",
        f"{work.gpus:,} × {plain(work.hours, 4)}",
    ]
    room = result.headroom
    if room is not None:
        labels.append(HEADROOM_LABEL)
        mark = MARKED if room.above_payg is not None else ""
        values.append(f"+{fixed(room.rise, 4)} ({fixed(room.rise_pct, 1)}%){mark}")
    return list(zip(labels, values, strict=True))


def grid_cell(value: float) -> str:
    """A change in cost in whole USD with its sign, or 3 significant digits when a
    non-zero value would round to 0 (D32), always positional: never "6e-09"
    (Phase 8 D14)."""
    if value == 0:
        return "0"
    exact = Decimal(repr(abs(value)))
    # Half up, so 2.5 shows 3 as 3.5 shows 4 (Python's round() goes to even, D50).
    whole = int(exact.quantize(Decimal(1), ROUND_HALF_UP))
    if whole:
        text = f"{whole:,}"
    else:
        step = Decimal(1).scaleb(exact.adjusted() - 2)  # the third significant digit
        text = format(exact.quantize(step, ROUND_HALF_UP).normalize(), "f")
    return ("+" if value > 0 else "−") + text


def grid_label(row: calculator.LadderRow) -> str:
    label = FALLBACK_LABEL if row.id == calculator.FALLBACK else row.label
    return label + (MARKED if row.above_payg is not None else "")


def grid_frame(ladder: calculator.Ladder) -> pd.DataFrame:
    """The scenario grid as display text: one row per ladder row, one column per GPU
    count; a refused row shows "n/a" in every cell (D7, D38)."""
    columns = [GRID_CORNER, *(str(n) for n in ladder.columns)]
    rows = [
        [
            grid_label(row),
            *(
                [grid_cell(c) for c in row.cells]
                if row.cells is not None
                else [NA] * len(ladder.columns)
            ),
        ]
        for row in ladder.rows
    ]
    return pd.DataFrame(rows, columns=columns)


def _cell_colour(row: calculator.LadderRow, index: int) -> str:
    if row.cells is None:
        return COLOURS["muted"]
    value = row.cells[index]
    if value > 0:
        return COLOURS["red"]
    if value < 0:
        return COLOURS["green"]
    return COLOURS["text"]


def grid_styles(
    ladder: calculator.Ladder, columns: pd.Index[str] | None = None
) -> pd.DataFrame:
    """CSS for each grid cell: colour by sign, the entered column shaded and bold, a
    rule above price rises and above the flat and extra rows (D7, D10, D16). The rules
    follow each row's kind and sign, not one ladder's step IDs (D50)."""
    extras = (calculator.FALLBACK, calculator.CUSTOM)
    presets = [row for row in ladder.rows if row.id not in extras]
    rise = next(
        (
            r.id
            for r in presets
            if r.kind == scenarios.PERCENT and (r.magnitude or 0) > 0
        ),
        None,
    )
    flat = next((r.id for r in presets if r.kind == scenarios.USD), None)
    extra = next((r.id for r in ladder.rows if r.id in extras), None)
    cell = grid_cell_css(len(ladder.columns))
    styles = []
    for row in ladder.rows:
        border = ""
        if row.id == rise:
            border = f"border-top: 2px solid {COLOURS['zero']};"
        elif row.id in (flat, extra):
            border = f"border-top: 1px solid {COLOURS['border']};"
        line = [f"color: {COLOURS['muted']}; {LABEL_CELL} {border}"]
        for index, column in enumerate(ladder.columns):
            css = f"color: {_cell_colour(row, index)}; {cell} {border}"
            if column == ladder.entered:
                css += f" background-color: {COLOURS['shade']}; font-weight: 700;"
            line.append(css)
        styles.append(line)
    shown = grid_frame(ladder).columns if columns is None else columns
    return pd.DataFrame(styles, columns=shown)


# Numbers right-aligned, labels left (phase-7 D7). The minimum widths set each table's
# width: the grid fills mock v3's 950 px column and COST its 540 px (14 px rem, D49).
LABEL_CELL = "text-align: left !important; min-width: 10rem;"
GRID_NUMBERS = 57.5  # rem the GPU columns share: 10rem + 57.5rem is 945 px (D49, D50)
COST_CELL = "text-align: right !important; min-width: 9.5rem;"


def grid_cell_css(count: int) -> str:
    """A grid number cell's CSS: the GPU columns share one width, so a sixth column for
    an entered count keeps the grid inside its column (D50)."""
    return f"text-align: right !important; min-width: {GRID_NUMBERS / count:.2f}rem;"


_HEADERS: list[CSSDict] = [
    {"selector": "th", "props": [("text-align", "right !important")]},
    {"selector": "th.col0", "props": [("text-align", "left !important")]},
]


def grid(ladder: calculator.Ladder) -> Styler:
    """The grid for `st.table`; Styler styles stay scoped to the table (D16)."""
    frame = grid_frame(ladder)
    styles = grid_styles(ladder, frame.columns)
    entered = 1 + ladder.columns.index(ladder.entered)
    return frame.style.apply(lambda _: styles, axis=None).set_table_styles(
        [
            *_HEADERS,
            {
                "selector": f"th.col{entered}",
                "props": [
                    ("color", COLOURS["accent"]),
                    ("font-weight", "700"),
                    ("background-color", COLOURS["shade"]),
                ],
            },
        ]
    )


def grid_title(work: Workload) -> str:
    return (
        f":gray[**{GRID_TITLE}** ·] **Δ cost, USD · {hours_text(work.hours)}**"
        f" :gray[· **{GRID_MARK}**]"
    )


def exclusions_tag(text: str) -> str:
    """The stored exclusions sentence as one tag line: "EXCL. " and every item, in
    order, joined by " · " (Phase 8 D30). Text of another shape is shown whole, so
    no exclusion is ever dropped."""
    if not (text.startswith(EXCLUDES) and text.endswith(".")):
        return text
    items = text.removeprefix(EXCLUDES).removesuffix(".").split(", ")
    return f"{EXCL_TAG} " + " · ".join(items)


def footer(result: Result) -> list[str]:
    """Under the grid, one line each: the exclusions tag line, then each clause that
    applies, its mark first (D9, D35, D36, D44, D49; Phase 8 D30). The grid title
    carries "NOT A FORECAST"."""
    lines = [exclusions_tag(result.start.group.exclusions)]
    if result.workload.storage is not None:
        lines.append(STORAGE_CLAUSE.format(amount=f"{result.workload.storage:,.2f}"))
    rows = {row.id: row for row in result.ladder.rows}
    fallback = rows.get(calculator.FALLBACK)
    if fallback is not None:
        crossing = CROSSING_CLAUSE
        if not fallback.computed:
            crossing += f" {NO_PAYG_CLAUSE}"
        lines.append(crossing)
    marks = [row.above_payg for row in result.ladder.rows if row.above_payg is not None]
    if result.headroom is not None and result.headroom.above_payg is not None:
        marks.append(result.headroom.above_payg)
    if marks:
        lines.append(MARK_CLAUSE.format(price=f"{marks[0]:.4f}"))
    custom = rows.get(calculator.CUSTOM)
    if custom is not None and not custom.computed:
        lines.append(ZERO_CLAUSE)
    return lines


def footer_text(result: Result) -> str:
    """The footer as markdown: muted lines joined by hard line breaks."""
    return "  \n".join(f":gray[{line}]" for line in footer(result))


def cost_table(result: Result) -> pd.DataFrame:
    """Compute, storage and total for the hours entered, as display text (D6)."""
    begin, work, cost = result.start, result.workload, result.cost
    price = begin.member.price
    published = "" if price is None else at_least_cents(price)
    storage = DASH if cost.storage is None else f"{cost.storage:,.2f}"
    return pd.DataFrame(
        [
            [
                "Compute",
                published,
                plain(cost.vms * work.hours, 4),
                f"{cost.compute:,.2f}",
            ],
            ["Storage", "", "", storage],
            ["Total", "", "", f"{cost.total:,.2f}"],
        ],
        columns=["", "USD/VM-h", "VM-h", "USD"],
    )


def cost_styles(result: Result) -> Styler:
    frame = cost_table(result)
    total = f"font-weight: 700; border-top: 1px solid {COLOURS['border']};"
    empty = f"color: {COLOURS['muted']};"
    storage = empty if result.cost.storage is None else ""
    rows = [[""] * 4, ["", "", "", storage], [total] * 4]
    styles = pd.DataFrame(
        [[LABEL_CELL + row[0], *(COST_CELL + css for css in row[1:])] for row in rows],
        columns=frame.columns,
    )
    return frame.style.apply(lambda _: styles, axis=None).set_table_styles(_HEADERS)


def headroom_text(result: Result) -> str | None:
    """The reverse calculation in words (phase-5 D9), or None without a budget. The
    page shows it in Sources (phase-7 D39)."""
    room = result.headroom
    if room is None:
        return None
    work = result.workload
    text = (
        f"A rise of USD {fixed(room.rise, 4)} per GPU-hour ({fixed(room.rise_pct, 1)}%"
        f" of starting price) would use up {money(room.budget)} over {work.gpus:,} GPUs"
        f" × {hours_text(work.hours)}. Storage unchanged. {scenarios.NOT_A_FORECAST}."
    )
    if room.above_payg is not None:
        text += " " + ABOVE_PAYG.format(price=f"{room.above_payg:.4f}")
    return text


def workload_sources(group: RegionGroup, result: Result | None) -> list[str]:
    """What the Workload tab's Sources section says, before its source records (D9).

    Without a checked result it names the group, snapshot and terms, and no price.
    """
    lines = [f"Group: {key_text(group.key)}"]
    if result is not None and result.payg_key is not None:
        where = (
            " (not listed in this snapshot)"
            if result.payg is None
            else f" ({result.payg.name}, item key {result.payg.item_key})"
        )
        lines.append(
            f"Spot → PAYG row {CROSSES_RENTAL}: {key_text(group.key)}"
            f" → {key_text(result.payg_key)}{where}"
        )
    lines.append(plain_caption(group.snapshot))
    lines.append(
        f"{scenarios.LADDER_VERSION} and {scenarios.VERSION}: {scenarios.JUDGEMENT}"
    )
    if len(group.members) > 1:  # the tab offers a Size choice
        lines.append(MULTI_SIZE)
    if result is not None:
        lines.append(start_text(result.start))
        lines.append(storage_line(result.workload))
    lines += [BILLING, HOURS_NOTE, HOURS_HELP]
    if group.key.rental_type == calculator.SPOT:
        lines.append(SPOT_LINE)
    if result is not None:
        marks = [r.above_payg for r in result.ladder.rows if r.above_payg is not None]
        if marks:
            lines.append(ABOVE_PAYG.format(price=f"{marks[0]:.4f}"))
        room = headroom_text(result)
        if room is not None:
            lines.append(room)
    lines += [WORKLOAD_INTRO, BUDGET_HINT]
    return lines


def _listed_payg(begin: Start, found: Sequence[RegionGroup]) -> float | None:
    """A Spot start's size on pay-as-you-go: its VM-hour price, looked up apart from
    the calculator so the check does not inherit its lookup."""
    key = begin.key
    if key.rental_type != calculator.SPOT:
        return None
    wanted = GroupKey(key.variant, key.gpu_count, key.region, calculator.ON_DEMAND)
    for group in found:
        if group.key == wanted and group.snapshot.run_id == begin.snapshot.run_id:
            for member in group.members:
                if member.name == begin.member.name:
                    return member.price
    return None


def check(
    begin: Start,
    result: Result,
    work: Workload,
    change: Custom | None,
    limit: float | None,
    found: Sequence[RegionGroup],
) -> list[str]:
    """Run the independent check on what the page would show (D19).

    The inputs come from the page: the member it picked (`begin`), the user's validated
    entries and the stored members. Only the figures come from `result`, so a result
    priced from another member, or one that drops a row or headroom, is caught.
    """
    member = begin.member
    if member.price is None:
        return ["published price missing"]
    inputs = workload_check.Inputs(
        gpus=work.gpus,
        hours=work.hours,
        storage=work.storage,
        item_key=member.item_key,
        vm_price=member.price,
        gpus_per_vm=begin.key.gpu_count,
        spot=begin.key.rental_type == calculator.SPOT,
        payg_vm_price=_listed_payg(begin, found),
        custom=None if change is None else (change.kind, change.magnitude),
        budget=limit,
    )
    room = result.headroom
    figures = workload_check.Figures(
        item_key=result.start.member.item_key,
        start=result.start.usd_per_gpu_hour,
        vms=result.cost.vms,
        compute=result.cost.compute,
        storage=result.cost.storage,
        total=result.cost.total,
        rows=tuple(
            workload_check.RowFigures(
                row.id,
                row.price,
                row.change,
                row.change_pct,
                row.cost,
                row.exposure,
                row.above_payg,
                row.effect,
            )
            for row in result.rows
        ),
        headroom=None if room is None else room.rise,
        headroom_pct=None if room is None else room.rise_pct,
        headroom_above_payg=None if room is None else room.above_payg,
        ladder=workload_check.LadderFigures(
            result.ladder.columns,
            result.ladder.entered,
            tuple(
                workload_check.LadderRowFigures(
                    row.id, row.cells, row.refusal, row.above_payg
                )
                for row in result.ladder.rows
            ),
        ),
    )
    return workload_check.check(inputs, figures)


def group_figures(group: RegionGroup) -> list[KeyFigure]:
    """The Comparable groups key figures: the lowest listed price with its size, and
    the member count (for marketplace groups, machines and offers) (phase-7 D6)."""
    low = groups.lowest(group.members)
    figures = [
        (
            f"Lowest, {price_label(group.key.rental_type)}",
            fixed(low.usd_per_gpu_hour, 4),
        ),
        (
            "Offer" if group.snapshot.source == MARKETPLACE else "Size",
            short_size(low.name),
        ),
    ]
    if group.stats is not None:  # marketplace: one price per machine
        figures += [
            ("Machines", str(group.stats.count)),
            ("Offers", str(len(group.members))),
        ]
    else:
        figures.append(("Members", str(len(group.members))))
    return figures
