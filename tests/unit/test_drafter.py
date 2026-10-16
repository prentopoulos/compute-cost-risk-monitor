"""The market-brief drafter, offline (Phase 8 design D16-D19, D28, D36; brief-drafter).

Every reply here is synthetic, from tests/fixtures/synthetic/drafter_replies.json or
built in the test; no test sends a request, needs a key or opens a socket.
"""

import json
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pytest

from compute_cost_risk_monitor import brief, brief_check, demo, drafter
from compute_cost_risk_monitor.drafter import Reply
from support import FIXTURES

REPLIES = json.loads((FIXTURES / "drafter_replies.json").read_text(encoding="utf-8"))
AS_OF = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)
USAGE = {"input_tokens": 5_000, "output_tokens": 900}


def reply(sections: dict[str, str], stop: str = "end_turn") -> Reply:
    return Reply(json.dumps(sections), stop, "req_synthetic", drafter.MODEL, USAGE)


def broken(case: str) -> Reply:
    section, text = REPLIES["breaks"][case]
    return reply({**REPLIES["valid"], section: text})


class Fake:
    """A sender that returns the given replies in turn and keeps every request."""

    def __init__(self, *replies: Reply | Exception) -> None:
        self.replies = list(replies)
        self.requests: list[dict[str, Any]] = []

    def __call__(self, body: dict[str, Any]) -> Reply:
        self.requests.append(body)
        item = self.replies.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture(scope="module")
def demo_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("demo") / "synthetic.duckdb"
    assert demo.build(path) == 0
    return path


@pytest.fixture(scope="module")
def con(demo_db: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    connection = duckdb.connect(
        str(demo_db), read_only=True, config={"TimeZone": "UTC"}
    )
    yield connection
    connection.close()


@pytest.fixture(scope="module")
def facts(con: duckdb.DuckDBPyConnection) -> brief.FactSet:
    return brief.build(con, AS_OF)


def test_fixture_is_labelled_synthetic() -> None:
    assert REPLIES["_label"] == "synthetic"


def test_request_shape(facts: brief.FactSet) -> None:
    body = drafter.request(facts)
    assert (body["model"], body["max_tokens"]) == ("claude-opus-5-5", 4000)
    assert body["output_config"]["effort"] == "low"
    schema = body["output_config"]["format"]["schema"]
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert schema["required"] == list(brief.SECTIONS)
    assert schema["additionalProperties"] is False
    assert body["system"] == drafter.SYSTEM_PROMPT
    assert "fallbacks" not in body and "betas" not in body
    (message,) = body["messages"]
    assert (
        "[[bl_cost]]: the workload's cost at the lowest listed price"
        in message["content"]
    )
    assert drafter.PROMPT_VERSION == "prompt v3"


def test_valid_draft_is_filled_and_checks(
    facts: brief.FactSet, con: duckdb.DuckDBPyConnection
) -> None:
    fake = Fake(reply(REPLIES["valid"]))
    outcome = drafter.draft(facts, fake)
    assert outcome.text_used == "draft" and len(fake.requests) == 1
    assert outcome.attempts[0]["outcome"] == "accepted"
    text = brief.render(facts, outcome.prose, drafter.disclosure(outcome.model))
    assert "cost USD 276,480.00 at the lowest listed pay-as-you-go price" in text
    assert (
        "Prose drafted by claude-opus-5-5 (prompt v3); every number placed and checked"
        " by code."
    ) in text
    work = facts.workload
    derived = brief_check.derive(
        con, AS_OF, work.variant, work.gpus_per_vm, work.gpus, work.hours
    )
    assert brief_check.check(text, derived).passed
    assert drafter.missing_texts(text, facts) == []


@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("digit", "changes: a digit outside placeholders ('2')"),
        ("number_word", "groups: the number word 'twice'"),
        ("unknown_placeholder", "regions: unknown placeholder n_regions_total"),
        ("missing_contingency", "bottom_line: missing placeholder bl_c25, bl_c50"),
        ("cheapest", "spot: the banned word 'cheapest'"),
        ("will", "quality: the banned word 'will'"),
        ("malformed", "groups: a malformed placeholder"),
    ],
)
def test_each_rejection_named(facts: brief.FactSet, case: str, reason: str) -> None:
    assert reason in drafter.rejections(broken(case), facts)


