"""The market brief's fact set and template (Phase 8 design D8, D27, D32; market-brief).

The database is built from the committed synthetic demo history. Every expected figure
is the hand-worked answer in tests/fixtures/synthetic/README.md.
"""

import copy
import hashlib
import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb
import pytest

from compute_cost_risk_monitor import brief, normalize, synthetic
from seed import database
from support import FIXTURES

AZURE_FILES = [
    FIXTURES / "azure_demo_history" / "snapshot-1.json",
    FIXTURES / "azure_demo_history" / "snapshot-2.json",
    FIXTURES / "azure_demo.json",
]
AS_OF = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)
NOW = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
BOTTOM_LINE = (
    "32 H100 NVLink 80GB GPUs (4 × ND96isr H100 v5) for 720 hours cost USD 276,480.00"
    " at the lowest listed pay-as-you-go price for this size: US East, 12.0000"
    " USD/GPU-h. This size lists in 5 regions at 12.0000–15.0000 USD/GPU-h, so the same"
    " workload costs USD 276,480.00–345,600.00. A contingency of USD 69,120.00 covers a"
    " +25% list-price move, and USD 138,240.00 a +50% move."
)


def stored(files: list[Path]) -> duckdb.DuckDBPyConnection:
    connection = database()
    for path in files:
        synthetic.ingest_file(connection, path)
    normalize.normalize_pending(connection, NOW)
    return connection


@pytest.fixture(scope="module")
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    connection = stored(AZURE_FILES)
    yield connection
    connection.close()


@pytest.fixture(scope="module")
def facts(con: duckdb.DuckDBPyConnection) -> brief.FactSet:
    return brief.build(con, AS_OF)


@pytest.fixture(scope="module")
def text(facts: brief.FactSet) -> str:
    return brief.render(facts)


def section(text: str, title: str) -> str:
    after = text.split(f"## {title}\n\n", 1)[1]
    return after.split("\n## ", 1)[0]


def test_facts_link_to_their_records(facts: brief.FactSet) -> None:
    price = facts.facts["bl_price"]
    assert (price.value, price.text, price.unit) == (12.0, "12.0000", "USD/GPU-h")
    assert price.group == "H100 NVLink 80GB × 8 · pay-as-you-go"
    (record,) = price.records
    assert record.run_id == facts.snapshot
    assert record.item_key is not None and "000101" in record.item_key
    assert record.sha256 == hashlib.sha256(AZURE_FILES[2].read_bytes()).hexdigest()
    assert (record.retrieved_at, record.currency, record.unit, record.rental_type) == (
        "2026-10-12 09:00 UTC",
        "USD",
        "1 Hour",
        "on_demand",
    )
    cost = facts.facts["bl_cost"]
    assert (cost.value, cost.text) == (276_480.0, "276,480.00")
    assert cost.derived_from == ("bl_gpus", "bl_hours", "bl_price")
    assert len(facts.facts["bl_regions"].records) == 5


def test_fact_set_header(facts: brief.FactSet) -> None:
    assert (facts.snapshots, facts.stale, facts.data_label) == (3, False, "synthetic")
    assert facts.snapshot_start == "2026-10-12 09:00 UTC"
    assert facts.as_of == "2026-10-12 09:00 UTC"
    assert (facts.rule_version, facts.map_version) == ("groups-v1", "gpu-map-v1")


def test_reproducible_bytes(con: duckdb.DuckDBPyConnection) -> None:
    assert brief.build(con, AS_OF).to_json() == brief.build(con, AS_OF).to_json()


def test_bottom_line_on_the_demo(text: str) -> None:
    shown = section(text, "Bottom line")
    assert shown.startswith(BOTTOM_LINE + "\n")
    assert "*This compares across regions.*" in shown
    assert "*Scenario calculation, not a forecast. Round sensitivities" in shown
    assert (
        "*Not priced: disks and storage, egress, public IPs, licences, taxes,"
        " negotiated discounts, reservations and savings plans, Spot eviction risk,"
        " capacity and quota.*"
    ) in shown
    for banned in ("cheapest", "monthly", "forecast will"):
        assert banned not in shown


