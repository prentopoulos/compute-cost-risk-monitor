"""The counts-only quality report per source and latest snapshot (design D6, D7,
D21).

It says how fresh the latest snapshot is, how every stored row was handled, what the
run records rejected or repeated, which fields are missing, and how many groups are
thin or hold one price. It never holds a price. A source without a succeeded run has
no snapshot, which is not the same as having no prices.

    uv run python -m compute_cost_risk_monitor.quality [--db PATH] [--as-of TIME]

"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb

from compute_cost_risk_monitor import db, groups, history, rules
from compute_cost_risk_monitor.collect import DEFAULT_DB

SOURCES = ("azure-retail", "synthetic-marketplace")
AZURE_OPTIONAL = ("location", "product_name", "effective_start_date")
# An offer without VRAM is never compared (unmapped_gpu_name), so VRAM is not counted.
MARKETPLACE_OPTIONAL = ("country_code",)
_WIN = re.compile(r"\bWin")
# A count the run records lack (no summary row): unknown, never zero.
UNKNOWN = "unknown (no run summary)"


@dataclass
class QualityReport:
    source: str
    as_of: datetime
    snapshot: groups.Snapshot | None = None
    stale: bool | None = None
    observations: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    unmapped_sizes: list[str] = field(default_factory=list)
    rejected: dict[str, int] = field(default_factory=dict)
    rejected_total: int | None = 0  # None when the run has no summary row
    out_of_scope: int | None = 0  # None when the run has no summary row
    repeats: int | None = 0
    duplicates: dict[str, int | None] = field(default_factory=dict)
    missing_fields: dict[str, int] = field(default_factory=dict)
    os_ambiguous: int = 0
    region_groups: int = 0
    single_price_groups: int = 0
    summaries: int = 0
    thin: int = 0
    changes: int | None = None  # None when there is no previous snapshot
    not_normalized: int = 0  # observations with no row under the rule version
    absent_once: int = 0
    not_listed: int = 0


def shown(count: int | None) -> int | str:
    """A count for display: one the run records lack reads as unknown."""
    return UNKNOWN if count is None else count


def _one(connection: duckdb.DuckDBPyConnection, sql: str, *params: object) -> int:
    row = connection.execute(sql, list(params)).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def _os_ambiguous(connection: duckdb.DuckDBPyConnection, run_id: str) -> int:
    """Rows naming "Win" anywhere but as the product name's last word (D13)."""
    rows = connection.execute(
        "SELECT a.product_name, a.sku_name, a.meter_name FROM azure_retail_price a"
        " JOIN price_observation p ON p.source = a.source AND p.item_key = a.item_key"
        " AND p.retrieved_at = a.retrieved_at"
        " JOIN raw_response rr ON rr.response_id = p.response_id WHERE rr.run_id = ?",
        [run_id],
    ).fetchall()
    count = 0
    for product, sku, meter in rows:
        words = (product or "").split()
        if (
            any(_WIN.search(word) for word in words[:-1])
            or _WIN.search(sku or "")
            or _WIN.search(meter or "")
        ):
            count += 1
    return count


def build(
    connection: duckdb.DuckDBPyConnection,
    source: str,
    as_of: datetime,
    rule_version: str = rules.RULE_VERSION,
    region_groups: list[groups.RegionGroup] | None = None,
) -> QualityReport:
    """The report for a source's latest snapshot as of a given time.

    A caller that already built the latest snapshot's region groups may pass them, so
    they are not built twice.
    """
    report = QualityReport(source, as_of)
    ordered = groups.snapshots(connection, source)
    if not ordered:
        return report
    params = rules.stored(connection, rule_version)
    latest = ordered[-1]
    run = latest.run_id
    report.snapshot = latest
    report.stale = as_of - latest.started_at > timedelta(
        days=params["stale_after_days"]
    )
    in_run = (
        " FROM normalized_price n JOIN price_observation p ON p.source = n.source"
        " AND p.item_key = n.item_key AND p.retrieved_at = n.retrieved_at"
        " JOIN raw_response rr ON rr.response_id = p.response_id"
        " LEFT JOIN azure_retail_price a ON a.source = n.source"
        " AND a.item_key = n.item_key AND a.retrieved_at = n.retrieved_at"
        " LEFT JOIN marketplace_offer m ON m.source = n.source"
        " AND m.item_key = n.item_key AND m.retrieved_at = n.retrieved_at"
        " WHERE rr.run_id = ? AND n.rule_version = ?"
    )
    report.observations = _one(
        connection,
        "SELECT count(*) FROM price_observation p"
        " JOIN raw_response rr ON rr.response_id = p.response_id WHERE rr.run_id = ?",
        run,
    )
    report.by_status = {
        status: count
        for status, count in connection.execute(
            "SELECT coalesce(n.excluded_reason, 'normalized'), count(*)"
            + in_run
            + " GROUP BY 1 ORDER BY 1",
            [run, rule_version],
        ).fetchall()
    }
    report.not_normalized = report.observations - sum(report.by_status.values())
    report.unmapped_sizes = [
        row[0]
        for row in connection.execute(
            "SELECT DISTINCT a.arm_sku_name"
            + in_run
            + " AND a.arm_sku_name IS NOT NULL AND n.arm_sku_name IS NULL ORDER BY 1",
            [run, rule_version],
        ).fetchall()
    ]
    # Each source's own optional fields (Phase 4 D31): never Azure fields for offers.
    detail, names = (
        ("m", MARKETPLACE_OPTIONAL)
        if source == "synthetic-marketplace"
        else ("a", AZURE_OPTIONAL)
    )
    report.missing_fields = {
        name: _one(
            connection,
            # Aliases and names come from the fixed tuples above, never from input.
            f"SELECT count(*) {in_run} AND n.excluded_reason IS NULL"  # noqa: S608
            f" AND {detail}.source IS NOT NULL AND {detail}.{name} IS NULL",
            run,
            rule_version,
        )
        for name in names
    }
    report.rejected = {
        reason: count
        for reason, count in connection.execute(
            "SELECT reason, occurrences FROM collection_run_tally"
            " WHERE run_id = ? AND kind = 'rejected' ORDER BY reason",
            [run],
        ).fetchall()
    }
    summary = connection.execute(
        "SELECT out_of_scope, repeats FROM collection_run_summary WHERE run_id = ?",
        [run],
    ).fetchone()
    # Tallies exist only for counts above zero; the summary row is the only record of a
    # zero. Without it, a count with no tally row is unknown, never 0.
    if summary:
        report.out_of_scope, report.repeats = summary
        report.rejected_total = sum(report.rejected.values())
    else:
        report.out_of_scope = report.repeats = report.rejected_total = None
    if region_groups is None:
        region_groups = groups.region_groups(connection, latest, rule_version)
    report.region_groups = len(region_groups)
    if source == "synthetic-marketplace":
        report.duplicates = {
            groups.DUPLICATE: sum(
                groups.DUPLICATE in m.flags for g in region_groups for m in g.members
            )
        }
        report.thin = sum(groups.THIN in g.labels for g in region_groups)
    else:
        shared = _one(
            connection,
            "SELECT coalesce(sum(occurrences), 0) FROM collection_run_tally"
            " WHERE run_id = ? AND kind = 'flagged'"
            " AND reason = 'shared_meter_key'",
            run,
        )
        report.duplicates = {
            "repeats": report.repeats,
            "shared_meter_key": shared if shared or summary else None,
        }
        report.os_ambiguous = _os_ambiguous(connection, run)
        report.single_price_groups = sum(
            groups.SINGLE in g.labels for g in region_groups
        )
        summaries = groups.cross_region(region_groups, params["thin_below_regions"])
        report.summaries = len(summaries)
        report.thin = sum(groups.THIN in s.labels for s in summaries)
    if len(ordered) > 1:
        report.changes = len(
            history.changes(connection, ordered[-2], latest, rule_version)
        )
    absences = history.absences(connection, source, rule_version)
    report.absent_once = sum(a.status == history.ABSENT_ONCE for a in absences)
    report.not_listed = sum(a.status == history.NOT_LISTED for a in absences)
    return report


