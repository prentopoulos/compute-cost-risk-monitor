"""Shared fakes for collector tests: a manual clock, scripted fetcher, page builders.

Everything here is synthetic. Nothing touches the network: the fetcher returns scripted
responses and the clock only moves when the code under test sleeps or a request runs.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from compute_cost_risk_monitor import azure_retail as az
from compute_cost_risk_monitor import fetch

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "synthetic"
START = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)
BASE_ITEM: dict[str, Any] = json.loads(
    (FIXTURES / "azure_items.json").read_text(encoding="utf-8")
)["base"]


class FakeClock:
    def __init__(self, start: datetime = START) -> None:
        self.start = start
        self.elapsed = 0.0
        self.sleeps: list[float] = []

    def now(self) -> datetime:
        return self.start + timedelta(seconds=self.elapsed)

    def monotonic(self) -> float:
        return self.elapsed

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.elapsed += seconds

    def clock(self) -> fetch.Clock:
        return fetch.Clock(self.now, self.monotonic, self.sleep)


class ScriptedFetcher:
    """Returns scripted responses in order; each call takes `latency` seconds."""

    def __init__(
        self,
        clock: FakeClock,
        responses: Sequence[fetch.Response | BaseException],
        latency: float = 0.25,
    ) -> None:
        self.clock = clock
        self.responses = list(responses)
        self.latency = latency
        self.calls: list[tuple[str, float]] = []

    def __call__(self, url: str, timeout: float) -> fetch.Response:
        self.calls.append((url, self.clock.elapsed))
        self.clock.elapsed += self.latency
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def item(**overrides: Any) -> dict[str, Any]:
    row = copy.deepcopy(BASE_ITEM)
    row.update(overrides)
    return row


def page_bytes(items: list[Any], next_link: str | None = None) -> bytes:
    document = {
        "_label": "synthetic",
        "BillingCurrency": "USD",
        "CustomerEntityId": "Default",
        "CustomerEntityType": "Retail",
        "Items": items,
        "NextPageLink": next_link,
        "Count": len(items),
    }
    return json.dumps(document).encode("utf-8")


def ok(body: bytes, *headers: tuple[str, str]) -> fetch.Response:
    return fetch.Response(
        200,
        "OK",
        [("Content-Type", "application/json; charset=utf-8"), *headers],
        body,
        None,
    )


def status(code: int, reason: str = "", *headers: tuple[str, str]) -> fetch.Response:
    return fetch.Response(code, reason, list(headers), reason.encode("ascii"), None)


def timed_out() -> fetch.Response:
    return fetch.Response(None, "", [], b"", "TimeoutError: timed out")


def next_link(skip: int) -> str:
    return f"{az.first_page_url()}&$skip={skip}"


def collect(
    raw_root: Path,
    responses: Sequence[fetch.Response | BaseException],
    limits: fetch.Limits | None = None,
    label: str = "synthetic",
) -> tuple[fetch.RunResult, ScriptedFetcher, FakeClock]:
    """Run the fetch loop against scripted responses."""
    clock = FakeClock()
    fetcher = ScriptedFetcher(clock, responses)
    result = fetch.fetch_run(
        raw_root,
        fetcher,
        clock.clock(),
        data_label=label,
        code_version="test",
        dependency_versions={"duckdb": "test"},
        user_agent="compute-cost-risk-monitor/test",
        limits=limits,
    )
    return result, fetcher, clock
