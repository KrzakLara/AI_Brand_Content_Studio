"""Deterministic mock providers. Nothing here touches the network.

Everything produced is explicitly labelled MOCK: strings start with "[MOCK]", structured
outputs carry ``mock=True``, PNGs have a yellow/black warning banner and a ``MOCK`` text
chunk, and the "video" is a JSON placeholder, not a playable video.
"""
import hashlib
import json
import struct
import zlib
from dataclasses import dataclass

from studio.config import Settings
from studio.contracts import (
    BrandProfile,
    ClaimRef,
    ContentPlan,
    CreativeSpec,
    PostFormat,
    ProviderKind,
    QADecision,
    QAVerdict,
    SlideSpec,
)
from studio.providers.base import (
    ProviderInfo,
    ResearchStep,
    ReviewIssue,
    ReviewResult,
    VisionResult,
)


class SimulatedCrash(BaseException):
    """Stands in for a killed process: not an Exception, so nothing handles it."""


def _h(*parts) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest(), 16)


def _info(name, kind, model_id, scoped_config=None, **config) -> ProviderInfo:
    return ProviderInfo(name=name, kind=kind, model_id=model_id, is_mock=True,
                        safe_to_retry=True, config=config, scoped_config=scoped_config or {})


# --------------------------------------------------------------------------- LLM
class MockLLM:
    def __init__(self, model_id: str, fail_rounds: dict[str, int] | None = None):
        self.fail_rounds = dict(fail_rounds or {})
        self.info = _info("mock-llm", ProviderKind.LLM, model_id, scoped_config={
            k: {"fail_rounds": v} for k, v in self.fail_rounds.items()})
        self.calls: list[dict] = []

    def structured(self, schema, *, task: str, payload: dict):
        self.calls.append({"task": task, "post_id": payload.get("post_id")})
        handler = getattr(self, f"_t_{task}")
        return schema.model_validate(handler(payload))

    # research ---------------------------------------------------------------
    def _t_research_policy(self, p):
        brief, hist = p["brief"], p["history"]
        n = len(hist)
        if n >= 4:
            return ResearchStep(action="finish", rationale="[MOCK] enough evidence").model_dump()
        if n % 2 == 0:
            q = f"{brief['brand_name']} {brief['product_name'] if n else ''}".strip()
            return ResearchStep(action="tool", tool="web_search", args={"query": q},
                                rationale="[MOCK] search").model_dump()
        url = hist[-1]["result"]["hits"][0]["url"]
        return ResearchStep(action="tool", tool="fetch_page", args={"url": url},
                            rationale="[MOCK] read top hit").model_dump()

    # analyst / planner ------------------------------------------------------
    def _t_brand_profile(self, p):
        b = p["brief"]
        seed = _h(b["brand_name"])
        palette = [f"#{(seed >> s) & 0xFFFFFF:06x}" for s in (0, 24, 48)]
        return BrandProfile(
            brand_name=b["brand_name"],
            positioning=f"[MOCK] {b['brand_name']} {b['product_name']}",
            voice=b["tone"], palette=palette,
            dos=["[MOCK] use the supplied facts only", "[MOCK] keep the CTA clear"],
            donts=["[MOCK] no medical claims"],
            banned_phrases=["guaranteed results", "miracle", "cure"],
            product_fact_ids=p["evidence_ids"],
            audience_summary=f"[MOCK] {b['audience']}",
            image_observations=p["vision_observations"], mock=True,
        ).model_dump()

    def _t_content_plan(self, p):
        b, ids = p["brief"], p["evidence_ids"]
        spec = [("01", PostFormat.CAROUSEL, "Explain the product in 5 swipes"),
                ("02", PostFormat.HERO, "One strong hero visual"),
                ("03", PostFormat.REEL, "Short motion teaser")]
        posts = []
        for i, (pid, fmt, what) in enumerate(spec):
            posts.append(dict(
                post_id=pid, format=fmt.value,
                objective=f"[MOCK] {what} for goal: {b['campaign_goal']}",
                hook=f"[MOCK] {b['product_name']} — idea {pid}",
                key_message=f"[MOCK] {b['brand_name']} for {b['audience']}",
                evidence_ids=[ids[i % len(ids)]], cta="Learn more"))
        return ContentPlan(posts=posts, mock=True).model_dump()

    # production -------------------------------------------------------------
    def _t_creative_spec(self, p):
        plan, fmt = p["post_plan"], p["post_plan"]["format"]
        note = ("; ".join(p["repair_instructions"])) if p["repair_instructions"] else ""
        body = f"{plan['key_message']}" + (f" (revision {p['attempt']}: {note})" if note else "")
        claims = [ClaimRef(text=p["evidence_claims"][e], evidence_id=e) for e in plan["evidence_ids"]]
        return CreativeSpec(
            post_id=plan["post_id"], format=fmt, headline=plan["hook"], body=body, cta=plan["cta"],
            visual_prompt=f"[MOCK] {plan['objective']} in palette {p['palette']}",
            slides=[SlideSpec(title=f"Slide {i + 1}", body=f"[MOCK] {plan['key_message']}")
                    for i in range(5)] if fmt == "carousel" else [],
            duration_s=12.0 if fmt == "reel" else None, claims=claims, mock=True,
        ).model_dump()

    # QA ---------------------------------------------------------------------
    def _review(self, p) -> dict:
        findings = []
        if p["primary"] and p["attempt"] < self.fail_rounds.get(p["post_id"], 0):
            findings.append(ReviewIssue(
                severity="major", category="injected_defect",
                message=f"[MOCK] injected defect for post {p['post_id']} (round {p['attempt']})"))
        return ReviewResult(findings=findings, mock=True).model_dump()

    _t_review_brand = _t_review_creative = _t_review_video = _review

    def _t_qa_judge(self, p):
        bad = [f for f in p["findings"] if f["severity"] in ("major", "blocker")]
        if not bad:
            return QADecision(post_id=p["post_id"], attempt=p["attempt"], verdict=QAVerdict.PASS,
                              rationale="[MOCK] no blocking findings").model_dump()
        return QADecision(
            post_id=p["post_id"], attempt=p["attempt"], verdict=QAVerdict.REPAIR,
            finding_ids=[f["finding_id"] for f in bad], repair_target=p["producer"],
            repair_instructions=[f["message"] for f in bad],
            rationale="[MOCK] blocking findings").model_dump()


