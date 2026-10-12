"""Price changes and absences between consecutive snapshots (design D7, D8, D23).

A change is one key with a different price in two consecutive snapshots: the item key
for Azure, the continuity key for marketplace offers, so a re-listed offer continues.
A listing missing once is "absent once (unconfirmed)"; missing from two consecutive
snapshots it is "not listed", dated at the first absence. Partial and failed runs
never count. No price is ever filled in for an absent listing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import duckdb
import pandas as pd

from compute_cost_risk_monitor import groups, normalize, rules
from compute_cost_risk_monitor.groups import GroupKey, Snapshot

ABSENT_ONCE = "absent once (unconfirmed)"
NOT_LISTED = "not listed"


@dataclass(frozen=True)
class Observed:
    """One listing in one snapshot, at its price-change key's price."""

    listing: tuple[str, ...]  # the key absences are tracked by
    price_key: str  # the key changes are tracked by
    item_key: str
    retrieved_at: datetime
    price: float  # the source's price for its unit
    usd_per_gpu_hour: float | None
    group: GroupKey | None  # when the row is compared


@dataclass(frozen=True)
class Change:
    price_key: str
    before: Observed
    after: Observed
    before_snapshot: Snapshot
    after_snapshot: Snapshot


@dataclass(frozen=True)
class Absence:
    listing: tuple[str, ...]
    status: str  # ABSENT_ONCE or NOT_LISTED
    since: Snapshot  # the first snapshot without it
    last_seen: Snapshot


_AZURE = """
SELECT a.arm_sku_name, p.region, p.rental_type, a.product_name, p.item_key,
       p.retrieved_at, p.price, n.usd_per_gpu_hour, n.gpu_model, n.gpu_count
FROM price_observation p
JOIN raw_response rr ON rr.response_id = p.response_id
JOIN azure_retail_price a ON a.source = p.source AND a.item_key = p.item_key
    AND a.retrieved_at = p.retrieved_at
LEFT JOIN normalized_price n ON n.source = p.source AND n.item_key = p.item_key
    AND n.retrieved_at = p.retrieved_at AND n.rule_version = ?
WHERE rr.run_id = ?
"""

_MARKETPLACE = """
SELECT m.machine_id, m.gpu_name_listed, m.num_gpus, p.region, p.rental_type,
       m.offer_id, p.item_key, p.retrieved_at, p.price, n.usd_per_gpu_hour,
       n.gpu_model, n.gpu_count
FROM price_observation p
JOIN raw_response rr ON rr.response_id = p.response_id
JOIN marketplace_offer m ON m.source = p.source AND m.item_key = p.item_key
    AND m.retrieved_at = p.retrieved_at
LEFT JOIN normalized_price n ON n.source = p.source AND n.item_key = p.item_key
    AND n.retrieved_at = p.retrieved_at AND n.rule_version = ?
WHERE rr.run_id = ?
ORDER BY p.price, m.offer_id
"""


def _group(
    model: str | None, count: float | None, region: str, rental: str, per_gpu: object
) -> GroupKey | None:
    if per_gpu is None or model is None or count is None:
        return None
    return GroupKey(model, int(count), region, rental)


def observed(
    connection: duckdb.DuckDBPyConnection,
    snapshot: Snapshot,
    rule_version: str = rules.RULE_VERSION,
) -> list[Observed]:
    """A snapshot's listings, keyed for changes and absences."""
    params = rules.stored(connection, rule_version)
    found: list[Observed] = []
    if snapshot.source == "synthetic-marketplace":
        seen: set[str] = set()
        rows = connection.execute(_MARKETPLACE, [rule_version, snapshot.run_id])
        for row in rows.fetchall():
            machine, name, gpus, region, rental, _offer, key, at, price = row[:9]
            per_gpu, model, count = row[9:]
            continuity = (machine, name, str(gpus), region, rental)
            joined = "|".join(continuity)
            if joined in seen:  # a machine's lowest offer stands for it (D23)
                continue
            seen.add(joined)
            group = _group(model, count, region, rental, per_gpu)
            found.append(Observed(continuity, joined, key, at, price, per_gpu, group))
        return found
    for row in connection.execute(_AZURE, [rule_version, snapshot.run_id]).fetchall():
        size, region, rental, product, key, at, price, per_gpu, model, count = row
        listing = (size, region, rental, _os(product, params))
        group = _group(model, count, region, rental, per_gpu)
        found.append(Observed(listing, key, key, at, price, per_gpu, group))
    return found


