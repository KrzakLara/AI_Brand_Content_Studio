"""Visual analysis, packshot selection and font choice for the live analyst.

Trust levels, applied consistently:
* ``verified``  - re-derived from a stored, hash-checked artifact in this run.
* ``manual``    - labelled by a named operator, linked to the posts/images they looked at, and (for
                  images) tied to a sha256 of the bytes they viewed. Never promoted to ``verified``.
* ``assumption`` - an inference; always says what it is based on.
"""
import email.utils
import hashlib
from collections import defaultdict
from pathlib import Path

import yaml

from studio.contracts import (
    ColorEntry,
    EvidenceItem,
    FontChoice,
    FontEntry,
    Observation,
    PackshotSelection,
    SourceItem,
)
from studio.fingerprint import sha256_bytes
from studio.tools import extract, imagecheck

MIN_SIDE = 1000  # px: shortest side a packshot must have to be usable as a hero asset


def evidence_id(subject: str, sid: str, key: str) -> str:
    return "E-" + hashlib.sha256(f"{subject}|{sid}|{key}".encode()).hexdigest()[:8]


def _prov_ok(doc: dict, limitations: list[str], what: str) -> dict | None:
    prov = (doc or {}).get("provenance") or {}
    if not all(prov.get(k) for k in ("observer", "method", "observed_at")):
        limitations.append(f"{what} ignored: provenance (observer, method, observed_at) incomplete.")
        return None
    return prov


# ---------------------------------------------------------------------------------------------
# Instagram cover analysis (operator-labelled; palette computed by studio.tools.imagecheck)
# ---------------------------------------------------------------------------------------------
class VisualResult:
    def __init__(self):
        self.observations: list[Observation] = []
        self.colors: list[ColorEntry] = []
        self.post_urls: list[str] = []
        self.pack_posts: dict[str, str] = {}  # post url -> pack generation seen in it
        self.type_posts: list[str] = []


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def aggregate_colors(rows: list[tuple[str, list[dict]]], top: int = 5) -> list[ColorEntry]:
    """Share-weighted dominant colours; colours within the same 3-bit RGB bucket are merged.

    Returns the ``top`` colours overall plus the ``top`` non-neutral (accent) colours, each labelled,
    because dark/grey backgrounds otherwise hide the accents that actually carry the brand."""
    acc: dict[tuple, dict] = defaultdict(lambda: {"w": 0.0, "rgb": [0.0, 0.0, 0.0], "posts": []})
    for url, pal in rows:
        for c in pal:
            r, g, b = _hex_to_rgb(c["hex"])
            a = acc[(r >> 5, g >> 5, b >> 5)]
            a["w"] += c["share"]
            for i, v in enumerate((r, g, b)):
                a["rgb"][i] += v * c["share"]
            if url not in a["posts"]:
                a["posts"].append(url)
    total = sum(a["w"] for a in acc.values()) or 1.0
    ranked = []
    for a in sorted(acc.values(), key=lambda a: -a["w"]):
        hexv = "#%02x%02x%02x" % tuple(round(v / a["w"]) for v in a["rgb"])
        ranked.append((a, hexv, extract.is_neutral(hexv)))
    accents = [r for r in ranked if not r[2]][:top]
    chosen = ranked[:top] + [r for r in accents if r not in ranked[:top]]
    out = []
    for a, hexv, neutral in chosen:
        out.append(ColorEntry(
            hex=hexv, scope="instagram_covers", frequency=len(a["posts"]), status="manual", post_urls=a["posts"],
            basis=f"{'neutral' if neutral else 'accent'}; {a['w'] / total:.0%} of analysed cover pixels (median-cut, "
                  f"k=5 per cover, merged by 3-bit RGB bucket); in {len(a['posts'])} of {len(rows)} covers"))
    return out


