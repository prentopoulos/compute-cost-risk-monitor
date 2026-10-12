"""The urllib fetcher and the paced fetch loop, against fakes only (no network)."""

import email.message
import http.client
import io
import json
import urllib.error
import urllib.request
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from compute_cost_risk_monitor import azure_retail as az
from compute_cost_risk_monitor import fetch, raw_store
from support import (
    START,
    FakeClock,
    collect,
    item,
    next_link,
    ok,
    page_bytes,
    status,
    timed_out,
)

# --- the urllib fetcher, with a fake opener ---


class FakeReply:
    def __init__(self, body: bytes, code: int = 200) -> None:
        self.body = body
        self.status = code
        self.reason = "OK"
        self.headers = email.message.Message()
        self.headers["Content-Type"] = "application/json"

    def read(self, limit: int) -> bytes:
        return self.body[:limit]

    def __enter__(self) -> "FakeReply":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class FakeOpener(urllib.request.OpenerDirector):
    def __init__(self, outcome: FakeReply | BaseException) -> None:
        super().__init__()
        self.outcome = outcome
        self.requests: list[tuple[urllib.request.Request, float | None]] = []

    def open(self, fullurl: Any, data: Any = None, timeout: Any = None) -> Any:
        self.requests.append((fullurl, timeout))
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


def test_fetcher_sends_a_plain_get() -> None:
    opener = FakeOpener(FakeReply(b"{}"))
    response = fetch.UrllibFetcher("ua/1", opener)(az.first_page_url(), 30.0)
    request, timeout = opener.requests[0]
    assert (request.get_method(), request.full_url, timeout) == (
        "GET",
        az.first_page_url(),
        30.0,
    )
    assert request.header_items() == [("User-agent", "ua/1")]
    assert request.data is None
    assert response == fetch.Response(
        200, "OK", [("Content-Type", "application/json")], b"{}", None
    )


def test_fetcher_keeps_an_http_error_body() -> None:
    headers = email.message.Message()
    headers["Retry-After"] = "7"
    error = urllib.error.HTTPError(
        "https://prices.azure.com/",
        429,
        "Too Many Requests",
        headers,
        io.BytesIO(b"busy"),
    )
    response = fetch.UrllibFetcher("ua/1", FakeOpener(error))("https://x.test/", 1.0)
    assert (response.status, response.body, response.error) == (429, b"busy", None)
    assert response.headers == [("Retry-After", "7")]


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("timed out"),
        urllib.error.URLError("refused"),
        http.client.IncompleteRead(b""),
    ],
)
def test_fetcher_reports_transport_errors(error: BaseException) -> None:
    response = fetch.UrllibFetcher("ua/1", FakeOpener(error))("https://x.test/", 1.0)
    assert (response.status, response.body) == (None, b"")
    assert response.error is not None
    assert response.error.startswith(type(error).__name__)


def test_fetcher_caps_the_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetch, "MAX_BODY", 4)
    response = fetch.UrllibFetcher("ua/1", FakeOpener(FakeReply(b"0123456789")))(
        "https://x.test/", 1.0
    )
    assert (response.body, response.error) == (b"0123", "body_too_large")


def test_opener_refuses_redirects_and_keeps_no_cookies() -> None:
    opener = fetch.build_opener()
    # OpenerDirector keeps its handlers in an attribute typeshed does not declare.
    kinds = [type(handler) for handler in vars(opener)["handlers"]]
    assert fetch._NoRedirect in kinds
    assert urllib.request.HTTPRedirectHandler not in kinds
    assert urllib.request.HTTPCookieProcessor not in kinds
    request = urllib.request.Request("https://prices.azure.com/")
    refused = fetch._NoRedirect().redirect_request(
        request, None, 302, "Found", {}, "https://evil.test/"
    )
    assert refused is None


# --- Retry-After ---


@pytest.mark.parametrize(
    ("value", "seconds"),
    [
        ("7", 7.0),
        (" 12 ", 12.0),
        ((START + timedelta(seconds=30)).strftime("%a, %d %b %Y %H:%M:%S GMT"), 30.0),
        ((START - timedelta(seconds=30)).strftime("%a, %d %b %Y %H:%M:%S GMT"), 0.0),
        ("soon", None),
        ("Mon, 12 Oct 2026 09:00:30 -0000", None),  # no zone: not trusted
        (None, None),
    ],
)
def test_retry_after_values(value: str | None, seconds: float | None) -> None:
    assert fetch.retry_after(value, START) == seconds


# --- the fetch loop ---