def render(report: QualityReport) -> str:
    """The report as text: counts, names and keys only, never a price (D17)."""
    if report.snapshot is None:
        return f"{report.source}: no snapshot (no succeeded run)"
    snap = report.snapshot
    lines = [
        f"{report.source}: snapshot {snap.run_id} ({snap.data_label}),"
        f" started {snap.started_at.isoformat()}"
        + (" — STALE" if report.stale else ", not stale")
        + f" as of {report.as_of.isoformat()}",
        f"  observations {report.observations}",
    ]
    if report.not_normalized:
        lines.append(
            f"    NOT NORMALIZED: {report.not_normalized} observations have no row"
            " under the rule set; run normalize"
        )
    lines += [f"    {status}: {n}" for status, n in report.by_status.items()]
    lines.append(
        f"  sizes not in the map: {len(report.unmapped_sizes)}"
        + (f" ({', '.join(report.unmapped_sizes)})" if report.unmapped_sizes else "")
    )
    lines.append(
        f"  run records: out of scope {shown(report.out_of_scope)},"
        f" repeats {shown(report.repeats)}, rejected {shown(report.rejected_total)}"
    )
    lines += [f"    rejected {reason}: {n}" for reason, n in report.rejected.items()]
    lines.append(
        "  duplicates: "
        + ", ".join(f"{k} {shown(v)}" for k, v in report.duplicates.items())
    )
    lines.append(
        "  missing among compared rows: "
        + ", ".join(f"{k} {v}" for k, v in report.missing_fields.items())
        + f"; os_ambiguous {report.os_ambiguous}"
    )
    lines.append(
        f"  region groups {report.region_groups} (single list price"
        f" {report.single_price_groups}); cross-region summaries {report.summaries};"
        f" thin {report.thin}"
    )
    changed = "no previous snapshot" if report.changes is None else str(report.changes)
    lines.append(
        f"  changes since previous snapshot: {changed}; absent once"
        f" {report.absent_once}; not listed {report.not_listed}"
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Print the report for every source; 2 when the database or rule set is missing."""
    parser = argparse.ArgumentParser(
        prog="python -m compute_cost_risk_monitor.quality",
        description="Counts-only quality report for each source's latest snapshot.",
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="DuckDB file")
    parser.add_argument(
        "--as-of", type=datetime.fromisoformat, help="UTC time (default: now)"
    )
    args = parser.parse_args(argv)
    as_of = args.as_of or datetime.now(UTC)
    if as_of.tzinfo is None:
        print("refused: --as-of needs a time zone", file=sys.stderr)
        return 2
    as_of = as_of.astimezone(UTC)  # shown in UTC, like every other time
    if not args.db.is_file():
        print(f"refused: no database at {args.db}", file=sys.stderr)
        return 2
    try:
        connection = db.connect(args.db)
    except duckdb.Error as error:
        print(f"refused: cannot open {args.db}: {error}", file=sys.stderr)
        return 2
    try:
        reports = [build(connection, source, as_of) for source in SOURCES]
    except KeyError as error:
        print(f"refused: {error}; run normalize first", file=sys.stderr)
        return 2
    finally:
        connection.close()
    print("\n".join(render(report) for report in reports))
    return 0


if __name__ == "__main__":
    sys.exit(main())