def visual_analysis(led, path: Path, index, limitations: list[str]) -> VisualResult | None:
    if not path.is_file():
        limitations.append(f"visual observations file {path} not found; Instagram visual style not analysed.")
        return None
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    prov = _prov_ok(doc, limitations, "visual observations")
    if prov is None:
        return None
    posts = {s.url: s for s in index.sources if s.kind == "instagram_post" and s.retrieval_status == "ok"}
    kept = []
    for ob in doc.get("observations", []):
        s = posts.get(ob.get("post_url"))
        if s is None:
            limitations.append(f"visual observation for {ob.get('post_url')} ignored: post is not in the source index.")
            continue
        eid = evidence_id("instagram_visual_observation", s.source_id, ob.get("cover_sha256", "")[:12])
        led.items.append(EvidenceItem(
            evidence_id=eid, source_id=s.source_id, source_url=s.url, retrieved_at=s.retrieved_at, origin="manual_import",
            subject="instagram_visual_observation", confidence=0.7, verification_status="manual",
            claim=f"Cover of {s.url}: composition {ob.get('composition')}, product {ob.get('product_shown')}, "
                  f"people {ob.get('people_shown')}, text overlay {ob.get('text_overlay')}",
            quote=str(ob.get("notes", ""))[:300],
            verification_note=f"labelled by {prov['observer']} on {prov['observed_at']}; the cover image bytes "
                              f"(sha256 {str(ob.get('cover_sha256'))[:16]}...) are not stored in the repository",
            structured_value={k: ob.get(k) for k in ("media_kind", "composition", "product_shown", "people_shown",
                                                      "text_overlay", "overlay_type_style", "dominant_colors",
                                                      "cover_sha256", "shows_creatine_pack")}))
        kept.append((ob, s, eid))
    if not kept:
        return None
    n = len(kept)
    res = VisualResult()
    res.post_urls = [s.url for _, s, _ in kept]
    base = (f"labelled by {prov['observer']} over the cover image (first frame / first slide) of {n} posts; "
            "not the full video or carousel")

    def agg(label: str, key: str, skip=("none", None, False, "")):
        by: dict[str, list] = defaultdict(list)
        for ob, s, eid in kept:
            vals = ob.get(key)
            for v in (vals if isinstance(vals, list) else [vals]):
                if v not in skip:
                    by[str(v)].append((s.url, eid))
        for v, hits in sorted(by.items(), key=lambda kv: -len(kv[1])):
            res.observations.append(Observation(
                statement=f"{label}: '{v}' in {len(hits)} of {n} analysed covers", status="manual", basis=base,
                evidence_ids=[e for _, e in hits], post_urls=[u for u, _ in hits]))

    agg("People", "people_shown")
    agg("Product display", "product_shown")
    agg("Composition", "composition")
    agg("Overlay typography", "overlay_type_style")
    texty = [(s.url, e) for ob, s, e in kept if ob.get("text_overlay")]
    res.observations.append(Observation(
        statement=f"Text overlay present on {len(texty)} of {n} analysed covers", status="manual", basis=base,
        evidence_ids=[e for _, e in texty], post_urls=[u for u, _ in texty]))
    no_people = [(s.url, e) for ob, s, e in kept if ob.get("people_shown") in ("none", None)]
    res.observations.append(Observation(
        statement=f"No person visible on {len(no_people)} of {n} analysed covers", status="manual", basis=base,
        evidence_ids=[e for _, e in no_people], post_urls=[u for u, _ in no_people]))
    res.colors = aggregate_colors([(s.url, ob.get("dominant_colors") or []) for ob, s, _ in kept])
    res.pack_posts = {s.url: ob["shows_creatine_pack"] for ob, s, _ in kept if ob.get("shows_creatine_pack")}
    res.observations.append(Observation(
        statement=f"Palette is computed from the pixels of the {n} covers (see colors, scope 'instagram_covers').",
        status="manual", basis=prov.get("palette_method", "computed with studio.tools.imagecheck.dominant_colors"),
        evidence_ids=[e for _, _, e in kept], post_urls=res.post_urls))
    return res


# ---------------------------------------------------------------------------------------------
# Packshot selection (+ checks + recorded cut-out)
# ---------------------------------------------------------------------------------------------
def _parse_http_date(v: str | None):
    try:
        return email.utils.parsedate_to_datetime(v) if v else None
    except (TypeError, ValueError):
        return None


