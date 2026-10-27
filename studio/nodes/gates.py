"""Deterministic gates: technical validation and evidence/compliance validation. No AI."""
import json
import struct

from studio.contracts import CreativeSpec, QAFinding, Severity
from studio.fingerprint import sha256_file
from studio.services import Services

TECH, EVID = "technical_validation", "evidence_validation"


def _finding(s: dict, reviewer: str, n: int, category: str, message: str) -> dict:
    return QAFinding(
        finding_id=f"{s['post_id']}-{reviewer}-a{s.get('attempt', 0)}-{n}", post_id=s["post_id"],
        reviewer=reviewer, severity=Severity.BLOCKER, category=category, message=message,
        attempt=s.get("attempt", 0)).dump()


def _png_size(data: bytes) -> tuple[int, int] | None:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", data[16:24])


def technical_validation(svc: Services, s: dict) -> dict:
    problems: list[tuple[str, str]] = []
    arts = s["artifacts"]
    for a in arts:
        path = svc.run_dir / a["relpath"]
        if not path.is_file() or path.stat().st_size == 0:
            problems.append(("missing_file", f"{a['relpath']} missing or empty"))
            continue
        if sha256_file(path) != a["sha256"]:
            problems.append(("hash_mismatch", f"{a['relpath']} does not match recorded sha256"))
            continue
        if a["kind"] == "image":
            size = _png_size(path.read_bytes())
            if size is None:
                problems.append(("bad_image", f"{a['relpath']} is not a PNG"))
            elif size != (a["metadata"]["width"], a["metadata"]["height"]) or size[0] * 5 != size[1] * 4:
                problems.append(("bad_dimensions", f"{a['relpath']} is {size}, expected 4:5 matching metadata"))
        elif a["kind"] in ("document", "video_placeholder"):
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                problems.append(("bad_json", f"{a['relpath']} is not valid JSON"))
        if a["kind"] in ("video", "video_placeholder") and not 5 <= a["metadata"].get("duration_s", 0) <= 60:
            problems.append(("bad_duration", f"{a['relpath']} duration outside 5-60 s"))
    images = [a for a in arts if a["kind"] == "image"]
    fmt = s["plan_post"]["format"]
    if fmt == "carousel" and len(images) < 3:
        problems.append(("slide_count", "carousel needs at least 3 slides"))
    if fmt == "hero" and len(images) != 1:
        problems.append(("image_count", "hero post needs exactly one image"))
    if fmt == "reel" and not any(a["kind"].startswith("video") for a in arts):
        problems.append(("no_video", "reel has no video artifact"))
    return {"gate_findings": [_finding(s, TECH, i, c, m) for i, (c, m) in enumerate(problems)]}


def evidence_validation(svc: Services, s: dict) -> dict:
    spec = CreativeSpec.model_validate(s["creative_spec"])
    registry = {e["evidence_id"]: e for e in s["evidence"]["items"]}
    problems: list[tuple[str, str]] = []
    if not spec.claims:
        problems.append(("no_claims", "post makes no evidence-backed claim"))
    for c in spec.claims:
        e = registry.get(c.evidence_id)
        if e is None:
            problems.append(("unknown_evidence", f"claim cites unknown evidence {c.evidence_id}"))
        elif e["claim"] != c.text:
            problems.append(("claim_mismatch", f"claim text differs from evidence {c.evidence_id}"))
    text = " ".join([spec.headline, spec.body, spec.cta, *(f"{x.title} {x.body}" for x in spec.slides)]).lower()
    for phrase in s["brand"]["banned_phrases"]:
        if phrase.lower() in text:
            problems.append(("banned_phrase", f"copy contains banned phrase {phrase!r}"))
    if svc.is_mock and not (spec.mock and all(a["mock"] for a in s["artifacts"])):
        problems.append(("mock_label", "mock output is not labelled mock"))
    base = len(s.get("gate_findings", []))
    return {"gate_findings": [*s.get("gate_findings", []),
                              *(_finding(s, EVID, base + i, c, m) for i, (c, m) in enumerate(problems))]}
