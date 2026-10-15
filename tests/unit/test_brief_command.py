"""The brief command (Phase 8 design D29, D37; market-brief "Brief command").

The database is the synthetic demo, built by the demo command into a temporary folder.
"""

import json
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from compute_cost_risk_monitor import (
    brief,
    brief_check,
    db,
    demo,
    drafter,
    normalize,
    synthetic,
)

AS_OF = "2026-10-12T09:00:00Z"


@pytest.fixture(scope="module")
def demo_db(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    path = tmp_path_factory.mktemp("demo") / "synthetic.duckdb"
    assert demo.build(path) == 0
    yield path


def run(*args: str, now: datetime | None = None) -> int:
    return brief.main(list(args), now=now)


def test_pinned_as_of_is_reproducible(
    demo_db: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    first, second = tmp_path / "a", tmp_path / "b"
    assert run("--db", str(demo_db), "--as-of", AS_OF, "--out", str(first)) == 0
    assert run("--db", str(demo_db), "--as-of", AS_OF, "--out", str(second)) == 0
    for name in ("brief.md", "facts.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
    record = json.loads((first / "run-record.json").read_text(encoding="utf-8"))
    assert (record["text_used"], record["requests"], record["provider"]) == (
        "template",
        0,
        None,
    )
    assert record["data_label"] == "synthetic"
    out = capsys.readouterr().out
    assert "numbers and 9 times re-derived" in out
    assert re.search(r"\d\.\d", out) is None  # counts and paths, never a price


def test_default_as_of_and_folder(
    demo_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(brief, "BRIEFS", tmp_path / "briefs")
    now = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
    assert run("--db", str(demo_db), now=now) == 0
    (folder,) = (tmp_path / "briefs").iterdir()
    assert folder.name.startswith("synthetic-20261012T090000Z-")
    assert "AS OF 2026-10-15 12:00 UTC" in (folder / "brief.md").read_text(
        encoding="utf-8"
    )


def test_offset_converted_to_utc(demo_db: Path, tmp_path: Path) -> None:
    out = tmp_path / "brief"
    assert (
        run(
            "--db",
            str(demo_db),
            "--as-of",
            "2026-10-12T05:00:00-04:00",
            "--out",
            str(out),
        )
        == 0
    )
    assert "AS OF 2026-10-12 09:00 UTC" in (out / "brief.md").read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--as-of", "2026-10-12T09:00:00"], "needs a time zone"),
        (["--as-of", "2026-10-11T09:00:00Z"], "before the latest snapshot"),
    ],
)
def test_refused_times(
    demo_db: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    args: list[str],
    message: str,
) -> None:
    out = tmp_path / "brief"
    assert run("--db", str(demo_db), *args, "--out", str(out)) == 2
    assert message in capsys.readouterr().err
    assert not out.exists()


def test_refused_databases(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run("--db", str(tmp_path / "missing.duckdb"), "--as-of", AS_OF) == 2
    assert "no database" in capsys.readouterr().err
    garbage = tmp_path / "garbage.duckdb"
    garbage.write_bytes(b"not a database")
    assert run("--db", str(garbage), "--as-of", AS_OF) == 2
    assert "cannot open" in capsys.readouterr().err
    empty = tmp_path / "empty.duckdb"
    db.connect(empty).close()
    assert run("--db", str(empty), "--as-of", AS_OF) == 2
    assert "not a monitor database" in capsys.readouterr().err


def test_not_normalized_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "stored-only.duckdb"
    assert (
        synthetic.main([str(demo.FIXTURES / "azure_demo.json"), "--db", str(path)]) == 0
    )
    capsys.readouterr()
    assert run("--db", str(path), "--as-of", AS_OF) == 2
    assert "run normalize first" in capsys.readouterr().err


def test_no_snapshot_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "marketplace-only.duckdb"
    marketplace = demo.FIXTURES / "marketplace" / "snapshot-1.json"
    assert synthetic.main([str(marketplace), "--db", str(path)]) == 0
    assert normalize.main(["--db", str(path)]) == 0
    capsys.readouterr()
    assert run("--db", str(path), "--as-of", AS_OF) == 2
    assert "no succeeded azure-retail snapshot" in capsys.readouterr().err


def live(original: Any) -> Any:
    def build(*args: Any, **kwargs: Any) -> brief.FactSet:
        facts: brief.FactSet = original(*args, **kwargs)
        facts.data_label = "live"
        return facts

    return build


def test_collected_prices_stay_under_data(
    demo_db: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(brief, "build", live(brief.build))
    docs = tmp_path / "docs" / "brief"
    assert run("--db", str(demo_db), "--as-of", AS_OF, "--out", str(docs)) == 2
    assert "stays under" in capsys.readouterr().err
    assert not docs.exists()
    monkeypatch.setattr(brief, "DATA", tmp_path / "data")
    local = tmp_path / "data" / "briefs" / "x"
    assert run("--db", str(demo_db), "--as-of", AS_OF, "--out", str(local)) == 0
    assert "**AZURE PUBLISHED LIST PRICES**" in (local / "brief.md").read_text(
        encoding="utf-8"
    )


def test_check_failure_writes_nothing(
    demo_db: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    original = brief.render
    monkeypatch.setattr(
        brief, "render", lambda facts: original(facts).replace("276,480.00", "1.23", 1)
    )
    out = tmp_path / "brief"
    assert run("--db", str(demo_db), "--as-of", AS_OF, "--out", str(out)) == 1
    err = capsys.readouterr().err
    assert "check failed: 1 unmatched (line 9); nothing written" in err
    assert "1.23" not in err  # the line, never the figure
    assert not out.exists()


def test_brief_reads_the_database_read_only(demo_db: Path, tmp_path: Path) -> None:
    holder = db.connect(demo_db, read_only=True)  # the dashboard holds it like this
    try:
        out = tmp_path / "brief"
        assert run("--db", str(demo_db), "--as-of", AS_OF, "--out", str(out)) == 0
    finally:
        holder.close()


# --- --draft, with a synthetic fake sender (brief-drafter spec) ---

REPLIES = json.loads(
    (demo.FIXTURES / "drafter_replies.json").read_text(encoding="utf-8")
)


class Sender:
    def __init__(self, *sections: dict[str, str]) -> None:
        self.replies = list(sections)
        self.sent = 0

    def __call__(self, body: dict[str, Any]) -> drafter.Reply:
        self.sent += 1
        return drafter.Reply(
            json.dumps(self.replies.pop(0)),
            "end_turn",
            "req_synthetic",
            drafter.MODEL,
            {"input_tokens": 5_000, "output_tokens": 900},
        )


def draft(demo_db: Path, out: Path, sender: Sender) -> int:
    args = ["--db", str(demo_db), "--as-of", AS_OF, "--out", str(out), "--draft"]
    return brief.main(args, sender=sender)


def test_draft_without_a_key_is_refused(
    demo_db: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    sender = Sender(REPLIES["valid"])
    assert draft(demo_db, tmp_path / "brief", sender) == 2
    assert "set ANTHROPIC_API_KEY" in capsys.readouterr().err
    assert sender.sent == 0 and not (tmp_path / "brief").exists()


def test_draft_of_collected_prices_is_refused(
    demo_db: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-test-value")
    monkeypatch.setattr(brief, "build", live(brief.build))
    monkeypatch.setattr(brief, "DATA", tmp_path)
    sender = Sender(REPLIES["valid"])
    assert draft(demo_db, tmp_path / "brief", sender) == 2
    assert "synthetic figures only" in capsys.readouterr().err
    assert sender.sent == 0


def test_accepted_draft_is_written(
    demo_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-test-value")
    out = tmp_path / "brief"
    assert draft(demo_db, out, Sender(REPLIES["valid"])) == 0
    text = (out / "brief.md").read_text(encoding="utf-8")
    assert "Prose drafted by claude-opus-5-5 (prompt v1)" in text
    record = json.loads((out / "run-record.json").read_text(encoding="utf-8"))
    assert (record["text_used"], record["requests"]) == ("draft", 1)
    assert record["attempts"][0]["outcome"] == "accepted"
    assert record["estimated_cost_usd"] == pytest.approx(0.038)
    assert "synthetic-test-value" not in json.dumps(record)


def test_rejected_drafts_fall_back_to_the_template(
    demo_db: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-test-value")
    bad = {**REPLIES["valid"], "spot": "The cheapest Spot listing."}
    out = tmp_path / "brief"
    assert draft(demo_db, out, Sender(bad, bad)) == 1
    text = (out / "brief.md").read_text(encoding="utf-8")
    assert "Prose drafted by" not in text
    record = json.loads((out / "run-record.json").read_text(encoding="utf-8"))
    assert (record["text_used"], record["requests"]) == ("template", 2)
    assert "prose: template (2 requests)" in capsys.readouterr().out


def test_draft_failing_the_check_falls_back(
    demo_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-test-value")
    original = brief.checked

    def strict(*args: Any) -> brief_check.CheckResult:
        result = original(*args)
        if "Prose drafted by" in args[2]:
            result.failures.append(brief_check.Failure(1, 1, "x", "number"))
        return result

    monkeypatch.setattr(brief, "checked", strict)
    out = tmp_path / "brief"
    assert draft(demo_db, out, Sender(REPLIES["valid"])) == 1
    record = json.loads((out / "run-record.json").read_text(encoding="utf-8"))
    assert record["text_used"] == "template"
    assert record["attempts"][0]["reasons"] == ["the independent check failed"]
