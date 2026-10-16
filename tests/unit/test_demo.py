"""The one-command synthetic demo build (Phase 8 design D39, demo-setup spec).

The fixtures it stores are the committed synthetic snapshots; nothing here touches the
database of collected prices or the network.
"""

import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path

import duckdb
import pytest

from compute_cost_risk_monitor import db, demo


def runs(path: Path) -> list[tuple[str, str]]:
    connection = db.connect(path)
    try:
        return connection.execute(
            "SELECT source, data_label FROM collection_run ORDER BY source, started_at"
        ).fetchall()
    finally:
        connection.close()


def unnormalized(path: Path) -> int:
    connection = db.connect(path)
    try:
        row = connection.execute(
            "SELECT count(*) FROM price_observation p WHERE NOT EXISTS ("
            " SELECT 1 FROM normalized_price n WHERE n.source = p.source"
            " AND n.item_key = p.item_key AND n.retrieved_at = p.retrieved_at)"
        ).fetchone()
    finally:
        connection.close()
    assert row is not None
    return int(row[0])


def leftovers(folder: Path) -> list[str]:
    return sorted(p.name for p in folder.iterdir() if "building" in p.name)


def test_fixture_files_exist() -> None:
    assert all(path.is_file() for path in demo.FILES)
    assert [p.parent.name for p in demo.FILES[:3]] == [
        "azure_demo_history",
        "azure_demo_history",
        "synthetic",
    ]


def test_fresh_build(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "data" / "synthetic.duckdb"
    assert demo.build(target) == 0
    assert runs(target) == [
        ("azure-retail", "synthetic"),
        ("azure-retail", "synthetic"),
        ("azure-retail", "synthetic"),
        ("synthetic-marketplace", "synthetic"),
        ("synthetic-marketplace", "synthetic"),
        ("synthetic-marketplace", "synthetic"),
    ]
    assert unnormalized(target) == 0
    assert leftovers(target.parent) == []
    out = capsys.readouterr().out
    assert f"built {target}" in out
    assert re.search(r"\d\.\d", out) is None  # counts and paths, never a price


def test_rebuild_replaces(tmp_path: Path) -> None:
    target = tmp_path / "synthetic.duckdb"
    assert demo.build(target) == 0
    first = runs(target)
    assert demo.build(target) == 0
    assert runs(target) == first
    assert leftovers(tmp_path) == []


def test_collected_database_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monitor = tmp_path / "monitor.duckdb"
    monkeypatch.setattr(demo, "MONITOR_DB", monitor)
    assert demo.build(monitor) == 2
    assert not monitor.exists()
    assert "refused" in capsys.readouterr().err


@pytest.mark.parametrize("failing", ["store", "normalize"])
def test_failed_step_keeps_the_old_demo(tmp_path: Path, failing: str) -> None:
    target = tmp_path / "synthetic.duckdb"
    target.write_bytes(b"old demo")

    def fail(_argv: Sequence[str]) -> int:
        return 1

    def touch(argv: Sequence[str]) -> int:
        Path(argv[-1]).write_bytes(b"partial")
        return 0

    store, normalize_db = (fail, touch) if failing == "store" else (touch, fail)
    assert demo.build(target, store=store, normalize_db=normalize_db) == 1
    assert target.read_bytes() == b"old demo"
    assert leftovers(tmp_path) == []


def test_in_use_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "synthetic.duckdb"

    def locked(_src: Path, _dst: Path) -> None:
        raise PermissionError("held by another process")

    monkeypatch.setattr(os, "replace", locked)
    assert demo.build(target) == 2
    assert "IN USE" in capsys.readouterr().err
    assert leftovers(tmp_path) == [] and not target.exists()


def test_serve_starts_the_dashboard_after_a_build(tmp_path: Path) -> None:
    started: list[list[str]] = []

    def launch(command: Sequence[str]) -> int:
        started.append(list(command))
        return 0

    target = tmp_path / "synthetic.duckdb"
    assert demo.main(["--db", str(target), "--serve"], launch=launch) == 0
    # The dashboard is told which database was built, so it offers only that one.
    assert started == [
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(demo.APP),
            "--",
            "--demo",
            str(target),
        ]
    ]
    assert demo.APP.name == "app.py" and demo.APP.is_file()


def test_a_stale_log_beside_the_target_is_removed(tmp_path: Path) -> None:
    target = tmp_path / "synthetic.duckdb"
    stale = tmp_path / "synthetic.duckdb.wal"
    stale.write_bytes(b"left by a crashed session")
    assert demo.build(target) == 0
    assert not stale.exists()
    connection = duckdb.connect(str(target), read_only=True)
    try:
        assert connection.execute("SELECT count(*) FROM collection_run").fetchone()
    finally:
        connection.close()


def test_serve_not_started_after_a_failed_build(tmp_path: Path) -> None:
    started: list[Sequence[str]] = []

    def fail(_argv: Sequence[str]) -> int:
        return 2

    code = demo.main(
        ["--db", str(tmp_path / "synthetic.duckdb"), "--serve"],
        store=fail,
        launch=started.append,  # type: ignore[arg-type]
    )
    assert code == 2 and started == []


def test_build_without_serve(tmp_path: Path) -> None:
    started: list[Sequence[str]] = []
    target = tmp_path / "synthetic.duckdb"
    assert demo.main(["--db", str(target)], launch=started.append) == 0  # type: ignore[arg-type]
    assert started == [] and target.is_file()


def test_launcher_returns_the_exit_code() -> None:
    assert demo._launch([sys.executable, "-c", "raise SystemExit(3)"]) == 3


def test_built_demo_is_readable(tmp_path: Path) -> None:
    target = tmp_path / "synthetic.duckdb"
    assert demo.build(target) == 0
    connection = duckdb.connect(str(target), read_only=True)
    try:
        assert connection.execute("SELECT count(*) FROM collection_run").fetchone() == (
            6,
        )
    finally:
        connection.close()