@pytest.mark.parametrize(
    ("stop", "text", "reason"),
    [
        ("refusal", "{}", "the model declined (stop reason refusal)"),
        ("max_tokens", "{", "the reply was cut off (stop reason max_tokens)"),
        ("end_turn", "not json", "the reply does not match the section schema"),
        ("end_turn", "[]", "the reply does not match the section schema"),
        (
            "end_turn",
            '{"bottom_line": "x"}',
            "the reply does not match the section schema",
        ),
    ],
)
def test_unusable_replies(
    facts: brief.FactSet, stop: str, text: str, reason: str
) -> None:
    assert drafter.rejections(Reply(text, stop, None, None), facts) == [reason]


def test_empty_section_is_unusable(facts: brief.FactSet) -> None:
    sections = {**REPLIES["valid"], "groups": "  "}
    assert drafter.rejections(reply(sections), facts) == [
        "the reply does not match the section schema"
    ]


def test_two_rejections_fall_back(facts: brief.FactSet) -> None:
    fake = Fake(broken("digit"), broken("cheapest"))
    outcome = drafter.draft(facts, fake)
    assert outcome.text_used == "template" and len(fake.requests) == 2
    assert outcome.prose == facts.template
    assert [a["outcome"] for a in outcome.attempts] == ["rejected", "rejected"]
    assert outcome.attempts[1]["reasons"] == ["spot: the banned word 'cheapest'"]


def test_second_attempt_accepted(facts: brief.FactSet) -> None:
    fake = Fake(broken("will"), reply(REPLIES["valid"]))
    outcome = drafter.draft(facts, fake)
    assert outcome.text_used == "draft"
    assert outcome.attempts[0]["reasons"] == ["quality: the banned word 'will'"]
    assert outcome.attempts[1]["outcome"] == "accepted"


def test_failed_request_falls_back_without_retry(facts: brief.FactSet) -> None:
    fake = Fake(drafter.DraftFailed("request failed: APIConnectionError"))
    outcome = drafter.draft(facts, fake)
    assert outcome.text_used == "template" and len(fake.requests) == 1
    assert outcome.attempts == [
        {"outcome": "failed", "reasons": ["request failed: APIConnectionError"]}
    ]


