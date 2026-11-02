"""fal.ai Kling 4.0 image-to-video adapter with a hard spend guard and no automatic retries.

Price per generated second (operator-supplied from fal.ai pricing, 2026-10-29): 720p 0.157 USD, 1080p 0.235 USD. The API pricing
endpoint lists only 0.157 (no resolution), so the higher 1080p figure is the one used for the guard.
The worst case of a request is duration * price, checked against the budget BEFORE the submit. The submit is the only paid call;
status polling and result download are free and are not retried as new generations. The key is never logged.
"""
import base64
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from studio.cost import BudgetExceeded
from studio.providers.base import ProviderInfo, ProviderResponseError, ProviderUnavailable
from studio.contracts import ProviderKind
from studio.tools.transport import Transport

ENDPOINT = "fal-ai/kling-video/v4/image-to-video"
QUEUE = "https://queue.fal.run/"
USD_PER_SECOND = {"720p": 0.157, "1080p": 0.235}


class VideoRequestLimitExceeded(BudgetExceeded):
    pass


@dataclass
class FalKlingVideo:
    transport: Transport
    api_key: str | None = field(default_factory=lambda: os.environ.get("FAL_KEY") or None)
    budget_usd: float = 2.0
    max_requests: int = 1
    usd_per_second: dict = field(default_factory=lambda: dict(USD_PER_SECOND))
    usage_path: Path | None = None
    poll_interval_s: float = 5.0
    max_wait_s: float = 600.0

    def __post_init__(self):
        self.info = ProviderInfo("fal-kling-video", ProviderKind.VIDEO, ENDPOINT, is_mock=False, safe_to_retry=False,
                                 config={"budget_usd": self.budget_usd, "max_requests": self.max_requests})
        self.api_requests, self.spent_usd = 0, 0.0
        if self.usage_path and Path(self.usage_path).is_file():
            for line in Path(self.usage_path).read_text(encoding="utf-8").splitlines():
                rec = json.loads(line)
                self.api_requests += int(rec.get("requests", 0))
                self.spent_usd = round(self.spent_usd + float(rec.get("cost_usd") or 0), 6)

    def _log(self, rec: dict) -> None:
        if self.usage_path:
            Path(self.usage_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.usage_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, sort_keys=True) + "\n")

    def estimate_usd(self, duration_s: int, resolution: str = "1080p") -> float:
        return round(duration_s * self.usd_per_second[resolution], 6)

    def check_budget(self, duration_s: int, resolution: str = "1080p") -> float:
        worst = self.estimate_usd(duration_s, resolution)
        if self.api_requests >= self.max_requests:
            raise VideoRequestLimitExceeded(f"video request limit {self.max_requests} reached - request NOT sent")
        if self.spent_usd + worst > self.budget_usd:
            raise BudgetExceeded(f"video would cost {worst:.3f} USD; spent {self.spent_usd:.3f} of {self.budget_usd:.2f} - NOT sent")
        return worst

    def _h(self) -> dict:
        return {"authorization": f"Key {self.api_key}", "content-type": "application/json"}

    @staticmethod
    def _data_uri(image: bytes) -> str:
        """Inputs go up as JPEG (q93) data URIs: a 1080x1920 PNG would make the request body needlessly large."""
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.open(io.BytesIO(image)).convert("RGB").save(buf, "JPEG", quality=93)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

    def generate_from_image(self, *, image: bytes, prompt: str, duration_s: int = 5, resolution: str = "1080p", end_image: bytes | None = None) -> dict:
        """ONE generation attempt (optional end frame). Returns {"mp4": bytes, "cost_usd", "request_id"}. Never resubmits."""
        if not self.api_key:
            raise ProviderUnavailable("FAL_KEY is not set; the video adapter cannot run")
        worst = self.check_budget(duration_s, resolution)
        body = {"prompt": prompt, "duration": duration_s, "resolution": resolution,
                "start_image_url": self._data_uri(image)}
        if end_image is not None:
            body["end_image_url"] = self._data_uri(end_image)
        self.api_requests += 1
        self._log({"kind": "video_submit", "requests": 1, "model": ENDPOINT, "duration_s": duration_s,
                   "resolution": resolution, "worst_usd": worst})  # BEFORE sending
        r = self.transport.request("POST", QUEUE + ENDPOINT, headers=self._h(), body=json.dumps(body).encode(), timeout=120.0)
        if r.status not in (200, 201):
            raise ProviderResponseError(f"fal submit failed: HTTP {r.status} {r.body[:200].decode(errors='replace')}")
        sub = json.loads(r.body)
        rid, status_url, result_url = sub["request_id"], sub["status_url"], sub["response_url"]
        self._log({"kind": "video_accepted", "requests": 0, "request_id": rid})
        deadline = time.monotonic() + self.max_wait_s
        while True:
            s = self.transport.request("GET", status_url, headers=self._h(), timeout=60.0)
            st = json.loads(s.body).get("status") if s.status in (200, 202) else None
            if st == "COMPLETED":
                break
            if time.monotonic() > deadline:
                raise ProviderResponseError(f"fal request {rid} not finished after {self.max_wait_s}s; NOT resubmitted")
            time.sleep(self.poll_interval_s)
        res = json.loads(self.transport.request("GET", result_url, headers=self._h(), timeout=60.0).body)
        mp4 = self.transport.request("GET", res["video"]["url"], timeout=300.0, max_bytes=200_000_000).body
        self.spent_usd = round(self.spent_usd + worst, 6)
        self._log({"kind": "usage", "requests": 0, "model": ENDPOINT, "cost_usd": worst, "request_id": rid})
        return {"mp4": mp4, "cost_usd": worst, "request_id": rid}
