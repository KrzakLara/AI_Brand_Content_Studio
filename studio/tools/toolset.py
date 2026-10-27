"""The research agent's tools: web_fetch, instagram_fetch, download_image.

Every call stores its raw payload under ``<run>/research/raw`` and returns a small JSON
result containing a ``SourceItem`` (even for failures: a failed or blocked source is
recorded with the reason, never silently dropped).
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from studio.config import ResearchConfig
from studio.contracts import ProviderKind, SourceItem
from studio.fingerprint import canonical, sha256_bytes
from studio.providers.base import ProviderInfo
from studio.tools import extract
from studio.tools.instagram import (
    InstagramMalformed,
    InstagramProvider,
    InstagramUnavailable,
)
from studio.tools.web import HttpClient, host_allowed

IMAGE_MAGIC = {b"\x89PNG\r\n\x1a\n": "png", b"\xff\xd8\xff": "jpg", b"GIF8": "gif", b"RIFF": "webp"}
LICENSE_NOTE = ("Third-party / brand-owned media. Stored locally for analysis only; not redistributed "
                "or exported with deliverables.")


def source_id(url: str) -> str:
    return "S-" + hashlib.sha256(url.encode()).hexdigest()[:10]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResearchToolset:
    tool_names = ("web_fetch", "instagram_fetch", "download_image")

    def __init__(self, run_dir: Path, http: HttpClient, cfg: ResearchConfig, *,
                 origin: str, instagram: InstagramProvider | None = None,
                 clock=now):
        if origin not in ("live", "fixture"):
            raise ValueError("origin must be 'live' or 'fixture'")
        self.run_dir, self.http, self.cfg, self.origin = run_dir, http, cfg, origin
        self.instagram, self._now = instagram, clock
        self.raw_dir = run_dir / "research" / "raw"
        self.info = ProviderInfo("research-tools", ProviderKind.RESEARCH, "web_fetch+download_image",
                                 is_mock=False, safe_to_retry=True, config={"origin": origin})
        self.calls: list[dict] = []

    def info_for(self, tool: str) -> ProviderInfo:
        if tool == "instagram_fetch" and self.instagram is not None:
            kind = ProviderKind.INSTAGRAM if self.instagram.paid else ProviderKind.RESEARCH  # manual import is free
            return ProviderInfo(self.instagram.name, kind, "instagram_fetch",
                                is_mock=False, safe_to_retry=not self.instagram.paid,
                                config={"origin": self.instagram.origin,
                                        "hint": getattr(self.instagram, "fingerprint_hint", lambda: "")()})
        return self.info

    def units(self, tool: str, args: dict) -> float:
        return float(args.get("limit", self.cfg.instagram_limit)) if tool == "instagram_fetch" else 1.0

    # -- storage ------------------------------------------------------------
    def _store(self, data: bytes, ext: str) -> tuple[str, str]:
        sha = sha256_bytes(data)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        path = self.raw_dir / f"{sha[:16]}.{ext}"
        path.write_bytes(data)
        return path.relative_to(self.run_dir).as_posix(), sha

    def artifact_ok(self, result: dict) -> bool:
        """Ledger reuse is valid only if every referenced raw file still matches its hash."""
        for s in result.get("sources", []):
            if s.get("artifact_path"):
                p = self.run_dir / s["artifact_path"]
                if not p.is_file() or sha256_bytes(p.read_bytes()) != s["artifact_sha256"]:
                    return False
        return True

    # -- dispatch -----------------------------------------------------------
    def call(self, tool: str, args: dict) -> dict:
        self.calls.append({"tool": tool, "args": args})
        if tool == "web_fetch":
            return self._web_fetch(str(args["url"]), kind=args.get("kind"))
        if tool == "download_image":
            return self._download_image(str(args["url"]), referrer=args.get("page_url"), role=args.get("role"))
        if tool == "instagram_fetch":
            return self._instagram(str(args["handle"]), int(args.get("limit", self.cfg.instagram_limit)))
        raise ValueError(f"unknown tool {tool!r}")

    # -- tools --------------------------------------------------------------
    def _failed(self, url: str, kind: str, status: str, why: str, tool: str) -> dict:
        src = SourceItem(source_id=source_id(url), url=url, title="", kind=kind, origin=self.origin,
                         retrieval_status=status, retrieved_at=self._now(), access_limitations=why)
        return {"ok": False, "tool": tool, "sources": [src.dump()], "error": why}

    def _web_fetch(self, url: str, kind: str | None) -> dict:
        r = self.http.get(url)
        if not r.ok:
            status = {"blocked_host": "blocked", "blocked_robots": "blocked"}.get(r.kind, "failed")
            return self._failed(url, kind or "web_page", status, f"{r.kind}: {r.error}", "web_fetch")
        ctype = r.content_type
        is_css = ctype == "text/css" or url.split("?")[0].endswith(".css")
        ext = "css" if is_css else ("json" if "json" in ctype else "html")
        path, sha = self._store(r.body, ext)
        text = r.body.decode("utf-8", "replace")
        flags, links, sheets, images, title, nprod, plist = [], [], [], [], "", 0, []
        if is_css:
            stype = "css"
        else:
            page = extract.parse_html(text, r.url)
            title, stype = page.title, kind or "web_page"
            if extract.looks_like_injection(page.text):
                flags.append("possible_prompt_injection")  # data only; never forwarded as instructions
            links = list(dict.fromkeys(l.split("#")[0] for l in page.links
                                       if host_allowed(l, self.cfg.allowed_hosts)))[:300]
            sheets = [s for s in page.stylesheets if host_allowed(s, self.cfg.allowed_hosts)][:6]
            products = extract.jsonld_products(page.jsonld)
            nprod = len(products)
            plist = [u for u in extract.item_list_urls(page.jsonld) if host_allowed(u, self.cfg.allowed_hosts)][:60]
            images = list(dict.fromkeys(i for p in products for i in p["images"]
                                        if host_allowed(i, self.cfg.allowed_hosts)))[:12]
            if page.meta.get("og:image") and host_allowed(page.meta["og:image"], self.cfg.allowed_hosts):
                images.append(page.meta["og:image"])
        src = SourceItem(source_id=source_id(url), url=url, title=extract.sanitize(title, 160), kind=stype,
                         content_sha256=sha, origin=self.origin, retrieval_status="ok",
                         retrieved_at=self._now(), artifact_path=path, artifact_sha256=sha, flags=flags,
                         provenance={"http_status": r.status, "content_type": ctype, "final_url": r.url,
                                     "bytes": len(r.body), "attempts": r.attempts})
        return {"ok": True, "tool": "web_fetch", "sources": [src.dump()], "links": links,
                "stylesheets": sheets, "images": images, "product_count": nprod,
                "product_urls": plist}

    def _download_image(self, url: str, referrer: str | None, role: str | None = None) -> dict:
        r = self.http.get(url)
        if not r.ok:
            status = "blocked" if r.kind.startswith("blocked") else "failed"
            return self._failed(url, "image", status, f"{r.kind}: {r.error}", "download_image")
        ext = next((e for magic, e in IMAGE_MAGIC.items() if r.body.startswith(magic)), None)
        if ext is None or not r.content_type.startswith("image/"):
            return self._failed(url, "image", "failed",
                                f"not an image (content-type {r.content_type!r}, magic mismatch)", "download_image")
        path, sha = self._store(r.body, ext)
        src = SourceItem(source_id=source_id(url), url=url, title=Path(urlparse(url).path).name, kind="image",
                         content_sha256=sha, origin=self.origin, retrieved_at=self._now(), artifact_path=path,
                         artifact_sha256=sha, access_limitations=LICENSE_NOTE,
                         provenance={"referrer_page": referrer, "content_type": r.content_type,
                                     "bytes": len(r.body), "license_note": LICENSE_NOTE, "role": role,
                                     "last_modified": (r.headers or {}).get("last-modified"),
                                     "etag": (r.headers or {}).get("etag")})
        return {"ok": True, "tool": "download_image", "sources": [src.dump()]}

    def _instagram(self, handle: str, limit: int) -> dict:
        profile_url = f"https://www.instagram.com/{handle.lstrip('@')}/"
        if self.instagram is None:
            return self._failed(profile_url, "instagram_profile", "not_collected",
                                "no Instagram collector configured", "instagram_fetch")
        try:
            res = self.instagram.fetch(handle, limit)
        except (InstagramUnavailable, InstagramMalformed) as e:
            return self._failed(profile_url, "instagram_profile", "failed", f"{type(e).__name__}: {e}",
                                "instagram_fetch")
        doc = {"handle": handle, "provenance": res.provenance, "origin": res.origin, "posts": res.posts,
               "excluded_non_owner_posts": res.excluded_non_owner}
        path, sha = self._store(json.dumps(doc, sort_keys=True, ensure_ascii=False, indent=1).encode(), "json")
        profile = SourceItem(
            source_id=source_id(profile_url), url=profile_url, title=f"@{handle} (collected posts)",
            kind="instagram_profile", content_sha256=sha, origin=res.origin, retrieved_at=self._now(),
            artifact_path=path, artifact_sha256=sha, provenance=res.provenance,
            access_limitations=("instagram.com HTML is not scraped (login wall / access control); posts come from "
                                f"{res.origin} collection, basic data only, metrics are a snapshot"))
        sources = [profile.dump()]
        for p in res.posts:
            sources.append(SourceItem(
                source_id=source_id(p["url"]), url=p["url"], title=f"@{p['owner']} {p['type']} {p['shortcode']}",
                kind="instagram_post", content_sha256=sha256_bytes(canonical(p).encode()),
                origin=res.origin, retrieved_at=self._now(), artifact_path=path, artifact_sha256=sha,
                record_sha256=sha256_bytes(canonical(p).encode()),
                provenance={"posted_at": p["timestamp"], "collection": res.provenance.get("method", "")}).dump())
        return {"ok": True, "tool": "instagram_fetch", "sources": sources, "post_count": len(res.posts),
                "excluded_non_owner_posts": res.excluded_non_owner, "est_cost_usd": res.est_cost_usd}
