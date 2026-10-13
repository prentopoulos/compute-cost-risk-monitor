"""The collect command: the 24-hour guard, ingest without network, and its report.

Runs here are synthetic: tests pass a fake fetcher, a fake clock and the synthetic label
through the function's keyword arguments, which the command line cannot set.
"""

import json
import re
from collections.abc import Sequence
from datetime import timedelta
from pathlib import Path

import pytest

from compute_cost_risk_monitor import collect as command
from compute_cost_risk_monitor import fetch, raw_store
from support import (
    START,
    FakeClock,
    ScriptedFetcher,
    collect,
    item,
    ok,
    page_bytes,
    status,
)


def write_live_manifest(raw_root: Path, hours_ago: float) -> str:
    started = START - timedelta(hours=hours_ago)
    run_id = raw_store.new_run_id(started, "aaaaaa")
    info = raw_store.RunInfo(
        source="azure-retail",
        run_id=run_id,
        data_label="live",
        started_at=started,
        code_version=None,
        folder=raw_store.run_folder(raw_root, "azure-retail", started),
    )
    raw_store.write_run_manifest(info, {}, {})
    return run_id


def run_command(
    tmp_path: Path, responses: Sequence[fetch.Response], *args: str
) -> tuple[int, ScriptedFetcher]:
    clock = FakeClock()
    fetcher = ScriptedFetcher(clock, responses)
    code = command.main(
        [
            "--db",
            str(tmp_path / "monitor.duckdb"),
            "--raw-dir",
            str(tmp_path / "raw"),
            *args,
        ],
        fetcher=fetcher,
        clock=clock.clock(),
        data_label="synthetic",
    )
    return code, fetcher


def test_fetch_then_ingest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, fetcher = run_command(
        tmp_path, [ok(page_bytes([item(), item(retailPrice=0.0)]))]
    )
    assert code == 0
    assert len(fetcher.calls) == 1
    out = capsys.readouterr().out
    assert "(synthetic): succeeded" in out
    assert "items 2: stored 1, repeats 0, out of scope 0, rejected 1" in out
    assert "rejected non_positive_price: 1" in out
    assert "7.0" not in out  # counts only, never prices


def test_unsuccessful_run_exits_non_zero(tmp_path: Path) -> None:
    code, _ = run_command(tmp_path, [status(400)])
    assert code == 1


def test_second_live_run_within_a_day_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    earlier = write_live_manifest(tmp_path / "raw", hours_ago=23)
    code, fetcher = run_command(tmp_path, [])
    assert code == 2
    assert fetcher.calls == []
    assert earlier in capsys.readouterr().err


def test_live_run_allowed_after_a_day(tmp_path: Path) -> None:
    write_live_manifest(tmp_path / "raw", hours_ago=25)
    code, fetcher = run_command(tmp_path, [ok(page_bytes([item()]))])
    assert (code, len(fetcher.calls)) == (0, 1)


def test_synthetic_runs_do_not_count_toward_the_guard(tmp_path: Path) -> None:
    collect(tmp_path / "raw", [ok(page_bytes([item()]))])
    assert command.recent_live_run(tmp_path / "raw", START) is None


