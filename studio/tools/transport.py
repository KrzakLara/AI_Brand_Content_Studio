"""HTTP transports. All network access in Phase 2 goes through a ``Transport``.

``UrllibTransport`` is the only code that opens sockets. Tests inject ``RecordedTransport``
(and the test suite also blocks sockets, so an accidental real call fails loudly).
"""
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class TransportError(Exception):
    """Network-level failure (DNS, timeout, reset). Retryable."""


class ResponseTooLarge(Exception):
    pass


class RequestLimitReached(Exception):
    """A GuardedTransport refused a request because the hard cap for that host was already used up."""


class UnrecordedRequest(AssertionError):
    """A RecordedTransport was asked for something that was not recorded."""


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str  # final URL after redirects

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", "").split(";")[0].strip().lower()


class Transport(Protocol):
    def request(self, method: str, url: str, *, headers: dict | None = None, body: bytes | None = None,
                timeout: float = 20.0, max_bytes: int = 4_000_000) -> Response: ...


class UrllibTransport:
    """Real network access (stdlib only)."""

    def request(self, method, url, *, headers=None, body=None, timeout=20.0, max_bytes=4_000_000):
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"refusing non-http(s) URL: {url!r}")
        req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return self._read(r, r.status, url=r.geturl(), max_bytes=max_bytes)
        except urllib.error.HTTPError as e:  # 4xx/5xx are responses, not exceptions
            return self._read(e, e.code, url=url, max_bytes=max_bytes)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise TransportError(f"{type(e).__name__}: {e}") from e

    @staticmethod
    def _read(r, status, *, url, max_bytes) -> Response:
        data = r.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ResponseTooLarge(f"response exceeds {max_bytes} bytes")
        return Response(status, {k.lower(): v for k, v in r.headers.items()}, data, url)


class GuardedTransport:
    """Final authority on how many requests may reach a paid host, independent of any adapter logic.

    Every request to ``hosts`` is counted and the count is written to ``log_path`` BEFORE it is forwarded
    (so a crash cannot hide a request). Once ``limit`` requests have been counted, further requests are
    refused without being sent. The log holds method + host + path only: no headers, no query, no key.
    Requests to other hosts pass through untouched.
    """

    def __init__(self, inner: Transport, *, limit: int, hosts: tuple[str, ...], log_path: Path | None = None):
        if limit < 0:
            raise ValueError("limit must be >= 0")
        self.inner, self.limit, self.hosts, self.log_path = inner, limit, tuple(hosts), log_path
        self.count = 0
        if log_path and Path(log_path).is_file():
            self.count = sum(1 for line in Path(log_path).read_text(encoding="utf-8").splitlines() if line.strip())

    def request(self, method, url, *, headers=None, body=None, timeout=20.0, max_bytes=4_000_000):
        from urllib.parse import urlparse
        u = urlparse(url)
        if (u.hostname or "").lower() in self.hosts:
            if self.count >= self.limit:
                raise RequestLimitReached(f"hard request limit {self.limit} for {u.hostname} reached "
                                          f"({self.count} counted) - request NOT sent")
            self.count += 1
            if self.log_path:
                Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(f"{method} {u.hostname}{u.path}\n")
        return self.inner.request(method, url, headers=headers, body=body, timeout=timeout, max_bytes=max_bytes)


@dataclass
class RecordedTransport:
    """Replays recorded responses. Each (method, url) entry is a queue; the last one repeats.

    A response may instead be an exception name in ``raise`` ("TransportError") to
    replay a failure. Unknown requests raise ``UnrecordedRequest``.
    """

    entries: dict[tuple[str, str], list] = field(default_factory=dict)
    calls: list[tuple[str, str]] = field(default_factory=list)
    bodies: list[bytes | None] = field(default_factory=list)  # request bodies, for tests

    def add(self, url: str, *, status: int = 200, body: bytes | str = b"", content_type: str = "text/html",
            method: str = "GET", final_url: str | None = None, headers: dict | None = None,
            raises: str | None = None) -> "RecordedTransport":
        data = body.encode("utf-8") if isinstance(body, str) else body
        h = {"content-type": content_type, **(headers or {})}
        self.entries.setdefault((method, url), []).append(
            raises if raises else Response(status, h, data, final_url or url))
        return self

    @classmethod
    def from_file(cls, path: Path) -> "RecordedTransport":
        """JSON: {"responses": [{"url","method","status","content_type","body" | "body_file", ...}]}."""
        t, doc = cls(), json.loads(Path(path).read_text(encoding="utf-8"))
        for r in doc["responses"]:
            body = r.get("body", "")
            if "body_file" in r:
                body = (Path(path).parent / r["body_file"]).read_bytes()
            t.add(r["url"], status=r.get("status", 200), body=body,
                  content_type=r.get("content_type", "text/html"), method=r.get("method", "GET"),
                  headers=r.get("headers"), raises=r.get("raises"))
        return t

    def request(self, method, url, *, headers=None, body=None, timeout=20.0, max_bytes=4_000_000):
        self.calls.append((method, url))
        self.bodies.append(body)
        queue = self.entries.get((method, url))
        if not queue:
            raise UnrecordedRequest(f"no recorded response for {method} {url}")
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, str):
            raise {"TransportError": TransportError, "ResponseTooLarge": ResponseTooLarge}[item](item)
        if len(item.body) > max_bytes:
            raise ResponseTooLarge(f"response exceeds {max_bytes} bytes")
        return item