def select_packshot(svc, led, index, attested: dict, pack_posts: dict, limitations: list[str]):
    """Choose the current-pack packshot. Returns (PackshotSelection | None, [derived SourceItem])."""
    cands = [s for s in index.sources if s.kind == "image" and s.retrieval_status == "ok"
             and (s.provenance or {}).get("role") == "packshot_candidate"]
    if not cands:
        limitations.append("No packshot candidates were downloaded (brief.seed_images empty or all failed); "
                           "no current-pack packshot selected.")
        return None, []
    rows, seen = [], {}
    for s in cands:
        reasons: list[str] = []
        data = led.bytes(s.source_id)
        if data is None:
            continue  # integrity failure is reported centrally
        if s.artifact_sha256 in seen:
            reasons.append(f"identical bytes to {seen[s.artifact_sha256]}")
        seen.setdefault(s.artifact_sha256, s.url)
        try:
            info = imagecheck.inspect_image(data, min_side=MIN_SIDE)
        except imagecheck.PillowMissing:
            info = {**imagecheck.header_info(data), "has_transparency": None, "transparent_background": False,
                    "meets_min_resolution": None, "background": None}
            reasons.append("Pillow missing: transparency could not be checked")
        ob = attested.get(s.source_id)
        if ob is None:
            reasons.append("no operator attestation of pack generation / view for this image")
        else:
            if ob.get("generation") != "new":
                reasons.append(f"pack generation is '{ob.get('generation')}', not the current design")
            if ob.get("view") != "front":
                reasons.append(f"view is '{ob.get('view') or 'unspecified'}', not a front packshot")
            if ob.get("includes_gift_merchandise"):
                reasons.append("image includes gift merchandise overlapping the pack")
        if info.get("meets_min_resolution") is False:
            reasons.append(f"resolution {info['width']}x{info['height']} below {MIN_SIDE}px")
        lm = _parse_http_date((s.provenance or {}).get("last_modified"))
        rows.append({"s": s, "info": info, "ob": ob, "reasons": reasons, "lm": lm})
    eligible = sorted((r for r in rows if not r["reasons"]),
                      key=lambda r: (-(r["lm"].timestamp() if r["lm"] else 0), -min(r["info"]["width"], r["info"]["height"]),
                                     r["s"].url))
    rejected = [{"url": r["s"].url, "reasons": r["reasons"]} for r in rows if r["reasons"]]
    if not eligible:
        limitations.append("No eligible packshot: every candidate was rejected (" + "; ".join(
            f"{x['url'].rsplit('/', 1)[-1]}: {', '.join(x['reasons'])}" for x in rejected)[:600] + ")")
        return None, []
    best = eligible[0]
    s, info = best["s"], best["info"]
    basis = [
        "operator attested: current orange/silver 'micronised' pouch, front view, no gift merchandise",
        f"newest eligible file by server Last-Modified ({(s.provenance or {}).get('last_modified')})",
        f"resolution {info['width']}x{info['height']} >= {MIN_SIDE}px",
        "rejection rules: not new generation / not front view / gift merchandise overlapping / below resolution / "
        "unattested / duplicate bytes",
    ]
    if pack_posts:
        basis.append("the same pack generation appears in Instagram post(s): " + ", ".join(pack_posts))
    cutout_src, cutout_rep = None, None
    new_sources: list[SourceItem] = []
    if not info.get("transparent_background"):
        try:
            png, rep = imagecheck.cutout_background(led.bytes(s.source_id))
            check = imagecheck.inspect_image(png, min_side=MIN_SIDE)
            out_dir = svc.run_dir / "research" / "packshots"
            out_dir.mkdir(parents=True, exist_ok=True)
            sha = sha256_bytes(png)
            path = out_dir / f"{sha[:16]}_cutout.png"
            path.write_bytes(png)
            cutout_src = SourceItem(
                source_id=evidence_id("packshot_cutout", s.source_id, sha[:12]).replace("E-", "S-"),
                url=f"derived://cutout/{s.artifact_sha256[:16]}", title=f"cut-out of {s.url.rsplit('/', 1)[-1]}",
                kind="packshot_cutout", content_sha256=sha, origin=s.origin, retrieved_at=s.retrieved_at,
                artifact_path=path.relative_to(svc.run_dir).as_posix(), artifact_sha256=sha,
                access_limitations="derived image; third-party media, stored locally only",
                provenance={"derived_from": s.source_id, "derived_from_sha256": s.artifact_sha256, **rep,
                            "result_has_transparency": check["has_transparency"],
                            "result_transparent_corners": check["transparent_background"]})
            new_sources.append(cutout_src)
            cutout_rep = {**rep, "output_sha256": sha, "result_transparent_background": check["transparent_background"],
                          "known_limitation": "mechanical cut-out only: anything that is not background colour and "
                                              "touches the pack (e.g. overlapping claim badges, shadows) is kept"}
        except imagecheck.PillowMissing:
            limitations.append("Packshot cut-out skipped: Pillow is not installed (pip install -e .[images]).")
        except ValueError as e:
            limitations.append(f"Packshot cut-out refused: {e}")
    eid = evidence_id("packshot_selection", s.source_id, s.artifact_sha256[:12])
    led.items.append(EvidenceItem(
        evidence_id=eid, source_id=s.source_id, source_url=s.url, retrieved_at=s.retrieved_at, origin=s.origin,
        subject="packshot_selection", confidence=0.7, verification_status="manual",
        claim=f"Selected current-pack packshot: {s.url.rsplit('/', 1)[-1]} (Last-Modified "
              f"{(s.provenance or {}).get('last_modified')}, retrieved {s.retrieved_at.isoformat() if s.retrieved_at else '?'})",
        quote=s.url.rsplit("/", 1)[-1],
        verification_note="pack generation and view attested by the operator; format, resolution, alpha and background "
                          "were computed from the stored image bytes (hash checked)",
        structured_value={"technical": {k: v for k, v in info.items()}, "rejected": rejected,
                          "cutout": cutout_rep, "last_modified": (s.provenance or {}).get("last_modified")}))
    if cutout_src is not None:
        led.items.append(EvidenceItem(
            evidence_id=evidence_id("packshot_cutout", s.source_id, cutout_rep["output_sha256"][:12]),
            source_id=cutout_src.source_id, source_url=cutout_src.url, retrieved_at=s.retrieved_at, origin=s.origin,
            subject="packshot_cutout", confidence=0.8, verification_status="verified",
            claim=f"Background removed from the selected packshot: transparent corners="
                  f"{cutout_rep['result_transparent_background']}, transparent area {cutout_rep['transparent_fraction']:.0%}",
            quote=f"{cutout_rep['method']} tol={cutout_rep['tolerance']}",
            verification_note="result re-inspected from its own stored bytes; see known_limitation in structured_value",
            structured_value=cutout_rep))
    sel = PackshotSelection(
        source_id=s.source_id, url=s.url, retrieved_at=s.retrieved_at,
        last_modified=(s.provenance or {}).get("last_modified"), pack_generation="new", view="front",
        format=info["format"], width=info["width"], height=info["height"],
        meets_min_resolution=bool(info.get("meets_min_resolution")), alpha_capable=bool(info["alpha_capable"]),
        has_transparency=bool(info.get("has_transparency")), transparent_background=bool(info.get("transparent_background")),
        background_hex=(info.get("background") or {}).get("hex"), selection_basis=basis, rejected=rejected,
        corroborating_post_urls=list(pack_posts), cutout_source_id=cutout_src.source_id if cutout_src else None,
        cutout=cutout_rep, status="manual", evidence_id=eid)
    return sel, new_sources


# ---------------------------------------------------------------------------------------------
# Font choice
# ---------------------------------------------------------------------------------------------
def choose_font(typography: list[FontEntry], font_evidence: dict[str, str], observed_posts: list[str]) -> FontChoice | None:
    if not typography:
        return None
    top = typography[0]
    return FontChoice(
        family=top.family, status="verified",
        basis=f"most frequently declared font-family in the site CSS ({top.frequency} declarations; scope: website). "
              "Verified only as the website text face.",
        recommended_use="stand-in for headline/overlay text in creatives (Instagram overlays observed in bold "
                        "geometric sans capitals; see observed_in_posts)",
        recommended_use_status="assumption",
        license_note="ASSUMPTION: Inter is published under the SIL Open Font License 1.1 (from general knowledge; "
                    "licence text not checked in this run) - confirm before commercial use",
        fallbacks=[t.family for t in typography[1:3]],
        logotype_note="The 'GymBeam' wordmark is a custom italic logotype whose typeface was not identified (unknown). "
                      "Use the official logo asset; never retype it in a font.",
        evidence_ids=[font_evidence[top.family]] if top.family in font_evidence else [],
        observed_in_posts=observed_posts)

