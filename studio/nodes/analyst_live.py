"""Brand & product analyst for real sources.

Everything stated as *verified* is extracted deterministically from a stored artifact and
re-checked against it (artifact hash + the quoted excerpt must occur in the stored content).
Qualitative judgements that need a model or a human are ``assumption`` or ``unknown`` and are
only produced by the optional LLM pass, which must cite verified evidence.
"""
import hashlib
import json
import re
from pathlib import Path
from collections import Counter
from datetime import datetime

import yaml
from pydantic import BaseModel, Field

from studio import prompts
from studio.contracts import (
    BrandProfile,
    BriefInput,
    ColorEntry,
    EvidenceItem,
    EvidenceRegistry,
    ExamplePost,
    FontEntry,
    Observation,
    PackagingObservation,
    ProductEntry,
    SourceIndex,
    SourceItem,
    VariantEntry,
)
from studio.fingerprint import fingerprint, sha256_bytes
from studio.nodes import visual
from studio.services import Services
from studio.tools import extract
from studio.tools.toolset import source_id

EXTRACTOR_VERSION = "ex-3"
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
HR_WORDS = {"i", "je", "za", "uz", "na", "vaš", "vas", "vam", "što", "se", "su", "da", "ne"}


class ToneAnalysis(BaseModel):
    """Optional LLM output. Always recorded as an assumption, and must cite verified evidence."""

    tone_descriptors: list[str] = Field(default_factory=list)
    audience_summary: str = ""
    cited_evidence_ids: list[str] = Field(default_factory=list)


_eid = visual.evidence_id  # same deterministic evidence ids everywhere


class _Ledger:
    """Collects evidence, verifying each item against the stored artifact it cites."""

    def __init__(self, svc: Services, index: SourceIndex):
        self.svc, self.items = svc, []
        self.src = {s.source_id: s for s in index.sources}
        self._text: dict[str, str | None] = {}
        self.integrity: dict[str, str] = {}  # source_id -> why its stored artifact was rejected

    def integrity_message(self, sid: str) -> str:
        """Provenance-rich report line for a rejected artifact."""
        s = self.src[sid]
        return (f"INTEGRITY FAILURE: {s.kind} {s.url} [source {sid}, origin {s.origin}, retrieved "
                f"{s.retrieved_at.isoformat() if s.retrieved_at else 'unknown'}]: stored artifact {s.artifact_path} {self.integrity.get(sid, 'was rejected')}; "
                f"expected sha256 {(s.artifact_sha256 or '')[:16]}...; excluded from the analysis.")

    def text(self, sid: str, mode: str) -> str | None:
        key = f"{sid}|{mode}"
        if key not in self._text:
            s = self.src[sid]
            p = self.svc.run_dir / s.artifact_path if s.artifact_path else None
            if not p or not p.is_file():
                self.integrity[sid] = "is missing"
                self._text[key] = None
            elif (actual := sha256_bytes(p.read_bytes())) != s.artifact_sha256:
                self.integrity[sid] = f"no longer matches (actual sha256 {actual[:16]}...)"
                self._text[key] = None  # tampered artifact
            else:
                raw = p.read_text(encoding="utf-8", errors="replace")
                if mode == "html":
                    raw = extract.searchable_text(raw)
                elif mode == "ig":
                    raw = "\n".join(x["caption"] for x in json.loads(raw)["posts"])
                self._text[key] = raw
        return self._text[key]

    def bytes(self, sid: str) -> bytes | None:
        """Hash-checked read of a binary artifact (None + integrity record on mismatch)."""
        s = self.src[sid]
        p = self.svc.run_dir / s.artifact_path if s.artifact_path else None
        if not p or not p.is_file():
            self.integrity[sid] = "is missing"
            return None
        data = p.read_bytes()
        if (actual := sha256_bytes(data)) != s.artifact_sha256:
            self.integrity[sid] = f"no longer matches (actual sha256 {actual[:16]}...)"
            return None
        return data

    def add(self, subject: str, sid: str, key: str, claim: str, quote: str, needles: list[str], mode: str,
            variant: str | None = None, value: dict | None = None, confidence: float = 0.9) -> str:
        s = self.src[sid]
        text = self.text(sid, mode)
        if text is None:
            status, note = "failed", "stored artifact missing or hash mismatch"
        else:
            missing = [n for n in needles if n not in text]
            status = "failed" if missing else "verified"
            note = f"not found in stored artifact: {missing}" if missing else \
                f"all {len(needles)} excerpt(s) located in stored artifact (hash checked)"
        item = EvidenceItem(
            evidence_id=_eid(subject, sid, key), claim=claim, source_id=sid, quote=quote[:400],
            confidence=confidence, origin=s.origin, subject=subject, source_url=s.url,
            retrieved_at=s.retrieved_at, verification_status=status, verification_note=note,
            packaging_variant=variant, structured_value=value or {})
        self.items.append(item)
        return item.evidence_id


