"""Raw-response files: exact bytes kept before parsing, each file written once.

Layout (phase-2-collector design D3 of Phase 1, D11 and D24), under a raw root such as
`data/raw`:

    <source>/YYYY/MM/DD/<run_id>.run.json        start manifest
    <source>/YYYY/MM/DD/<run_id>-<seq>.json.gz   response body, gzip of the exact bytes
    <source>/YYYY/MM/DD/<run_id>-<seq>.meta.json sidecar, written after its body
    <source>/YYYY/MM/DD/<run_id>.end.json        end manifest

The date is the run's UTC start date, so one run's files sit together.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import secrets
import zlib
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any

SIDECAR_VERSION = 1
MANIFEST_VERSION = 1
RUN_ID = re.compile(r"\d{8}T\d{6}Z-[0-9a-f]{6}")
_DROPPED_HEADERS = {"set-cookie", "set-cookie2"}


class IntegrityError(Exception):
    """A kept file does not match its sidecar or the expected layout."""


def new_run_id(started_at: datetime, token: str | None = None) -> str:
    """A run ID from the UTC start time plus random hex, safe in file names."""
    return f"{started_at:%Y%m%dT%H%M%SZ}-{token or secrets.token_hex(3)}"


def check_run_id(run_id: str) -> str:
    if not RUN_ID.fullmatch(run_id):
        raise ValueError(f"not a run ID: {run_id!r}")
    return run_id


def run_folder(raw_root: Path, source: str, started_at: datetime) -> Path:
    return (
        raw_root / source / f"{started_at:%Y}" / f"{started_at:%m}" / f"{started_at:%d}"
    )


def write_once(path: Path, data: bytes) -> None:
    """Write a whole file, or fail; never overwrite and never leave a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path.name}")
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        # A hard link fails if the target exists, on Windows and POSIX alike.
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _json_bytes(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, ensure_ascii=True) + "\n").encode("ascii")


def _iso(moment: datetime | None) -> str | None:
    return None if moment is None else moment.isoformat()


def compress(body: bytes) -> bytes:
    """gzip with a fixed timestamp, so the same bytes always give the same file."""
    return gzip.compress(body, compresslevel=9, mtime=0)


@dataclass(frozen=True)
class Exchange:
    """One request attempt as it happened, before anything is parsed."""

    url: str
    requested_at: datetime
    received_at: datetime | None
    elapsed_ms: int
    status: int | None
    reason: str
    headers: list[tuple[str, str]]
    body: bytes
    error: str | None


@dataclass(frozen=True)
class RunInfo:
    source: str
    run_id: str
    data_label: str
    started_at: datetime
    code_version: str | None
    folder: Path


def write_run_manifest(
    info: RunInfo,
    dependency_versions: dict[str, str],
    request_params: dict[str, Any],
) -> Path:
    path = info.folder / f"{info.run_id}.run.json"
    document = {
        "manifest_version": MANIFEST_VERSION,
        "source": info.source,
        "run_id": info.run_id,
        "data_label": info.data_label,
        "started_at": _iso(info.started_at),
        "code_version": info.code_version,
        "dependency_versions": dependency_versions,
        "request_params": request_params,
    }
    write_once(path, _json_bytes(document))
    return path


def write_end_manifest(
    info: RunInfo,
    finished_at: datetime,
    stop_reason: str,
    detail: str,
    requests: int | None = None,
) -> Path:
    path = info.folder / f"{info.run_id}.end.json"
    document = {
        "manifest_version": MANIFEST_VERSION,
        "run_id": info.run_id,
        "finished_at": _iso(finished_at),
        "stop_reason": stop_reason,
        "detail": detail,
        "requests": requests,
    }
    write_once(path, _json_bytes(document))
    return path


def keep_exchange(
    raw_root: Path,
    info: RunInfo,
    seq: int,
    page: int,
    attempt: int,
    exchange: Exchange,
    user_agent: str,
) -> dict[str, Any]:
    """Keep an attempt's body, then its sidecar; return the sidecar."""
    stem = f"{info.run_id}-{seq:04d}"
    body_path = info.folder / f"{stem}.json.gz"
    packed = compress(exchange.body)
    write_once(body_path, packed)
    sidecar: dict[str, Any] = {
        "sidecar_version": SIDECAR_VERSION,
        "source": info.source,
        "run_id": info.run_id,
        "seq": seq,
        "page": page,
        "attempt": attempt,
        "data_label": info.data_label,
        "code_version": info.code_version,
        "method": "GET",
        "url": exchange.url,
        "user_agent": user_agent,
        "requested_at": _iso(exchange.requested_at),
        "received_at": _iso(exchange.received_at),
        "elapsed_ms": exchange.elapsed_ms,
        "http_status": exchange.status,
        "reason": exchange.reason,
        "headers": [
            [name.lower(), value]
            for name, value in exchange.headers
            if name.lower() not in _DROPPED_HEADERS
        ],
        "byte_length": len(exchange.body),
        "sha256": hashlib.sha256(exchange.body).hexdigest(),
        "gzip_byte_length": len(packed),
        "file": body_path.relative_to(raw_root).as_posix(),
        "error": exchange.error,
    }
    write_once(info.folder / f"{stem}.meta.json", _json_bytes(sidecar))
    return sidecar


