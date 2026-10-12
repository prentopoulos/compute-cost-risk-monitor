"""The verbatim skill copies still match their recorded SHA-256 digests.

Git stores these files byte-for-byte (`-text` in .gitattributes), so this holds on any
checkout, Windows or Linux.
"""

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = (
    ROOT
    / ".agents"
    / "skills"
    / "compute-cost-risk-monitor-build-safety"
    / "references"
    / "source-manifest.json"
)


def _entries() -> list[dict[str, str]]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries: list[dict[str, str]] = data["files"]
    return entries


def test_manifest_lists_all_26_verbatim_files() -> None:
    copies = [entry["copy"] for entry in _entries()]
    assert len(copies) == 26
    assert len(set(copies)) == 26


@pytest.mark.parametrize("entry", _entries(), ids=lambda entry: entry["copy"])
def test_verbatim_copy_matches_digest(entry: dict[str, str]) -> None:
    copy = ROOT / entry["copy"]
    assert hashlib.sha256(copy.read_bytes()).hexdigest() == entry["sha256"]