def live_analyst(svc: Services, state: dict) -> dict:
    brief = BriefInput.model_validate(state["brief"])
    research = state["research"]
    use_llm = bool(getattr(svc.llm, "supports_analysis", False))
    obs_file = Path(brief.manual_observations_path) if brief.manual_observations_path else None
    obs_hash = sha256_bytes(obs_file.read_bytes()) if obs_file and obs_file.is_file() else ""
    vis_file = Path(brief.visual_observations_path) if brief.visual_observations_path else None
    obs_hash += sha256_bytes(vis_file.read_bytes()) if vis_file and vis_file.is_file() else ""
    fp = fingerprint("analyst-live", research["fingerprint"], brief.brand_name, brief.product_name,
                     brief.instagram_handle, brief.focus_keywords, brief.seed_images, EXTRACTOR_VERSION, obs_hash,
                     svc.llm.info.fingerprint() if use_llm else "heuristic_only", prompts.version("brand_analyst"))

    def compute() -> dict:
        index = SourceIndex.model_validate(research["source_index"])
        reg, profile = _analyse(svc, brief, index, use_llm, fp)
        return {"profile": profile.dump(), "evidence": reg.dump(), "source_index": index.dump()}

    out, hit = svc.stage(svc.GLOBAL, "analyst", fp, compute)
    out_dir = svc.run_dir / "research"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, doc in (("brand_profile", out["profile"]), ("evidence_registry", out["evidence"]),
                      ("source_index", out["source_index"])):
        (out_dir / f"{name}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    ev = out["evidence"]["items"]
    return {
        "brand_profile": {"profile": out["profile"], "fingerprint": fp},
        "research": {**research, "evidence": out["evidence"], "source_index": out["source_index"]},
        "events": [f"brand_product_analyst(live): stage cache {'hit' if hit else 'miss'}, mode="
                   f"{out['profile']['analysis_mode']}, evidence verified="
                   f"{sum(e['verification_status'] == 'verified' for e in ev)}/{len(ev)}"]}


def _analyse(svc: Services, brief: BriefInput, index: SourceIndex, use_llm: bool, fp: str):
    led = _Ledger(svc, index)
    ok = [s for s in index.sources if s.retrieval_status == "ok"]
    limitations = [
        "Which packaging generation (old vs new) is shipped for each priced variant is NOT established: "
        "text data cannot tell, so every variant carries packaging_generation='unverified'. Gallery photos "
        "show both generations (see packaging_observations, operator-attested).",
        "Product images are listed per product page, not per variant: the JSON-LD gives fewer images than "
        "variants, and file names such as 'km750g' only suggest a size. Image-to-variant mapping is unverified.",
        "Prices, availability and ratings are snapshots as of each source's retrieved_at.",
    ]
    assumptions: list[Observation] = []
    identity: list[Observation] = []
    catalog: list[ProductEntry] = []

    # --- website: identity, products ---------------------------------------------------------
    home = next((s for s in ok if s.url.rstrip("/") == (brief.website_url or "").rstrip("/")), None)
    positioning = ""
    if home:
        meta = extract.parse_html(led.text(home.source_id, "raw") or "", home.url).meta
        for key, label in (("og:site_name", "Official site name"), ("og:description", "Site self-description"),
                           ("theme-color", "Site theme colour")):
            if meta.get(key):
                e = led.add("site_meta", home.source_id, key, f"{label}: {meta[key]}", meta[key], [meta[key]], "html")
                identity.append(Observation(statement=f"{label}: {meta[key]}", status="verified",
                                            basis=f"{home.url} meta '{key}'", evidence_ids=[e]))
                if key == "og:description":
                    positioning = meta[key]
    for s in ok:
        if s.kind == "css" or not s.artifact_path or s.kind in ("image", "instagram_profile", "instagram_post"):
            continue
        raw = led.text(s.source_id, "raw")
        if raw is None:
            continue  # reported centrally below
        page = extract.parse_html(raw, s.url)
        for prod in extract.jsonld_products(page.jsonld):
            if not s.url.endswith(".html"):
                continue  # category listings carry teaser products; the product page is authoritative
            twin = next((c for c in catalog if c.sku == prod["sku"]), None)
            if twin:  # same sku served under another URL: record the alias, do not duplicate evidence
                twin.alias_urls.append(s.url)
                continue
            catalog.append(_product(led, s, prod, index))

    attested: dict[str, dict] = {}
    if brief.manual_observations_path:
        attested = _manual_observations(led, Path(brief.manual_observations_path), index, catalog, limitations)
    with_images = sum(bool(c.image_source_ids) for c in catalog)
    if with_images < len(catalog):
        limitations.append(f"Reference images were downloaded for {with_images} of {len(catalog)} catalog products "
                           "(research.max_images cap); the others have none stored.")

    # --- css: colours & typography -----------------------------------------------------------
    fonts, colors = Counter(), Counter()
    for s in (x for x in ok if x.kind == "css"):
        st = extract.css_stats(led.text(s.source_id, "raw") or "")
        fonts.update(dict(st["fonts"]))
        colors.update(dict(st["colors"]))
    typography = []
    for fam, n in fonts.most_common(4):
        sid = next(s.source_id for s in ok if s.kind == "css" and fam in (led.text(s.source_id, "raw") or ""))
        e = led.add("css_font", sid, fam, f"font-family '{fam}' declared {n} times in site CSS", fam, [fam], "raw", confidence=0.8)
        typography.append(FontEntry(family=fam, scope="website", basis=f"declaration count in site CSS ({e})", frequency=n))
    palette, color_entries = [], []
    theme = next((o for o in identity if "theme colour" in o.statement), None)
    if theme:
        hexv = theme.statement.rsplit(" ", 1)[-1]
        if re.fullmatch(r"#[0-9a-fA-F]{6}", hexv):
            palette.append(hexv.lower())
            color_entries.append(ColorEntry(hex=hexv.lower(), scope="website", basis="meta theme-color"))
    for hexv, n in [c for c in colors.most_common(40) if not extract.is_neutral(c[0])][:5]:
        color_entries.append(ColorEntry(hex=hexv, scope="website", frequency=n, basis="occurrences in site CSS (non-neutral)"))
        if hexv not in palette:
            palette.append(hexv)
    if not fonts:
        limitations.append("No site CSS was retrieved, so typography is unknown.")
    limitations.append("Website colours/typography are measured from CSS. Instagram cover analysis (if present) is "
                       "operator-labelled on cover frames only, from images that are not stored in the repository; "
                       "no vision model ran in the studio.")

    # --- instagram ---------------------------------------------------------------------------
    posts, tone, formats, audience, ex_posts = _instagram(led, index, ok, limitations)
    vres = visual.visual_analysis(led, Path(brief.visual_observations_path), index, limitations) \
        if brief.visual_observations_path else None
    if vres is None:
        limitations.append("Instagram visual style was not analysed (no visual observations supplied or usable).")
    visual_obs = list(vres.observations) if vres else [Observation(
        statement="Instagram visual style (imagery, layout, graphics) was not analysed.", status="unknown",
        basis="no vision capability in this run and no operator observations")]
    if vres:
        color_entries += vres.colors
    selection, derived = visual.select_packshot(svc, led, index, attested, vres.pack_posts if vres else {}, limitations)
    index.sources.extend(derived)
    for d in derived:
        led.src[d.source_id] = d
    font_ev = {t.family: next((i.evidence_id for i in led.items if i.subject == "css_font" and t.family in i.claim), "")
               for t in typography}
    font = visual.choose_font(typography, {k: v for k, v in font_ev.items() if v},
                              [u for o in (vres.observations if vres else []) if "typography" in o.statement for u in o.post_urls])
    if palette:
        visual_obs.append(Observation(statement=f"Website palette: {', '.join(palette)} (website only).",
                                  status="verified", basis="theme-color + CSS frequency",
                                  evidence_ids=[i.evidence_id for i in led.items if i.subject in ("css_font", "site_meta")][:6]))
    tone.append(Observation(statement="Qualitative tone (e.g. playful vs. serious) is not determined: "
                            "needs an LLM or human review.", status="unknown", basis="heuristic_only analysis"))
    assumptions.append(Observation(
        statement="Primary audience: Croatian-speaking people interested in fitness, health and sports apparel.",
        status="assumption", basis="inferred from caption language, topic hashtags and product range; "
        "no audience analytics were available"))

    mode = "heuristic_only"
    if use_llm and posts:
        mode = "llm_assisted"
        assumptions += _llm_tone(svc, brief, led, posts, fp)

    # --- failed / blocked sources are part of the report ------------------------------------
    for s in index.sources:
        if s.retrieval_status != "ok":
            limitations.append(f"{s.kind} {s.url}: {s.retrieval_status} - {s.access_limitations}")
    for sid in led.integrity:  # every rejected artifact, however it was read: report + mark the index
        limitations.append(led.integrity_message(sid))
        src = led.src[sid]
        src.flags = [*src.flags, "artifact_integrity_failed"]
        src.access_limitations = (src.access_limitations + " | " + led.integrity_message(sid)).strip(" |")
        if src.kind == "instagram_profile":  # its posts share the rejected artifact
            for post in (x for x in index.sources if x.kind == "instagram_post" and x.artifact_sha256 == src.artifact_sha256):
                post.flags = [*post.flags, "artifact_integrity_failed"]
    reg = EvidenceRegistry(items=led.items)
    reg.check_sources(index)
    ver = {i.evidence_id for i in reg.items if i.verification_status == "verified"}
    products_ev = [i.evidence_id for i in reg.items if i.subject.startswith("product") and i.evidence_id in ver]
    origins = Counter(s.origin for s in ok)
    profile = BrandProfile(
        brand_name=brief.brand_name, positioning=positioning or "unknown",
        voice="UNDETERMINED (heuristic_only): see communication_tone for measured signals" if mode == "heuristic_only"
        else "see communication_tone (model-inferred items are assumptions)",
        palette=palette, product_fact_ids=products_ev, mock=False, analysis_mode=mode,
        audience_summary="ASSUMPTION (unverified): " + assumptions[0].statement,
        data_origins=dict(origins), identity=identity, communication_tone=tone, audience=audience,
        visual_style=visual_obs, colors=color_entries, typography=typography, content_formats=formats,
        example_posts=ex_posts, product_catalog=catalog, assumptions=assumptions, limitations=limitations,
        selected_packshot=selection, selected_font=font,
        visual_analysis_post_urls=vres.post_urls if vres else [])
    return reg, profile


def _product(led: _Ledger, s: SourceItem, prod: dict, index: SourceIndex) -> ProductEntry:
    fam = f"{prod['name']} [sku {prod['sku']}]"
    desc = " ".join(prod["description"].split())[:300]
    ids = []
    if desc:
        ids.append(led.add("product_description", s.source_id, prod["sku"], f"Description of {prod['name']}", desc,
                           [desc], "html", variant=None, value={"sku": prod["sku"]}))
    r = prod["rating"]
    if r.get("ratingValue") is not None:
        ids.append(led.add("product_rating", s.source_id, prod["sku"], f"Listed rating {r['ratingValue']} from "
                           f"{r.get('reviewCount')} reviews for {prod['name']}", f"{r['ratingValue']}",
                           [str(r["ratingValue"])], "html", value=r))
    variants = []
    for o in prod["offers"]:
        size, flavor = extract.split_variant(o["name"] or "")
        vkey = f"sku:{o['sku']} | {size or '?'} | {flavor or 'none'}"
        needles = [str(o["name"]), str(o["sku"])] + ([str(o["gtin13"])] if o.get("gtin13") else []) + \
                  ([str(o["price"])] if o.get("price") is not None else [])
        eid = led.add("product_variant", s.source_id, str(o["sku"]),
                      f"Variant {o['sku']} '{o['name']}' listed at {o.get('price')} {o.get('priceCurrency')}, "
                      f"availability {str(o.get('availability') or '').rsplit('/', 1)[-1]}",
                      str(o["name"]), needles, "html", variant=vkey,
                      value={**o, "price_retrieved_at": s.retrieved_at.isoformat() if s.retrieved_at else None})
        variants.append(VariantEntry(
            sku=str(o["sku"]), name=str(o["name"]), size=size, flavor=flavor, price=o.get("price"),
            currency=str(o.get("priceCurrency") or ""), gtin13=str(o.get("gtin13") or ""),
            availability=str(o.get("availability") or "").rsplit("/", 1)[-1],
            price_retrieved_at=s.retrieved_at, evidence_id=eid))
        ids.append(eid)
    got = {x.source_id for x in index.sources if x.retrieval_status == "ok" and x.kind == "image"}
    imgs = [source_id(i) for i in prod["images"] if source_id(i) in got]
    return ProductEntry(brand=prod.get("brand", ""), product_family=fam, url=s.url, sku=prod["sku"], name=prod["name"], description_excerpt=desc,
                        image_source_ids=imgs, variants=variants, evidence_ids=ids)


def _manual_observations(led: "_Ledger", path: Path, index: SourceIndex, catalog: list[ProductEntry],
                         limitations: list[str]) -> dict[str, dict]:
    """Operator-attested image observations: linked to the stored artifact by sha256, status 'manual'.

    Returns {source_id: observation} for the observations that matched a stored image."""
    matched: dict[str, dict] = {}
    if not path.is_file():
        limitations.append(f"manual observations file {path} not found; packaging not reviewed.")
        return matched
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    prov = doc.get("provenance") or {}
    if not all(prov.get(k) for k in ("observer", "method", "observed_at")):
        limitations.append("manual observations ignored: provenance (observer, method, observed_at) incomplete.")
        return matched
    images: dict[str, list[SourceItem]] = {}
    for s in index.sources:
        if s.kind == "image" and s.retrieval_status == "ok":
            images.setdefault(s.artifact_sha256, []).append(s)
    for ob in doc.get("observations", []):
        wanted = ob.get("image_sha256")
        shas = wanted if isinstance(wanted, list) else [wanted]  # every listed hash was inspected by the observer
        # an attestation is about BYTES: it applies to every URL that served those bytes
        srcs = list({s.source_id: s for h in shas for s in images.get(h, [])}.values())
        if not srcs:
            limitations.append(f"manual observation for {ob.get('image_url')} ignored: no downloaded image with "
                               "that sha256 in the source index.")
            continue
        for src in srcs:
            _attest_one(led, ob, src, prov, catalog, matched, limitations)
    if prov.get("caveat"):
        limitations.append("Packaging observations caveat: " + " ".join(str(prov["caveat"]).split()))
    return matched


def _attest_one(led, ob, src, prov, catalog, matched, limitations) -> None:
    """Attach one operator observation to one stored image (re-checking the stored bytes first)."""
    p = led.svc.run_dir / src.artifact_path
    if sha256_bytes(p.read_bytes()) != src.artifact_sha256:
        limitations.append(f"manual observation for {ob['image_url']} ignored: stored image no longer matches its hash.")
        return
    variant = f"pack:{ob['generation']} | {ob.get('size', '?')} | {ob.get('flavor', '?')}"
    item = EvidenceItem(
        evidence_id=_eid("packaging_observation", src.source_id, src.artifact_sha256[:12]),
        claim=" ".join(str(ob["statement"]).split()), source_id=src.source_id,
        quote=f"image sha256 {src.artifact_sha256[:16]}", confidence=0.7, origin="manual_import",
        subject="packaging_observation", source_url=src.url, retrieved_at=src.retrieved_at,
        verification_status="manual",
        verification_note=f"attested by {prov['observer']} on {prov['observed_at']}; image artifact hash matches",
        packaging_variant=variant, structured_value={
            "generation": ob["generation"], "view": ob.get("view", ""),
            "includes_gift_merchandise": bool(ob.get("includes_gift_merchandise"))})
    led.items.append(item)
    matched[src.source_id] = ob
    for c in catalog:
        if src.source_id in c.image_source_ids:
            c.packaging_observations.append(PackagingObservation(
                generation=ob["generation"], view=str(ob.get("view", "")), size=str(ob.get("size", "")),
                flavor=str(ob.get("flavor", "")), image_source_id=src.source_id, evidence_id=item.evidence_id,
                includes_gift_merchandise=bool(ob.get("includes_gift_merchandise"))))


def _instagram(led, index, ok, limitations):
    prof = next((s for s in ok if s.kind == "instagram_profile"), None)
    if not prof:
        limitations.append("No Instagram posts were collected; tone, formats and example posts are unavailable.")
        return [], [], [], [], []
    raw = led.text(prof.source_id, "raw")  # hash-checked read
    if raw is None:
        return [], [], [], [], []  # reported centrally in _analyse
    doc = json.loads(raw)
    posts = doc["posts"]
    limitations.append(
        f"Instagram: {len(posts)} brand-owned posts from '{doc['provenance'].get('method')}' "
        f"(origin: {prof.origin}); {doc.get('excluded_non_owner_posts', 0)} collaboration/tagged posts by other "
        "accounts were seen and excluded from brand-voice analysis. Likes/comments are a snapshot; hidden counts stay null.")
    if len(posts) < 20:
        limitations.append(f"Only {len(posts)} of the 20-30 targeted Instagram references are available.")
    post_src = {s.url: s for s in index.sources if s.kind == "instagram_post"}
    ex, ev_ids = [], []
    for p in posts:
        s = post_src[p["url"]]
        cap = p["caption"].strip()
        eid = led.add("instagram_post", s.source_id, p["shortcode"],
                      f"@{p['owner']} published a {p['type']} on {p['timestamp'][:10]} (post {p['shortcode']})",
                      cap[:160], [cap[:160]] if cap else [], "ig", value={"type": p["type"], "hashtags": p["hashtags"]})
        ev_ids.append(eid)
        ex.append(ExamplePost(
            source_id=s.source_id, url=p["url"], shortcode=p["shortcode"], post_type=p["type"],
            posted_at=datetime.fromisoformat(p["timestamp"].replace("Z", "+00:00")), caption_excerpt=cap[:200],
            hashtags=p["hashtags"], likes=p.get("likes"), comments=p.get("comments"),
            metrics_collected_at=prof.retrieved_at if p.get("likes") is not None else None, evidence_id=eid,
            origin=prof.origin))
    n = len(posts)
    basis = f"computed over {n} brand-owned posts ({prof.origin})"
    caps = [p["caption"] for p in posts]
    types = Counter(p["type"] for p in posts)
    tags = Counter(t.lower() for p in posts for t in p["hashtags"])
    hr = sum(bool(re.search("[čćšžđ]", c.lower())) or len(HR_WORDS & set(re.findall(r"\w+", c.lower()))) >= 3 for c in caps)
    plural = sum(bool(re.search(r"\b(vaš\w*|vam|vas|vi)\b", c.lower())) for c in caps)
    tone = [
        Observation(statement=f"{hr} of {n} captions are Croatian (diacritics / stop-word heuristic).",
                    status="verified", basis=basis + "; heuristic", evidence_ids=ev_ids),
        Observation(statement=f"{sum(bool(EMOJI.search(c)) for c in caps)} of {n} captions use emoji.",
                    status="verified", basis=basis, evidence_ids=ev_ids),
        Observation(statement=f"{sum('opisu profila' in c.lower() for c in caps)} of {n} captions point to the "
                    "'link u opisu profila' (link in bio) call to action.", status="verified", basis=basis, evidence_ids=ev_ids),
        Observation(statement=f"{plural} of {n} captions "
                    "address the reader with plural 'vi/vaš' forms.", status="verified", basis=basis, evidence_ids=ev_ids),
        Observation(statement="Most frequent hashtags: " + ", ".join(f"#{t} ({c})" for t, c in tags.most_common(6)),
                    status="verified", basis=basis, evidence_ids=ev_ids),
    ]
    by_type: dict[str, list[tuple[str, str]]] = {}
    for p, e in zip(posts, ev_ids):
        by_type.setdefault(p["type"], []).append((p["url"], e))
    names = {"Video": "Video (Reel or feed video; the collected data cannot tell them apart)",
             "Sidecar": "Sidecar (carousel)", "Image": "Image (single photo)"}
    formats = [Observation(statement=f"Post formats over {n} posts: " + ", ".join(
        f"{t} {c} ({c * 100 // n}%)" for t, c in types.most_common()), status="verified", basis=basis,
        evidence_ids=ev_ids, post_urls=[p["url"] for p in posts])]
    formats += [Observation(statement=f"{names.get(t, t)}: {len(h)} of {n} posts ({len(h) * 100 // n}%)",
                            status="verified", basis=basis, evidence_ids=[e for _, e in h], post_urls=[u for u, _ in h])
                for t, h in sorted(by_type.items(), key=lambda kv: -len(kv[1]))]
    seg = {t: tags[t] for t in ("gbwomen", "gbmen", "gbhealthy", "gbfit") if tags[t]}
    audience = [Observation(statement="Content is tagged by the brand's own segments: " +
                            ", ".join(f"#{t} ({c})" for t, c in seg.items()), status="verified", basis=basis,
                            evidence_ids=ev_ids)] if seg else []
    return posts, tone, formats, audience, ex


def _llm_tone(svc, brief, led, posts, fp) -> list[Observation]:
    verified = {i.evidence_id for i in led.items if i.verification_status == "verified"}
    raw = svc.op(
        node="brand_product_analyst", scope=svc.GLOBAL, stage="analyst", fp=fp, suffix="tone", provider=svc.llm.info,
        fn=lambda: svc.llm.structured(ToneAnalysis, task="tone_analysis", payload={
            "brand": brief.brand_name, "evidence_ids": sorted(verified),
            "captions": [extract.untrusted(p["caption"], 400) for p in posts]}).model_dump())
    t = ToneAnalysis.model_validate(raw)
    cited = [e for e in t.cited_evidence_ids if e in verified]
    if not cited:  # an unsupported model claim is dropped, not recorded
        return []
    return [Observation(statement=f"Tone (model-inferred): {', '.join(t.tone_descriptors)}", status="assumption",
                        basis=f"LLM {svc.llm.info.model_id}; cites verified evidence", evidence_ids=cited),
            Observation(statement=f"Audience (model-inferred): {t.audience_summary}", status="assumption",
                        basis=f"LLM {svc.llm.info.model_id}", evidence_ids=cited)]
