"""Build the planner's research dossier from the verified research assets (never from the Haiku run alone).

The dossier is the ONLY research the content planner sees. Every item keeps its verification status
(verified / manual / assumption / unknown) so the model, the validator and the human reviewer can tell them apart.
Captions and page text are third-party data: the adapter wraps the whole payload in <data> and the prompt
forbids obeying anything inside it.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from studio.fingerprint import fingerprint, sha256_file

FOCAL_SKU = "3885"
FOCAL_NAME = "100% Kreatin Monohidrat - GymBeam"
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")
CAPTION_CHARS = 220


@dataclass
class Dossier:
    payload: dict  # exactly what is sent to the model
    evidence: dict  # evidence_id -> full registry item (not sent in full)
    obs_evidence: dict  # O-id -> list of evidence ids it summarises
    family: dict  # evidence_id -> product family sku
    hexes: set  # colours the research actually contains
    hashtags: set  # hashtags actually used by the brand
    crops: dict  # usable label crops of the selected original packshot: id -> crop
    constraints: dict  # human decisions from the canonical brief (locked copy, confirmed product)
    selected_variant: dict  # what the selected packshot establishes (flavour yes, size no)
    packshot: dict  # provenance of the selected original packshot (added to the plan by code)
    fingerprint: str = ""
    problems: list = field(default_factory=list)


def _family_map(profile: dict) -> dict:
    fam: dict = {}
    for p in profile.get("product_catalog", []):
        for e in p.get("evidence_ids", []):
            fam[e] = p["sku"]
        for v in p.get("variants", []):
            fam[v["evidence_id"]] = p["sku"]
        for o in p.get("packaging_observations", []):
            fam[o["evidence_id"]] = p["sku"]
    return fam


def _text(e: dict) -> str:
    s = e["subject"]
    if s == "product_description":
        return e["quote"]
    if s == "instagram_post":
        return f"{e['claim']} | caption starts: {' '.join(e['quote'].split())[:CAPTION_CHARS]} | hashtags: {e['structured_value'].get('hashtags')}"
    return e["claim"]


def _load_brief(research_dir: Path, brief_path):
    """Canonical brief (human decisions). 'auto' = <repo>/briefs/gymbeam_hr.yaml next to the research folder, if present."""
    from studio.contracts import BriefInput
    path = Path(research_dir).parents[1] / "briefs" / "gymbeam_hr.yaml" if brief_path == "auto" else brief_path
    if not path or not Path(path).is_file():
        return None, None
    return BriefInput.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8"))), Path(path)


def build_dossier(research_dir: Path, *, artifact_root: Path | None = None, brief_path="auto") -> Dossier:
    research_dir = Path(research_dir)
    brief, brief_file = _load_brief(research_dir, brief_path)
    profile = json.loads((research_dir / "brand_profile.json").read_text(encoding="utf-8"))
    registry = {i["evidence_id"]: i for i in json.loads(
        (research_dir / "evidence_registry.json").read_text(encoding="utf-8"))["items"]}
    sources = {s["source_id"]: s for s in json.loads(
        (research_dir / "source_index.json").read_text(encoding="utf-8"))["sources"]}
    family = _family_map(profile)

    observations, obs_ev = [], {}

    def add_obs(group: str, items: list[dict]):
        for it in items:
            oid = f"O{len(observations) + 1}"
            ids = it.get("evidence_ids", [])
            obs_ev[oid] = list(ids)
            observations.append({"id": oid, "group": group, "statement": it["statement"], "status": it["status"],
                                 "evidence_count": len(ids), "sample_evidence_ids": ids[:3]})
    for g in ("identity", "communication_tone", "audience", "content_formats", "assumptions"):
        add_obs(g, profile.get(g, []))
    add_obs("visual_style", [v for v in profile.get("visual_style", []) if not v["statement"].startswith("Palette is computed")])

    evidence = []
    for eid, e in registry.items():
        if e["subject"] in ("product_variant", "product_rating") and family.get(eid) != FOCAL_SKU:
            continue  # other creatine products: sizes/ratings are noise for the planner (their descriptions stay, as 'not the focal product')
        evidence.append({"id": eid, "subject": e["subject"], "status": e["verification_status"],
                         "sku_family": family.get(eid), "text": _text(e),
                         **({"retrieved_at": e["retrieved_at"][:10]} if e["subject"] in ("product_rating", "product_variant", "product_description") else {})})

    colors = profile.get("colors", [])
    hexes = {c["hex"].lower() for c in colors}
    for rel in (brief.extra_evidence_paths if brief else []):  # focused research on another product: evidence items and the colours it may use
        xdoc = yaml.safe_load((Path(brief_file).parents[1] / rel).read_text(encoding="utf-8"))
        hexes |= {c["hex"].lower() for c in xdoc.get("colors", [])}
        for x in xdoc["evidence"]:
            registry[x["id"]] = {"evidence_id": x["id"], "claim": x["claim"], "source_id": "colla-page", "quote": x["quote"], "confidence": 0.9, "mock": False,
                                 "origin": "manual_import", "subject": x["subject"], "source_url": xdoc["provenance"]["page_url"],
                                 "retrieved_at": xdoc["provenance"]["retrieved_at"], "verification_status": x["status"],
                                 "verification_note": x.get("note", "re-found in the stored, hash-checked official product page"), "packaging_variant": None,
                                 "structured_value": {"page_sha256": xdoc["provenance"]["page_sha256"]}}
            evidence.append({"id": x["id"], "subject": x["subject"], "status": x["status"], "sku_family": None, "text": x["claim"] + " | " + x["quote"]})
    hashtags = set()
    for e in registry.values():
        if e["subject"] == "instagram_post":
            hashtags |= {h.lower() for h in e["structured_value"].get("hashtags", [])}

    ps = profile["selected_packshot"]
    src, cut = sources[ps["source_id"]], sources[ps["cutout_source_id"]]
    root = Path(artifact_root) if artifact_root else None
    on_disk = {}
    if root:
        for label, s in (("original", src), ("cutout", cut)):
            p = root / s["artifact_path"]
            on_disk[label] = bool(p.is_file() and sha256_file(p) == s["artifact_sha256"])
    packshot = {"original_source_id": src["source_id"], "original_url": src["url"], "original_sha256": src["artifact_sha256"],
                "original_run_path": src["artifact_path"], "cutout_source_id": cut["source_id"],
                "cutout_sha256": cut["artifact_sha256"], "cutout_run_path": cut["artifact_path"],
                "pack_generation": ps["pack_generation"], "evidence_ids": [ps["evidence_id"], "E-5af7d045"],
                "status": "manual (operator-attested selection); cut-out is a mechanical edge flood-fill",
                "known_limitation": ps["cutout"]["known_limitation"],
                "file_hash_verified_on_disk": on_disk or "not checked"}

    typography = {"website_text_face": profile["selected_font"]["family"], "status": profile["selected_font"]["status"],
                  "overlay_style_observed": "bold geometric sans in capitals / bold sans sentence case (manual, 14 covers)",
                  "logotype": profile["selected_font"]["logotype_note"], "licence": profile["selected_font"]["license_note"]}
    conf = brief.confirmed_focal_product if brief else None
    focal_confirmed = bool(conf and conf.sku == FOCAL_SKU)
    crops, crops_excluded = {}, []
    crops_file = (Path(brief_file).parents[1] / brief.label_crops_path) if brief and brief.label_crops_path else None
    if crops_file and crops_file.is_file():
        cdoc = yaml.safe_load(crops_file.read_text(encoding="utf-8"))
        if cdoc["provenance"]["source_sha256"] != src["artifact_sha256"]:
            raise ValueError("label_crops file does not describe the selected packshot (sha256 differs)")
        for c in cdoc["crops"]:
            if c["origin"] not in ("physical_packaging", "webshop_graphic", "uncertain"):
                raise ValueError(f"crop {c['id']}: unknown origin {c['origin']!r}")
            if c["usable"] and c["origin"] != "uncertain":  # an uncertain origin can be neither "on the packaging" nor "on the product page"
                crops[c["id"]] = {"id": c["id"], "shows": c["shows"], "printed_text": c["printed_text"], "box": c["box"], "origin": c["origin"],
                                  "origin_basis": c["origin_basis"], "max_upscale": c["max_upscale"], "status": "manual (operator-labelled)"}
            else:
                crops_excluded.append({"id": c["id"], "origin": c["origin"], "reason": c.get("exclusion_reason", "origin uncertain")})
    for cid, c in crops.items():  # printed text of a crop = manual evidence tied to the stored original image (callouts may cite it)
        what = ("Printed on the selected NEW pack (crop {cid}): " if c["origin"] == "physical_packaging"
                else "Graphic badge placed around the pack in the official webshop product image, NOT printed packaging (crop {cid}): ").format(cid=cid)
        registry[f"E-crop-{cid}"] = {
            "evidence_id": f"E-crop-{cid}", "claim": what + "; ".join(c["printed_text"]),
            "source_id": src["source_id"], "quote": " | ".join(c["printed_text"]), "confidence": 0.8, "mock": False, "origin": "manual_import",
            "subject": "label_crop", "source_url": src["url"], "retrieved_at": src["retrieved_at"], "verification_status": "manual",
            "verification_note": "operator-labelled by viewing the stored original image", "packaging_variant": None,
            "structured_value": {"crop_box": c["box"], "image_sha256": src["artifact_sha256"], "origin": c["origin"], "origin_basis": c["origin_basis"]}}
        evidence.append({"id": f"E-crop-{cid}", "subject": "label_crop", "status": "manual", "sku_family": None,
                         "text": registry[f"E-crop-{cid}"]["claim"]})
    selected_variant = {"flavour": "bez okusa (Unflavoured), as printed on the selected packshot", "size_g": None,
                        "basis": "the selected packshot is the current unflavoured pack and prints NO weight; which size ships with which pack "
                                 "generation is unverified, so no quantity can be matched to it",
                        "rule": "no quantities (grams, servings, doses, scoops) anywhere in copy"}
    constraints = {"hero_headline": (brief.locked_copy.get("hero_headline") if brief else None),
                   "rules": list(brief.campaign_constraints) if brief else []}
    payload = {
        "frame": {
            "brand": profile["brand_name"], "instagram_handle": "gymbeamhr", "market": "Croatia (hr)",
            "focal_product": {"sku": FOCAL_SKU, "name": FOCAL_NAME,
                              "basis": (f"CONFIRMED by the human on {conf.confirmed_on} (canonical brief briefs/gymbeam_hr.yaml)" if focal_confirmed
                                        else "NOT confirmed in a brief: treat as an operator assumption")},
            "selected_variant": selected_variant,
            "human_constraints": constraints,
            "deliverable": "ONE Instagram mini-campaign of exactly three posts: carousel (educational), hero image (product), reel (storytelling)",
            "snapshot": "prices, ratings and availability are snapshots from 2026-10-27; never put a price in copy",
            "other_creatine_products_exist": "capsules (sku 120100, 3000 mg), Creapure, tabs, pink creatine: NOT the focal product; their facts must not be attributed to it",
        },
        "status_legend": "verified = re-found in a stored, hash-checked source; manual = labelled by the operator/a human reviewer "
                         "(14 Instagram covers viewed at thumbnail scale, packaging photos), NOT machine-verified; assumption; unknown = not determined",
        "observations": observations,
        "evidence": evidence,
        "palette": [{"hex": c["hex"], "scope": c["scope"], "basis": c["basis"][:90], "status": c["status"]} for c in colors],
        "typography": typography,
        "selected_packshot": {k: packshot[k] for k in ("original_source_id", "cutout_source_id", "pack_generation", "status", "known_limitation")}
                             | {"printed_on_the_image": "the image itself carries manufacturer badges incl. 'Quality guaranteed' and 'Fast absorption / Rapid effect'; "
                                "they come with the unaltered pack image and are NOT campaign statements - list this under open_questions for the human"},
        "label_crops": list(crops.values()),
        "label_crops_excluded": crops_excluded,
        "brand_hashtags_observed": sorted(hashtags),
        "limitations": profile.get("limitations", []),
    }
    d = Dossier(payload, registry, obs_ev, family, hexes, hashtags, crops, constraints, selected_variant, packshot)
    d.fingerprint = fingerprint(payload, packshot)
    return d
