"""The GPU size map: Azure VM sizes to GPU variant, memory and count, from Learn.

The packaged CSV is map version gpu-map-v1, built by hand from Microsoft Learn VM size
pages (phase-3-normalization design D3, D9, D14). Loading validates every row before
anything is written; storing writes the rows once and refuses a stored version that
differs.
"""

from __future__ import annotations

import csv
import io
import math
import re
from dataclasses import dataclass
from fractions import Fraction
from importlib import resources
from urllib.parse import urlsplit

import duckdb

from compute_cost_risk_monitor.rules import FrozenMismatch

MAP_VERSION = "gpu-map-v1"
COLUMNS = (
    "arm_sku_name",
    "gpu_model",
    "gpu_form_factor",
    "gpu_vram_gb",
    "gpu_count",
    "source_url",
    "notes",
)
_LABEL = re.compile(r"(?P<model>\S.*?) (?P<memory>\d+)GB(?: confidential)?")
_RETRIEVED = re.compile(r"retrieved \d{4}-\d{2}-\d{2}")
_COUNT = re.compile(r"[1-9]\d*(?:/[1-9]\d*)?")


class MapError(ValueError):
    """The map file breaks a rule; the message names the line and size."""


@dataclass(frozen=True)
class MapRow:
    arm_sku_name: str
    gpu_model: str  # the variant label, e.g. "H100 NVL 94GB"
    gpu_form_factor: str | None
    gpu_vram_gb: float  # per whole GPU
    gpu_count: Fraction  # GPUs per VM; a fraction for partial-GPU sizes
    source_url: str
    notes: str

    @property
    def whole(self) -> bool:
        return self.gpu_count.denominator == 1

    def stored(self) -> tuple[object, ...]:
        """The row as gpu_sku_map holds it, after the version column."""
        return (
            self.arm_sku_name,
            self.gpu_model,
            self.gpu_form_factor,
            self.gpu_vram_gb,
            float(self.gpu_count),
            self.source_url,
            self.notes,
        )


def _row(line: int, record: dict[str, str]) -> MapRow:
    def fail(why: str) -> MapError:
        return MapError(f"line {line} ({record.get('arm_sku_name') or '?'}): {why}")

    if any(record.get(column) is None for column in COLUMNS):
        raise fail("missing column value")
    size = record["arm_sku_name"].strip()
    label = record["gpu_model"].strip()
    form = record["gpu_form_factor"].strip() or None
    if not size.startswith("Standard_N") or size != record["arm_sku_name"]:
        raise fail("size must be an exact Standard_N ARM name")
    try:
        vram = float(record["gpu_vram_gb"])
    except ValueError:
        raise fail("memory is not a number") from None
    if not math.isfinite(vram) or vram <= 0:
        raise fail("memory must be greater than zero")
    if not _COUNT.fullmatch(record["gpu_count"].strip()):
        raise fail("GPU count must be a whole number or fraction greater than zero")
    count = Fraction(record["gpu_count"].strip())
    match = _LABEL.fullmatch(label)
    if match is None or float(match["memory"]) != vram:
        raise fail("label must be '<model>[ <form factor>] <memory>GB' matching memory")
    if form is not None and f" {form} " not in f" {match['model']} ":
        raise fail("label must name the form factor")
    url = urlsplit(record["source_url"].strip())
    if url.scheme != "https" or url.hostname != "learn.microsoft.com":
        raise fail("source URL must be on https://learn.microsoft.com")
    if not _RETRIEVED.search(record["notes"]):
        raise fail("notes must give the retrieval date ('retrieved YYYY-MM-DD')")
    return MapRow(
        size, label, form, vram, count, record["source_url"].strip(), record["notes"]
    )


def parse(text: str) -> dict[str, MapRow]:
    """Validate map CSV text; '#' lines are comments. Raise MapError on any bad row."""
    lines = [
        (number, line)
        for number, line in enumerate(text.lstrip("﻿").splitlines(), start=1)
        if line.strip() and not line.startswith("#")
    ]
    if not lines:
        raise MapError("map file is empty")
    reader = csv.DictReader(io.StringIO("\n".join(line for _, line in lines)))
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise MapError(f"line {lines[0][0]}: header must be {','.join(COLUMNS)}")
    rows: dict[str, MapRow] = {}
    for (number, _), record in zip(lines[1:], reader, strict=True):
        if None in record:
            raise MapError(f"line {number}: too many fields")
        row = _row(number, record)
        if row.arm_sku_name in rows:
            raise MapError(f"line {number} ({row.arm_sku_name}): size listed twice")
        rows[row.arm_sku_name] = row
    return rows


def load() -> dict[str, MapRow]:
    """The packaged gpu-map-v1 rows, keyed by ARM size name."""
    path = resources.files("compute_cost_risk_monitor").joinpath(
        "reference", "gpu_sku_map_v1.csv"
    )
    return parse(path.read_text("utf-8-sig"))


def store(
    connection: duckdb.DuckDBPyConnection,
    rows: dict[str, MapRow],
    version: str = MAP_VERSION,
) -> int:
    """Insert the map version if absent; return rows written. Refuse a changed one."""
    stored = {
        row[0]: row
        for row in connection.execute(
            "SELECT arm_sku_name, gpu_model, gpu_form_factor, gpu_vram_gb, gpu_count,"
            " source_url, notes FROM gpu_sku_map WHERE mapping_version = ?",
            [version],
        ).fetchall()
    }
    if stored:
        expected = {name: row.stored() for name, row in rows.items()}
        if stored != expected:
            changed = sorted(set(stored) ^ set(expected)) or sorted(
                name for name in stored if stored[name] != expected[name]
            )
            raise FrozenMismatch(
                f"stored map {version} differs from the code: {', '.join(changed[:5])}"
            )
        return 0
    connection.executemany(
        "INSERT INTO gpu_sku_map VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [[version, *row.stored()] for row in rows.values()],
    )
    return len(rows)
