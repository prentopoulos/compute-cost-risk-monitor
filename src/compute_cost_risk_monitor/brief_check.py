"""Independent check of a market brief before it is written (Phase 8 design D32).

This module imports no brief, groups, history, quality or calculator code. It reads the
stored tables with its own queries and re-derives, with its own arithmetic, every value
a brief may show:
- per-GPU prices as the published VM-hour price over the stored GPU count;
- region groups, cross-region spreads, changes, absences, Spot pairs and quality counts;
- the bottom line's costs and contingencies, from the workload and `ladder-v1`.

A brief passes only when every number in its text, outside the Records table and
outside names and identifiers, equals one of those values at its shown decimals,
rounded half up, and every time in it is a stored snapshot start or the given as-of
time. A failure names each unmatched number or time and its line and column.
"""

from __future__ import annotations

import json
import re
import statistics
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import duckdb

from compute_cost_risk_monitor.scenarios import LADDER_V1, PERCENT

SOURCE = "azure-retail"
ON_DEMAND, SPOT = "on_demand", "spot"
CONTINGENCY_STEPS = ("up-25", "up-50")
TIME = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC")
NUMBER = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")
# Identifiers that hold digits but are not figures.
MASKS = (
    re.compile(r"https?://\S+"),
    re.compile(r"CC BY \d+(?:\.\d+)?"),
    re.compile(r"\bclaude-[a-z0-9-]+"),
    re.compile(r"\bprompt v\d+"),
    re.compile(r"\b[a-z0-9]+(?:-[a-z0-9]+)*-v\d+\b"),  # groups-v1, ladder-v1, ...
    re.compile(r"\bSHA-256\b"),
)


@dataclass(frozen=True)
class Failure:
    line: int
    column: int
    token: str
    kind: str  # "number" or "time"


@dataclass
class CheckResult:
    numbers: int = 0
    times: int = 0
    failures: list[Failure] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures


@dataclass
class Derived:
    """Every value a brief may show, as display strings, and every name to mask."""

    texts: set[str] = field(default_factory=set)
    times: set[str] = field(default_factory=set)
    names: set[str] = field(default_factory=set)

    def count(self, value: int) -> None:
        self.texts.add(f"{value:,}")

    def per_gpu(self, value: float) -> None:
        self.texts.add(_fixed(value, 4))

    def usd(self, value: float) -> None:
        self.texts.add(_fixed(value, 2))

    def percent(self, value: float) -> None:
        self.texts.add(_fixed(value, 1))

    def published(self, value: float) -> None:
        exponent = Decimal(repr(value)).normalize().as_tuple().exponent
        places = -exponent if isinstance(exponent, int) and exponent < 0 else 0
        self.texts.add(_fixed(value, max(2, places)))

    def plain(self, value: float) -> None:
        exact = Decimal(repr(value)).normalize()
        self.texts.add(f"{exact:,f}")


def _fixed(value: float, places: int) -> str:
    rounded = Decimal(repr(value)).quantize(Decimal(1).scaleb(-places), ROUND_HALF_UP)
    return f"{rounded:,}"


