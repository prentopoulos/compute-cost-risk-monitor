"""The committed synthetic brief still checks (market-brief spec).

docs/brief holds a brief built from the synthetic demo as of 2026-10-12 09:00 UTC. Its
fact set must equal a freshly built one, and its text must pass the independent check
against a freshly built demo database, whether its prose is the template or a draft.
"""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pytest

from compute_cost_risk_monitor import brief, brief_check, db, demo

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = ROOT / "docs" / "brief"
AS_OF = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def con(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[duckdb.DuckDBPyConnection]:
    path = tmp_path_factory.mktemp("demo") / "synthetic.duckdb"
    assert demo.build(path) == 0
    connection = db.connect(path, read_only=True)
    yield connection
    connection.close()


def test_committed_fact_set_is_reproducible(con: duckdb.DuckDBPyConnection) -> None:
    committed = (COMMITTED / "facts.json").read_text(encoding="utf-8")
    assert brief.build(con, AS_OF).to_json() == committed


def test_committed_brief_passes_the_check(con: duckdb.DuckDBPyConnection) -> None:
    text = (COMMITTED / "brief.md").read_text(encoding="utf-8")
    work = brief.Workload()
    derived = brief_check.derive(
        con, AS_OF, work.variant, work.gpus_per_vm, work.gpus, work.hours
    )
    result = brief_check.check(text, derived)
    assert result.passed, result.failures
    assert text.startswith(
        "# Market brief\n\n**SYNTHETIC DATA — NOT AZURE LIST PRICES**"
    )


def test_committed_run_record() -> None:
    record = json.loads((COMMITTED / "run-record.json").read_text(encoding="utf-8"))
    assert record["data_label"] == "synthetic"
    assert record["text_used"] in ("template", "draft")
    assert "ANTHROPIC_API_KEY" not in json.dumps(record)
