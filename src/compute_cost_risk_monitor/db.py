"""DuckDB connection helper and schema runner.

Open every connection through `connect`: DuckDB reports TIMESTAMPTZ values in the
session time zone, which otherwise defaults to the machine's zone.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

MEMORY = ":memory:"
TEXT = "string[python]"
_MIGRATION = re.compile(r"(?P<version>\d{3})_(?P<name>[a-z0-9_]+)\.sql")


def connect(
    path: str | Path = MEMORY, read_only: bool = False
) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection whose session time zone is UTC.

    A read-only connection never creates a file or folder; a missing file is an error.
    While it is open, other processes cannot write the file (Phase 4 design D13).
    """
    if str(path) != MEMORY and not read_only:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path), read_only=read_only, config={"TimeZone": "UTC"})


def parse_migrations(files: Iterable[tuple[str, str]]) -> list[tuple[int, str, str]]:
    """Turn (file name, sql) pairs into (version, description, sql), in version order.

    Names that do not look like `NNN_name.sql` are ignored. Two files with the same
    version number are an error.
    """
    found: dict[int, tuple[int, str, str]] = {}
    for name, sql in files:
        match = _MIGRATION.fullmatch(name)
        if not match:
            continue
        version = int(match["version"])
        if version in found:
            raise ValueError(f"two schema files share version {version:03d}")
        found[version] = (version, match["name"].replace("_", " "), sql)
    return [found[version] for version in sorted(found)]


def migrations() -> list[tuple[int, str, str]]:
    """Return the packaged schema files as (version, description, sql), in order."""
    folder = resources.files("compute_cost_risk_monitor").joinpath("schema")
    return parse_migrations(
        (entry.name, entry.read_text("utf-8")) for entry in folder.iterdir()
    )


def _version_table(connection: duckdb.DuckDBPyConnection) -> str:
    row = connection.execute("SELECT current_schema()").fetchone()
    schema = row[0] if row else "main"
    return '"' + schema.replace('"', '""') + '".schema_version'


def applied_versions(connection: duckdb.DuckDBPyConnection) -> set[int]:
    """Versions recorded in this database's schema_version table, never a temp one."""
    exists = connection.execute(
        "SELECT count(*) FROM duckdb_tables() WHERE table_name = 'schema_version'"
        " AND NOT temporary AND database_name = current_database()"
        " AND schema_name = current_schema()"
    ).fetchone()
    if not exists or exists[0] == 0:
        return set()
    query = f"SELECT version FROM {_version_table(connection)}"  # noqa: S608
    return {row[0] for row in connection.execute(query).fetchall()}


def create_schema(connection: duckdb.DuckDBPyConnection) -> list[int]:
    """Apply packaged schema versions not yet applied; return those applied now.

    Each version runs in its own transaction, so call this outside an open transaction.
    """
    done = applied_versions(connection)
    applied: list[int] = []
    for version, description, sql in migrations():
        if version in done:
            continue
        try:
            connection.begin()
        except duckdb.TransactionException as error:
            raise RuntimeError(
                "create_schema manages its own transactions; call it outside one"
            ) from error
        try:
            connection.execute(sql)
            insert = f"INSERT INTO {_version_table(connection)} VALUES (?, ?, ?)"  # noqa: S608
            connection.execute(insert, [version, datetime.now(UTC), description])
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        applied.append(version)
    return applied


# Nullable dtypes, so a missing value reaches DuckDB as NULL, never NaN or "None".
_DTYPES: dict[str, Any] = {
    TEXT: pd.StringDtype("python"),
    "Float64": pd.Float64Dtype(),
    "Int64": pd.Int64Dtype(),
    "boolean": pd.BooleanDtype(),
}


def frame(columns: dict[str, tuple[str, list[Any]]]) -> pd.DataFrame:
    """Build a DataFrame from (dtype, values) columns, for a bulk insert."""
    data: dict[str, Any] = {}
    for name, (kind, values) in columns.items():
        if kind == "timestamp":
            data[name] = pd.to_datetime(pd.Series(values, dtype="object"), utc=True)
        else:
            data[name] = pd.array(values, dtype=_DTYPES[kind])
    return pd.DataFrame(data)


def insert_frame(
    connection: duckdb.DuckDBPyConnection, table: str, rows: pd.DataFrame
) -> None:
    """Insert every row of a frame into a table, matching columns by name."""
    if rows.empty:
        return
    columns = ", ".join(rows.columns)
    connection.register("_frame_rows", rows)
    try:
        # Table and column names come from calling code, never from input data.
        connection.execute(
            f"INSERT INTO {table} ({columns}) SELECT {columns} FROM _frame_rows"  # noqa: S608
        )
    finally:
        connection.unregister("_frame_rows")
