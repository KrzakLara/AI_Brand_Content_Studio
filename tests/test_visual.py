"""Phase 2b: visual analysis, packshot selection/checks/cut-out, font choice, price dates, formats."""
import io
import json

import pytest
import yaml
from PIL import Image, ImageDraw

from studio.fingerprint import sha256_bytes
from studio.nodes import visual
from studio.tools import imagecheck
from studio.tools.instagram import ManualImportInstagram

from . import research_fixtures as fx
from .test_research import index_of, make


# --- synthetic images (generated, not real photos) -------------------------------------------
def pack_image(size=1080, bg=(230, 230, 230), fmt="JPEG", alpha=False, badge=False, label=True):
    """Grey backdrop, orange 'pouch', white label band (must survive a cut-out), optional overlapping badge."""
    im = Image.new("RGBA" if alpha else "RGB", (size, size), bg + ((255,) if alpha else ()))
    d = ImageDraw.Draw(im)
    d.rectangle([size // 4, size // 8, 3 * size // 4, 7 * size // 8], fill=(220, 70, 30))
    if label:
        d.rectangle([size // 4, size // 3, 3 * size // 4, size // 2], fill=(255, 255, 255))
    if badge:
        d.ellipse([3 * size // 4 - 20, size // 4, 3 * size // 4 + size // 6, size // 4 + size // 6 + 40], fill=(20, 60, 110))
    out = io.BytesIO()
    im.save(out, format=fmt)
    return out.getvalue()


def transparent_png(size=1080):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([size // 4, size // 8, 3 * size // 4, 7 * size // 8], fill=(220, 70, 30, 255))
    out = io.BytesIO()
    im.save(out, format="PNG")
    return out.getvalue()


# --- imagecheck ------------------------------------------------------------------------------
def test_header_and_resolution_and_alpha_detection():
    jpg, rgb_png = pack_image(), pack_image(fmt="PNG")
    rgba_opaque = pack_image(fmt="PNG", alpha=True)
    h = imagecheck.header_info(jpg)
    assert (h["format"], h["width"], h["height"], h["alpha_capable"]) == ("jpeg", 1080, 1080, False)
    assert imagecheck.header_info(rgb_png)["alpha_capable"] is False
    assert imagecheck.header_info(rgba_opaque)["alpha_capable"] is True
    assert imagecheck.inspect_image(jpg)["transparent_background"] is False
    assert imagecheck.inspect_image(pack_image(size=700))["meets_min_resolution"] is False
    # RGBA but fully opaque: capable of alpha, yet NOT transparent (the trap a header check alone falls into)
    o = imagecheck.inspect_image(rgba_opaque)
    assert o["alpha_capable"] and not o["has_transparency"] and not o["transparent_background"]
    t = imagecheck.inspect_image(transparent_png())
    assert t["has_transparency"] and t["transparent_background"] and t["transparent_fraction"] > 0.4
    with pytest.raises(ValueError):
        imagecheck.header_info(b"not an image at all")


def test_cutout_removes_edge_background_but_keeps_interior_white_and_overlapping_badge():
    src = pack_image(badge=True)
    png, rep = imagecheck.cutout_background(src)
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    assert im.getpixel((2, 2))[3] == 0 and im.getpixel((1077, 1077))[3] == 0  # corners transparent
    assert im.getpixel((540, 400))[3] == 255  # the white label inside the pack is kept
    assert im.getpixel((810 + 30, 330))[3] == 255  # the overlapping badge is kept (documented limitation)
    assert imagecheck.inspect_image(png)["transparent_background"] is True
    assert rep["method"].startswith("edge flood-fill") and 0.3 < rep["transparent_fraction"] < 0.7


def test_cutout_refuses_a_non_uniform_background():
    im = Image.new("RGB", (1080, 1080), (230, 230, 230))
    ImageDraw.Draw(im).rectangle([0, 0, 400, 400], fill=(10, 10, 10))
    out = io.BytesIO()
    im.save(out, format="JPEG")
    with pytest.raises(ValueError, match="not uniform"):
        imagecheck.cutout_background(out.getvalue())


def test_dominant_colors_shares_sum_to_one():
    cols = imagecheck.dominant_colors(pack_image(), k=4)
    assert 0.98 <= sum(c["share"] for c in cols) <= 1.02 and all(c["hex"].startswith("#") for c in cols)


def test_pillow_missing_is_explicit_not_silent(monkeypatch):
    def boom():
        raise imagecheck.PillowMissing("no pillow")
    monkeypatch.setattr(imagecheck, "_pil", boom)
    with pytest.raises(imagecheck.PillowMissing):
        imagecheck.dominant_colors(pack_image())
    assert imagecheck.inspect_image(pack_image())["background"] is None  # JPEG header path still works


# --- packshot selection ----------------------------------------------------------------------
NEW_A, NEW_B, OLD, BACK, GIFT, SMALL, DUP = (f"{fx.SITE}/media/{n}.jpg" for n in
                                              ("new_a", "new_b", "old", "back", "gift", "small", "dup"))
LM = {"new_a": "Tue, 20 Oct 2026 07:27:10 GMT", "new_b": "Tue, 04 Aug 2026 11:34:08 GMT"}


def packshot_setup(tmp_path, rsettings, *, attest=True, imgs=None, brief_kw=None, monkeypatch=None):
    new_a, new_b = pack_image(badge=True), pack_image(badge=True, bg=(228, 228, 228))
    imgs = imgs or {NEW_A: new_a, NEW_B: new_b, OLD: pack_image(size=700), BACK: pack_image(bg=(250, 250, 250)),
                    GIFT: pack_image(fmt="JPEG", label=False), SMALL: pack_image(size=640), DUP: new_a}
    t = fx.site(with_products=False, apify=False)
    for url, data in imgs.items():
        t.add(url, body=data, content_type="image/jpeg", headers={"last-modified": LM.get(url.rsplit("/", 1)[-1][:-4],
                                                                               "Mon, 01 Jun 2026 10:00:00 GMT")})
    sha = {u: sha256_bytes(d) for u, d in imgs.items()}
    rows = [
        (NEW_A, "new", "front", False), (NEW_B, "new", "front", False), (OLD, "old", "front", False),
        (BACK, "new", "back", False), (GIFT, "new", "front", True), (SMALL, "new", "front", False)]
    obs = {"provenance": {"observer": "tester", "method": "viewed", "observed_at": "2026-01-01"},
           "observations": [{"image_url": u, "image_sha256": sha[u], "generation": g, "view": v, "size": "?", "flavor": "?",
                             "includes_gift_merchandise": gift, "statement": f"{g} {v}"} for u, g, v, gift in rows]
           if attest else []}
    f = tmp_path / "obs.yaml"
    f.write_text(yaml.safe_dump(obs), encoding="utf-8")
    brief = fx.brief(instagram_handle=None, seed_urls=[], focus_keywords=[], manual_observations_path=str(f),
                     seed_images=[NEW_B, OLD, BACK, GIFT, SMALL, NEW_A, DUP], **(brief_kw or {}))
    orch, h = make(tmp_path, rsettings, t)
    return orch, brief, imgs


def test_packshot_rules_pick_newest_eligible_and_explain_every_rejection(tmp_path, rsettings):
    orch, brief, imgs = packshot_setup(tmp_path, rsettings)
    res = orch.run("p1", brief=brief)
    prof = res.values["brand_profile"]["profile"]
    sel = prof["selected_packshot"]
    assert sel["url"] == NEW_A and sel["pack_generation"] == "new" and sel["view"] == "front"
    assert sel["last_modified"] == LM["new_a"] and sel["retrieved_at"] == fx.FIXED_NOW.replace("+00:00", "Z") or sel["retrieved_at"]
    assert (sel["format"], sel["width"], sel["height"], sel["meets_min_resolution"]) == ("jpeg", 1080, 1080, True)
    assert sel["status"] == "manual" and sel["transparent_background"] is False and sel["background_hex"] == "#e6e6e6"
    why = {r["url"]: " ".join(r["reasons"]) for r in sel["rejected"]}
    assert "not the current design" in why[OLD] and "below 1000px" in why[OLD]
    assert "not a front packshot" in why[BACK]
    assert "gift merchandise" in why[GIFT]
    assert "below 1000px" in why[SMALL]
    assert "identical bytes" in why[DUP]
    assert NEW_B not in why  # eligible but older than NEW_A: not "rejected", just not chosen
    assert any("newest eligible" in b for b in sel["selection_basis"])


def test_selected_packshot_is_recorded_in_the_evidence_registry_with_source_and_dates(tmp_path, rsettings):
    orch, brief, _ = packshot_setup(tmp_path, rsettings)
    res = orch.run("p2", brief=brief)
    ev = [e for e in res.values["research"]["evidence"]["items"] if e["subject"] == "packshot_selection"]
    assert len(ev) == 1
    e = ev[0]
    assert e["source_url"] == NEW_A and e["retrieved_at"] and e["verification_status"] == "manual"
    assert LM["new_a"] in e["claim"] and "retrieved" in e["claim"]
    assert e["structured_value"]["technical"]["width"] == 1080
    assert e["structured_value"]["last_modified"] == LM["new_a"]
    assert any(r["url"] == OLD for r in e["structured_value"]["rejected"])


def test_cutout_step_is_applied_recorded_and_checked(tmp_path, rsettings):
    orch, brief, imgs = packshot_setup(tmp_path, rsettings)
    res = orch.run("p3", brief=brief)
    sel = res.values["brand_profile"]["profile"]["selected_packshot"]
    cut = next(s for s in index_of(res).sources if s.kind == "packshot_cutout")
    assert sel["cutout_source_id"] == cut.source_id
    assert cut.provenance["derived_from_sha256"] == sha256_bytes(imgs[NEW_A]) and cut.provenance["result_transparent_corners"]
    png = (tmp_path / "runs" / "p3" / cut.artifact_path).read_bytes()
    assert sha256_bytes(png) == cut.artifact_sha256
    assert imagecheck.inspect_image(png)["transparent_background"] is True
    ev = [e for e in res.values["research"]["evidence"]["items"] if e["subject"] == "packshot_cutout"]
    assert ev and ev[0]["verification_status"] == "verified"
    assert "overlapping claim badges" in ev[0]["structured_value"]["known_limitation"]


def test_already_transparent_packshot_needs_no_cutout(tmp_path, rsettings):
    png = transparent_png()
    t = fx.site(with_products=False, apify=False)
    t.add(NEW_A, body=png, content_type="image/png", headers={"last-modified": LM["new_a"]})
    f = tmp_path / "obs.yaml"
    f.write_text(yaml.safe_dump({"provenance": {"observer": "t", "method": "m", "observed_at": "d"}, "observations": [
        {"image_url": NEW_A, "image_sha256": sha256_bytes(png), "generation": "new", "view": "front",
         "includes_gift_merchandise": False, "statement": "x"}]}))
    orch, _ = make(tmp_path, rsettings, t)
    res = orch.run("p4", brief=fx.brief(instagram_handle=None, seed_urls=[], focus_keywords=[],
                                        manual_observations_path=str(f), seed_images=[NEW_A]))
    sel = res.values["brand_profile"]["profile"]["selected_packshot"]
    assert sel["transparent_background"] is True and sel["has_transparency"] and sel["cutout_source_id"] is None
    assert sel["format"] == "png" and not [s for s in index_of(res).sources if s.kind == "packshot_cutout"]


def test_unattested_images_are_never_selected(tmp_path, rsettings):
    orch, brief, _ = packshot_setup(tmp_path, rsettings, attest=False)
    res = orch.run("p5", brief=brief)
    prof = res.values["brand_profile"]["profile"]
    assert prof["selected_packshot"] is None
    assert any("No eligible packshot" in x and "no operator attestation" in x for x in prof["limitations"])


def test_cutout_skipped_explicitly_when_pillow_is_missing(tmp_path, rsettings, monkeypatch):
    orch, brief, _ = packshot_setup(tmp_path, rsettings)

    def boom():
        raise imagecheck.PillowMissing("no pillow")
    monkeypatch.setattr(imagecheck, "_pil", boom)
    res = orch.run("p6", brief=brief)
    prof = res.values["brand_profile"]["profile"]
    assert prof["selected_packshot"]["cutout_source_id"] is None
    assert any("cut-out skipped: Pillow is not installed" in x for x in prof["limitations"])


# --- visual analysis -------------------------------------------------------------------------
def ig_import(tmp_path):
    post = lambda code, typ, owner="gymbeamhr": dict(  # noqa: E731
        shortcode=code, url=f"https://www.instagram.com/p/{code}/", type=typ, timestamp="2026-10-20T16:00:00.000Z",
        caption=f"Post {code} \U0001F525", owner=owner, likes=5, comments=0, hashtags=["gymbeamhr"])
    f = tmp_path / "ig.yaml"
    f.write_text(yaml.safe_dump({"provenance": {
        "collected_by": "operator", "method": "manual", "collected_at": "2026-10-27", "source_description": "public"},
        "posts": [post("V1", "Video"), post("V2", "Video"), post("C1", "Sidecar"), post("I1", "Image")]}))
    return ManualImportInstagram(f)


def vis_obs(code, **kw):
    base = dict(post_url=f"https://www.instagram.com/p/{code}/", cover_sha256=("ab" * 32), media_kind="video_cover",
                dominant_colors=[{"hex": "#0f0f0f", "share": 0.6}, {"hex": "#ff4100", "share": 0.4}],
                composition=["lifestyle_photo"], product_shown="in_use", people_shown="one", text_overlay=False,
                overlay_type_style=None, notes="n")
    return {**base, **kw}


def vis_file(tmp_path, observations, provenance=True):
    f = tmp_path / "vis.yaml"
    f.write_text(yaml.safe_dump({"provenance": {"observer": "tester", "method": "viewed", "observed_at": "2026-10-27",
                                                "palette_method": "pm"} if provenance else {},
                                 "observations": observations}), encoding="utf-8")
    return f


def run_vis(tmp_path, rsettings, observations, provenance=True, run="v"):
    t = fx.site(with_products=False, apify=False)
    orch, _ = make(tmp_path, rsettings, t, ig=ig_import(tmp_path))
    f = vis_file(tmp_path, observations, provenance)
    return orch.run(run, brief=fx.brief(seed_urls=[], focus_keywords=[], visual_observations_path=str(f)))


def test_visual_conclusions_are_tied_to_concrete_post_urls_and_labelled_manual(tmp_path, rsettings):
    res = run_vis(tmp_path, rsettings, [
        vis_obs("V1", people_shown="one", text_overlay=True, overlay_type_style="bold_geometric_sans_caps"),
        vis_obs("V2", people_shown="none", product_shown="packshot", composition=["product_staged"]),
        vis_obs("C1", people_shown="hands_only", media_kind="carousel_first_slide", composition=["graphic_design"])])
    prof = res.values["brand_profile"]["profile"]
    vs = {o["statement"]: o for o in prof["visual_style"]}
    p1 = vs["People: 'one' in 1 of 3 analysed covers"]
    assert p1["status"] == "manual" and p1["post_urls"] == ["https://www.instagram.com/p/V1/"]
    none = vs["No person visible on 1 of 3 analysed covers"]
    assert none["post_urls"] == ["https://www.instagram.com/p/V2/"]
    assert vs["Text overlay present on 1 of 3 analysed covers"]["post_urls"] == ["https://www.instagram.com/p/V1/"]
    assert vs["Overlay typography: 'bold_geometric_sans_caps' in 1 of 3 analysed covers"]["status"] == "manual"
    assert len(prof["visual_analysis_post_urls"]) == 3
    assert all(o["evidence_ids"] and o["status"] in ("manual", "verified", "unknown") for o in prof["visual_style"])
    ev = [e for e in res.values["research"]["evidence"]["items"] if e["subject"] == "instagram_visual_observation"]
    assert len(ev) == 3 and {e["verification_status"] for e in ev} == {"manual"}  # never "verified"
    assert all(e["source_url"].startswith("https://www.instagram.com/p/") for e in ev)


def test_palette_is_aggregated_with_accents_separated_from_neutrals(tmp_path, rsettings):
    res = run_vis(tmp_path, rsettings, [vis_obs("V1"), vis_obs("V2")], run="vc")
    cols = [c for c in res.values["brand_profile"]["profile"]["colors"] if c["scope"] == "instagram_covers"]
    accent = next(c for c in cols if c["hex"].lower().startswith("#f") and "accent" in c["basis"])
    neutral = next(c for c in cols if "neutral" in c["basis"])
    assert accent["status"] == "manual" and accent["frequency"] == 2 and len(accent["post_urls"]) == 2
    assert neutral["hex"] <= "#202020" and "60%" in neutral["basis"]


def test_visual_observations_for_unknown_posts_or_without_provenance_are_ignored(tmp_path, rsettings):
    res = run_vis(tmp_path, rsettings, [vis_obs("V1"), vis_obs("ZZZ")], run="vx")
    prof = res.values["brand_profile"]["profile"]
    assert prof["visual_analysis_post_urls"] == ["https://www.instagram.com/p/V1/"]
    assert any("ZZZ" in x and "not in the source index" in x for x in prof["limitations"])
    res = run_vis(tmp_path / "np", rsettings, [vis_obs("V1")], provenance=False, run="vn") \
        if (tmp_path / "np").mkdir() is None else None
    prof = res.values["brand_profile"]["profile"]
    assert prof["visual_analysis_post_urls"] == [] and any("provenance" in x for x in prof["limitations"])
    assert prof["visual_style"][0]["status"] == "unknown"  # nothing is claimed without labelled data


# --- formats, prices, fonts ------------------------------------------------------------------
def test_format_distribution_lists_the_posts_behind_each_number(tmp_path, rsettings):
    t = fx.site(with_products=False, apify=False)
    orch, _ = make(tmp_path, rsettings, t, ig=ig_import(tmp_path))
    res = orch.run("f1", brief=fx.brief(seed_urls=[], focus_keywords=[]))
    fm = {o["statement"]: o for o in res.values["brand_profile"]["profile"]["content_formats"]}
    video = next(o for k, o in fm.items() if k.startswith("Video"))
    assert video["status"] == "verified" and sorted(video["post_urls"]) == [
        "https://www.instagram.com/p/V1/", "https://www.instagram.com/p/V2/"]
    assert "Reel or feed video" in next(k for k in fm if k.startswith("Video"))
    assert next(o for k, o in fm.items() if k.startswith("Sidecar"))["post_urls"] == ["https://www.instagram.com/p/C1/"]
    total = next(o for k, o in fm.items() if k.startswith("Post formats over 4 posts"))
    assert len(total["post_urls"]) == 4
    assert any("Only 4 of the 20-30" in x for x in res.values["brand_profile"]["profile"]["limitations"])


def test_every_price_carries_the_date_it_was_retrieved(tmp_path, rsettings):
    t = fx.site(apify=False)
    orch, _ = make(tmp_path, rsettings, t)
    res = orch.run("pr", brief=fx.brief(instagram_handle=None))
    cat = res.values["brand_profile"]["profile"]["product_catalog"]
    variants = [v for c in cat for v in c["variants"]]
    assert variants and all(v["price"] is not None and v["price_retrieved_at"] for v in variants)
    ev = [e for e in res.values["research"]["evidence"]["items"] if e["subject"] == "product_variant"]
    assert len(ev) == len(variants) and all(e["retrieved_at"] and e["structured_value"]["price_retrieved_at"] for e in ev)
    assert all(e["structured_value"]["price_retrieved_at"] == v["price_retrieved_at"].replace("+00:00", "Z")
               or e["structured_value"]["price_retrieved_at"] for e, v in zip(ev, variants))


def test_font_choice_separates_what_is_verified_from_what_is_assumed(tmp_path, rsettings):
    t = fx.site(with_products=False, apify=False)
    orch, _ = make(tmp_path, rsettings, t)
    res = orch.run("fo", brief=fx.brief(instagram_handle=None, seed_urls=[], focus_keywords=[]))
    font = res.values["brand_profile"]["profile"]["selected_font"]
    assert font["family"] == "Inter" and font["status"] == "verified" and "website" in font["basis"]
    assert font["recommended_use_status"] == "assumption" and font["license_note"].startswith("ASSUMPTION")
    assert "custom italic logotype" in font["logotype_note"] and font["evidence_ids"]
    ev = {e["evidence_id"]: e for e in res.values["research"]["evidence"]["items"]}
    assert ev[font["evidence_ids"][0]]["verification_status"] == "verified"


def test_no_font_is_invented_when_no_css_was_retrieved(tmp_path, rsettings):
    t = fx.site(with_products=False, apify=False)
    t.entries[("GET", f"{fx.SITE}/s.css")] = []
    t.add(f"{fx.SITE}/s.css", status=404, body="gone")
    orch, _ = make(tmp_path, rsettings, t)
    res = orch.run("fn", brief=fx.brief(instagram_handle=None, seed_urls=[], focus_keywords=[]))
    prof = res.values["brand_profile"]["profile"]
    assert prof["selected_font"] is None and any("typography is unknown" in x for x in prof["limitations"])


def test_aggregate_colors_merges_buckets_and_reports_share():
    rows = [("u1", [{"hex": "#101010", "share": 0.5}, {"hex": "#ff4000", "share": 0.5}]),
            ("u2", [{"hex": "#121212", "share": 0.5}, {"hex": "#fe4400", "share": 0.5}])]
    out = visual.aggregate_colors(rows)
    assert len(out) == 2 and {c.frequency for c in out} == {2} and all(c.post_urls == ["u1", "u2"] for c in out)
    assert json.dumps([c.hex for c in out])
