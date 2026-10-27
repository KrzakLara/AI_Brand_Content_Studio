"""Instagram collection adapters.

Instagram offers no open public API and its web pages sit behind a login wall, so the
studio never scrapes instagram.com itself (that would bypass access controls). Two
sanctioned routes exist:

* ``ApifyInstagram``  - a third-party collector the operator is entitled to use; needs APIFY_TOKEN.
* ``ManualImportInstagram`` - posts a human/operator collected elsewhere, with mandatory provenance.

Neither invents data: likes hidden by the platform (-1) become ``None``.
"""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import yaml

from studio.tools.transport import ResponseTooLarge, Transport, TransportError

APIFY_ACTOR = "apify~instagram-post-scraper"
REQUIRED_PROVENANCE = ("collected_by", "method", "collected_at", "source_description")
REQUIRED_POST = ("shortcode", "url", "type", "timestamp", "caption", "owner")


class InstagramUnavailable(Exception):
    """Collector cannot run (no credentials, no import file). Reported, never faked."""


class InstagramMalformed(Exception):
    """The collector returned data that does not match the expected shape."""


@dataclass
class InstagramResult:
    posts: list[dict]  # normalised, brand-owned only
    excluded_non_owner: int
    origin: str  # live | fixture | manual_import
    provenance: dict
    est_cost_usd: float = 0.0
    raw_note: str = ""


class InstagramProvider(Protocol):
    name: str
    paid: bool
    origin: str

    def fetch(self, handle: str, limit: int) -> InstagramResult: ...


def _post(d: dict) -> dict:
    missing = [k for k in REQUIRED_POST if k not in d]
    if missing:
        raise InstagramMalformed(f"post missing fields {missing}: {str(d)[:120]}")
    return {
        "shortcode": str(d["shortcode"]), "url": str(d["url"]), "type": str(d["type"]),
        "timestamp": str(d["timestamp"]), "caption": str(d.get("caption") or ""),
        "hashtags": [str(h) for h in d.get("hashtags") or []], "owner": str(d["owner"]).lower(),
        "likes": d.get("likes"), "comments": d.get("comments"),
    }


def _split(posts: list[dict], handle: str, limit: int) -> tuple[list[dict], int]:
    own = [p for p in posts if p["owner"] == handle.lower().lstrip("@")]
    return own[:limit], len(posts) - len(own)


@dataclass
class ManualImportInstagram:
    """Reads a YAML file with a ``provenance`` block and a ``posts`` list."""

    path: Path
    name: str = "instagram-manual-import"
    paid: bool = False
    origin: str = "manual_import"

    def fetch(self, handle: str, limit: int) -> InstagramResult:
        if not Path(self.path).is_file():
            raise InstagramUnavailable(f"manual import file not found: {self.path}")
        try:
            doc = yaml.safe_load(Path(self.path).read_text(encoding="utf-8"))
            prov, raw_posts = doc["provenance"], doc["posts"]
        except (yaml.YAMLError, KeyError, TypeError) as e:
            raise InstagramMalformed(f"unreadable import file: {e}") from e
        missing = [k for k in REQUIRED_PROVENANCE if not prov.get(k)]
        if missing:
            raise InstagramMalformed(f"import file lacks provenance fields {missing}")
        posts = [_post(p) for p in raw_posts]
        own, excluded = _split(posts, handle, limit)
        excluded += int(prov.get("non_owner_posts_seen_and_excluded", 0))  # declared by the operator
        return InstagramResult(own, excluded, self.origin, {**prov, "import_file": Path(self.path).name})

    def fingerprint_hint(self) -> str:
        """Content hash of the import file, so editing it invalidates cached research."""
        from studio.fingerprint import sha256_file
        return sha256_file(Path(self.path)) if Path(self.path).is_file() else "missing"


def normalize_apify_item(it: dict) -> dict:
    try:
        return _post({
            "shortcode": it["shortCode"], "url": it["url"], "type": it["type"], "timestamp": it["timestamp"],
            "caption": it.get("caption"), "hashtags": it.get("hashtags"), "owner": it["ownerUsername"],
            "likes": None if it.get("likesCount", -1) in (-1, None) else it["likesCount"],
            "comments": None if it.get("commentsCount", -1) in (-1, None) else it["commentsCount"],
        })
    except (KeyError, TypeError) as e:
        raise InstagramMalformed(f"unexpected Apify item shape: {e!r}") from e


@dataclass
class ApifyInstagram:
    transport: Transport
    token: str | None = field(default_factory=lambda: os.environ.get("APIFY_TOKEN") or None)
    origin: str = "live"
    price_per_post: float = 0.0017
    max_charge_usd: float = 0.10
    timeout_s: float = 120.0
    name: str = "apify-instagram-post-scraper"
    paid: bool = True

    def fetch(self, handle: str, limit: int) -> InstagramResult:
        if not self.token:
            raise InstagramUnavailable("APIFY_TOKEN is not set; Instagram collection is blocked "
                                       "(use a manual import instead)")
        # Over-request: collaboration posts on the profile are not brand-owned and get excluded.
        want = min(limit * 3, 60)
        url = (f"https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items"
               f"?maxTotalChargeUsd={self.max_charge_usd}")
        body = json.dumps({"username": [handle], "resultsLimit": want, "dataDetailLevel": "basicData"}).encode()
        try:
            r = self.transport.request("POST", url, body=body, timeout=self.timeout_s, headers={
                "Content-Type": "application/json", "Authorization": f"Bearer {self.token}"})
        except (TransportError, ResponseTooLarge) as e:
            raise InstagramUnavailable(f"Apify request failed: {e}") from e
        if r.status >= 400:
            raise InstagramUnavailable(f"Apify returned HTTP {r.status}")
        try:
            items = json.loads(r.body)
        except ValueError as e:
            raise InstagramMalformed("Apify response is not JSON") from e
        if not isinstance(items, list):
            raise InstagramMalformed("Apify response is not a list")
        posts = [normalize_apify_item(i) for i in items]
        own, excluded = _split(posts, handle, limit)
        return InstagramResult(
            own, excluded, self.origin,
            {"collected_by": "studio runtime", "method": f"Apify actor {APIFY_ACTOR}", "source_description":
             "run-sync-get-dataset-items", "requested_results": want},
            est_cost_usd=round(len(items) * self.price_per_post, 6))