def test_missing_required_text_rejects(
    facts: brief.FactSet, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(drafter, "required_texts", lambda _facts: ["not in any brief"])
    outcome = drafter.draft(
        facts, Fake(reply(REPLIES["valid"]), reply(REPLIES["valid"]))
    )
    assert outcome.text_used == "template"
    assert outcome.attempts[0]["reasons"] == [
        "missing required text 'not in any brief'"
    ]


def test_required_texts_follow_the_facts(con: duckdb.DuckDBPyConnection) -> None:
    facts = brief.build(con, AS_OF)
    labels = drafter.required_texts(facts)
    assert brief.SYNTHETIC_LABEL in labels and brief.CREDIT in labels
    assert "absent once (unconfirmed)" in labels and "not listed" in labels
    assert "Scenario calculation, not a forecast." in labels
    none = brief.build(con, AS_OF, brief.Workload(variant="B200"))
    assert "bl_cost" not in drafter.usable(none)
    assert "Scenario calculation, not a forecast." not in drafter.required_texts(none)
    none.data_label = "live"
    assert brief.FRAMING in drafter.required_texts(none)
    single = dict(none.facts)
    single["n_absent_once"] = brief.Fact("n_absent_once", 0, "count", "0", "x")
    single["n_not_listed"] = brief.Fact("n_not_listed", 0, "count", "0", "x")
    none.facts = single
    assert "not listed" not in drafter.required_texts(none)


def test_no_pay_as_you_go_draft_skips_missing_figures(
    con: duckdb.DuckDBPyConnection,
) -> None:
    facts = brief.build(con, AS_OF, brief.Workload(variant="B200"))
    sections = {
        **REPLIES["valid"],
        "bottom_line": "No [[bl_variant]] listing.",
        "changes": "[[n_changes]] listed prices changed by [[snap_time]].",
    }
    assert drafter.rejections(reply(sections), facts) == []
    # A figure that does not exist here is still an unknown placeholder.
    assert "changes: unknown placeholder bl_region" in drafter.rejections(
        reply(REPLIES["valid"]), facts
    )


def test_cost_and_record_fields(facts: brief.FactSet) -> None:
    outcome = drafter.draft(facts, Fake(reply(REPLIES["valid"])))
    assert drafter.estimated_cost(outcome.attempts) == pytest.approx(0.038)
    assert drafter.estimated_cost([{"outcome": "failed"}]) == 0.0
    fields = drafter.record_fields(outcome)
    assert fields["provider"] == "Anthropic Claude API"
    assert (fields["model"], fields["model_used"]) == (
        "claude-opus-5-5",
        "claude-opus-5-5",
    )
    assert (fields["prompt_version"], fields["pricing"]["date"]) == (
        "prompt v3",
        "2026-10-14",
    )
    assert fields["prompt_sha256"] == drafter.prompt_sha256()
    assert fields["sdk_version"].startswith("1.")


class FakeError(Exception):
    pass


def test_anthropic_sender_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    import anthropic

    made: list[dict[str, Any]] = []

    class Block:
        type = "text"
        text = '{"bottom_line": "x"}'

    class Usage:
        def model_dump(self) -> dict[str, int]:
            return USAGE

    class Response:
        content = [Block()]
        stop_reason = "end_turn"
        _request_id = "req_synthetic"
        model = "claude-opus-5-5"
        usage = Usage()

    class Messages:
        def create(self, **body: Any) -> Response:
            if body["model"] == "fail":
                raise FakeError("boom")
            return Response()

    class Client:
        def __init__(self, **options: Any) -> None:
            made.append(options)
            self.messages = Messages()

    monkeypatch.setattr(anthropic, "Anthropic", Client)
    monkeypatch.setattr(anthropic, "APIError", FakeError)
    send = drafter.anthropic_sender()
    assert made == [{"max_retries": 0, "timeout": 120.0}]
    got = send({"model": drafter.MODEL})
    assert got == Reply(
        '{"bottom_line": "x"}', "end_turn", "req_synthetic", "claude-opus-5-5", USAGE
    )
    with pytest.raises(drafter.DraftFailed, match="request failed: FakeError"):
        send({"model": "fail"})
    assert "anthropic" in sys.modules


def test_line_breaks_headings_and_quantity_words_rejected(
    facts: brief.FactSet,
) -> None:
    # Code review: a heading could end the checked body early, and plurals, multiples
    # and ordinals state quantities that no code checks.
    sections = {
        **REPLIES["valid"],
        "absences": REPLIES["valid"]["absences"] + "\n## Records",
        "groups": "Prices rose by thousands; Spot halved in tenfold moves, both ways.",
    }
    reasons = drafter.rejections(reply(sections), facts)
    assert "absences: a line break or '#' (prose is one paragraph)" in reasons
    for word in ("thousands", "halved", "tenfold", "both"):
        assert f"groups: the number word {word!r}" in reasons
    absent_once = {**REPLIES["valid"], "absences": "A listing is absent once."}
    assert drafter.rejections(reply(absent_once), facts) == []  # the defined term


def test_names_with_digits_are_not_figures(facts: brief.FactSet) -> None:
    # Phase 8 design D46, after the first real run rejected both drafts for names.
    expected = {"H100 NVLink 80GB", "H100", "T4", "ND96isr H100 v5", "US West 3"}
    assert expected <= set(facts.names)
    sections = {
        **REPLIES["valid"],
        "changes": "[[n_changes]] listed prices changed between [[prev_time]] and"
        " [[snap_time]], each for H100 NVLink 80GB on ND96isr H100 v5 in US East.",
        "regions": "The summaries cover US West 3 and Sweden Central:"
        " [[n_summaries]] in all.",
    }
    assert drafter.rejections(reply(sections), facts) == []
    named = {
        **REPLIES["valid"],
        "groups": "H100 has [[n_groups]] groups, T4 more than 8.",
    }
    assert drafter.rejections(reply(named), facts) == [
        "groups: a digit outside placeholders ('8.')"
    ]
    assert "Names you may write as they are: " in drafter.fact_list(facts)


def test_attempts_keep_the_reply(facts: brief.FactSet) -> None:
    outcome = drafter.draft(facts, Fake(broken("digit"), reply(REPLIES["valid"])))
    assert outcome.attempts[0]["reply"] == broken("digit").text