def changes(
    connection: duckdb.DuckDBPyConnection,
    before: Snapshot,
    after: Snapshot,
    rule_version: str = rules.RULE_VERSION,
) -> list[Change]:
    """Keys priced differently in two snapshots; equal prices are not a change."""
    earlier = {o.price_key: o for o in observed(connection, before, rule_version)}
    found = []
    for later in observed(connection, after, rule_version):
        first = earlier.get(later.price_key)
        if first is not None and first.price != later.price:
            found.append(Change(later.price_key, first, later, before, after))
    return sorted(found, key=lambda c: c.price_key)


def _os(product: str | None, params: dict[str, Any]) -> str:
    # The one OS rule (D13), shared with normalization so listings never flip.
    return "windows" if normalize.is_windows(product, params) else "linux"


_LAST_SEEN_AZURE = """
SELECT a.arm_sku_name, p.region, p.rental_type, coalesce(o.os, 'linux'), max(s.idx)
FROM price_observation p
JOIN raw_response rr ON rr.response_id = p.response_id
JOIN _snapshot_order s ON s.run_id = rr.run_id
JOIN azure_retail_price a ON a.source = p.source AND a.item_key = p.item_key
    AND a.retrieved_at = p.retrieved_at
LEFT JOIN _product_os o ON o.product_name = a.product_name
GROUP BY 1, 2, 3, 4
"""

_LAST_SEEN_MARKETPLACE = """
SELECT m.machine_id, m.gpu_name_listed, CAST(m.num_gpus AS VARCHAR), p.region,
       p.rental_type, max(s.idx)
FROM price_observation p
JOIN raw_response rr ON rr.response_id = p.response_id
JOIN _snapshot_order s ON s.run_id = rr.run_id
JOIN marketplace_offer m ON m.source = p.source AND m.item_key = p.item_key
    AND m.retrieved_at = p.retrieved_at
GROUP BY 1, 2, 3, 4, 5
"""


def _last_seen(
    connection: duckdb.DuckDBPyConnection,
    ordered: list[Snapshot],
    params: dict[str, Any],
) -> dict[tuple[str, ...], int]:
    """Each listing's last snapshot index, aggregated in one query."""
    order = pd.DataFrame(
        {"run_id": [s.run_id for s in ordered], "idx": list(range(len(ordered)))}
    )
    connection.register("_snapshot_order", order)
    try:
        if ordered[0].source == "synthetic-marketplace":
            rows = connection.execute(_LAST_SEEN_MARKETPLACE).fetchall()
        else:
            names = [
                row[0]
                for row in connection.execute(
                    "SELECT DISTINCT product_name FROM azure_retail_price"
                    " WHERE product_name IS NOT NULL"
                ).fetchall()
            ]
            products = pd.DataFrame(
                {
                    "product_name": pd.array(names, dtype="string"),
                    "os": pd.array([_os(n, params) for n in names], dtype="string"),
                }
            )
            connection.register("_product_os", products)
            try:
                rows = connection.execute(_LAST_SEEN_AZURE).fetchall()
            finally:
                connection.unregister("_product_os")
    finally:
        connection.unregister("_snapshot_order")
    return {tuple(row[:-1]): row[-1] for row in rows}


def absences(
    connection: duckdb.DuckDBPyConnection,
    source: str,
    rule_version: str = rules.RULE_VERSION,
) -> list[Absence]:
    """Listings missing from the latest snapshot, by how many snapshots in a row."""
    params = rules.stored(connection, rule_version)
    needed = params["not_listed_after_absences"]
    ordered = groups.snapshots(connection, source)
    if len(ordered) < 2:
        return []
    latest = len(ordered) - 1
    found = []
    for listing, index in sorted(_last_seen(connection, ordered, params).items()):
        missing = latest - index
        if missing <= 0:
            continue
        status = NOT_LISTED if missing >= needed else ABSENT_ONCE
        found.append(Absence(listing, status, ordered[index + 1], ordered[index]))
    return found
