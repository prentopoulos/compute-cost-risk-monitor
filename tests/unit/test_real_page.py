"""Contract check against one real Azure page kept locally under data/, never committed.

It reads the first page of the newest live run in data/raw. Where none is kept (CI, a
fresh clone), every test here is skipped (phase-2-collector design D23). Assertions are
about the response's shape and the rules applied to it, never about price levels.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from compute_cost_risk_monitor import azure_retail as az
from compute_cost_risk_monitor import db, ingest, raw_store

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
DRIFT = {"missing_field", "invalid_value", "not_an_object"}


def kept_first_page() -> tuple[dict[str, Any], bytes] | None:
    if not RAW.is_dir():
        return None
    for path, manifest in reversed(list(raw_store.run_manifests(RAW, az.SOURCE))):
        if manifest.get("data_label") != "live":
            continue
        first = path.parent / f"{manifest['run_id']}-0000.meta.json"
        if not first.exists():
            continue
        sidecar = json.loads(first.read_text(encoding="ascii"))
        if sidecar.get("http_status") == 200:
            return sidecar, raw_store.read_body(RAW, sidecar)
    return None


KEPT = kept_first_page()
pytestmark = pytest.mark.skipif(
    KEPT is None, reason="no live Azure page kept in data/raw"
)


def page() -> tuple[dict[str, Any], bytes, az.Page]:
    assert KEPT is not None
    sidecar, body = KEPT
    parsed = az.parse_page(body)
    assert parsed is not None, "the kept page no longer parses as a Retail Prices page"
    return sidecar, body, parsed


def test_real_page_matches_the_documented_shape() -> None:
    _, _, parsed = page()
    assert parsed.items
    verdicts = [az.classify(item) for item in parsed.items]
    drift = [v.reason for v in verdicts if v.reason in DRIFT]
    assert drift == [], "fields the parser relies on are missing or changed type"
    link = parsed.next_link
    if isinstance(link, str) and link:
        assert az.next_link_problem(link) is None
        assert az.missing_params(link) == []


def test_real_rows_follow_the_rules() -> None:
    _, _, parsed = page()
    rows = [v.row for v in map(az.classify, parsed.items) if v.row is not None]
    assert rows
    for row in rows:
        assert row.arm_sku_name.startswith(az.GPU_FAMILIES)
        assert row.retail_price > 0
        assert row.is_primary_meter_region
        assert row.rental_type in {
            "on_demand",
            "spot",
            "reservation",
            "dev_test",
            "other",
        }
        if row.rental_type == "reservation":
            assert row.price_unit.endswith(" term")
        else:
            assert row.price_unit == row.unit_of_measure


def test_real_page_ingests_as_a_recorded_run(tmp_path: Path) -> None:
    # A new run built from a kept response is `recorded` (PROJECT.md §3). One page of a
    # longer run is not a complete snapshot, so it must not come out `succeeded`.
    sidecar, body, parsed = page()
    started = datetime(2026, 1, 1, tzinfo=UTC)
    info = raw_store.RunInfo(
        source=az.SOURCE,
        run_id=raw_store.new_run_id(started, "0ecded"),
        data_label="recorded",
        started_at=started,
        code_version=None,
        folder=raw_store.run_folder(tmp_path, az.SOURCE, started),
    )
    raw_store.write_run_manifest(info, {}, {"recorded_from": sidecar["run_id"]})
    exchange = raw_store.Exchange(
        url=sidecar["url"],
        requested_at=started,
        received_at=started,
        elapsed_ms=sidecar["elapsed_ms"],
        status=200,
        reason=sidecar["reason"],
        headers=[(name, value) for name, value in sidecar["headers"]],
        body=body,
        error=None,
    )
    raw_store.keep_exchange(tmp_path, info, 0, 0, 1, exchange, sidecar["user_agent"])
    raw_store.write_end_manifest(info, started, "recorded_page", "one kept page")
    connection = db.connect()
    result = ingest.ingest_run(connection, tmp_path, info.run_id)
    counts = result.summary
    assert (result.data_label, result.status) == ("recorded", "partial")
    assert counts.items_seen == len(parsed.items)
    assert counts.items_seen == (
        counts.observations_stored
        + counts.repeats
        + counts.out_of_scope
        + counts.rejected
    )
    stored = connection.execute("SELECT count(*) FROM price_observation").fetchone()
    assert stored == (counts.observations_stored,)
    connection.close()