def test_ingest_run_needs_no_network(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result, _, _ = collect(tmp_path / "raw", [ok(page_bytes([item()]))])
    code, fetcher = run_command(tmp_path, [], "--ingest-run", result.run_id)
    assert (code, fetcher.calls) == (0, [])
    assert f"run {result.run_id} (synthetic): succeeded" in capsys.readouterr().out


@pytest.mark.parametrize("run_id", ["../../etc", "20261012T090000Z-000000"])
def test_ingest_run_refuses_bad_or_unknown_ids(tmp_path: Path, run_id: str) -> None:
    code, _ = run_command(tmp_path, [], "--ingest-run", run_id)
    assert code == 2


def test_ingest_run_twice_refused(tmp_path: Path) -> None:
    result, _, _ = collect(tmp_path / "raw", [ok(page_bytes([item()]))])
    assert run_command(tmp_path, [], "--ingest-run", result.run_id)[0] == 0
    assert run_command(tmp_path, [], "--ingest-run", result.run_id)[0] == 2


def test_failed_ingest_keeps_the_files_and_says_how_to_retry(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*args: object) -> None:
        raise RuntimeError("simulated")

    monkeypatch.setattr(command, "_ingest", broken)
    code, _ = run_command(tmp_path, [ok(page_bytes([item()]))])
    assert code == 1
    assert "--ingest-run" in capsys.readouterr().err
    assert list((tmp_path / "raw").rglob("*.end.json"))


def test_command_line_cannot_set_the_label() -> None:
    with pytest.raises(SystemExit):
        command.main(["--data-label", "synthetic"])


def test_run_metadata() -> None:
    versions = command.dependency_versions()
    assert {"python", "duckdb", "pandas", "pytz", "compute-cost-risk-monitor"} <= set(
        versions
    )
    assert command.user_agent().startswith("compute-cost-risk-monitor/")
    version = command.code_version()
    assert version is None or re.fullmatch(r"[0-9a-f]{40}(-dirty)?", version)


def test_code_version_without_git(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert command.code_version() is None


def test_manifest_label_is_read_from_disk(tmp_path: Path) -> None:
    run_id = write_live_manifest(tmp_path, hours_ago=1)
    path = next(tmp_path.rglob(f"{run_id}.run.json"))
    assert json.loads(path.read_text(encoding="ascii"))["data_label"] == "live"
    found = command.recent_live_run(tmp_path, START)
    assert found is not None and found[0] == run_id


def test_system_clock_is_utc() -> None:
    assert command.system_clock().now().utcoffset() == timedelta(0)


# --- code review fixes (PR #7) ---


def test_default_paths_do_not_depend_on_the_working_directory() -> None:
    assert command.DEFAULT_RAW.is_absolute() and command.DEFAULT_DB.is_absolute()
    assert command.DEFAULT_RAW == command.REPO / "data" / "raw"


def test_run_that_sent_no_request_does_not_count(tmp_path: Path) -> None:
    run_id = write_live_manifest(tmp_path / "raw", hours_ago=1)
    folder = next((tmp_path / "raw").rglob(f"{run_id}.run.json")).parent
    info = raw_store.RunInfo("azure-retail", run_id, "live", START, None, folder)
    raw_store.write_end_manifest(info, START, "error", "OSError: disk full", requests=0)
    assert command.recent_live_run(tmp_path / "raw", START) is None


def test_run_that_may_still_be_fetching_is_not_ingested(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run_id = write_live_manifest(tmp_path / "raw", hours_ago=0.1)
    code, _ = run_command(tmp_path, [], "--ingest-run", run_id)
    assert code == 2
    assert "may still be fetching" in capsys.readouterr().err


def test_crashed_run_can_be_ingested_once_its_time_cap_has_passed(
    tmp_path: Path,
) -> None:
    result, _, _ = collect(tmp_path / "raw", [ok(page_bytes([item()]))])
    (result.folder / f"{result.run_id}.end.json").unlink()
    clock = FakeClock()
    clock.elapsed = 3600.0  # an hour after the run started
    code = command.main(
        [
            "--db",
            str(tmp_path / "m.duckdb"),
            "--raw-dir",
            str(tmp_path / "raw"),
            "--ingest-run",
            result.run_id,
        ],
        clock=clock.clock(),
    )
    assert code == 1  # stored as partial (no end manifest), not refused


def test_manifest_write_failure_is_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def full_disk(*args: object, **kwargs: object) -> None:
        raise OSError("disk full (simulated)")

    monkeypatch.setattr(raw_store, "write_run_manifest", full_disk)
    code, fetcher = run_command(tmp_path, [ok(page_bytes([item()]))])
    assert (code, fetcher.calls) == (1, [])
    assert "could not be recorded" in capsys.readouterr().err


def test_code_version_outside_a_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # tmp_path may sit inside this repository, so point Git at a folder that is none.
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "not-a-repository"))
    assert command.code_version(tmp_path) is None
