"""Raw-response files: exact bytes, written once, sidecars without private details."""

import gzip
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from compute_cost_risk_monitor import raw_store

T0 = datetime(2026, 10, 12, 9, 0, 1, tzinfo=UTC)
BODY = b'{"Items": [], "NextPageLink": null}'


def info(raw_root: Path, run_id: str = "20261012T090001Z-abc123") -> raw_store.RunInfo:
    return raw_store.RunInfo(
        source="azure-retail",
        run_id=run_id,
        data_label="synthetic",
        started_at=T0,
        code_version="test",
        folder=raw_store.run_folder(raw_root, "azure-retail", T0),
    )


def exchange(
    body: bytes = BODY,
    status: int | None = 200,
    headers: list[tuple[str, str]] | None = None,
    error: str | None = None,
) -> raw_store.Exchange:
    return raw_store.Exchange(
        url="https://prices.azure.com/api/retail/prices?api-version=x",
        requested_at=T0,
        received_at=T0 if status is not None else None,
        elapsed_ms=250,
        status=status,
        reason="OK" if status == 200 else "",
        headers=headers or [("Content-Type", "application/json")],
        body=body,
        error=error,
    )


def keep(
    raw_root: Path, attempt: raw_store.Exchange | None = None
) -> tuple[raw_store.RunInfo, dict[str, object]]:
    run = info(raw_root)
    sidecar = raw_store.keep_exchange(
        raw_root, run, 0, 0, 1, attempt or exchange(), "ua/1"
    )
    return run, sidecar


def test_run_ids_are_file_safe_and_dated() -> None:
    run_id = raw_store.new_run_id(T0, "abc123")
    assert run_id == "20261012T090001Z-abc123"
    assert raw_store.check_run_id(run_id) == run_id
    assert raw_store.RUN_ID.fullmatch(raw_store.new_run_id(T0))
    for bad in ["../etc", "20261012T090001Z-ABC123", "x"]:
        with pytest.raises(ValueError, match="not a run ID"):
            raw_store.check_run_id(bad)


def test_files_sit_in_the_run_start_date_folder(tmp_path: Path) -> None:
    assert raw_store.run_folder(tmp_path, "azure-retail", T0) == (
        tmp_path / "azure-retail" / "2026" / "10" / "12"
    )


def test_body_kept_byte_for_byte(tmp_path: Path) -> None:
    _, sidecar = keep(tmp_path)
    assert raw_store.read_body(tmp_path, sidecar) == BODY
    assert sidecar["sha256"] == hashlib.sha256(BODY).hexdigest()
    assert sidecar["byte_length"] == len(BODY)
    stored = tmp_path / str(sidecar["file"])
    assert gzip.decompress(stored.read_bytes()) == BODY
    assert sidecar["gzip_byte_length"] == stored.stat().st_size


def test_same_bytes_give_the_same_file(tmp_path: Path) -> None:
    run = info(tmp_path)
    first = raw_store.keep_exchange(tmp_path, run, 0, 0, 1, exchange(), "ua/1")
    second = raw_store.keep_exchange(tmp_path, run, 1, 0, 2, exchange(), "ua/1")
    first_bytes = (tmp_path / str(first["file"])).read_bytes()
    assert first_bytes == (tmp_path / str(second["file"])).read_bytes()
    assert first_bytes == raw_store.compress(BODY)


def test_existing_file_never_overwritten(tmp_path: Path) -> None:
    target = tmp_path / "kept.json"
    raw_store.write_once(target, b"first")
    with pytest.raises(FileExistsError):
        raw_store.write_once(target, b"second")
    assert target.read_bytes() == b"first"
    assert [path.name for path in tmp_path.iterdir()] == ["kept.json"]


def test_rewriting_a_sidecar_fails(tmp_path: Path) -> None:
    keep(tmp_path)
    with pytest.raises(FileExistsError):
        keep(tmp_path)


def test_failed_request_kept_as_an_empty_body(tmp_path: Path) -> None:
    _, sidecar = keep(
        tmp_path, exchange(body=b"", status=None, error="TimeoutError: timed out")
    )
    assert raw_store.read_body(tmp_path, sidecar) == b""
    assert sidecar["http_status"] is None
    assert sidecar["received_at"] is None
    assert sidecar["error"] == "TimeoutError: timed out"
    assert sidecar["sha256"] == hashlib.sha256(b"").hexdigest()


