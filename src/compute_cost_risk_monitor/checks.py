"""Independent checks of stored normalized rows (phase-3-normalization design D16).

This module imports no normalization, rule or map code. It reads the stored tables and
the rule set's stored parameters, and re-derives what must hold: the multiply-back
identity, one row per observation, reasons and prices that exclude each other, GPU
fields that equal the map's, compared rows that meet the rules, and totals that
reconcile with the run records. Failures name rows by key, never by price.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any

import duckdb

REL_TOL = 1e-9
SHOWN = 5  # failing keys listed per check


@dataclass
class Verdict:
    name: str
    checked: int
    failures: list[str] = field(default_factory=list)
    failed: int = 0

    @property
    def passed(self) -> bool:
        return self.failed == 0

    def fail(self, what: str) -> None:
        self.failed += 1
        if len(self.failures) < SHOWN:
            self.failures.append(what)


def _params(connection: duckdb.DuckDBPyConnection, version: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT parameters FROM rule_set WHERE rule_version = ?", [version]
    ).fetchone()
    if row is None:
        raise KeyError(f"rule set {version} is not stored")
    value: dict[str, Any] = json.loads(row[0])
    return value


def multiply_back(connection: duckdb.DuckDBPyConnection, version: str) -> Verdict:
    rows = connection.execute(
        "SELECT n.source, n.item_key, n.usd_per_gpu_hour, n.gpu_count, p.price"
        " FROM normalized_price n JOIN price_observation p"
        " USING (source, item_key, retrieved_at)"
        " WHERE n.rule_version = ? AND n.excluded_reason IS NULL",
        [version],
    ).fetchall()
    verdict = Verdict("multiply_back", len(rows))
    for source, key, per_gpu, count, price in rows:
        if not math.isclose(per_gpu * count, price, rel_tol=REL_TOL, abs_tol=0.0):
            verdict.fail(f"{source} {key}")
    return verdict


def one_row_per_observation(
    connection: duckdb.DuckDBPyConnection, version: str
) -> Verdict:
    rows = connection.execute(
        "SELECT p.source, p.item_key, count(n.item_key) FROM price_observation p"
        " LEFT JOIN normalized_price n ON n.source = p.source"
        " AND n.item_key = p.item_key AND n.retrieved_at = p.retrieved_at"
        " AND n.rule_version = ? GROUP BY p.source, p.item_key, p.retrieved_at",
        [version],
    ).fetchall()
    verdict = Verdict("one_row_per_observation", len(rows))
    for source, key, count in rows:
        if count != 1:
            verdict.fail(f"{source} {key}: {count} rows")
    return verdict


def reason_or_price(connection: duckdb.DuckDBPyConnection, version: str) -> Verdict:
    rows = connection.execute(
        "SELECT source, item_key, excluded_reason, usd_per_gpu_hour, gpu_model,"
        " exclusions FROM normalized_price WHERE rule_version = ?",
        [version],
    ).fetchall()
    params = _params(connection, version)
    known = set(params["exclusion_order"]) | set(params["marketplace_exclusion_order"])
    verdict = Verdict("reason_or_price", len(rows))
    for source, key, reason, per_gpu, model, exclusions in rows:
        if (reason is None) == (per_gpu is None):
            verdict.fail(f"{source} {key}: reason and price must exclude each other")
        elif reason is not None and reason not in known:
            verdict.fail(f"{source} {key}: unknown reason {reason}")
        elif reason is None and model is None:
            verdict.fail(f"{source} {key}: normalized without a GPU variant")
        elif exclusions != params["exclusions"]:
            verdict.fail(f"{source} {key}: exclusions text differs from the rule set")
    return verdict


def gpu_fields_match(connection: duckdb.DuckDBPyConnection, version: str) -> Verdict:
    params = _params(connection, version)
    rows = connection.execute(
        "SELECT n.source, n.item_key, n.excluded_reason, n.gpu_model, n.gpu_count,"
        " n.mapping_version, g.gpu_model, g.gpu_count, m.gpu_name_listed, m.num_gpus,"
        " m.gpu_vram_gb FROM normalized_price n"
        " LEFT JOIN gpu_sku_map g ON g.mapping_version = n.mapping_version"
        " AND g.arm_sku_name = n.arm_sku_name"
        " LEFT JOIN marketplace_offer m ON m.source = n.source"
        " AND m.item_key = n.item_key AND m.retrieved_at = n.retrieved_at"
        " WHERE n.rule_version = ?",
        [version],
    ).fetchall()
    names = params["marketplace_gpu_names"]
    verdict = Verdict("gpu_fields_match", len(rows))
    for row in rows:
        source, key, reason, model, count, map_version = row[:6]
        map_model, map_count, listed, gpus, vram = row[6:]
        if source == "azure-retail":
            if map_version is None:
                if reason is None or model is not None or count is not None:
                    verdict.fail(f"{source} {key}: unmapped row carries GPU fields")
            elif map_version != params["map_version"]:
                verdict.fail(f"{source} {key}: map {map_version} is not the rule set's")
            elif (model, count) != (map_model, map_count):
                verdict.fail(f"{source} {key}: GPU fields differ from the map")
        else:
            entry = names.get(listed)
            expected = entry["variant"] if entry and entry["vram_gb"] == vram else None
            if count != gpus or model != expected:
                verdict.fail(f"{source} {key}: GPU fields differ from the offer")
    return verdict


def compared_rows_follow_rules(
    connection: duckdb.DuckDBPyConnection, version: str
) -> Verdict:
    params = _params(connection, version)
    rows = connection.execute(
        "SELECT n.source, n.item_key, n.rental_type, n.region, n.gpu_count,"
        " p.price_unit, a.product_name FROM normalized_price n"
        " JOIN price_observation p USING (source, item_key, retrieved_at)"
        " LEFT JOIN azure_retail_price a USING (source, item_key, retrieved_at)"
        " WHERE n.rule_version = ? AND n.excluded_reason IS NULL",
        [version],
    ).fetchall()
    government = tuple(params["government_region_prefixes"])
    windows = set(params["windows_product_suffixes"])
    verdict = Verdict("compared_rows_follow_rules", len(rows))
    for source, key, rental, region, count, unit, product in rows:
        last = (product or "").split()[-1:] or [""]
        if rental not in params["compared_rental_types"]:
            verdict.fail(f"{source} {key}: rental type {rental} is not compared")
        elif count != math.floor(count) or count < 1:
            verdict.fail(f"{source} {key}: GPU count is not whole")
        elif source == "azure-retail" and unit != params["hourly_unit"]:
            verdict.fail(f"{source} {key}: unit is not hourly")
        elif source == "azure-retail" and region.startswith(government):
            verdict.fail(f"{source} {key}: government region {region}")
        elif source == "azure-retail" and last[0] in windows:
            verdict.fail(f"{source} {key}: Windows product")
    return verdict


def totals_reconcile(connection: duckdb.DuckDBPyConnection, version: str) -> Verdict:
    rows = connection.execute(
        "SELECT r.run_id, s.observations_stored, count(DISTINCT p.item_key),"
        " count(n.item_key) FROM collection_run r"
        " LEFT JOIN collection_run_summary s ON s.run_id = r.run_id"
        " LEFT JOIN raw_response rr ON rr.run_id = r.run_id"
        " LEFT JOIN price_observation p ON p.response_id = rr.response_id"
        " LEFT JOIN normalized_price n ON n.source = p.source"
        " AND n.item_key = p.item_key AND n.retrieved_at = p.retrieved_at"
        " AND n.rule_version = ? GROUP BY r.run_id, s.observations_stored",
        [version],
    ).fetchall()
    verdict = Verdict("totals_reconcile", len(rows))
    for run_id, stored, observed, normalized in rows:
        if stored is not None and stored != observed:
            verdict.fail(f"run {run_id}: summary says {stored}, found {observed}")
        elif normalized != observed:
            verdict.fail(f"run {run_id}: {normalized} rows for {observed} observations")
    return verdict


CHECKS = (
    multiply_back,
    one_row_per_observation,
    reason_or_price,
    gpu_fields_match,
    compared_rows_follow_rules,
    totals_reconcile,
)


def run(connection: duckdb.DuckDBPyConnection, version: str) -> list[Verdict]:
    """Every check, in order. A failing check never stops the others."""
    return [check(connection, version) for check in CHECKS]
