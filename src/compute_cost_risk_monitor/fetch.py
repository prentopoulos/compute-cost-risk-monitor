"""Read-only HTTP fetch and the paced fetch loop for the Azure Retail Prices API.

The loop keeps every attempt's bytes on disk (raw_store) before parsing them, and parses
only to find the next page. It writes no database rows: ingest does that from the files.
The fetcher, clock and sleep are injected so tests never touch the network.
"""

from __future__ import annotations

import http.client
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Protocol

from compute_cost_risk_monitor import azure_retail as az
from compute_cost_risk_monitor import raw_store

MAX_BODY = 64 * 1024 * 1024


@dataclass(frozen=True)
class Response:
    status: int | None
    reason: str
    headers: list[tuple[str, str]]
    body: bytes
    error: str | None


class Fetcher(Protocol):
    def __call__(self, url: str, timeout: float) -> Response: ...


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse redirects: urllib then raises HTTPError for the 3xx response."""

    def redirect_request(
        self, *args: Any, **kwargs: Any
    ) -> urllib.request.Request | None:
        return None


def build_opener() -> urllib.request.OpenerDirector:
    """urllib's default handlers with redirects refused and no cookie handling."""
    return urllib.request.build_opener(_NoRedirect())


class UrllibFetcher:
    """GET with the standard library. http.client sends `Accept-Encoding: identity`,
    so the body read is the exact entity the server sent."""

    def __init__(
        self, user_agent: str, opener: urllib.request.OpenerDirector | None = None
    ) -> None:
        self.user_agent = user_agent
        self.opener = opener or build_opener()

    def __call__(self, url: str, timeout: float) -> Response:
        request = urllib.request.Request(  # noqa: S310 (callers pass checked https URLs)
            url, method="GET", headers={"User-Agent": self.user_agent}
        )
        try:
            with self.opener.open(request, timeout=timeout) as reply:
                body = reply.read(MAX_BODY + 1)
                status, reason = reply.status, reply.reason
                headers = list(reply.headers.items())
        except urllib.error.HTTPError as error:
            body = error.read(MAX_BODY + 1) if error.fp is not None else b""
            status, reason = error.code, str(error.reason)
            headers = list(error.headers.items()) if error.headers else []
        except (OSError, http.client.HTTPException) as error:
            return Response(None, "", [], b"", f"{type(error).__name__}: {error}")
        if len(body) > MAX_BODY:
            return Response(status, reason, headers, body[:MAX_BODY], "body_too_large")
        return Response(status, reason, headers, body, None)


@dataclass(frozen=True)
class Limits:
    """Pacing and bounds (phase-2-collector design D17)."""

    min_interval: float = 1.0
    throttled_interval: float = 2.0
    timeout: float = 30.0
    attempts: int = 5
    retry_after_cap: float = 300.0
    throttle_wait: float = 60.0
    backoff: tuple[float, ...] = (2.0, 4.0, 8.0, 16.0)
    max_pages: int = 200
    max_seconds: float = 1800.0
    empty_page_wait: float = 60.0


@dataclass(frozen=True)
class Clock:
    now: Callable[[], datetime]  # aware UTC
    monotonic: Callable[[], float]
    sleep: Callable[[float], None]


@dataclass(frozen=True)
class RunResult:
    run_id: str
    folder: Path
    stop_reason: str
    detail: str
    requests: int
    pages_parsed: int


def header(headers: list[tuple[str, str]], name: str) -> str | None:
    for key, value in headers:
        if key.lower() == name:
            return value
    return None


def retry_after(value: str | None, now: datetime) -> float | None:
    """Seconds asked for by a Retry-After header (delta-seconds or HTTP date)."""
    if value is None:
        return None
    text = value.strip()
    if text.isdigit():
        return float(text)
    try:
        moment = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        return None
    return max(0.0, (moment - now).total_seconds())


def retry_wait(
    response: Response, attempt: int, limits: Limits, now: datetime
) -> float:
    asked = retry_after(header(response.headers, "retry-after"), now)
    if asked is not None:
        return min(asked, limits.retry_after_cap)
    if response.status == 429:
        return limits.throttle_wait
    return limits.backoff[min(attempt, len(limits.backoff)) - 1]


def judge(response: Response) -> tuple[str, az.Page | None]:
    """'ok' with a page, 'retry', or 'stop:<reason>'."""
    status = response.status
    if status is None:
        return "retry", None
    if response.error is not None:
        return f"stop:{response.error}", None
    if status == 200:
        page = az.parse_page(response.body)
        return ("ok", page) if page is not None else ("retry", None)
    if status == 429 or 500 <= status <= 599:
        return "retry", None
    return f"stop:http_{status}", None


class _Stop(Exception):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


