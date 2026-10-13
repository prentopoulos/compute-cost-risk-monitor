"""View model for the local Streamlit dashboard (Phase 4 design D3, D9, D10, D13, D17,
D23-D26, D31; phase-5-calculator D8, D10, D16, D18, D19, D21, D27).

Plain Python and pandas with no Streamlit import, so every rule here is tested directly.
It only arranges what Phase 3 code computes (region groups, cross-region summaries,
marketplace groups and the quality report) and what `calculator` computes from them, and
formats values for display. Workload figures pass `workload_check` before they are
shown. Nothing is computed from a rounded value, and nothing is written.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import altair as alt
import duckdb
import pandas as pd

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
from compute_cost_risk_monitor.calculator import Custom, Result, Row, Start, Workload
from compute_cost_risk_monitor.collect import DEFAULT_DB as MONITOR_DB
from compute_cost_risk_monitor.groups import (
    CrossRegionSummary,
    GroupKey,
    RegionGroup,
    Snapshot,
    Stats,
)

TITLE = "Compute Cost & Risk Monitor"
LIVE_DATASET = "Live Azure list prices (local only)"
SYNTHETIC_DATASET = "Synthetic (invented prices)"
KNOWN: tuple[tuple[str, Path], ...] = (
    (LIVE_DATASET, MONITOR_DB),
    (SYNTHETIC_DATASET, synthetic.DEFAULT_DB),
)
AZURE = azure_retail.SOURCE
MARKETPLACE = synthetic.SOURCE
SOURCE_NAMES = {AZURE: "Azure retail list prices", MARKETPLACE: "Synthetic marketplace"}
RENTAL_NAMES = {"on_demand": "pay-as-you-go", "spot": "Spot"}

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
POINT_COLOUR = "#4c78a8"
RULE_COLOURS = ["#9e9e9e", "#f58518", "#9e9e9e"]  # minimum, median, maximum

USD = "USD/GPU-hour"
PUBLISHED = "Published price"
OFFER = "Offer price"
AMOUNT = "Amount (USD)"
CHANGE_USD = "Change (USD/GPU-hour)"
CHANGE_PCT = "Change (% of starting price)"
SCENARIO_USD = "Scenario USD/GPU-hour"
SCENARIO_COST = "Scenario cost (USD)"
EXPOSURE = "Exposure (USD)"
# Display formats (D9; phase-5-calculator D21): Streamlit NumberColumn formats, by
# column name. USD amounts carry thousands separators.
FORMATS = {
    USD: "%.4f",
    PUBLISHED: "plain",  # the full stored number, as published
    OFFER: "plain",
    "Minimum": "%.4f",
    "Median": "%.4f",
    "Maximum": "%.4f",
    AMOUNT: "%,.2f",
    CHANGE_USD: "%.4f",
    CHANGE_PCT: "%.1f",
    SCENARIO_USD: "%.4f",
    SCENARIO_COST: "%,.2f",
    EXPOSURE: "%,.2f",
}


class Problem(Exception):
    """The page cannot show figures; the message says why and what to run."""


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
        raise Problem(NO_DATABASE)
    try:
        return db.connect(path, read_only=True)
    except duckdb.IOException as error:
        if any(text in str(error) for text in LOCK_ERRORS):
            raise Problem(IN_USE) from error
        raise Problem(f"Cannot open {path}: {error}") from error
    except duckdb.Error as error:
        raise Problem(f"Cannot open {path}: {error}") from error


@dataclass
class SourceView:
    """What the page shows for one source, read before the connection closes."""

    source: str
    report: quality.QualityReport
    labels: tuple[str, ...] = ()  # data labels of the source's succeeded snapshots
    stale_after_days: int | None = None
    region_groups: list[RegionGroup] = field(default_factory=list)
    summaries: list[CrossRegionSummary] = field(default_factory=list)

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
        raise Problem(EMPTY.format(path=path)) from error
    labels = tuple(sorted({s.data_label for s in ordered}))
    if not ordered:
        report = quality.build(connection, source, as_of, rule_version)
        return SourceView(source, report, labels)
    try:
        params = rules.stored(connection, rule_version)
    except KeyError as error:  # no rule set stored yet
        raise Problem(NO_RULES.format(path=path)) from error
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
    return view


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
        for source in SOURCE_NAMES
    }


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


def group_caption(group: RegionGroup) -> str:
    return (
        f"Group: {key_text(group.key)} · {snapshot_text(group.snapshot)}"
        f" · {group.exclusions}"
    )


def summary_caption(summary: CrossRegionSummary) -> str:
    where = (
        f"Crosses regions: {summary.variant} · {gpus(summary.gpu_count)}"
        f" · {rental_name(summary.rental_type)}"
    )
    return f"{where} · {snapshot_text(summary.snapshot)} · {summary.exclusions}"


def plain_caption(snapshot: Snapshot) -> str:
    """For tables with no price: the snapshot and its label only."""
    return snapshot_text(snapshot)[0].upper() + snapshot_text(snapshot)[1:]


def framing(
    snapshot: Snapshot, stale: bool | None, as_of: datetime, stale_after_days: int
) -> str:
    """The line under the title saying what the data is (D6)."""
    when = utc(snapshot.started_at)
    if snapshot.data_label == synthetic.LABEL:
        text = (
            "Synthetic data: invented prices for demonstration, not Azure list prices"
            f" · snapshot {when}"
        )
    else:
        text = (
            f"Published Azure retail list prices for GPU VMs · {snapshot.data_label}"
            f" · snapshot {when} · local analysis only"
        )
    if stale:
        text += f" · STALE (older than {stale_after_days} days as of {utc(as_of)})"
    return text


def labels_text(labels: Sequence[str]) -> str:
    return " · ".join(f"`{label}`" for label in labels)


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


def summary_frame(summary: CrossRegionSummary) -> pd.DataFrame:
    """Each region's lowest listed size, by region."""
    return pd.DataFrame(
        [
            {
                "Region": c.region,
                "Lowest listed size": c.member.name,
                USD: c.member.usd_per_gpu_hour,
            }
            for c in summary.contributions
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
    found: Sequence[RegionGroup], variant: str | None = None
) -> pd.DataFrame:
    """Group keys with member counts and labels, in key order, with no prices (D4).

    A marketplace group counts its distinct machines and its offers, so a `thin` label
    (fewer than 5 machines) matches the count beside it.
    """
    marketplace = any(g.snapshot.source == MARKETPLACE for g in found)
    counts = ["Machines", "Offers"] if marketplace else ["Members"]
    rows = []
    for g in sorted(
        found,
        key=lambda g: (g.key.variant, g.key.gpu_count, g.key.region, g.key.rental_type),
    ):
        if variant is not None and g.key.variant != variant:
            continue
        row: dict[str, object] = {
            "Variant": g.key.variant,
            "GPUs": g.key.gpu_count,
            "Region": g.key.region,
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


def summary_chart(summary: CrossRegionSummary) -> alt.LayerChart:
    """Each region's lowest listed USD/GPU-hour as a point, with min, median and max.

    Only regions with a listing are plotted, and no line joins the points.
    """
    points = summary_frame(summary)
    marks = pd.DataFrame(
        {
            "Statistic": ["minimum", MEDIAN, "maximum"],
            USD: [summary.stats.minimum, summary.stats.median, summary.stats.maximum],
        }
    )
    x = alt.X(
        f"{USD}:Q",
        title="USD per GPU-hour",
        scale=alt.Scale(zero=False),
        axis=alt.Axis(format=".4~f"),
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
    name = SOURCE_NAMES[view.source]
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
                ", ".join(f"{k} {v}" for k, v in report.duplicates.items()),
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
        ("Rejected by the collector", sum(report.rejected.values())),
        *((f"Rejected: {k}", v) for k, v in report.rejected.items()),
        ("Out of scope", report.out_of_scope),
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


# --- workload cost (phase-5-calculator D3, D8, D10, D16, D18, D19, D21, D27) ---

WORKLOAD_INTRO = (
    "How the cost of one workload would change under labelled price changes. These are"
    " scenario calculations from published list prices, not forecasts, market prices or"
    " what a customer would pay."
)
MARKETPLACE_NOTE = (
    "The workload calculator uses Azure list-price groups: choose the Azure retail list"
    " prices source. The synthetic marketplace data exercises the data-quality rules."
)
WITHHELD_WORKLOAD = (
    "The workload figures are withheld until this snapshot is normalized."
)
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
    " See 'Spot to pay-as-you-go fallback'."
)
CROSSES_RENTAL = "crosses rental types (Spot → pay-as-you-go)"
CHECK_FAILED = "The independent check failed: {checks}. No figures are shown."
BUDGET_HINT = (
    "Enter a budget to see the price rise per GPU-hour that would use it up (a reverse"
    " scenario calculation)."
)
LOWEST_MEMBER = "lowest listed in this group"
STARTING = "Starting price (listed)"
BASELINE = "baseline"
CUSTOM_KINDS = {
    "% of starting price": scenarios.PERCENT,
    "USD per GPU-hour": scenarios.USD,
}


def money(value: float) -> str:
    return f"USD {value:,.2f}"


def per_gpu_hour(value: float) -> str:
    return f"USD {value:.4f}/GPU-hour"


def hours_text(hours: float) -> str:
    return f"{hours:,.2f}".rstrip("0").rstrip(".") + " h"


def size_key(key: GroupKey) -> str:
    """The size choice's widget key: one per group, so each keeps its pick (D27)."""
    return "|".join(
        ["size", key.variant, str(key.gpu_count), key.region, key.rental_type]
    )


def sizes(group: RegionGroup) -> list[str]:
    """Member sizes, lowest listed first, so the first is the default."""
    ordered = sorted(group.members, key=lambda m: (m.usd_per_gpu_hour, m.name))
    return [m.name for m in ordered]


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


def vms_text(work: Workload, begin: Start) -> str:
    vms = work.gpus // begin.gpus_per_vm
    return (
        f"{work.gpus:,} GPUs = {vms:,} {'VM' if vms == 1 else 'VMs'}"
        f" of {gpus(begin.gpus_per_vm)}"
    )


def storage_line(work: Workload) -> str:
    if work.storage is None:
        return STORAGE_NONE
    return STORAGE_ENTERED.format(amount=f"{work.storage:,.2f}")


def workload_caption(result: Result) -> str:
    """Every workload figure: key, snapshot, label, exclusions and assumptions (D10)."""
    begin = result.start
    parts = [
        f"Group: {key_text(begin.key)}",
        snapshot_text(begin.snapshot),
        begin.group.exclusions,
        storage_line(result.workload),
        BILLING,
        HOURS_NOTE,
    ]
    if begin.spot:
        parts.append(SPOT_LINE)
    return " · ".join(parts)


def scenario_caption(result: Result) -> str:
    """The workload caption plus the scenario set, its label and any crossing."""
    parts = [
        workload_caption(result),
        result.version,
        scenarios.NOT_A_FORECAST,
        scenarios.JUDGEMENT,
    ]
    if result.payg_key is not None:
        missing = " (not listed in this snapshot)" if result.payg is None else ""
        parts.append(
            f"Fallback row {CROSSES_RENTAL}: {key_text(result.start.key)}"
            f" → {key_text(result.payg_key)}{missing}"
        )
    return " · ".join(parts)


def cost_frame(result: Result) -> pd.DataFrame:
    """Compute, storage and total for the hours entered."""
    begin, work, cost = result.start, result.workload, result.cost
    entered = work.storage is not None
    compute = (
        f"{work.gpus:,} GPUs ({cost.vms:,} VMs) × {hours_text(work.hours)}"
        f" × {per_gpu_hour(begin.usd_per_gpu_hour)}"
    )
    storage = "entered by you, not an Azure list price" if entered else "not included"
    total = "compute plus storage entered" if entered else "compute only"
    return pd.DataFrame(
        [
            {"Item": "Compute", "Basis": compute, AMOUNT: cost.compute},
            {"Item": "Storage", "Basis": storage, AMOUNT: cost.storage},
            {"Item": "Total", "Basis": total, AMOUNT: cost.total},
        ],
        columns=["Item", "Basis", AMOUNT],
    )


def note(row: Row) -> str:
    if row.id == calculator.FALLBACK:
        return CROSSES_RENTAL
    if row.above_payg is not None:
        return ABOVE_PAYG.format(price=f"{row.above_payg:.4f}")
    return ""


# The outcome first and the long narrative last, so a wide table never hides the
# effect or a note off-screen (manual check, task 4.1).
SCENARIO_COLUMNS = [
    "Scenario",
    "Effect",
    EXPOSURE,
    SCENARIO_COST,
    SCENARIO_USD,
    CHANGE_USD,
    CHANGE_PCT,
    "Note",
    "Narrative",
]


def scenario_frame(result: Result) -> pd.DataFrame:
    """The starting price first, then each scenario; a refused row shows no figure."""
    begin = result.start
    rows: list[dict[str, object]] = [
        {
            "Scenario": STARTING,
            "Narrative": f"The listed price of {begin.member.name}.",
            CHANGE_USD: None,
            CHANGE_PCT: None,
            SCENARIO_USD: begin.usd_per_gpu_hour,
            SCENARIO_COST: result.cost.total,
            EXPOSURE: None,
            "Effect": BASELINE,
            "Note": "",
        }
    ]
    rows += [
        {
            "Scenario": row.name,
            "Narrative": row.narrative,
            CHANGE_USD: row.change,
            CHANGE_PCT: row.change_pct,
            SCENARIO_USD: row.price,
            SCENARIO_COST: row.cost,
            EXPOSURE: row.exposure,
            "Effect": row.effect,
            "Note": note(row),
        }
        for row in result.rows
    ]
    return pd.DataFrame(rows, columns=SCENARIO_COLUMNS)


def headroom_text(result: Result) -> str | None:
    """The reverse calculation in words (D9), or None without a budget."""
    room = result.headroom
    if room is None:
        return None
    work = result.workload
    text = (
        f"A rise of USD {room.rise:.4f} per GPU-hour ({room.rise_pct:.1f}% of starting"
        f" price) would use up {money(room.budget)} over {work.gpus:,} GPUs ×"
        f" {hours_text(work.hours)}. Storage unchanged. {scenarios.NOT_A_FORECAST}."
    )
    if room.above_payg is not None:
        text += " " + ABOVE_PAYG.format(price=f"{room.above_payg:.4f}")
    return text


def exposure_chart(result: Result) -> alt.LayerChart:
    """One bar per computed scenario row, with a rule at zero (D8)."""
    computed = [row for row in result.rows if row.computed]
    bars = pd.DataFrame(
        {
            "Scenario": [row.name for row in computed],
            EXPOSURE: [row.exposure for row in computed],
            "Effect": [row.effect for row in computed],
        }
    )
    drawn = (
        alt.Chart(bars)
        .mark_bar(color=POINT_COLOUR)
        .encode(
            x=alt.X(
                f"{EXPOSURE}:Q",
                title="Exposure in USD (scenario calculation, not a forecast)",
                axis=alt.Axis(format=",.0f"),
            ),
            y=alt.Y("Scenario:N", sort=None, title=None, axis=alt.Axis(labelLimit=0)),
            tooltip=[
                "Scenario:N",
                alt.Tooltip(f"{EXPOSURE}:Q", format=",.2f"),
                "Effect:N",
            ],
        )
    )
    zero = (
        alt.Chart(pd.DataFrame({EXPOSURE: [0.0]}))
        .mark_rule(color=RULE_COLOURS[0], strokeWidth=2)
        .encode(x=f"{EXPOSURE}:Q")
    )
    return alt.LayerChart(layer=[drawn, zero])


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
    result: Result,
    work: Workload,
    change: Custom | None,
    limit: float | None,
    found: Sequence[RegionGroup],
) -> list[str]:
    """Run the independent check on what the page would show (D19).

    The inputs come from the user's validated entries and the stored members, not from
    the result, so a dropped row or headroom is caught too.
    """
    begin = result.start
    if begin.member.price is None:
        return ["published price missing"]
    inputs = workload_check.Inputs(
        gpus=work.gpus,
        hours=work.hours,
        storage=work.storage,
        vm_price=begin.member.price,
        gpus_per_vm=begin.key.gpu_count,
        spot=begin.key.rental_type == calculator.SPOT,
        payg_vm_price=_listed_payg(begin, found),
        custom=None if change is None else (change.kind, change.magnitude),
        budget=limit,
    )
    room = result.headroom
    figures = workload_check.Figures(
        start=begin.usd_per_gpu_hour,
        vms=result.cost.vms,
        compute=result.cost.compute,
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
            )
            for row in result.rows
        ),
        headroom=None if room is None else room.rise,
        headroom_pct=None if room is None else room.rise_pct,
        headroom_above_payg=None if room is None else room.above_payg,
    )
    return workload_check.check(inputs, figures)
