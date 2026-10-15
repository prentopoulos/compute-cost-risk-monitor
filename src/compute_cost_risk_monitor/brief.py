"""The market brief: a fact set from stored snapshots and the brief built on it.

Phase 8 design D8, D24, D27, D29, D32, D37, D45 (market-brief spec). Every figure comes
from the existing groups, history, quality, calculator and scenario code, reading stored
rows only. Each fact carries its record links, or the facts it is derived from.

A brief is prose per section, holding placeholders `[[fact_id]]`, plus lists, tables and
labels that code writes. The template prose is written here; an AI-drafted prose
(brief-drafter spec) can replace only the prose. `fill` puts every figure in place, and
`brief_check` re-derives every number in the result independently.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import duckdb

from compute_cost_risk_monitor import (
    azure_retail,
    brief_check,
    calculator,
    collect,
    db,
    groups,
    history,
    quality,
    rules,
    scenarios,
    synthetic,
)
from compute_cost_risk_monitor.dashboard import short_size
from compute_cost_risk_monitor.groups import (
    CrossRegionSummary,
    GroupKey,
    Member,
    RegionGroup,
    Snapshot,
)

SOURCE = azure_retail.SOURCE
SYNTHETIC_LABEL = "SYNTHETIC DATA — NOT AZURE LIST PRICES"
SYNTHETIC_FRAMING = "Invented prices for demonstration, in the shape of Azure's API."
PUBLISHED_LABEL = "AZURE PUBLISHED LIST PRICES"
FRAMING = (
    "Published retail list prices for GPU VMs from one cloud provider, Azure"
    " (Azure Retail Prices API)."
)
EXCLUDES = "Excludes "
CREDIT = (
    "GPU map: contains material from Microsoft Learn, © Microsoft, licensed under"
    " CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)."
)
CROSSES_REGIONS = "This compares across regions."
CROSSES_RENTAL = (
    "Each line crosses rental types (Spot → pay-as-you-go): same size, same region."
)
MEDIAN_NOTE = "The median is a statistic, not a listed price."
# scenarios.JUDGEMENT without "(one snapshot)", which is not true of every database.
JUDGEMENT = (
    "Round sensitivities chosen by judgement, not calibrated to history or to"
    " any model."
)
NO_PAYG = "no pay-as-you-go listing for this size in this region"
DISCLOSURE = (
    "Prose drafted by {model} ({prompt}); every number placed and checked by code."
)
DEFAULT_VARIANT = "H100 NVLink 80GB"
DEFAULT_GPUS_PER_VM = 8
CONTINGENCY_STEPS = ("up-25", "up-50")  # the ladder-v1 rows behind the bottom line
SECTIONS = (
    "bottom_line",
    "changes",
    "absences",
    "groups",
    "spot",
    "regions",
    "quality",
)
TITLES = {
    "bottom_line": "Bottom line",
    "changes": "Changes since the previous snapshot",
    "absences": "Absences",
    "groups": "Groups per GPU",
    "spot": "Spot against pay-as-you-go",
    "regions": "Across regions",
    "quality": "Data quality",
}
# Placeholders a section's prose must use, when the fact exists (D19).
REQUIRED = {
    "bottom_line": (
        "bl_cost",
        "bl_region",
        "bl_min",
        "bl_max",
        "bl_cost_min",
        "bl_cost_max",
        "bl_c25",
        "bl_c50",
    ),
}
PLACEHOLDER = re.compile(r"\[\[([a-z0-9_]+)\]\]")
RENTAL_NAMES = {calculator.ON_DEMAND: "pay-as-you-go", calculator.SPOT: "Spot"}


class BriefError(ValueError):
    """The database cannot give a brief, such as no succeeded snapshot."""


@dataclass(frozen=True)
class Record:
    """Where a figure comes from: one stored observation, or a whole run."""

    run_id: str
    sha256: str | None
    item_key: str | None = None
    retrieved_at: str | None = None
    currency: str | None = None
    unit: str | None = None
    rental_type: str | None = None


@dataclass(frozen=True)
class Fact:
    id: str
    value: float | int | str | None
    unit: str
    text: str  # as shown in the brief
    meaning: str  # what it is, for the drafter
    group: str | None = None
    records: tuple[Record, ...] = ()
    derived_from: tuple[str, ...] = ()
    reason: str | None = None  # why the value is missing


@dataclass(frozen=True)
class Workload:
    variant: str = DEFAULT_VARIANT
    gpus_per_vm: int = DEFAULT_GPUS_PER_VM
    gpus: int = calculator.DEFAULT_GPUS
    hours: float = calculator.DEFAULT_HOURS


@dataclass
class FactSet:
    source: str
    as_of: str
    data_label: str
    snapshot: str  # run ID
    snapshot_start: str
    previous: str | None
    snapshots: int
    stale: bool
    rule_version: str
    map_version: str | None
    exclusions: str
    workload: Workload
    facts: dict[str, Fact] = field(default_factory=dict)
    lists: dict[str, list[str]] = field(default_factory=dict)  # code-written lines
    notes: dict[str, list[str]] = field(default_factory=dict)  # code-written labels
    template: dict[str, str] = field(default_factory=dict)  # the template prose

    def add(self, fact: Fact) -> str:
        if fact.id in self.facts:
            raise ValueError(f"duplicate fact {fact.id}")
        if not re.fullmatch(r"[a-z0-9_]+", fact.id):
            raise ValueError(f"bad fact ID {fact.id}")
        self.facts[fact.id] = fact
        return f"[[{fact.id}]]"

    def to_json(self) -> str:
        return (
            json.dumps(asdict(self), sort_keys=True, indent=2, ensure_ascii=False)
            + "\n"
        )


# --- formats: the dashboard's decimals, rounded half up (Phase 7 D32) ---


def _half_up(value: float, places: int) -> Decimal:
    return Decimal(repr(value)).quantize(Decimal(1).scaleb(-places), ROUND_HALF_UP)


def usd(value: float) -> str:
    return f"{_half_up(value, 2):,}"


def per_gpu(value: float) -> str:
    return f"{_half_up(value, 4):,}"


def percent(value: float) -> str:
    return f"{_half_up(value, 1):,}"


def move(value: float) -> str:
    """A ladder move: "25", or one decimal when it has one."""
    return f"{int(value):,}" if float(value).is_integer() else percent(value)


def published(value: float) -> str:
    """A published price with every stored decimal and never fewer than two."""
    exponent = Decimal(repr(value)).normalize().as_tuple().exponent
    places = max(2, -exponent if isinstance(exponent, int) and exponent < 0 else 0)
    return f"{_half_up(value, places):,}"


def count(value: int) -> str:
    return f"{value:,}"


def hours_text(hours: float) -> str:
    return f"{Decimal(repr(hours)).normalize():f}"


def when(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def plural(n: int, one: str, many: str) -> str:
    return one if n == 1 else many


def exclusion_items(text: str) -> str:
    """The stored exclusions sentence without its verb: "disks and storage, …"."""
    return text.removeprefix(EXCLUDES).removesuffix(".")


def rental_name(rental: str) -> str:
    return RENTAL_NAMES.get(rental, rental)


# --- records ---


def _member_record(member: Member, rental: str) -> Record:
    return Record(
        run_id=member.run_id or "",
        sha256=member.sha256,
        item_key=member.item_key,
        retrieved_at=when(member.retrieved_at),
        currency=member.currency,
        unit=member.price_unit,
        rental_type=rental,
    )


def _run_records(
    connection: duckdb.DuckDBPyConnection, run_id: str
) -> tuple[Record, ...]:
    rows = connection.execute(
        "SELECT sha256 FROM raw_response WHERE run_id = ? ORDER BY seq", [run_id]
    ).fetchall()
    return tuple(Record(run_id=run_id, sha256=row[0]) for row in rows)


_ITEM = """
SELECT r.run_id, r.sha256, p.currency, p.price_unit, p.rental_type
FROM price_observation p JOIN raw_response r ON r.response_id = p.response_id
WHERE p.source = ? AND p.item_key = ? AND p.retrieved_at = ?
"""


def _item_record(
    connection: duckdb.DuckDBPyConnection, item_key: str, at: datetime
) -> Record:
    row = connection.execute(_ITEM, [SOURCE, item_key, at]).fetchone()
    if row is None:  # pragma: no cover - every observation has its response (schema FK)
        raise BriefError(f"no stored observation {item_key} at {when(at)}")
    run_id, sha, currency, unit, rental = row
    return Record(run_id, sha, item_key, when(at), currency, unit, rental)


def _locations(connection: duckdb.DuckDBPyConnection, run_id: str) -> dict[str, str]:
    rows = connection.execute(
        "SELECT DISTINCT a.arm_region_name, a.location FROM azure_retail_price a"
        " JOIN price_observation p ON p.source = a.source AND p.item_key = a.item_key"
        " AND p.retrieved_at = a.retrieved_at"
        " JOIN raw_response r ON r.response_id = p.response_id"
        " WHERE r.run_id = ? AND a.location IS NOT NULL ORDER BY 1, 2",
        [run_id],
    ).fetchall()
    return {code: name for code, name in rows}


def _map_version(connection: duckdb.DuckDBPyConnection, run_id: str) -> str | None:
    row = connection.execute(
        "SELECT min(n.mapping_version) FROM normalized_price n"
        " JOIN price_observation p ON p.source = n.source AND p.item_key = n.item_key"
        " AND p.retrieved_at = n.retrieved_at"
        " JOIN raw_response r ON r.response_id = p.response_id WHERE r.run_id = ?",
        [run_id],
    ).fetchone()
    return None if row is None else row[0]


# --- the fact set ---


def build(
    connection: duckdb.DuckDBPyConnection,
    as_of: datetime,
    workload: Workload | None = None,
    rule_version: str = rules.RULE_VERSION,
) -> FactSet:
    """Every fact of the latest succeeded snapshot, as of a time not before it."""
    work = workload or Workload()
    ordered = groups.snapshots(connection, SOURCE)
    if not ordered:
        raise BriefError(f"no succeeded {SOURCE} snapshot")
    snap = ordered[-1]
    if as_of < snap.started_at:
        raise BriefError(
            f"the as-of time {when(as_of)} is before the latest snapshot"
            f" ({when(snap.started_at)})"
        )
    previous = ordered[-2] if len(ordered) > 1 else None
    params = rules.stored(connection, rule_version)
    report = quality.build(connection, SOURCE, as_of, rule_version)
    found = groups.region_groups(connection, snap, rule_version)
    summaries = groups.cross_region(found, params["thin_below_regions"])
    facts = FactSet(
        source=SOURCE,
        as_of=when(as_of),
        data_label=snap.data_label,
        snapshot=snap.run_id,
        snapshot_start=when(snap.started_at),
        previous=None if previous is None else previous.run_id,
        snapshots=len(ordered),
        stale=bool(report.stale),
        rule_version=rule_version,
        map_version=_map_version(connection, snap.run_id),
        exclusions=str(params["exclusions"]),
        workload=work,
    )
    run = _run_records(connection, snap.run_id)
    names = _locations(connection, snap.run_id)
    facts.add(Fact("as_of", facts.as_of, "UTC", facts.as_of, "the brief's as-of time"))
    facts.add(
        Fact(
            "snap_time",
            facts.snapshot_start,
            "UTC",
            facts.snapshot_start,
            "start of the latest snapshot",
            records=run,
        )
    )
    if previous is not None:
        start = when(previous.started_at)
        facts.add(
            Fact(
                "prev_time",
                start,
                "UTC",
                start,
                "start of the previous snapshot",
                records=_run_records(connection, previous.run_id),
            )
        )
    _bottom_line(facts, found, summaries, work, names, run, params)
    _changes(facts, connection, previous, snap, names, rule_version)
    _absences(facts, connection, names, rule_version)
    _groups(facts, found, run)
    _spot(facts, found, work, names)
    _regions(facts, summaries, names, params)
    _quality(facts, report, ordered, run, params)
    return facts


def _name(names: Mapping[str, str], code: str) -> str:
    return names.get(code, code)


def _key_text(key: GroupKey) -> str:
    return f"{key.variant} × {key.gpu_count} · {rental_name(key.rental_type)}"


def _bottom_line(
    facts: FactSet,
    found: list[RegionGroup],
    summaries: list[CrossRegionSummary],
    work: Workload,
    names: Mapping[str, str],
    run: tuple[Record, ...],
    params: Mapping[str, Any],
) -> None:
    label = f"{work.variant} × {work.gpus_per_vm} · pay-as-you-go"
    facts.add(
        Fact("bl_gpus", work.gpus, "GPUs", count(work.gpus), "GPUs in the workload")
    )
    facts.add(
        Fact(
            "bl_hours",
            work.hours,
            "hours",
            hours_text(work.hours),
            "hours in the workload",
        )
    )
    facts.add(Fact("bl_variant", work.variant, "text", work.variant, "the GPU variant"))
    summary = next(
        (
            s
            for s in summaries
            if (s.variant, s.gpu_count, s.rental_type)
            == (work.variant, work.gpus_per_vm, calculator.ON_DEMAND)
        ),
        None,
    )
    if summary is None:
        facts.add(
            Fact(
                "bl_cost",
                None,
                "USD",
                "not computed",
                "the workload's cost",
                group=label,
                records=run,
                reason="no pay-as-you-go listing for this GPU and count",
            )
        )
        facts.template["bottom_line"] = (
            "No pay-as-you-go listing for [[bl_variant]] in this snapshot, so no cost"
            " is stated."
        )
        facts.notes["bottom_line"] = [
            f"Not priced: {exclusion_items(facts.exclusions)}."
        ]
        return
    low = min(summary.contributions, key=lambda c: groups.price_order(c.member))
    high = max(summary.contributions, key=lambda c: groups.price_order(c.member))
    group = next(
        g
        for g in found
        if g.key
        == GroupKey(work.variant, work.gpus_per_vm, low.region, calculator.ON_DEMAND)
    )
    plan = calculator.workload(work.gpus, work.hours, None, work.gpus_per_vm)
    result = calculator.calculate(calculator.start(group), plan, found)
    entered = result.ladder.columns.index(result.ladder.entered)
    steps = {row.id: row for row in result.ladder.rows}
    low_record = (_member_record(low.member, calculator.ON_DEMAND),)
    high_record = (_member_record(high.member, calculator.ON_DEMAND),)
    gpu_hours = work.gpus * work.hours
    facts.add(
        Fact(
            "bl_vms",
            result.cost.vms,
            "VMs",
            count(result.cost.vms),
            "VMs the workload needs",
            derived_from=("bl_gpus",),
        )
    )
    facts.add(
        Fact(
            "bl_size",
            low.member.name,
            "text",
            short_size(low.member.name),
            "the lowest listed size",
            group=label,
            records=low_record,
        )
    )
    facts.add(
        Fact(
            "bl_region",
            low.region,
            "text",
            _name(names, low.region),
            "the region of the lowest listed price",
            group=label,
            records=low_record,
        )
    )
    facts.add(
        Fact(
            "bl_price",
            low.member.usd_per_gpu_hour,
            "USD/GPU-h",
            per_gpu(low.member.usd_per_gpu_hour),
            "the lowest listed pay-as-you-go price",
            group=label,
            records=low_record,
        )
    )
    facts.add(
        Fact(
            "bl_cost",
            result.cost.total,
            "USD",
            usd(result.cost.total),
            "the workload's cost at the lowest listed price",
            group=label,
            derived_from=("bl_gpus", "bl_hours", "bl_price"),
        )
    )
    contributions = tuple(
        _member_record(c.member, calculator.ON_DEMAND) for c in summary.contributions
    )
    facts.add(
        Fact(
            "bl_regions",
            summary.stats.count,
            "regions",
            count(summary.stats.count),
            "regions listing this GPU and count",
            group=label,
            records=contributions,
        )
    )
    facts.add(
        Fact(
            "bl_min",
            summary.stats.minimum,
            "USD/GPU-h",
            per_gpu(summary.stats.minimum),
            "the lowest listed price across regions",
            group=label,
            records=low_record,
        )
    )
    facts.add(
        Fact(
            "bl_max",
            summary.stats.maximum,
            "USD/GPU-h",
            per_gpu(summary.stats.maximum),
            "the highest of the regions' lowest listed prices",
            group=label,
            records=high_record,
        )
    )
    for name, value, source, side in (
        ("bl_cost_min", gpu_hours * summary.stats.minimum, "bl_min", "lowest"),
        ("bl_cost_max", gpu_hours * summary.stats.maximum, "bl_max", "highest"),
    ):
        facts.add(
            Fact(
                name,
                value,
                "USD",
                usd(value),
                f"the workload's cost at the {side} regional price",
                group=label,
                derived_from=("bl_gpus", "bl_hours", source),
            )
        )
    for step, name in zip(CONTINGENCY_STEPS, ("c25", "c50"), strict=True):
        row = steps[step]
        if row.cells is None or row.magnitude is None:  # pragma: no cover
            raise BriefError(f"{step} is not computed")  # ladder-v1 always is
        facts.add(
            Fact(
                f"bl_{name}_move",
                row.magnitude,
                "%",
                move(row.magnitude),
                f"a {scenarios.LADDER_VERSION} list-price move",
            )
        )
        facts.add(
            Fact(
                f"bl_{name}",
                row.cells[entered],
                "USD",
                usd(row.cells[entered]),
                f"the contingency covering the +{move(row.magnitude)}% move",
                group=label,
                derived_from=("bl_gpus", "bl_hours", "bl_price", f"bl_{name}_move"),
            )
        )
    thin = groups.THIN in summary.labels
    facts.template["bottom_line"] = (
        "[[bl_gpus]] [[bl_variant]] GPUs ([[bl_vms]] × [[bl_size]]) for [[bl_hours]]"
        " hours cost USD [[bl_cost]] at the lowest listed pay-as-you-go price for"
        " this size: [[bl_region]], [[bl_price]] USD/GPU-h. This size lists in"
        " [[bl_regions]] regions at [[bl_min]]–[[bl_max]] USD/GPU-h, so the same"
        " workload costs USD"
        " [[bl_cost_min]]–[[bl_cost_max]]. A contingency of USD [[bl_c25]] covers a"
        " +[[bl_c25_move]]% list-price move, and USD [[bl_c50]] a +[[bl_c50_move]]%"
        " move."
    )
    notes = [
        CROSSES_REGIONS + (" Thin: fewer than [[thin_below]] regions." if thin else "")
    ]
    if thin:
        _thin_fact(facts, params)
    notes += [
        f"{scenarios.NOT_A_FORECAST}. {JUDGEMENT}",
        f"Not priced: {exclusion_items(facts.exclusions)}.",
    ]
    facts.notes["bottom_line"] = notes


def _thin_fact(facts: FactSet, params: Mapping[str, Any]) -> None:
    if "thin_below" not in facts.facts:
        below = int(params["thin_below_regions"])
        facts.add(
            Fact(
                "thin_below",
                below,
                "regions",
                count(below),
                "a cross-region figure from fewer regions is thin (groups-v1)",
            )
        )


def _listing_text(
    names: Mapping[str, str], size: str, region: str, rental: str, os_name: str
) -> str:
    parts = (_name(names, region), short_size(size), rental_name(rental), os_name)
    return " · ".join(parts)


def _changes(
    facts: FactSet,
    connection: duckdb.DuckDBPyConnection,
    previous: Snapshot | None,
    snap: Snapshot,
    names: Mapping[str, str],
    rule_version: str,
) -> None:
    if previous is None:
        facts.template["changes"] = (
            "Changes need a second snapshot; this database holds [[n_snapshots]]."
        )
        facts.lists["changes"] = []
        return
    found = history.changes(connection, previous, snap, rule_version)
    lines = []
    for i, change in enumerate(found, start=1):
        size, region, rental, os_name = change.after.listing
        before = _item_record(
            connection, change.before.item_key, change.before.retrieved_at
        )
        after = _item_record(
            connection, change.after.item_key, change.after.retrieved_at
        )
        listing = _listing_text(names, size, region, rental, os_name)
        f = f"chg_{i}"
        facts.add(
            Fact(
                f"{f}_before",
                change.before.price,
                "USD/VM-h",
                published(change.before.price),
                f"{listing}: the earlier price",
                records=(before,),
            )
        )
        facts.add(
            Fact(
                f"{f}_after",
                change.after.price,
                "USD/VM-h",
                published(change.after.price),
                f"{listing}: the later price",
                records=(after,),
            )
        )
        line = f"- {listing}: [[{f}_before]] → [[{f}_after]] USD/VM-h"
        if (
            change.before.usd_per_gpu_hour is not None
            and change.after.usd_per_gpu_hour is not None
        ):
            for side, value, record in (
                ("before", change.before.usd_per_gpu_hour, before),
                ("after", change.after.usd_per_gpu_hour, after),
            ):
                facts.add(
                    Fact(
                        f"{f}_{side}_gpu",
                        value,
                        "USD/GPU-h",
                        per_gpu(value),
                        f"{listing}: the {side} price per GPU-hour",
                        records=(record,),
                    )
                )
            line += f" ([[{f}_before_gpu]] → [[{f}_after_gpu]] USD/GPU-h)"
        lines.append(line + ".")
    n = len(found)
    facts.add(
        Fact(
            "n_changes",
            n,
            "count",
            count(n),
            "listed prices that changed since the previous snapshot",
            derived_from=("prev_time", "snap_time"),
        )
    )
    facts.lists["changes"] = lines
    if n == 0:
        facts.template["changes"] = (
            "No listed price changed between [[prev_time]] and [[snap_time]]."
        )
    else:
        verb = plural(n, "listed price changed", "listed prices changed")
        facts.template["changes"] = (
            f"[[n_changes]] {verb} between [[prev_time]] and [[snap_time]]."
        )


def _absences(
    facts: FactSet,
    connection: duckdb.DuckDBPyConnection,
    names: Mapping[str, str],
    rule_version: str,
) -> None:
    found = history.absences(connection, SOURCE, rule_version)
    lines = []
    by_status: Counter[str] = Counter()
    for i, absence in enumerate(found, start=1):
        size, region, rental, os_name = absence.listing
        by_status[absence.status] += 1
        f = f"abs_{i}"
        since, seen = when(absence.since.started_at), when(absence.last_seen.started_at)
        facts.add(
            Fact(
                f"{f}_since",
                since,
                "UTC",
                since,
                "first snapshot without it",
                records=_run_records(connection, absence.since.run_id),
            )
        )
        facts.add(
            Fact(
                f"{f}_seen",
                seen,
                "UTC",
                seen,
                "last snapshot with it",
                records=_run_records(connection, absence.last_seen.run_id),
            )
        )
        lines.append(
            f"- {_listing_text(names, size, region, rental, os_name)}: {absence.status}"
            f" since [[{f}_since]], last seen [[{f}_seen]]."
        )
    once, gone = by_status[history.ABSENT_ONCE], by_status[history.NOT_LISTED]
    facts.add(
        Fact(
            "n_absent_once",
            once,
            "count",
            count(once),
            "listings absent once (unconfirmed)",
            derived_from=("snap_time",),
        )
    )
    facts.add(
        Fact(
            "n_not_listed",
            gone,
            "count",
            count(gone),
            "listings not listed: absent from two snapshots in a row",
            derived_from=("snap_time",),
        )
    )
    facts.lists["absences"] = lines
    if not found:
        facts.template["absences"] = "No listing is missing from the latest snapshot."
    else:
        facts.template["absences"] = (
            f"[[n_absent_once]] {plural(once, 'listing is', 'listings are')}"
            f" {history.ABSENT_ONCE}, and [[n_not_listed]]"
            f" {plural(gone, 'is', 'are')} {history.NOT_LISTED}."
        )


def _groups(facts: FactSet, found: list[RegionGroup], run: tuple[Record, ...]) -> None:
    by_variant: dict[str, list[RegionGroup]] = defaultdict(list)
    for group in found:
        by_variant[group.key.variant].append(group)
    lines = ["| GPU | Region groups | Single list price |", "|---|---:|---:|"]
    for i, (variant, members) in enumerate(sorted(by_variant.items()), start=1):
        single = sum(1 for g in members if groups.SINGLE in g.labels)
        facts.add(
            Fact(
                f"grp_{i}_n",
                len(members),
                "count",
                count(len(members)),
                f"{variant}: region groups",
                records=run,
            )
        )
        facts.add(
            Fact(
                f"grp_{i}_single",
                single,
                "count",
                count(single),
                f"{variant}: groups with a single list price",
                records=run,
            )
        )
        lines.append(f"| {variant} | [[grp_{i}_n]] | [[grp_{i}_single]] |")
    single = sum(1 for g in found if groups.SINGLE in g.labels)
    facts.add(
        Fact(
            "n_groups",
            len(found),
            "count",
            count(len(found)),
            "region groups in the latest snapshot",
            records=run,
        )
    )
    facts.add(
        Fact(
            "n_variants",
            len(by_variant),
            "count",
            count(len(by_variant)),
            "GPU variants",
            records=run,
        )
    )
    facts.add(
        Fact(
            "n_single",
            single,
            "count",
            count(single),
            "region groups with a single list price",
            records=run,
        )
    )
    facts.lists["groups"] = lines if found else []
    facts.template["groups"] = (
        "[[n_groups]] region groups across [[n_variants]] GPU variants; [[n_single]]"
        " of them have a single list price."
    )


def _spot(
    facts: FactSet, found: list[RegionGroup], work: Workload, names: Mapping[str, str]
) -> None:
    payg = {
        (g.key.variant, g.key.gpu_count, g.key.region, m.name): m
        for g in found
        if g.key.rental_type == calculator.ON_DEMAND
        for m in g.members
    }
    total = paired = equal = above = 0
    lines = [
        "| Region | Size | Spot, USD/GPU-h | Pay-as-you-go, USD/GPU-h | Spot as % of"
        " pay-as-you-go |",
        "|---|---|---:|---:|---:|",
    ]
    i = 0
    for group in found:
        if group.key.rental_type != calculator.SPOT:
            continue
        for member in group.members:
            total += 1
            twin = payg.get(
                (group.key.variant, group.key.gpu_count, group.key.region, member.name)
            )
            if twin is not None:
                paired += 1
                equal += member.usd_per_gpu_hour == twin.usd_per_gpu_hour
                above += member.usd_per_gpu_hour > twin.usd_per_gpu_hour
            if (group.key.variant, group.key.gpu_count) != (
                work.variant,
                work.gpus_per_vm,
            ):
                continue
            i += 1
            f = f"spot_{i}"
            record = _member_record(member, calculator.SPOT)
            facts.add(
                Fact(
                    f"{f}_spot",
                    member.usd_per_gpu_hour,
                    "USD/GPU-h",
                    per_gpu(member.usd_per_gpu_hour),
                    "a Spot listed price",
                    group=_key_text(group.key),
                    records=(record,),
                )
            )
            region = _name(names, group.key.region)
            if twin is None:
                lines.append(
                    f"| {region} | {short_size(member.name)} | [[{f}_spot]]"
                    f" | {NO_PAYG} | — |"
                )
                continue
            ratio = 100.0 * member.usd_per_gpu_hour / twin.usd_per_gpu_hour
            facts.add(
                Fact(
                    f"{f}_payg",
                    twin.usd_per_gpu_hour,
                    "USD/GPU-h",
                    per_gpu(twin.usd_per_gpu_hour),
                    "the same size's pay-as-you-go listed price",
                    records=(_member_record(twin, calculator.ON_DEMAND),),
                )
            )
            facts.add(
                Fact(
                    f"{f}_ratio",
                    ratio,
                    "%",
                    percent(ratio),
                    "Spot as a share of pay-as-you-go",
                    derived_from=(f"{f}_spot", f"{f}_payg"),
                )
            )
            lines.append(
                f"| {region} | {short_size(member.name)} | [[{f}_spot]] | [[{f}_payg]]"
                f" | [[{f}_ratio]] |"
            )
    for name, value, meaning in (
        ("n_spot", total, "Spot listings compared"),
        (
            "n_spot_paired",
            paired,
            "Spot listings with the same size on pay-as-you-go in the same region",
        ),
        ("n_spot_equal", equal, "Spot listings equal to that pay-as-you-go price"),
        ("n_spot_above", above, "Spot listings above that pay-as-you-go price"),
    ):
        facts.add(
            Fact(
                name, value, "count", count(value), meaning, derived_from=("snap_time",)
            )
        )
    facts.lists["spot"] = lines if i else []
    facts.notes["spot"] = [CROSSES_RENTAL]
    facts.template["spot"] = (
        "[[n_spot_paired]] of [[n_spot]] Spot listings have the same size on"
        f" pay-as-you-go in the same region; [[n_spot_equal]]"
        f" {plural(equal, 'equals', 'equal')} it and [[n_spot_above]]"
        f" {plural(above, 'is', 'are')} above it."
        + (" The table shows [[bl_variant]]." if i else "")
    )


def _regions(
    facts: FactSet,
    summaries: list[CrossRegionSummary],
    names: Mapping[str, str],
    params: Mapping[str, Any],
) -> None:
    lines = [
        "| GPU | Pricing | Regions | Lowest | Median | Highest | Labels |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    thin = 0
    for i, summary in enumerate(summaries, start=1):
        f = f"reg_{i}"
        records = tuple(
            _member_record(c.member, summary.rental_type) for c in summary.contributions
        )
        pricing = rental_name(summary.rental_type)
        key = f"{summary.variant} × {summary.gpu_count} · {pricing}"
        stats = summary.stats
        for part, value, meaning in (
            ("n", stats.count, "regions"),
            ("min", stats.minimum, "the lowest listed price, USD/GPU-h"),
            ("median", stats.median, "the median, a statistic, USD/GPU-h"),
            ("max", stats.maximum, "the highest regional price, USD/GPU-h"),
        ):
            text = count(int(value)) if part == "n" else per_gpu(value)
            unit = "regions" if part == "n" else "USD/GPU-h"
            facts.add(
                Fact(
                    f"{f}_{part}",
                    value,
                    unit,
                    text,
                    f"{key}: {meaning}",
                    group=key,
                    records=records,
                )
            )
        labels = [label for label in summary.labels if label != groups.LOWEST]
        thin += groups.THIN in summary.labels
        lines.append(
            f"| {summary.variant} × {summary.gpu_count} |"
            f" {rental_name(summary.rental_type)} | [[{f}_n]] | [[{f}_min]] |"
            f" [[{f}_median]] | [[{f}_max]] | {' · '.join(labels)} |"
        )
    _thin_fact(facts, params)
    facts.add(
        Fact(
            "n_summaries",
            len(summaries),
            "count",
            count(len(summaries)),
            "cross-region summaries",
            derived_from=("snap_time",),
        )
    )
    facts.add(
        Fact(
            "n_thin",
            thin,
            "count",
            count(thin),
            "thin cross-region summaries",
            derived_from=("snap_time", "thin_below"),
        )
    )
    facts.lists["regions"] = lines if summaries else []
    facts.notes["regions"] = [
        f"{CROSSES_REGIONS} Each region counts once, at its lowest listed price."
        f" {MEDIAN_NOTE}"
    ]
    facts.template["regions"] = (
        "[[n_summaries]] cross-region summaries; [[n_thin]] of them are thin, from"
        " fewer than [[thin_below]] regions."
    )


def _quality(
    facts: FactSet,
    report: quality.QualityReport,
    ordered: list[Snapshot],
    run: tuple[Record, ...],
    params: Mapping[str, Any],
) -> None:
    normalized = report.by_status.get("normalized", 0)
    days = (ordered[-1].started_at - ordered[0].started_at).days
    stale_days = int(params["stale_after_days"])
    entries: list[tuple[str, int, str]] = [
        ("q_obs", report.observations, "observations in the latest snapshot"),
        ("q_normalized", normalized, "observations compared"),
        ("q_unmapped", len(report.unmapped_sizes), "sizes not in the GPU map"),
        ("n_snapshots", len(ordered), "succeeded snapshots"),
        ("n_days", days, "days from the first snapshot to the latest"),
        ("stale_days", stale_days, "a snapshot is stale after this many days"),
    ]
    for name, value, meaning in entries:
        facts.add(Fact(name, value, "count", count(value), meaning, records=run))
    lines = [
        "- Observations: [[q_obs]], of which [[q_normalized]] are compared.",
    ]
    for i, (status, n) in enumerate(sorted(report.by_status.items()), start=1):
        if status == "normalized":
            continue
        facts.add(
            Fact(
                f"q_reason_{i}",
                n,
                "count",
                count(n),
                f"excluded as {status}",
                records=run,
            )
        )
        lines.append(f"- Excluded as `{status}`: [[q_reason_{i}]].")
    lines += [
        "- Sizes not in the GPU map: [[q_unmapped]].",
        "- Region groups: [[n_groups]], [[n_single]] with a single list price.",
        "- Cross-region summaries: [[n_summaries]], [[n_thin]] thin.",
        "- Changes since the previous snapshot: "
        + ("[[n_changes]]." if "n_changes" in facts.facts else "no previous snapshot."),
        f"- {history.ABSENT_ONCE.capitalize()}: [[n_absent_once]];"
        f" {history.NOT_LISTED}: [[n_not_listed]].",
        "- Stale: "
        + ("yes" if report.stale else "no")
        + ", as of [[as_of]] (stale after [[stale_days]] days).",
    ]
    facts.lists["quality"] = lines
    facts.notes["quality"] = [
        "Sample too thin for trends: [[n_snapshots]]"
        f" {plural(len(ordered), 'snapshot', 'snapshots')} over [[n_days]]"
        f" {plural(days, 'day', 'days')}."
    ]
    facts.template["quality"] = (
        "The latest snapshot holds [[q_obs]] observations; [[q_normalized]] are"
        " compared and the rest are excluded, each with its reason."
    )


# --- the brief ---


def fill(text: str, facts: FactSet) -> str:
    """Every `[[fact_id]]` replaced by its fact's text; an unknown ID raises
    KeyError."""
    return PLACEHOLDER.sub(lambda match: facts.facts[match.group(1)].text, text)


def header(facts: FactSet) -> list[str]:
    synthetic_data = facts.data_label == synthetic.LABEL
    label = SYNTHETIC_LABEL if synthetic_data else PUBLISHED_LABEL
    status = (
        f"**{label}** · snapshot [[snap_time]] (run {facts.snapshot}) · AS OF [[as_of]]"
    )
    if facts.stale:
        status += " · STALE — OLDER THAN [[stale_days]] DAYS AS OF [[as_of]]"
    framing = SYNTHETIC_FRAMING if synthetic_data else FRAMING
    return ["# Market brief", "", status, "", framing]


def assemble(
    facts: FactSet, prose: Mapping[str, str], disclosure: str | None = None
) -> str:
    """The brief's Markdown with placeholders: header, then each section's prose, its
    lists and its labels, then the credit, the disclosure and the Records table."""
    lines = header(facts)
    for section in SECTIONS:
        lines += ["", f"## {TITLES[section]}", "", prose[section].strip()]
        if facts.lists.get(section):
            lines += ["", *facts.lists[section]]
        for note in facts.notes.get(section, []):
            lines += ["", f"*{note}*"]
    lines += ["", "---", "", CREDIT]
    if disclosure is not None:
        lines += ["", disclosure]
    return "\n".join(lines) + "\n"


def records_table(facts: FactSet, used: list[str]) -> str:
    lines = [
        "## Records",
        "",
        "| Fact | Run | Item | Retrieved | Raw-response SHA-256 |",
        "|---|---|---|---|---|",
    ]
    for fact_id in used:
        fact = facts.facts[fact_id]
        if fact.derived_from and not fact.records:
            sources = ", ".join(f"`{d}`" for d in fact.derived_from)
            lines.append(f"| `{fact_id}` | derived from {sources} | | | |")
            continue
        if not fact.records:
            lines.append(f"| `{fact_id}` | stated input or fixed rule | | | |")
            continue
        for record in fact.records:
            item = (record.item_key or "").replace("|", "\\|")  # a table cell
            lines.append(
                f"| `{fact_id}` | {record.run_id} | {item} |"
                f" {record.retrieved_at or ''} | {record.sha256 or ''} |"
            )
    return "\n".join(lines) + "\n"


def used_facts(text: str) -> list[str]:
    """Fact IDs in order of first use."""
    return list(dict.fromkeys(PLACEHOLDER.findall(text)))


def render(
    facts: FactSet,
    prose: Mapping[str, str] | None = None,
    disclosure: str | None = None,
) -> str:
    """The final brief: the template prose unless drafted prose is given."""
    raw = assemble(facts, prose or facts.template, disclosure)
    used = used_facts(raw)
    return fill(raw, facts) + "\n" + records_table(facts, used)


# --- the command ---

DATA = collect.REPO / "data"
BRIEFS = DATA / "briefs"


def run_record(
    facts: FactSet,
    text_used: str,
    attempts: Sequence[Mapping[str, Any]] = (),
    drafter: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """What produced a brief; a template-only run records no request (brief-drafter
    spec)."""
    record: dict[str, Any] = {
        "as_of": facts.as_of,
        "attempts": list(attempts),
        "code_version": collect.code_version(),
        "data_label": facts.data_label,
        "fact_set_sha256": hashlib.sha256(facts.to_json().encode("utf-8")).hexdigest(),
        "requests": len(attempts),
        "snapshot": facts.snapshot,
        "text_used": text_used,
    }
    record.update(drafter or {"provider": None, "model": None})
    return record


def write(out: Path, text: str, facts: FactSet, record: Mapping[str, Any]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "brief.md").write_bytes(text.encode("utf-8"))
    (out / "facts.json").write_bytes(facts.to_json().encode("utf-8"))
    body = json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    (out / "run-record.json").write_bytes(body.encode("utf-8"))


def checked(
    connection: duckdb.DuckDBPyConnection, facts: FactSet, text: str, as_of: datetime
) -> brief_check.CheckResult:
    work = facts.workload
    derived = brief_check.derive(
        connection,
        as_of,
        work.variant,
        work.gpus_per_vm,
        work.gpus,
        work.hours,
        facts.rule_version,
    )
    return brief_check.check(text, derived)


def _inside(path: Path, folder: Path) -> bool:
    return path.resolve().is_relative_to(folder.resolve())


def main(argv: Sequence[str] | None = None, *, now: datetime | None = None) -> int:
    """Build, check and write a brief: 0 when written, 1 when the independent check
    fails (nothing written), 2 when refused (nothing written)."""
    parser = argparse.ArgumentParser(
        prog="python -m compute_cost_risk_monitor.brief",
        description="Write the market brief for a database's latest snapshot.",
    )
    parser.add_argument("--db", type=Path, required=True, help="DuckDB file")
    parser.add_argument(
        "--as-of", type=datetime.fromisoformat, help="time with a zone (default: now)"
    )
    parser.add_argument(
        "--out", type=Path, help="output folder (default: data/briefs/<run ID>)"
    )
    args = parser.parse_args(argv)
    as_of = args.as_of or now or datetime.now(UTC)
    if as_of.tzinfo is None:
        print("refused: --as-of needs a time zone", file=sys.stderr)
        return 2
    as_of = as_of.astimezone(UTC)
    if not args.db.is_file():
        print(f"refused: no database at {args.db}", file=sys.stderr)
        return 2
    try:
        connection = db.connect(args.db, read_only=True)
    except duckdb.Error as error:
        print(f"refused: cannot open {args.db}: {error}", file=sys.stderr)
        return 2
    try:
        try:
            facts = build(connection, as_of)
        except KeyError as error:
            print(f"refused: {error}; run normalize first", file=sys.stderr)
            return 2
        except BriefError as error:
            print(f"refused: {error}", file=sys.stderr)
            return 2
        except duckdb.CatalogException as error:  # a DuckDB file of another kind
            print(f"refused: not a monitor database: {error}", file=sys.stderr)
            return 2
        out = args.out or BRIEFS / facts.snapshot
        if facts.data_label != synthetic.LABEL and not _inside(out, DATA):
            print(
                f"refused: a brief of collected prices stays under {DATA}",
                file=sys.stderr,
            )
            return 2
        text = render(facts)
        result = checked(connection, facts, text, as_of)
    finally:
        connection.close()
    if not result.passed:
        where = ", ".join(f"line {f.line}" for f in result.failures)
        print(
            f"check failed: {len(result.failures)} unmatched ({where});"
            " nothing written",
            file=sys.stderr,
        )
        return 1
    write(out, text, facts, run_record(facts, "template"))
    print(
        f"wrote {out}: {len(facts.facts)} facts; {result.numbers} numbers and"
        f" {result.times} times re-derived"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