def sidecars(result: fetch.RunResult) -> list[dict[str, Any]]:
    paths = sorted(result.folder.glob(f"{result.run_id}-*.meta.json"))
    return [json.loads(path.read_text(encoding="ascii")) for path in paths]


def starts(calls: list[tuple[str, float]]) -> list[float]:
    return [moment for _, moment in calls]


def gaps(calls: list[tuple[str, float]]) -> list[float]:
    times = starts(calls)
    return [later - earlier for earlier, later in zip(times, times[1:], strict=False)]


def test_three_pages_are_paced_and_kept(tmp_path: Path) -> None:
    responses = [
        ok(page_bytes([item()], next_link(1000))),
        ok(page_bytes([item()], next_link(2000))),
        ok(page_bytes([item()])),
    ]
    result, fetcher, _ = collect(tmp_path, responses)
    assert (result.stop_reason, result.requests, result.pages_parsed) == (
        "completed",
        3,
        3,
    )
    assert [url for url, _ in fetcher.calls] == [
        az.first_page_url(),
        next_link(1000),
        next_link(2000),
    ]
    assert all(gap >= 1.0 for gap in gaps(fetcher.calls))
    kept = sidecars(result)
    assert [(s["seq"], s["page"], s["attempt"]) for s in kept] == [
        (0, 0, 1),
        (1, 1, 1),
        (2, 2, 1),
    ]
    assert all(s["data_label"] == "synthetic" for s in kept)
    end = json.loads((result.folder / f"{result.run_id}.end.json").read_text("ascii"))
    assert end["stop_reason"] == "completed"
    manifest = json.loads(
        (result.folder / f"{result.run_id}.run.json").read_text("ascii")
    )
    assert manifest["request_params"]["first_url"] == az.first_page_url()


def test_throttled_request_waits_for_retry_after(tmp_path: Path) -> None:
    responses = [
        status(429, "Too Many Requests", ("Retry-After", "7")),
        ok(page_bytes([item()], next_link(1000))),
        ok(page_bytes([item()])),
    ]
    result, fetcher, clock = collect(tmp_path, responses)
    assert result.stop_reason == "completed"
    assert 7.0 in clock.sleeps
    assert gaps(fetcher.calls)[1] >= 2.0  # slower pacing after a 429
    assert [(s["page"], s["attempt"], s["http_status"]) for s in sidecars(result)] == [
        (0, 1, 429),
        (0, 2, 200),
        (1, 1, 200),
    ]


def test_throttled_request_without_retry_after_waits_a_minute(tmp_path: Path) -> None:
    result, _, clock = collect(tmp_path, [status(429), ok(page_bytes([item()]))])
    assert result.stop_reason == "completed"
    assert clock.sleeps == [60.0]


def test_azure_retry_header_honoured_after_a_429(tmp_path: Path) -> None:
    azure = ("x-ms-ratelimit-retailprices-retry-after", "45")
    responses = [status(429, "", azure), ok(page_bytes([item()]))]
    _, _, clock = collect(tmp_path, responses)
    assert clock.sleeps == [45.0]


def test_azure_retry_header_ignored_after_a_server_error(tmp_path: Path) -> None:
    azure = ("x-ms-ratelimit-retailprices-retry-after", "60")
    responses = [status(503, "", azure), ok(page_bytes([item()]))]
    _, _, clock = collect(tmp_path, responses)
    assert clock.sleeps == [2.0]


def test_retry_after_is_capped(tmp_path: Path) -> None:
    responses = [status(429, "", ("Retry-After", "3600")), ok(page_bytes([item()]))]
    _, _, clock = collect(tmp_path, responses)
    assert clock.sleeps == [300.0]


def test_retries_exhausted_after_five_attempts(tmp_path: Path) -> None:
    result, fetcher, clock = collect(tmp_path, [status(503)] * 5)
    assert (result.stop_reason, result.requests, result.pages_parsed) == (
        "retries_exhausted",
        5,
        0,
    )
    assert clock.sleeps == [2.0, 4.0, 8.0, 16.0]
    assert len(sidecars(result)) == 5


@pytest.mark.parametrize("code", [400, 404, 302, 204])
def test_other_statuses_stop_without_retry(tmp_path: Path, code: int) -> None:
    result, fetcher, _ = collect(tmp_path, [status(code)])
    assert (result.stop_reason, len(fetcher.calls)) == (f"http_{code}", 1)