def test_changes_and_absences_on_the_demo(text: str) -> None:
    changes = section(text, "Changes since the previous snapshot")
    assert changes.splitlines()[:4] == [
        "2 listed prices changed between 2026-10-05 09:00 UTC and"
        " 2026-10-12 09:00 UTC.",
        "",
        "- US East · ND96isr H100 v5 · pay-as-you-go · linux: 88.00 → 96.00 USD/VM-h"
        " (11.0000 → 12.0000 USD/GPU-h).",
        "- US East · ND96isr H100 v5 · Spot · linux: 88.00 → 96.00 USD/VM-h"
        " (11.0000 → 12.0000 USD/GPU-h).",
    ]
    absences = section(text, "Absences")
    assert absences.splitlines()[:4] == [
        "1 listing is absent once (unconfirmed), and 1 is not listed.",
        "",
        "- EU West · NC24ads A100 v4 · pay-as-you-go · linux: absent once (unconfirmed)"
        " since 2026-10-12 09:00 UTC, last seen 2026-10-05 09:00 UTC.",
        "- EU West · NC8as T4 v3 · pay-as-you-go · linux: not listed since"
        " 2026-10-05 09:00 UTC, last seen 2026-09-28 09:00 UTC.",
    ]


def test_groups_spot_regions_and_quality(text: str) -> None:
    assert section(text, "Groups per GPU").startswith(
        "11 region groups across 3 GPU variants; 10 of them have a single list price."
    )
    assert "| H100 NVLink 80GB | 8 | 8 |" in text
    assert "| T4 16GB | 2 | 1 |" in text
    spot = section(text, "Spot against pay-as-you-go")
    assert spot.startswith(
        "2 of 3 Spot listings have the same size on pay-as-you-go in the same region;"
        " 1 equals it and 0 are above it."
    )
    assert "| US East | ND96isr H100 v5 | 12.0000 | 12.0000 | 100.0 |" in spot
    assert "| EU West | ND96isr H100 v5 | 5.0000 | 12.5000 | 40.0 |" in spot
    assert f"| UK South | ND96isr H100 v5 | 6.0000 | {brief.NO_PAYG} | — |" in spot
    assert f"*{brief.CROSSES_RENTAL}*" in spot
    regions = section(text, "Across regions")
    assert regions.startswith(
        "4 cross-region summaries; 3 of them are thin, from fewer than 5 regions."
    )
    assert (
        "| H100 NVLink 80GB × 8 | pay-as-you-go | 5 | 12.0000 | 13.0000 | 15.0000 |"
        " crosses regions |"
    ) in regions
    assert "| T4 16GB × 1 | pay-as-you-go | 2 | 0.6000 | 0.6500 | 0.7000 |" in regions
    quality = section(text, "Data quality")
    assert "- Observations: 14, of which 12 are compared." in quality
    assert "- Changes since the previous snapshot: 2." in quality
    assert "- Absent once (unconfirmed): 1; not listed: 1." in quality
    assert "*Sample too thin for trends: 3 snapshots over 14 days.*" in quality


def test_header_and_credit(text: str, facts: brief.FactSet) -> None:
    assert text.startswith(
        "# Market brief\n\n**SYNTHETIC DATA — NOT AZURE LIST PRICES**"
    )
    assert f"(run {facts.snapshot}) · AS OF 2026-10-12 09:00 UTC" in text
    assert brief.SYNTHETIC_FRAMING in text
    assert brief.CREDIT in text
    assert "STALE" not in text


def test_every_fact_used_is_in_the_records_table(facts: brief.FactSet) -> None:
    raw = brief.assemble(facts, facts.template)
    table = brief.records_table(facts, brief.used_facts(raw))
    for fact_id in brief.used_facts(raw):
        assert f"| `{fact_id}` |" in table
    assert "\\|" in table  # item keys hold "|", escaped in the table
    rendered = brief.render(facts)
    assert "[[" not in rendered.split("\n## Records\n")[0]


def test_stale_and_published_headers(con: duckdb.DuckDBPyConnection) -> None:
    late = brief.build(con, AS_OF + timedelta(days=8))
    assert late.stale
    shown = brief.render(late)
    assert "· STALE — OLDER THAN 7 DAYS AS OF 2026-10-20 09:00 UTC" in shown
    late.data_label = "live"
    assert brief.header(late)[2].startswith(f"**{brief.PUBLISHED_LABEL}**")
    assert brief.header(late)[4] == brief.FRAMING


def test_single_snapshot() -> None:
    connection = stored([FIXTURES / "azure_demo.json"])
    try:
        text = brief.render(brief.build(connection, AS_OF))
    finally:
        connection.close()
    assert section(text, "Changes since the previous snapshot").startswith(
        "Changes need a second snapshot; this database holds 1."
    )
    assert section(text, "Absences").startswith(
        "No listing is missing from the latest snapshot."
    )
    assert "*Sample too thin for trends: 1 snapshot over 0 days.*" in text