class _Loop:
    def __init__(
        self,
        raw_root: Path,
        info: raw_store.RunInfo,
        fetcher: Fetcher,
        clock: Clock,
        limits: Limits,
        user_agent: str,
    ) -> None:
        self.raw_root = raw_root
        self.info = info
        self.fetcher = fetcher
        self.clock = clock
        self.limits = limits
        self.user_agent = user_agent
        self.deadline = clock.monotonic() + limits.max_seconds
        self.interval = limits.min_interval
        self.last_start: float | None = None
        self.seq = 0
        self.pages_parsed = 0
        self.page_requests: dict[int, int] = {}

    def _request(self, url: str, page: int, attempt: int) -> Response:
        if self.last_start is not None:
            wait = self.interval - (self.clock.monotonic() - self.last_start)
            if wait > 0:
                self.clock.sleep(wait)
        if self.clock.monotonic() >= self.deadline:
            raise _Stop("time_cap")
        self.last_start = self.clock.monotonic()
        requested_at = self.clock.now()
        response = self.fetcher(url, self.limits.timeout)
        received_at = self.clock.now() if response.status is not None else None
        elapsed = round((self.clock.monotonic() - self.last_start) * 1000)
        exchange = raw_store.Exchange(
            url=url,
            requested_at=requested_at,
            received_at=received_at,
            elapsed_ms=elapsed,
            status=response.status,
            reason=response.reason,
            headers=response.headers,
            body=response.body,
            error=response.error,
        )
        # The bytes are on disk before anything reads them.
        raw_store.keep_exchange(
            self.raw_root, self.info, self.seq, page, attempt, exchange, self.user_agent
        )
        self.seq += 1
        return response

    def _wait(self, seconds: float) -> None:
        if self.clock.monotonic() + seconds >= self.deadline:
            raise _Stop("time_cap")
        self.clock.sleep(seconds)

    def fetch_page(self, url: str, page: int) -> az.Page:
        for tries in range(1, self.limits.attempts + 1):
            # Attempt numbers keep counting if a page is fetched again.
            attempt = self.page_requests.get(page, 0) + 1
            self.page_requests[page] = attempt
            response = self._request(url, page, attempt)
            verdict, parsed = judge(response)
            if verdict == "ok" and parsed is not None:
                self.pages_parsed += 1
                return parsed
            if verdict.startswith("stop:"):
                raise _Stop(verdict.removeprefix("stop:"), f"page {page}")
            if response.status == 429:
                self.interval = max(self.interval, self.limits.throttled_interval)
            if tries < self.limits.attempts:
                self._wait(retry_wait(response, tries, self.limits, self.clock.now()))
        raise _Stop("retries_exhausted", f"page {page}")

    def run(self) -> tuple[str, str]:
        url = az.first_page_url()
        seen = {url}
        previous_count: int | None = None
        for page in range(self.limits.max_pages):
            result = self.fetch_page(url, page)
            link = result.next_link
            empty_end = not result.items and not link
            if empty_end and previous_count == az.PAGE_SIZE:
                # Throttling once looked like an empty last page; ask once more.
                self._wait(self.limits.empty_page_wait)
                result = self.fetch_page(url, page)
                link = result.next_link
            previous_count = len(result.items)
            if link is None or link == "":
                return "completed", f"{page + 1} pages"
            if not isinstance(link, str):
                raise _Stop("invalid_next_link", f"page {page}: not text")
            problem = az.next_link_problem(link)
            if problem is not None:
                raise _Stop("invalid_next_link", f"page {page}: {problem}")
            if link in seen:
                raise _Stop("repeated_next_link", f"page {page}")
            seen.add(link)
            url = link
        raise _Stop("page_cap", f"{self.limits.max_pages} pages")


def fetch_run(
    raw_root: Path,
    fetcher: Fetcher,
    clock: Clock,
    *,
    data_label: str,
    code_version: str | None,
    dependency_versions: dict[str, str],
    user_agent: str,
    limits: Limits | None = None,
    run_id: str | None = None,
) -> RunResult:
    """Fetch one run into raw files. Always ends with an end manifest unless killed."""
    limits = limits or Limits()
    started_at = clock.now()
    run_id = raw_store.check_run_id(run_id or raw_store.new_run_id(started_at))
    info = raw_store.RunInfo(
        source=az.SOURCE,
        run_id=run_id,
        data_label=data_label,
        started_at=started_at,
        code_version=code_version,
        folder=raw_store.run_folder(raw_root, az.SOURCE, started_at),
    )
    request_params = {
        "first_url": az.first_page_url(),
        "params": dict(az.PARAMS),
        "user_agent": user_agent,
        "limits": asdict(limits),
    }
    raw_store.write_run_manifest(info, dependency_versions, request_params)
    loop = _Loop(raw_root, info, fetcher, clock, limits, user_agent)
    try:
        reason, detail = loop.run()
    except _Stop as stop:
        reason, detail = stop.reason, stop.detail
    except KeyboardInterrupt:
        reason, detail = "interrupted", "Ctrl-C"
    raw_store.write_end_manifest(info, clock.now(), reason, detail)
    return RunResult(run_id, info.folder, reason, detail, loop.seq, loop.pages_parsed)