@pytest.mark.parametrize(
    "first",
    [timed_out(), ok(b"<html>not json</html>"), ok(b'{"Items": "none"}'), status(500)],
)
def test_transient_failures_are_retried(tmp_path: Path, first: fetch.Response) -> None:
    result, _, clock = collect(tmp_path, [first, ok(page_bytes([item()]))])
    assert (result.stop_reason, result.requests, result.pages_parsed) == (
        "completed",
        2,
        1,
    )
    assert clock.sleeps == [2.0]


def test_oversized_body_stops_the_run(tmp_path: Path) -> None:
    oversized = fetch.Response(200, "OK", [], b"{", "body_too_large")
    result, _, _ = collect(tmp_path, [oversized])
    assert result.stop_reason == "body_too_large"


def test_page_cap(tmp_path: Path) -> None:
    responses = [ok(page_bytes([item()], next_link(1000 * n))) for n in range(1, 4)]
    result, fetcher, _ = collect(tmp_path, responses, fetch.Limits(max_pages=3))
    assert (result.stop_reason, len(fetcher.calls)) == ("page_cap", 3)


def test_time_cap(tmp_path: Path) -> None:
    result, fetcher, _ = collect(
        tmp_path, [status(503)] * 5, fetch.Limits(max_seconds=10.0)
    )
    assert result.stop_reason == "time_cap"
    assert len(fetcher.calls) == 3  # waits of 2 and 4 fit, 8 more would not


def test_time_cap_reached_while_pacing(tmp_path: Path) -> None:
    responses = [ok(page_bytes([item()], next_link(1000)))]
    result, fetcher, _ = collect(tmp_path, responses, fetch.Limits(max_seconds=1.0))
    assert (result.stop_reason, len(fetcher.calls)) == ("time_cap", 1)


def test_suspicious_empty_page_is_fetched_again(tmp_path: Path) -> None:
    full = [item() for _ in range(az.PAGE_SIZE)]
    responses = [
        ok(page_bytes(full, next_link(1000))),
        ok(page_bytes([])),
        ok(page_bytes([item()])),
    ]
    result, fetcher, clock = collect(tmp_path, responses)
    assert result.stop_reason == "completed"
    assert 60.0 in clock.sleeps
    assert [url for url, _ in fetcher.calls][1:] == [next_link(1000), next_link(1000)]
    assert [(s["page"], s["attempt"]) for s in sidecars(result)] == [
        (0, 1),
        (1, 1),
        (1, 2),
    ]


def test_empty_last_page_after_a_short_page_is_accepted(tmp_path: Path) -> None:
    responses = [ok(page_bytes([item()], next_link(1000))), ok(page_bytes([]))]
    result, _, clock = collect(tmp_path, responses)
    assert result.stop_reason == "completed"
    assert 60.0 not in clock.sleeps


@pytest.mark.parametrize(
    "link",
    [
        "https://evil.test/api/retail/prices?$skip=1000",
        "http://prices.azure.com/api/retail/prices?$skip=1000",
        5,
    ],
)
def test_bad_next_link_is_never_requested(tmp_path: Path, link: object) -> None:
    body = json.dumps({"Items": [item()], "NextPageLink": link}).encode()
    result, fetcher, _ = collect(tmp_path, [ok(body)])
    assert result.stop_reason == "invalid_next_link"
    assert len(fetcher.calls) == 1


def test_repeated_next_link_stops_the_run(tmp_path: Path) -> None:
    responses = [
        ok(page_bytes([item()], next_link(1000))),
        ok(page_bytes([item()], next_link(1000))),
    ]
    result, fetcher, _ = collect(tmp_path, responses)
    assert (result.stop_reason, len(fetcher.calls)) == ("repeated_next_link", 2)


def test_interrupt_writes_the_end_manifest(tmp_path: Path) -> None:
    responses: list[fetch.Response | BaseException] = [
        ok(page_bytes([item()], next_link(1000))),
        KeyboardInterrupt(),
    ]
    result, _, _ = collect(tmp_path, responses)
    assert result.stop_reason == "interrupted"
    files = raw_store.read_run(tmp_path, az.SOURCE, result.run_id)
    assert files.end is not None and files.end["stop_reason"] == "interrupted"
    assert len(files.sidecars) == 1


def test_every_request_targets_the_api(tmp_path: Path) -> None:
    responses = [
        ok(page_bytes([item()], next_link(1000))),
        status(503),
        ok(page_bytes([item()])),
    ]
    _, fetcher, _ = collect(tmp_path, responses)
    for url, _ in fetcher.calls:
        assert az.next_link_problem(url) is None
        assert az.missing_params(url) == []


def test_fake_clock_starts_at_the_fixture_time() -> None:
    assert FakeClock().now() == START
