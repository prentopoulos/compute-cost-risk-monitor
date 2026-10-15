"""The market-brief drafter: a hosted model writes prose, code places every number.

Phase 8 design D16-D19, D28, D36, D44, D45 (brief-drafter spec). One request per attempt
to the Anthropic Claude API, at most two attempts, synthetic figures only. The reply is
one prose string per brief section, with placeholders `[[fact_id]]` and no numbers. A
deterministic validator rejects any digit, number word, unknown placeholder, missing
required placeholder or banned word; after a second rejection, or a failed request, the
template brief is used. Code fills every placeholder and inserts every required label,
and the brief command's independent check verifies the result.

Only this module imports the SDK, and only when a real request is made. No fallback
model is set: the spend gate (PROJECT.md §6, 2026-10-14) approves one model.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from importlib import metadata
from typing import Any

from compute_cost_risk_monitor import brief, history, scenarios, synthetic
from compute_cost_risk_monitor.brief import FactSet

PROVIDER = "Anthropic Claude API"
MODEL = "claude-opus-5-5"
EFFORT = "low"  # thinking cannot be turned off on this model (D16)
MAX_TOKENS = 4_000
TIMEOUT_SECONDS = 120.0
ATTEMPTS = 2  # one retry after a rejected draft (D19)
PROMPT_VERSION = "prompt v1"
# USD per million tokens, from Anthropic's pricing page, retrieved 2026-10-14 (D17).
PRICING = {"date": "2026-10-14", "input": 4.0, "output": 20.0}
NUMBER_WORDS = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
    "hundred",
    "thousand",
    "million",
    "billion",
    "half",
    "halves",
    "twice",
    "double",
    "doubled",
    "triple",
    "tripled",
    "quarter",
    "percent",
    "dozen",
] + ["per cent"]
# Recorded (D44) and owner-added (D28) words the model may not write.
BANNED = (
    "market price",
    "market prices",
    "market rate",
    "market rates",
    "marketplace",
    "index",
    "indices",
    "indexes",
    "benchmark",
    "benchmarks",
    "executed",
    "trade",
    "trades",
    "traded",
    "trading",
    "what customers pay",
    "customers pay",
    "actual cost",
    "forecast",
    "forecasts",
    "forecasting",
    "predict",
    "predicts",
    "predicted",
    "prediction",
    "predictions",
    "projected",
    "projection",
    "projections",
    "trend",
    "trends",
    "trending",
    "live",
    "will",
    "expect",
    "expects",
    "expected",
    "expectation",
    "likely",
    "capacity",
    "availability",
    "in stock",
    "AWS",
    "Amazon",
    "Google Cloud",
    "GCP",
    "Oracle",
    "CoreWeave",
    "Lambda",
    "other clouds",
    "market-wide",
    "the market",
    "industry",
    "ticker",
    "bid",
    "bid/ask",
    "monthly",
    "per month",
    "a month",
    "cheapest",
    "spread",
    "deal",
    "deals",
    "bargain",
    "guarantee",
    "guaranteed",
    "safe",
    "risk-free",
    "hedge",
    "hedging",
    "futures",
)
SYSTEM_PROMPT = f"""\
You write the prose of a short market brief. It describes published retail list prices
for GPU virtual machines from one cloud provider, Azure. The data in this request is
synthetic: invented prices in the shape of Azure's data. Code has already computed and
checked every figure; you only write words around them.

Return JSON with one string per section: {", ".join(brief.SECTIONS)}.
Each string is one to three plain sentences for a reader at a GPU buyer or on a trading
desk: terse, factual, no headings, no lists, no Markdown.

Rules you must follow, or the draft is discarded:
1. Never write a number: no digits and no number words (one, two, half, twice, percent
   and so on). Refer to every figure only through a placeholder [[fact_id]] taken from
   the fact list, exactly as written there. Do not invent fact IDs.
2. The bottom_line section must use these placeholders:
   {", ".join(f"[[{f}]]" for f in brief.REQUIRED["bottom_line"])}.
