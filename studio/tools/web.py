"""Polite, bounded HTTP fetching: allowlist, robots.txt, retries with backoff."""
import time
import urllib.robotparser
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlparse

from studio.config import ResearchConfig
from studio.tools.transport import ResponseTooLarge, Transport, TransportError

RETRY_STATUS = {429, 500, 502, 503, 504}


@dataclass
class FetchResult:
    ok: bool
    url: str
    status: int | None = None
    body: bytes = b""
    content_type: str = ""
    error: str | None = None
    kind: str = "ok"  # ok | blocked_host | blocked_robots | http_error | network_error | too_large
    attempts: int = 0


def host_allowed(url: str, allowed: list[str]) -> bool:
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    h = p.hostname.lower()
    return any(h == a or h.endswith("." + a) for a in (x.lower() for x in allowed))


class HttpClient:
    def __init__(self, transport: Transport, cfg: ResearchConfig,
                 sleep: Callable[[float], None] = time.sleep):
        self.transport, self.cfg, self._sleep = transport, cfg, sleep
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None | bool] = {}
        self.requests = 0  # network requests actually attempted (incl. retries, robots)

    def _headers(self) -> dict:
        return {"User-Agent": self.cfg.user_agent, "Accept": "*/*"}

    def _send(self, url: str) -> FetchResult:
        last = FetchResult(False, url, error="not attempted", kind="network_error")
        for attempt in range(1, self.cfg.retries + 2):
            self.requests += 1
            try:
                r = self.transport.request("GET", url, headers=self._headers(),
                                           timeout=self.cfg.timeout_s, max_bytes=self.cfg.max_bytes)
            except TransportError as e:
                last = FetchResult(False, url, error=str(e), kind="network_error", attempts=attempt)
            except ResponseTooLarge as e:
                return FetchResult(False, url, error=str(e), kind="too_large", attempts=attempt)
            else:
                if not host_allowed(r.url, self.cfg.allowed_hosts):
                    return FetchResult(False, url, status=r.status, kind="blocked_host", attempts=attempt,
                                       error=f"redirected outside allowlist to {r.url}")
                if r.status < 400:
                    return FetchResult(True, r.url, r.status, r.body, r.content_type, attempts=attempt)
                last = FetchResult(False, url, r.status, kind="http_error", attempts=attempt,
                                   error=f"HTTP {r.status}")
                if r.status not in RETRY_STATUS:
                    return last
            if attempt <= self.cfg.retries:
                self._sleep(min(self.cfg.backoff_s * 2 ** (attempt - 1), 10.0))
        return last

    def _robots_for(self, url: str):
        p = urlparse(url)
        origin = f"{p.scheme}://{p.netloc}"
        if origin not in self._robots:
            r = self._send(origin + "/robots.txt")
            if r.ok:
                rp = urllib.robotparser.RobotFileParser()
                rp.parse(r.body.decode("utf-8", "replace").splitlines())
                self._robots[origin] = rp
            elif r.status is not None and 400 <= r.status < 500:
                self._robots[origin] = True  # no robots.txt: everything allowed (RFC 9309)
            else:
                self._robots[origin] = False  # robots unreachable: be conservative, allow nothing
        return self._robots[origin]

    def get(self, url: str) -> FetchResult:
        if not host_allowed(url, self.cfg.allowed_hosts):
            return FetchResult(False, url, kind="blocked_host", error="host not in research allowlist")
        if self.cfg.respect_robots:
            rob = self._robots_for(url)
            allowed = rob is True or (rob is not False and rob.can_fetch(self.cfg.user_agent, url))
            if not allowed:
                return FetchResult(False, url, kind="blocked_robots",
                                   error="disallowed by robots.txt (or robots.txt unreachable)")
        return self._send(url)