@dataclass(frozen=True)
class RunFiles:
    folder: Path
    manifest: dict[str, Any]
    end: dict[str, Any] | None
    sidecars: list[dict[str, Any]]
    orphan_bodies: list[str]


def find_run(raw_root: Path, source: str, run_id: str) -> Path:
    """The folder holding a run's start manifest."""
    check_run_id(run_id)
    found = sorted((raw_root / source).glob(f"*/*/*/{run_id}.run.json"))
    if len(found) != 1:
        raise IntegrityError(f"expected one start manifest for run {run_id}")
    return found[0].parent


def _load(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="ascii"))
    except (OSError, ValueError) as error:
        raise IntegrityError(f"{path.name} cannot be read: {error}") from error
    if not isinstance(document, dict):
        raise IntegrityError(f"{path.name} is not a JSON object")
    return document


def run_manifests(
    raw_root: Path, source: str, days: Iterable[date] | None = None
) -> Iterator[tuple[Path, dict[str, Any]]]:
    """Start manifests and their paths, optionally only from the given date folders."""
    base = raw_root / source
    if days is None:
        paths: Iterable[Path] = base.glob("*/*/*/*.run.json")
    else:
        paths = (
            path
            for day in sorted(set(days))
            for path in (base / f"{day:%Y}" / f"{day:%m}" / f"{day:%d}").glob(
                "*.run.json"
            )
        )
    for path in sorted(paths):
        yield path, _load(path)


def _seq(sidecar: dict[str, Any], path: Path) -> int:
    seq = sidecar.get("seq")
    if not isinstance(seq, int) or isinstance(seq, bool):
        raise IntegrityError(f"{path.name} has no sequence number")
    return seq


def read_run(raw_root: Path, source: str, run_id: str) -> RunFiles:
    folder = find_run(raw_root, source, run_id)
    manifest = _load(folder / f"{run_id}.run.json")
    if manifest.get("run_id") != run_id or manifest.get("source") != source:
        raise IntegrityError(f"start manifest of {run_id} names another run or source")
    end_path = folder / f"{run_id}.end.json"
    end = _load(end_path) if end_path.exists() else None
    loaded = [(path, _load(path)) for path in folder.glob(f"{run_id}-*.meta.json")]
    # Order by the recorded number, not the file name: past seq 9999 names stop sorting.
    loaded.sort(key=lambda pair: _seq(pair[1], pair[0]))
    sidecars = [sidecar for _, sidecar in loaded]
    for expected, (path, sidecar) in enumerate(loaded):
        body = folder / f"{run_id}-{expected:04d}.json.gz"
        if (
            sidecar["seq"] != expected
            or sidecar.get("run_id") != run_id
            or path.name != f"{run_id}-{expected:04d}.meta.json"
            # A sidecar describes its own run's body, never another file.
            or sidecar.get("file") != body.relative_to(raw_root).as_posix()
        ):
            raise IntegrityError(
                f"sidecar {expected} of {run_id} is missing or misnamed"
            )
    stems = {
        path.name.removesuffix(".meta.json") for path in folder.glob("*.meta.json")
    }
    orphans = sorted(
        path.name
        for path in folder.glob(f"{run_id}-*.json.gz")
        if path.name.removesuffix(".json.gz") not in stems
    )
    return RunFiles(folder, manifest, end, sidecars, orphans)


def read_body(raw_root: Path, sidecar: dict[str, Any]) -> bytes:
    """A kept body, checked against its sidecar's length and SHA-256."""
    text = str(sidecar.get("file", ""))
    relative = PurePosixPath(text)
    # Sidecars store POSIX paths under the raw root. On Windows "/x" or "C:x" would
    # escape the root when joined, so refuse anything but plain relative parts.
    if relative.is_absolute() or ".." in relative.parts or "\\" in text or ":" in text:
        raise IntegrityError(f"sidecar points outside the raw root: {text}")
    try:
        body = gzip.decompress(raw_root.joinpath(*relative.parts).read_bytes())
        expected = (sidecar["byte_length"], sidecar["sha256"])
    except (OSError, EOFError, zlib.error, KeyError) as error:
        name = type(error).__name__
        raise IntegrityError(f"{text} cannot be read ({name})") from error
    if (len(body), hashlib.sha256(body).hexdigest()) != expected:
        raise IntegrityError(f"{text} does not match its sidecar")
    return body
