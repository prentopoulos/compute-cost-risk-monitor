"""DuckDB connection helper and schema runner.

Open every connection through `connect`: DuckDB reports TIMESTAMPTZ values in the
session time zone, which otherwise defaults to the machine's zone.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

import duckdb

MEMORY = ":memory:"
_MIGRATION = re.compile(r"(?P<version>\d{3})_(?P<name>[a-z0-9_]+)\.sql")


def connect(path: str | Path = MEMORY) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection whose session time zone is UTC."""
    if str(path) != MEMORY:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path), config={"TimeZone": "UTC"})


def migrations() -> list[tuple[int, str, str]]:
    """Return packaged schema files as (version, description, sql), in order."""
    found = []
    for entry in (
        resources.files("compute_cost_risk_monitor").joinpath("schema").iterdir()
    ):
        match = _MIGRATION.fullmatch(entry.name)
        if match:
            description = match["name"].replace("_", " ")
            found.append((int(match["version"]), description, entry.read_text("utf-8")))
    return sorted(found)


def applied_versions(connection: duckdb.DuckDBPyConnection) -> set[int]:
    exists = connection.execute(
        "SELECT count(*) FROM duckdb_tables() WHERE table_name = 'schema_version'"
    ).fetchone()
    if not exists or exists[0] == 0:
        return set()
    return {
        row[0]
        for row in connection.execute("SELECT version FROM schema_version").fetchall()
    }


def create_schema(connection: duckdb.DuckDBPyConnection) -> list[int]:
    """Apply packaged schema versions not yet applied; return those applied now."""
    done = applied_versions(connection)
    applied: list[int] = []
    for version, description, sql in migrations():
        if version in done:
            continue
        connection.begin()
        try:
            connection.execute(sql)
            connection.execute(
                "INSERT INTO schema_version VALUES (?, ?, ?)",
                [version, datetime.now(UTC), description],
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        applied.append(version)
    return applied