def test_no_pay_as_you_go_listing(con: duckdb.DuckDBPyConnection) -> None:
    facts = brief.build(con, AS_OF, brief.Workload(variant="B200 NVLink 192GB"))
    cost = facts.facts["bl_cost"]
    assert (cost.value, cost.text) == (None, "not computed")
    assert cost.reason == "no pay-as-you-go listing for this GPU and count"
    shown = section(brief.render(facts), "Bottom line")
    assert shown.startswith(
        "No pay-as-you-go listing for B200 NVLink 192GB in this snapshot, so no cost is"
        " stated."
    )
    assert "USD" not in shown.split("*Not priced")[0]


def test_thin_bottom_line(con: duckdb.DuckDBPyConnection) -> None:
    facts = brief.build(con, AS_OF, brief.Workload(variant="T4 16GB", gpus_per_vm=1))
    shown = section(brief.render(facts), "Bottom line")
    assert "*This compares across regions. Thin: fewer than 5 regions.*" in shown
    assert facts.facts["bl_cost"].text == "13,824.00"  # 32 x 720 x 0.6, eastus


def test_no_changes_between_identical_snapshots() -> None:
    connection = stored(AZURE_FILES[:2])
    try:
        text = brief.render(brief.build(connection, AS_OF))
    finally:
        connection.close()
    assert section(text, "Changes since the previous snapshot").startswith(
        "No listed price changed between 2026-09-28 09:00 UTC and 2026-10-05 09:00 UTC."
    )


def test_refusals(con: duckdb.DuckDBPyConnection) -> None:
    with pytest.raises(brief.BriefError, match="before the latest snapshot"):
        brief.build(con, AS_OF - timedelta(minutes=1))
    empty = database()
    try:
        with pytest.raises(brief.BriefError, match="no succeeded"):
            brief.build(empty, AS_OF)
    finally:
        empty.close()


def test_fill_and_add_guard(facts: brief.FactSet) -> None:
    assert brief.fill("[[bl_cost]] USD", facts) == "276,480.00 USD"
    with pytest.raises(KeyError):
        brief.fill("[[no_such_fact]]", facts)
    with pytest.raises(ValueError, match="duplicate"):
        facts.add(facts.facts["bl_cost"])
    with pytest.raises(ValueError, match="bad fact ID"):
        facts.add(brief.Fact("Bad-ID", 1, "count", "1", "bad"))


@pytest.mark.parametrize(
    ("value", "shown"),
    [(3.8, "3.80"), (96.0, "96.00"), (0.125, "0.125"), (1234.5, "1,234.50")],
)
def test_published_keeps_every_decimal(value: float, shown: str) -> None:
    assert brief.published(value) == shown


def test_small_formats() -> None:
    assert (brief.move(25.0), brief.move(12.5)) == ("25", "12.5")
    assert (brief.hours_text(720.0), brief.hours_text(0.5)) == ("720", "0.5")
    assert (brief.usd(2.005), brief.per_gpu(0.00005), brief.percent(9.95)) == (
        "2.01",
        "0.0001",
        "10.0",
    )
    assert brief.rental_name("dev_test") == "dev_test"
    assert brief.exclusion_items("Excludes a, b.") == "a, b"


def test_disclosure_line(facts: brief.FactSet) -> None:
    line = brief.DISCLOSURE.format(model="claude-opus-5-5", prompt="prompt v1")
    shown = brief.render(facts, facts.template, line)
    assert f"{brief.CREDIT}\n\n{line}\n" in shown


def test_change_to_an_excluded_row(tmp_path: Path) -> None:
    """A Windows row is stored but not compared: its change has no per-GPU price."""
    demo = json.loads((FIXTURES / "azure_demo.json").read_text(encoding="utf-8"))
    later = copy.deepcopy(demo)
    later["observed_at"] = "2026-10-19T09:00:00+00:00"
    (windows,) = [i for i in later["Items"] if i["productName"].endswith("Windows")]
    windows["retailPrice"] = windows["unitPrice"] = 1.1  # invented, from 0.9
    path = tmp_path / "later.json"
    path.write_bytes(json.dumps(later).encode("utf-8"))
    connection = stored([FIXTURES / "azure_demo.json", path])
    try:
        text = brief.render(
            brief.build(connection, datetime(2026, 10, 19, 9, tzinfo=UTC))
        )
    finally:
        connection.close()
    changes = section(text, "Changes since the previous snapshot")
    assert (
        "- US East · NC4as T4 v3 · pay-as-you-go · windows: 0.90 → 1.10 USD/VM-h."
        in (changes)
    )