# ------------------------------------------------------------------------ vision
class MockVision:
    def __init__(self, model_id: str):
        self.info = _info("mock-vision", ProviderKind.VISION, model_id)
        self.calls: list[dict] = []

    def describe(self, data: bytes, *, question: str, meta: dict) -> VisionResult:
        self.calls.append(meta)
        sha = hashlib.sha256(data).hexdigest()[:8]
        return VisionResult(description=f"[MOCK] vision of {len(data)} bytes (sha {sha})",
                            observations=[f"[MOCK] observation for {question!r}"], mock=True)


# ------------------------------------------------------------------------- image
def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))


def mock_png(width: int, height: int, rgb: tuple[int, int, int], label: str) -> bytes:
    """Solid-colour PNG with a yellow/black MOCK warning banner on top."""
    body = bytes(rgb) * width
    banner = b"".join(bytes((255, 214, 0) if (x // 40) % 2 == 0 else (0, 0, 0)) for x in range(width))
    rows = [b"\x00" + banner] * min(60, height) + [b"\x00" + body] * max(0, height - 60)
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + _chunk(b"tEXt", b"Comment\x00MOCK placeholder - not AI generated: " + label.encode())
            + _chunk(b"IDAT", zlib.compress(b"".join(rows), 6))
            + _chunk(b"IEND", b""))


class MockImage:
    def __init__(self, model_id: str):
        self.info = _info("mock-image", ProviderKind.IMAGE, model_id)
        self.calls: list[dict] = []

    def generate(self, *, prompt, width, height, seed, meta) -> bytes:
        self.calls.append(dict(meta))
        s = _h(prompt, seed)
        rgb = (60 + s % 150, 60 + (s >> 8) % 150, 60 + (s >> 16) % 150)
        return mock_png(width, height, rgb, prompt[:80])


# ------------------------------------------------------------------------- video
class MockVideo:
    def __init__(self, model_id: str, crash_post: str | None = None):
        self.info = _info("mock-video", ProviderKind.VIDEO, model_id)
        self.crash_post = crash_post
        self._crashed = False
        self.calls: list[dict] = []

    def generate(self, *, storyboard, duration_s, meta) -> bytes:
        self.calls.append(dict(meta))
        if self.crash_post and meta.get("post_id") == self.crash_post and not self._crashed:
            self._crashed = True
            raise SimulatedCrash(f"simulated process death during video call for post {self.crash_post}")
        doc = {"mock": True, "type": "video_placeholder",
               "notice": "MOCK placeholder. Not a video; no model or FFmpeg was run.",
               "duration_s": duration_s, "storyboard": storyboard}
        return json.dumps(doc, sort_keys=True, indent=2).encode("utf-8")


# -------------------------------------------------------------------- research
class MockResearchTools:
    tool_names = ("web_search", "fetch_page")

    def __init__(self):
        self.info = _info("mock-research-tools", ProviderKind.RESEARCH, "mock-tools")
        self.calls: list[dict] = []

    def call(self, tool: str, args: dict) -> dict:
        self.calls.append({"tool": tool, "args": args})
        if tool == "web_search":
            slug = hashlib.sha256(args["query"].encode()).hexdigest()[:8]
            return {"hits": [{"url": f"https://mock.invalid/{slug}",
                              "title": f"[MOCK] result for {args['query']}"}]}
        if tool == "fetch_page":
            url = args["url"]
            return {"url": url, "title": f"[MOCK] page {url[-8:]}",
                    "text": f"[MOCK] page body for {url}",
                    "facts": [
                        {"claim": f"[MOCK] fact A from {url[-8:]}", "quote": "[MOCK] quote A"},
                        {"claim": f"[MOCK] fact B from {url[-8:]}", "quote": "[MOCK] quote B"}]}
        raise ValueError(f"unknown tool {tool!r}")


@dataclass
class MockProviders:
    llm: MockLLM
    vision: MockVision
    image: MockImage
    video: MockVideo
    research: MockResearchTools


def build_mock_providers(settings: Settings, *, fail_rounds: dict[str, int] | None = None,
                         crash_post: str | None = None) -> MockProviders:
    m = settings.models
    return MockProviders(
        llm=MockLLM(m.llm, fail_rounds), vision=MockVision(m.vision), image=MockImage(m.image),
        video=MockVideo(m.video, crash_post), research=MockResearchTools())
