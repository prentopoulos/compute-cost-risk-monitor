"""The independent brief check (Phase 8 design D32; market-brief spec).

The briefs here are built from the committed synthetic demo history. The check must pass
a correct brief and name every number or time it cannot re-derive.
"""

import ast
import inspect
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pytest

from compute_cost_risk_monitor import brief, brief_check, normalize, synthetic
from seed import database
from support import FIXTURES

FILES = [
    FIXTURES / "azure_demo_history" / "snapshot-1.json",
    FIXTURES / "azure_demo_history" / "snapshot-2.json",
    FIXTURES / "azure_demo.json",
]
AS_OF = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)
NOW = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
H100 = "H100 NVLink 80GB"


def stored(files: list[Path]) -> duckdb.DuckDBPyConnection:
    connection = database()
    for path in files:
        synthetic.ingest_file(connection, path)
    normalize.normalize_pending(connection, NOW)
    return connection


@pytest.fixture(scope="module")
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    connection = stored(FILES)
    yield connection
    connection.close()


@pytest.fixture(scope="module")
def text(con: duckdb.DuckDBPyConnection) -> str:
    return brief.render(brief.build(con, AS_OF))


@pytest.fixture(scope="module")
def derived(con: duckdb.DuckDBPyConnection) -> brief_check.Derived:
    return brief_check.derive(con, AS_OF, H100, 8, 32, 720.0)


def test_correct_brief_passes(text: str, derived: brief_check.Derived) -> None:
    result = brief_check.check(text, derived)
    assert result.passed, result.failures
    assert result.numbers > 50
    assert result.times == 9


def test_tampered_number_named(text: str, derived: brief_check.Derived) -> None:
    lines = text.splitlines()
    line = next(i for i, shown in enumerate(lines, start=1) if "276,480.00" in shown)
    tampered = text.replace("276,480.00", "276,480.01", 1)
    result = brief_check.check(tampered, derived)
    assert not result.passed
    (failure,) = result.failures
    assert (failure.line, failure.token, failure.kind) == (line, "276,480.01", "number")
    assert lines[line - 1][failure.column - 1 :].startswith("276,480.0")


def test_unknown_number_named(text: str, derived: brief_check.Derived) -> None:
    extra = text.replace("## Records", "Extra figure 999.5\n\n## Records", 1)
    failures = brief_check.check(extra, derived).failures
    assert [(f.token, f.kind) for f in failures] == [("999.5", "number")]


def test_wrong_time_named(text: str, derived: brief_check.Derived) -> None:
    shifted = text.replace("2026-10-05 09:00 UTC", "2026-10-06 09:00 UTC", 1)
    failures = brief_check.check(shifted, derived).failures
    assert [(f.token, f.kind) for f in failures] == [("2026-10-06 09:00 UTC", "time")]


def test_records_table_and_identifiers_are_not_figures(
    derived: brief_check.Derived,
) -> None:
    text = (
        "Prose drafted by claude-opus-5-5 (prompt v1), ladder-v1, groups-v1;"
        " CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/); SHA-256;"
        " ND96isr H100 v5 in US West 3.\n\n## Records\n\n| `x` | 123.456 |\n"
    )
    assert brief_check.check(text, derived).failures == []


def test_single_snapshot_and_other_workloads() -> None:
    connection = stored([FIXTURES / "azure_demo.json"])
    try:
        text = brief.render(brief.build(connection, AS_OF))
        derived = brief_check.derive(connection, AS_OF, H100, 8, 32, 720.0)
        assert brief_check.check(text, derived).passed
        none = brief.build(connection, AS_OF, brief.Workload(variant="B200"))
        other = brief_check.derive(connection, AS_OF, "B200", 8, 32, 720.0)
        assert brief_check.check(brief.render(none), other).passed
    finally:
        connection.close()


def test_thin_and_stale_briefs_pass(con: duckdb.DuckDBPyConnection) -> None:
    work = brief.Workload(variant="T4 16GB", gpus_per_vm=1, gpus=10, hours=0.5)
    late = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)
    text = brief.render(brief.build(con, late, work))
    assert "STALE" in text
    derived = brief_check.derive(con, late, "T4 16GB", 1, 10, 0.5)
    assert brief_check.check(text, derived).passed


def test_empty_database_and_missing_rule_set() -> None:
    empty = database()
    try:
        derived = brief_check.derive(empty, AS_OF, H100, 8, 32, 720.0)
        assert derived.times == {"2026-10-12 09:00 UTC"} and derived.texts == set()
        result = brief_check.check("As of 2026-10-12 09:00 UTC.", derived)
        assert result.passed and result.times == 1
    finally:
        empty.close()


def test_defaults_without_a_stored_rule_set(con: duckdb.DuckDBPyConnection) -> None:
    derived = brief_check.derive(con, AS_OF, H100, 8, 32, 720.0, rule_version="none")
    assert "7" in derived.texts and "5" in derived.texts  # the groups-v1 defaults


def test_check_imports_no_brief_or_grouping_code() -> None:
    tree = ast.parse(inspect.getsource(brief_check))
    imported = {
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    forbidden = ("brief", "groups", "history", "quality", "calculator", "normalize")
    project = {
        name for name in imported if name.startswith("compute_cost_risk_monitor")
    }
    assert project == {"compute_cost_risk_monitor.scenarios"}
    assert not any(name.endswith(word) for name in project for word in forbidden)


def test_windows_line_endings(text: str, derived: brief_check.Derived) -> None:
    result = brief_check.check(text.replace("\n", "\r\n"), derived)
    assert result.passed, result.failures
