"""Comparable groups over stored normalized rows (phase-3-normalization D6, D8, D19).

A region group is the compared rows of one snapshot that share GPU variant, GPU
count, region and rental type. A cross-region summary takes each region's lowest
listed member for one variant, count and rental type. A marketplace group counts
machines, not offers. Only succeeded runs are snapshots, and excluded rows never
enter a group. Thresholds come from the rule set stored in the database.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

import duckdb

from compute_cost_risk_monitor import rules

SINGLE = "single list price"
LOWEST = "lowest listed per region"
CROSSES = "crosses regions"
THIN = "thin"
SYNTHETIC = "synthetic"
DUPLICATE = "machine_duplicate"


@dataclass(frozen=True)
class Snapshot:
    source: str
    run_id: str
    started_at: datetime
    data_label: str


@dataclass(frozen=True)
class GroupKey:
    variant: str
    gpu_count: int
    region: str
    rental_type: str


@dataclass(frozen=True)
class Member:
    name: str  # the Azure size, or the marketplace offer ID
    usd_per_gpu_hour: float
    item_key: str
    retrieved_at: datetime
    machine_id: str | None = None
    flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Stats:
    count: int  # regions or distinct machines
    minimum: float
    median: float
    maximum: float


@dataclass
class RegionGroup:
    key: GroupKey
    snapshot: Snapshot
    members: list[Member]
    exclusions: str
    labels: list[str] = field(default_factory=list)
    stats: Stats | None = None  # marketplace groups: one price per machine


@dataclass(frozen=True)
class Contribution:
    region: str
    member: Member


@dataclass
class CrossRegionSummary:
    variant: str
    gpu_count: int
    rental_type: str
    snapshot: Snapshot
    contributions: list[Contribution]
    stats: Stats
    exclusions: str
    labels: list[str] = field(default_factory=list)


def snapshots(connection: duckdb.DuckDBPyConnection, source: str) -> list[Snapshot]:
    """Succeeded runs of a source, oldest first; partial and failed runs never count."""
    rows = connection.execute(
        "SELECT source, run_id, started_at, data_label FROM collection_run"
        " WHERE source = ? AND status = 'succeeded' ORDER BY started_at, run_id",
        [source],
    ).fetchall()
    return [Snapshot(*row) for row in rows]


def stats(values: list[float]) -> Stats:
    """Count, min, median (mean of the middle two for an even count) and max."""
    return Stats(len(values), min(values), statistics.median(values), max(values))


def _lowest(members: list[Member]) -> Member:
    # Ties go to the lexically first name, so output never depends on row order.
    return min(members, key=lambda m: (m.usd_per_gpu_hour, m.name))


_ROWS = """
SELECT n.gpu_model, n.gpu_count, n.region, n.rental_type, n.usd_per_gpu_hour,
       n.item_key, n.retrieved_at, n.exclusions, a.arm_sku_name, m.offer_id,
       m.machine_id
FROM normalized_price n
JOIN price_observation p ON p.source = n.source AND p.item_key = n.item_key
    AND p.retrieved_at = n.retrieved_at
JOIN raw_response rr ON rr.response_id = p.response_id
LEFT JOIN azure_retail_price a ON a.source = n.source AND a.item_key = n.item_key
    AND a.retrieved_at = n.retrieved_at
LEFT JOIN marketplace_offer m ON m.source = n.source AND m.item_key = n.item_key
    AND m.retrieved_at = n.retrieved_at
WHERE rr.run_id = ? AND n.rule_version = ? AND n.excluded_reason IS NULL
ORDER BY n.item_key
"""


def region_groups(
    connection: duckdb.DuckDBPyConnection,
    snapshot: Snapshot,
    rule_version: str = rules.RULE_VERSION,
) -> list[RegionGroup]:
    """Every region group of a snapshot, sorted by key, with its labels."""
    params = rules.stored(connection, rule_version)
    found: dict[GroupKey, list[Member]] = defaultdict(list)
    exclusions: dict[GroupKey, str] = {}
    rows = connection.execute(_ROWS, [snapshot.run_id, rule_version]).fetchall()
    for row in rows:
        model, count, region, rental, per_gpu, key, at, text, size, offer, machine = row
        group = GroupKey(model, int(count), region, rental)
        found[group].append(Member(size or offer, per_gpu, key, at, machine))
        exclusions[group] = text
    marketplace = snapshot.source == "synthetic-marketplace"
    groups = []
    for group in sorted(
        found, key=lambda g: (g.variant, g.gpu_count, g.region, g.rental_type)
    ):
        members = sorted(found[group], key=lambda m: (m.usd_per_gpu_hour, m.name))
        built = RegionGroup(group, snapshot, members, exclusions[group])
        if marketplace:
            _by_machine(built, params["thin_below_machines"])
        elif len(members) == 1:
            built.labels.append(SINGLE)
        groups.append(built)
    return groups


def _by_machine(group: RegionGroup, thin_below: int) -> None:
    """One price per machine, its lowest; other offers flagged as duplicates (D8)."""
    machines: dict[str, list[Member]] = defaultdict(list)
    for member in group.members:
        machines[member.machine_id or member.name].append(member)
    kept = {_lowest(offers).item_key for offers in machines.values()}
    group.members = [
        m
        if m.item_key in kept
        else Member(
            m.name,
            m.usd_per_gpu_hour,
            m.item_key,
            m.retrieved_at,
            m.machine_id,
            (*m.flags, DUPLICATE),
        )
        for m in group.members
    ]
    prices = [m.usd_per_gpu_hour for m in group.members if m.item_key in kept]
    group.stats = stats(prices)
    group.labels.append(SYNTHETIC)
    if len(machines) < thin_below:
        group.labels.append(THIN)


def cross_region(
    groups: list[RegionGroup], thin_below: int
) -> list[CrossRegionSummary]:
    """Per variant, count and rental type, each region's lowest member (D6)."""
    by_key: dict[tuple[str, int, str], list[RegionGroup]] = defaultdict(list)
    for group in groups:
        key = (group.key.variant, group.key.gpu_count, group.key.rental_type)
        by_key[key].append(group)
    summaries = []
    for (variant, count, rental), members in sorted(by_key.items()):
        contributions = [
            Contribution(g.key.region, _lowest(g.members))
            for g in sorted(members, key=lambda g: g.key.region)
        ]
        values = [c.member.usd_per_gpu_hour for c in contributions]
        summary = CrossRegionSummary(
            variant,
            count,
            rental,
            members[0].snapshot,
            contributions,
            stats(values),
            members[0].exclusions,
            [LOWEST, CROSSES],
        )
        if len(contributions) < thin_below:
            summary.labels.append(THIN)
        summaries.append(summary)
    return summaries


def summaries(
    connection: duckdb.DuckDBPyConnection,
    snapshot: Snapshot,
    rule_version: str = rules.RULE_VERSION,
) -> list[CrossRegionSummary]:
    """Cross-region summaries of an Azure snapshot, thin below the stored threshold."""
    params = rules.stored(connection, rule_version)
    groups = region_groups(connection, snapshot, rule_version)
    return cross_region(groups, params["thin_below_regions"])