def test_sidecar_leaves_out_private_details(tmp_path: Path) -> None:
    headers = [
        ("Content-Type", "application/json"),
        ("Set-Cookie", "session=private"),
        ("X-Ms-Request-Id", "synthetic-1"),
    ]
    run, sidecar = keep(tmp_path, exchange(headers=headers))
    assert sidecar["headers"] == [
        ["content-type", "application/json"],
        ["x-ms-request-id", "synthetic-1"],
    ]
    text = (run.folder / f"{run.run_id}-0000.meta.json").read_text(encoding="ascii")
    assert "session=private" not in text
    assert str(tmp_path) not in text
    assert str(tmp_path).replace("\\", "/") not in text
    assert (
        sidecar["file"]
        == "azure-retail/2026/10/12/20261012T090001Z-abc123-0000.json.gz"
    )
    assert json.loads(text) == sidecar


def test_tampered_body_refused(tmp_path: Path) -> None:
    _, sidecar = keep(tmp_path)
    path = tmp_path / str(sidecar["file"])
    path.unlink()
    path.write_bytes(raw_store.compress(b'{"Items": [1]}'))
    with pytest.raises(raw_store.IntegrityError, match="does not match"):
        raw_store.read_body(tmp_path, sidecar)


@pytest.mark.parametrize(
    "file",
    ["../outside.json.gz", "/abs/outside.json.gz", "C:outside.json.gz", r"a\..\b.gz"],
)
def test_sidecar_cannot_point_outside_the_raw_root(tmp_path: Path, file: str) -> None:
    with pytest.raises(raw_store.IntegrityError, match="outside"):
        raw_store.read_body(tmp_path, {"file": file, "byte_length": 0, "sha256": ""})


def test_run_read_back_with_manifests(tmp_path: Path) -> None:
    run = info(tmp_path)
    raw_store.write_run_manifest(run, {"duckdb": "test"}, {"first_url": "x"})
    raw_store.keep_exchange(tmp_path, run, 0, 0, 1, exchange(), "ua/1")
    raw_store.write_end_manifest(run, T0, "completed", "1 pages")
    files = raw_store.read_run(tmp_path, "azure-retail", run.run_id)
    assert files.manifest["data_label"] == "synthetic"
    assert files.end is not None and files.end["stop_reason"] == "completed"
    assert [sidecar["seq"] for sidecar in files.sidecars] == [0]
    assert files.orphan_bodies == []


def test_body_without_sidecar_is_an_orphan(tmp_path: Path) -> None:
    run = info(tmp_path)
    raw_store.write_run_manifest(run, {}, {})
    raw_store.write_once(
        run.folder / f"{run.run_id}-0000.json.gz", raw_store.compress(BODY)
    )
    files = raw_store.read_run(tmp_path, "azure-retail", run.run_id)
    assert files.end is None
    assert files.sidecars == []
    assert files.orphan_bodies == [f"{run.run_id}-0000.json.gz"]


def test_missing_sidecar_in_sequence_refused(tmp_path: Path) -> None:
    run = info(tmp_path)
    raw_store.write_run_manifest(run, {}, {})
    raw_store.keep_exchange(tmp_path, run, 1, 0, 1, exchange(), "ua/1")
    with pytest.raises(raw_store.IntegrityError, match="missing or misnamed"):
        raw_store.read_run(tmp_path, "azure-retail", run.run_id)


def test_unknown_run_refused(tmp_path: Path) -> None:
    with pytest.raises(raw_store.IntegrityError, match="expected one start manifest"):
        raw_store.read_run(tmp_path, "azure-retail", "20261012T090001Z-000000")


def test_manifest_naming_another_run_refused(tmp_path: Path) -> None:
    run = info(tmp_path)
    raw_store.write_run_manifest(run, {}, {})
    other = run.folder / "20261012T090001Z-ffffff.run.json"
    text = (run.folder / f"{run.run_id}.run.json").read_text(encoding="ascii")
    other.write_text(text, encoding="ascii")
    with pytest.raises(raw_store.IntegrityError, match="names another run"):
        raw_store.read_run(tmp_path, "azure-retail", "20261012T090001Z-ffffff")


def test_manifest_that_is_not_an_object_refused(tmp_path: Path) -> None:
    run = info(tmp_path)
    raw_store.write_once(run.folder / f"{run.run_id}.run.json", b"[1, 2]\n")
    with pytest.raises(raw_store.IntegrityError, match="not a JSON object"):
        raw_store.read_run(tmp_path, "azure-retail", run.run_id)