def _when(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _short(size: str) -> str:
    return size.removeprefix("Standard_").replace("_", " ")


_RUNS = (
    "SELECT run_id, started_at FROM collection_run WHERE source = ?"
    " AND status = 'succeeded' ORDER BY started_at, run_id"
)
_COMPARED = """
SELECT n.gpu_model, n.gpu_count, n.region, n.rental_type, p.price, a.arm_sku_name
FROM normalized_price n
JOIN price_observation p ON p.source = n.source AND p.item_key = n.item_key
    AND p.retrieved_at = n.retrieved_at
JOIN raw_response r ON r.response_id = p.response_id
JOIN azure_retail_price a ON a.source = n.source AND a.item_key = n.item_key
    AND a.retrieved_at = n.retrieved_at
WHERE r.run_id = ? AND n.rule_version = ? AND n.excluded_reason IS NULL
"""
_PRICES = """
SELECT p.item_key, p.price, n.gpu_count, n.excluded_reason
FROM price_observation p
JOIN raw_response r ON r.response_id = p.response_id
LEFT JOIN normalized_price n ON n.source = p.source AND n.item_key = p.item_key
    AND n.retrieved_at = p.retrieved_at AND n.rule_version = ?
WHERE r.run_id = ?
"""
_LISTINGS = """
SELECT DISTINCT a.arm_sku_name, p.region, p.rental_type,
       coalesce(a.product_name, ''), r.run_id
FROM price_observation p
JOIN raw_response r ON r.response_id = p.response_id
JOIN collection_run c ON c.run_id = r.run_id AND c.status = 'succeeded'
JOIN azure_retail_price a ON a.source = p.source AND a.item_key = p.item_key
    AND a.retrieved_at = p.retrieved_at
WHERE p.source = ?
"""


def derive(
    connection: duckdb.DuckDBPyConnection,
    as_of: datetime,
    variant: str,
    gpus_per_vm: int,
    gpus: int,
    hours: float,
    rule_version: str = "groups-v1",
) -> Derived:
    """Every value a brief of the latest snapshot may show, re-derived."""
    derived = Derived()
    runs = connection.execute(_RUNS, [SOURCE]).fetchall()
    row = connection.execute(
        "SELECT parameters FROM rule_set WHERE rule_version = ?", [rule_version]
    ).fetchone()
    params: dict[str, Any] = json.loads(row[0]) if row else {}
    derived.times.add(_when(as_of))
    derived.names.add(variant)  # an input name, such as "B200", is not a figure
    derived.times.update(_when(at) for _, at in runs)
    derived.names.update(run for run, _ in runs)
    if not runs:
        return derived
    latest = runs[-1][0]
    _names(connection, derived)
    rows = connection.execute(_COMPARED, [latest, rule_version]).fetchall()
    region_groups: dict[tuple[str, int, str, str], list[tuple[float, str]]] = (
        defaultdict(list)
    )
    for model, count, region, rental, price, size in rows:
        region_groups[(model, int(count), region, rental)].append((price / count, size))
    _groups(derived, region_groups)
    spread = _regions(derived, region_groups, int(params.get("thin_below_regions", 5)))
    _bottom_line(derived, spread, variant, gpus_per_vm, gpus, hours)
    _spot(derived, region_groups, variant, gpus_per_vm)
    _changes(connection, derived, runs, rule_version)
    _absences(connection, derived, runs, params)
    _quality(connection, derived, latest, rule_version, runs, params)
    return derived


def _names(connection: duckdb.DuckDBPyConnection, derived: Derived) -> None:
    for (size,) in connection.execute(
        "SELECT DISTINCT arm_sku_name FROM azure_retail_price WHERE arm_sku_name"
        " IS NOT NULL"
    ).fetchall():
        derived.names.update((size, _short(size)))
    for code, location in connection.execute(
        "SELECT DISTINCT arm_region_name, location FROM azure_retail_price"
    ).fetchall():
        derived.names.update(name for name in (code, location) if name)
    for (model,) in connection.execute(
        "SELECT DISTINCT gpu_model FROM gpu_sku_map"
    ).fetchall():
        # The model alone ("H100") is a name too, as the drafter may write it.
        derived.names.update((model, model.split()[0]))


def _groups(
    derived: Derived,
    region_groups: dict[tuple[str, int, str, str], list[tuple[float, str]]],
) -> None:
    by_variant: dict[str, list[int]] = defaultdict(list)
    for (model, count, _region, _rental), members in region_groups.items():
        by_variant[model].append(len(members))
        derived.count(count)
    single = 0
    for sizes in by_variant.values():
        derived.count(len(sizes))
        derived.count(sum(1 for n in sizes if n == 1))
        single += sum(1 for n in sizes if n == 1)
    derived.count(len(region_groups))
    derived.count(len(by_variant))
    derived.count(single)


def _regions(
    derived: Derived,
    region_groups: dict[tuple[str, int, str, str], list[tuple[float, str]]],
    thin_below: int,
) -> dict[tuple[str, int, str], list[float]]:
    spread: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    for (model, count, _region, rental), members in sorted(region_groups.items()):
        spread[(model, count, rental)].append(min(price for price, _ in members))
    thin = 0
    for lows in spread.values():
        derived.count(len(lows))
        for value in (min(lows), statistics.median(lows), max(lows)):
            derived.per_gpu(value)
        thin += len(lows) < thin_below
    derived.count(len(spread))
    derived.count(thin)
    derived.count(thin_below)
    return spread


def _bottom_line(
    derived: Derived,
    spread: dict[tuple[str, int, str], list[float]],
    variant: str,
    gpus_per_vm: int,
    gpus: int,
    hours: float,
) -> None:
    derived.count(gpus)
    derived.count(gpus // gpus_per_vm)
    derived.plain(hours)
    lows = spread.get((variant, gpus_per_vm, ON_DEMAND))
    if not lows:
        return
    gpu_hours = gpus * hours
    derived.usd(gpu_hours * min(lows))
    derived.usd(gpu_hours * max(lows))
    steps = {step.id: step for step in LADDER_V1}
    for step_id in CONTINGENCY_STEPS:
        step = steps[step_id]
        if step.kind != PERCENT:  # pragma: no cover - both are % steps in ladder-v1
            continue
        derived.plain(step.magnitude)
        derived.usd(gpu_hours * min(lows) * step.magnitude / 100.0)


def _spot(
    derived: Derived,
    region_groups: dict[tuple[str, int, str, str], list[tuple[float, str]]],
    variant: str,
    gpus_per_vm: int,
) -> None:
    # The counts cover the workload's GPU and count only, like the brief's table.
    payg = {
        (model, count, region, size): price
        for (model, count, region, rental), members in region_groups.items()
        if rental == ON_DEMAND
        for price, size in members
    }
    total = paired = equal = above = 0
    for (model, count, region, rental), members in region_groups.items():
        if rental != SPOT or (model, count) != (variant, gpus_per_vm):
            continue
        for price, size in members:
            total += 1
            derived.per_gpu(price)
            twin = payg.get((model, count, region, size))
            if twin is None:
                continue
            paired += 1
            equal += price == twin
            above += price > twin
            derived.per_gpu(twin)
            derived.percent(100.0 * price / twin)
    for value in (total, paired, equal, above):
        derived.count(value)


def _changes(
    connection: duckdb.DuckDBPyConnection,
    derived: Derived,
    runs: list[tuple[str, datetime]],
    rule_version: str,
) -> None:
    if len(runs) < 2:
        derived.count(len(runs))
        return

    def prices(run: str) -> dict[str, tuple[float, float | None]]:
        found = {}
        for key, price, count, reason in connection.execute(
            _PRICES, [rule_version, run]
        ).fetchall():
            per_gpu = price / count if count and reason is None else None
            found[key] = (price, per_gpu)
        return found

    before, after = prices(runs[-2][0]), prices(runs[-1][0])
    changed = 0
    for key, (price, per_gpu) in after.items():
        if key not in before or before[key][0] == price:
            continue
        changed += 1
        derived.published(before[key][0])
        derived.published(price)
        for value in (before[key][1], per_gpu):
            if value is not None:
                derived.per_gpu(value)
    derived.count(changed)


def _os(product: str, params: dict[str, Any]) -> str:
    # Windows when the product name's last word is a stored Windows suffix (rule D13).
    words = product.split()
    windows = words and words[-1] in params.get("windows_product_suffixes", ())
    return "windows" if windows else "linux"


def _absences(
    connection: duckdb.DuckDBPyConnection,
    derived: Derived,
    runs: list[tuple[str, datetime]],
    params: dict[str, Any],
) -> None:
    # A listing is keyed by size, region, rental type and the OS its product name
    # gives; its last snapshot sets how many snapshots in a row it has been missing.
    needed = int(params.get("not_listed_after_absences", 2))
    order = {run: idx for idx, (run, _) in enumerate(runs)}
    last: dict[tuple[str, str, str, str], int] = {}
    for size, region, rental, product, run in connection.execute(
        _LISTINGS, [SOURCE]
    ).fetchall():
        key = (size, region, rental, _os(product, params))
        last[key] = max(last.get(key, -1), order[run])
    latest = len(runs) - 1
    missing = [latest - idx for idx in last.values() if idx < latest]
    derived.count(sum(1 for n in missing if n < needed))
    derived.count(sum(1 for n in missing if n >= needed))


def _quality(
    connection: duckdb.DuckDBPyConnection,
    derived: Derived,
    latest: str,
    rule_version: str,
    runs: list[tuple[str, datetime]],
    params: dict[str, Any],
) -> None:
    (observations,) = connection.execute(
        "SELECT count(*) FROM price_observation p JOIN raw_response r"
        " ON r.response_id = p.response_id WHERE r.run_id = ?",
        [latest],
    ).fetchone() or (0,)
    derived.count(int(observations))
    for _reason, n in connection.execute(
        "SELECT coalesce(n.excluded_reason, 'normalized'), count(*)"
        " FROM normalized_price n JOIN price_observation p ON p.source = n.source"
        " AND p.item_key = n.item_key AND p.retrieved_at = n.retrieved_at"
        " JOIN raw_response r ON r.response_id = p.response_id"
        " WHERE r.run_id = ? AND n.rule_version = ? GROUP BY 1",
        [latest, rule_version],
    ).fetchall():
        derived.count(int(n))
    # A size is not in the map when no row of it carries a mapped size, whatever reason
    # excluded the row (a Windows-only unmapped size counts too).
    (unmapped,) = connection.execute(
        "SELECT count(DISTINCT a.arm_sku_name) FROM normalized_price n"
        " JOIN price_observation p ON p.source = n.source AND p.item_key = n.item_key"
        " AND p.retrieved_at = n.retrieved_at"
        " JOIN raw_response r ON r.response_id = p.response_id"
        " JOIN azure_retail_price a ON a.source = n.source AND a.item_key = n.item_key"
        " AND a.retrieved_at = n.retrieved_at"
        " WHERE r.run_id = ? AND n.rule_version = ?"
        " AND a.arm_sku_name IS NOT NULL AND n.arm_sku_name IS NULL",
        [latest, rule_version],
    ).fetchone() or (0,)
    derived.count(int(unmapped))
    derived.count(len(runs))
    derived.count((runs[-1][1] - runs[0][1]).days)
    derived.count(int(params.get("stale_after_days", 7)))


def _masked(line: str, names: Iterable[str]) -> str:
    for pattern in MASKS:
        line = pattern.sub(lambda m: " " * len(m.group(0)), line)
    for name in sorted(names, key=len, reverse=True):
        line = line.replace(name, " " * len(name))
    return line


def check(text: str, derived: Derived) -> CheckResult:
    """Every number and time in the brief, outside its Records table, re-derived."""
    result = CheckResult()
    # Code appends the Records table last, so only the last such heading starts it; one
    # inside a section's prose must not hide the numbers after it.
    head, sep, _ = text.replace("\r\n", "\n").rpartition("\n## Records\n")
    body = head if sep else text.replace("\r\n", "\n")
    names = [name for name in derived.names if any(ch.isdigit() for ch in name)]
    for number, line in enumerate(body.splitlines(), start=1):
        masked = _masked(line, names)
        for match in TIME.finditer(masked):
            result.times += 1
            if match.group(0) not in derived.times:
                result.failures.append(
                    Failure(number, match.start() + 1, match.group(0), "time")
                )
        masked = TIME.sub(lambda m: " " * len(m.group(0)), masked)
        for match in NUMBER.finditer(masked):
            result.numbers += 1
            if match.group(0) not in derived.texts:
                result.failures.append(
                    Failure(number, match.start() + 1, match.group(0), "number")
                )
    return result