3. State only what the facts say. Do not recommend, forecast, predict or describe a
   market, an index, trading or other providers. Never use these words or phrases:
   {", ".join(BANNED)}.
4. Say "lowest listed", never "cheapest"; say "for [[bl_hours]] hours", never "monthly".
5. Do not add labels or caveats: code adds the data label, the exclusions, the
   not-a-forecast label and the sources after each section.
"""
PLACEHOLDER = brief.PLACEHOLDER


class DraftFailed(RuntimeError):
    """A request did not complete; the error text never holds the key."""


@dataclass(frozen=True)
class Reply:
    text: str
    stop_reason: str | None
    request_id: str | None
    model: str | None
    usage: dict[str, Any] = field(default_factory=dict)


Sender = Callable[[dict[str, Any]], Reply]


@dataclass
class Outcome:
    text_used: str  # "draft" or "template"
    prose: dict[str, str]
    attempts: list[dict[str, Any]]
    model: str | None = None


def prompt_sha256() -> str:
    return hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()


def schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {section: {"type": "string"} for section in brief.SECTIONS},
        "required": list(brief.SECTIONS),
        "additionalProperties": False,
    }


def usable(facts: FactSet) -> dict[str, brief.Fact]:
    """Facts the model may name: every fact with a value."""
    return {key: fact for key, fact in facts.facts.items() if fact.value is not None}


def fact_list(facts: FactSet) -> str:
    """The user message: the fact IDs with their meanings, and the template prose."""
    lines = ["Facts (ID: meaning; unit; value shown by code):"]
    for key, fact in usable(facts).items():
        group = f"; group {fact.group}" if fact.group else ""
        lines.append(f"- [[{key}]]: {fact.meaning}; {fact.unit}{group}; {fact.text}")
    lines += ["", "The plain template version of each section, for reference:"]
    lines += [f"- {section}: {facts.template[section]}" for section in brief.SECTIONS]
    return "\n".join(lines)


def request(facts: FactSet) -> dict[str, Any]:
    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "output_config": {
            "effort": EFFORT,
            "format": {"type": "json_schema", "schema": schema()},
        },
        "messages": [{"role": "user", "content": fact_list(facts)}],
    }


def _pattern(term: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![\w-]){re.escape(term)}(?![\w-])", re.IGNORECASE)


_NUMBER_WORDS = [(word, _pattern(word)) for word in NUMBER_WORDS]
_BANNED = [(term, _pattern(term)) for term in BANNED]


def parse(reply: Reply) -> dict[str, str] | None:
    try:
        data = json.loads(reply.text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or set(data) != set(brief.SECTIONS):
        return None
    if not all(isinstance(value, str) and value.strip() for value in data.values()):
        return None
    return {key: str(value) for key, value in data.items()}


def rejections(reply: Reply, facts: FactSet) -> list[str]:
    """Why a reply cannot be used; empty when it can (brief-drafter spec)."""
    if reply.stop_reason == "refusal":
        return ["the model declined (stop reason refusal)"]
    if reply.stop_reason == "max_tokens":
        return ["the reply was cut off (stop reason max_tokens)"]
    prose = parse(reply)
    if prose is None:
        return ["the reply does not match the section schema"]
    known = usable(facts)
    reasons = []
    for section, text in prose.items():
        named = PLACEHOLDER.findall(text)
        unknown = sorted({key for key in named if key not in known})
        if unknown:
            reasons.append(f"{section}: unknown placeholder {', '.join(unknown)}")
        words = PLACEHOLDER.sub(" ", text)
        if "[[" in words or "]]" in words:
            reasons.append(f"{section}: a malformed placeholder")
        if re.search(r"\d", words):
            reasons.append(f"{section}: a digit outside placeholders")
        for word, pattern in _NUMBER_WORDS:
            if pattern.search(words):
                reasons.append(f"{section}: the number word {word!r}")
        for term, pattern in _BANNED:
            if pattern.search(words):
                reasons.append(f"{section}: the banned word {term!r}")
        required = brief.REQUIRED.get(section, ())
        missing = [key for key in required if key in known and key not in named]
        if missing:
            reasons.append(f"{section}: missing placeholder {', '.join(missing)}")
    return reasons


def required_texts(facts: FactSet) -> list[str]:
    """Labels the final brief must hold, inserted by code (D45)."""
    texts = [
        brief.SYNTHETIC_LABEL if facts.data_label == synthetic.LABEL else brief.FRAMING,
        "AS OF",
        brief.exclusion_items(facts.exclusions),
        brief.CREDIT,
        "Sample too thin for trends:",
    ]
    if facts.facts.get("bl_cost") and facts.facts["bl_cost"].value is not None:
        texts += [
            f"{scenarios.NOT_A_FORECAST}.",
            brief.JUDGEMENT,
            brief.CROSSES_REGIONS,
        ]
    if facts.facts["n_absent_once"].value:
        texts.append(history.ABSENT_ONCE)
    if facts.facts["n_not_listed"].value:
        texts.append(history.NOT_LISTED)
    return texts


def missing_texts(text: str, facts: FactSet) -> list[str]:
    return [label for label in required_texts(facts) if label not in text]


def disclosure(model: str | None) -> str:
    return brief.DISCLOSURE.format(model=model or MODEL, prompt=PROMPT_VERSION)


def _attempt(reply: Reply, reasons: Sequence[str]) -> dict[str, Any]:
    return {
        "model": reply.model,
        "outcome": "rejected" if reasons else "accepted",
        "reasons": list(reasons),
        "request_id": reply.request_id,
        "stop_reason": reply.stop_reason,
        "usage": reply.usage,
    }


def draft(facts: FactSet, send: Sender) -> Outcome:
    """Up to two attempts; the template prose when none is usable."""
    attempts: list[dict[str, Any]] = []
    for _ in range(ATTEMPTS):
        try:
            reply = send(request(facts))
        except DraftFailed as error:
            attempts.append({"outcome": "failed", "reasons": [str(error)]})
            break
        reasons = rejections(reply, facts)
        prose = None if reasons else parse(reply)
        if prose is not None:
            text = brief.render(facts, prose, disclosure(reply.model))
            missing = missing_texts(text, facts)
            reasons = [f"missing required text {label!r}" for label in missing]
        attempts.append(_attempt(reply, reasons))
        if prose is not None and not reasons:
            return Outcome("draft", prose, attempts, reply.model)
    return Outcome("template", dict(facts.template), attempts)


def estimated_cost(attempts: Sequence[Mapping[str, Any]]) -> float:
    """USD at the recorded pricing; thinking tokens bill as output tokens."""
    total = 0.0
    for attempt in attempts:
        usage = attempt.get("usage") or {}
        total += usage.get("input_tokens", 0) * PRICING["input"] / 1_000_000
        total += usage.get("output_tokens", 0) * PRICING["output"] / 1_000_000
    return round(total, 6)


def record_fields(outcome: Outcome) -> dict[str, Any]:
    """The drafter's part of the run record; never the key (brief-drafter spec)."""
    return {
        "estimated_cost_usd": estimated_cost(outcome.attempts),
        "model": MODEL,
        "model_used": outcome.model,
        "pricing": PRICING,
        "prompt_sha256": prompt_sha256(),
        "prompt_version": PROMPT_VERSION,
        "provider": PROVIDER,
        "sdk_version": metadata.version("anthropic"),
    }


def anthropic_sender() -> Sender:
    """The real sender: the official SDK, no SDK retries, no fallback model."""
    import anthropic  # only here, so the package never needs the SDK otherwise

    client = anthropic.Anthropic(max_retries=0, timeout=TIMEOUT_SECONDS)

    def send(body: dict[str, Any]) -> Reply:
        try:
            response = client.messages.create(**body)
        except anthropic.APIError as error:
            raise DraftFailed(f"request failed: {type(error).__name__}") from None
        text = next((b.text for b in response.content if b.type == "text"), "")
        return Reply(
            text=text,
            stop_reason=response.stop_reason,
            request_id=response._request_id,
            model=response.model,
            usage=response.usage.model_dump(),
        )

    return send
