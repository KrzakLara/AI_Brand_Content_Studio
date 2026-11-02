"""A VALID campaign plan (schema CampaignPlan/2) built against the real research files, used only to test the machinery.

It is test data: it is never presented as the live planning result and is not stored in plans/.
"""
import copy
import json
from pathlib import Path

from studio.strategy.dossier import build_dossier

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research" / "gymbeam_hr"

QUOTE = "100% Kreatin monohidrat učinkovit je dodatak za povećanje fizičke izvedbe."
DESC = "E-0921eae1"          # verified description of sku 3885 (health/performance wording: NOT usable in copy)
RATING = "E-f34fb0e8"        # verified rating of sku 3885
CAPSULE_RATING = "E-b81dd91f"  # verified rating of a DIFFERENT product (capsules, sku 120100)
PACK = "E-8637dbdb"          # manual observation of the NEW pack
OLD_PACK = "E-df0f1f81"      # OLD pack observation
CROP_PURITY, CROP_IFS = "E-crop-label_purity", "E-crop-badge_ifs"


def dossier():
    return build_dossier(RESEARCH)


def _obs(d, prefix):
    return next(o["id"] for o in d.payload["observations"] if o["statement"].startswith(prefix))


def L(text, *claims):
    return {"text": text, "claim_ids": list(claims)}


def packshot(instructions=("Place the unaltered cut-out in the lower third, 38% of frame width, soft contact shadow, 8% safe margin",)):
    return {"used": True, "packshot_ref": "selected_packshot", "treatment": "unaltered_cutout_composite", "instructions": list(instructions)}


NO_PACK = {"used": False, "packshot_ref": None, "treatment": None, "instructions": []}


def people(kind="none", why="Product and idea carry the post", notes=""):
    return {"appear": kind != "none", "treatment": kind, "rationale": why, "casting_notes": notes}


def slide(n, role, headline, *, body=(), crops=(), callouts=(), visual="Dark ground, large type, orange rule", alt="Tamna kartica s naslovom"):
    return {"n": n, "role": role, "headline": headline, "body": list(body), "label_crops": [{"crop_id": c, "purpose": "unaltered label detail"} for c in crops],
            "callouts": list(callouts), "visual_composition": visual, "people_in_frame": False, "alt_text_hr": alt}


def shot(n, *, product=False, hands=False, sil=False, copy_=(), dur=3):
    pt = "hands" if hands else "faceless_silhouette" if sil else "none"
    return {"n": n, "duration_s": dur, "visual": f"shot {n}", "camera_movement": "slow push-in", "transition_out": "match cut",
            "on_screen_copy": list(copy_), "sound": "room tone", "product_visible": product,
            "product_treatment": "deterministic_composite" if product else "none", "people_in_frame": pt != "none", "people_treatment": pt}


def valid_plan(d=None) -> dict:
    d = d or dossier()
    croatian = _obs(d, "29 of 30 captions are Croatian")
    plural = _obs(d, "22 of 30 captions address")
    basis_v = {"statement": "Captions are Croatian and address the reader as Vi", "status": "verified", "evidence_ids": [croatian, plural]}
    basis_m = {"statement": "Staged product covers exist on the brand feed", "status": "manual", "evidence_ids": ["E-13e05eb8"]}
    basis_a = {"statement": "Audience is Croatian-speaking fitness-minded adults", "status": "assumption", "evidence_ids": []}
    basis_u = {"statement": "Qualitative tone of the brand is not established", "status": "unavailable", "evidence_ids": []}
    return {
        "brand": "GymBeam", "instagram_handle": "gymbeamhr",
        "focal_product": {"sku": "3885", "name": "100% Kreatin Monohidrat - GymBeam"},
        "identity": {
            "campaign_name": "Tihi ritam", "big_idea": "Consistency is quiet", "throughline": "One small daily habit, shown three ways",
            "address_form": "vi_plural", "voice_notes": "Calm, precise, plural Vi", "palette_use": ["#0f0d0d ground", "#ff8c32 accent only"],
            "typography": "Inter bold caps for headlines", "shared_devices": ["dark ground with one orange accent", "single object in a large empty field"],
            "basis": [basis_v, basis_m, basis_u]},
        "claims": [
            {"claim_id": "C1", "text": "Ocjena 4,8 na gymbeam.hr (stanje 27. 10. 2026.)", "claim_type": "rating", "evidence_ids": [RATING],
             "basis_quote": "4.8", "as_of": "2026-10-27"},
            {"claim_id": "C2", "text": "Na pakiranju piše: 100% Pure micronised", "claim_type": "pack_text", "evidence_ids": [CROP_PURITY],
             "basis_quote": "100% Pure micronised", "as_of": None},
            {"claim_id": "C3", "text": "Na stranici proizvoda piše: HPLC Tested, Pure composition", "claim_type": "page_graphic", "evidence_ids": ["E-crop-badge_hplc"],
             "basis_quote": "HPLC Tested", "as_of": None},
            {"claim_id": "C4", "text": "Na stranici proizvoda piše: Produced in an IFS-certified facility", "claim_type": "page_graphic", "evidence_ids": [CROP_IFS],
             "basis_quote": "Produced in an IFS-certified facility", "as_of": None}],
        "deferred_claims": [{"text": QUOTE, "evidence_ids": [DESC], "why_deferred": "performance wording about the product",
                             "review_needed": ["claim-specific compliance review", "uvjeti uporabe (conditions of use)"]}],
        "carousel": {
            "post_id": "01", "objective": "education and saves", "concept_name": "Čitanje pakiranja", "big_idea": "A guided tour of what the real pack prints",
            "creative_device": "real label crops each paired with a typeset callout", "hook": L("Što sve piše na pakiranju?"),
            "narrative_arc": "question -> three real details -> rating -> save",
            "slides": [
                slide(1, "hook", L("Što sve piše na pakiranju?")),
                slide(2, "purity", L("Prvo pročitajte traku"), crops=["label_purity"], callouts=[L("Na pakiranju piše: 100% Pure micronised", "C2")]),
                slide(3, "facility", L("Pogledajte oznaku proizvodnje"), crops=["badge_ifs"], callouts=[L("Na stranici proizvoda piše: Produced in an IFS-certified facility", "C4")]),
                slide(4, "testing", L("Pronađite sitni tisak"), crops=["badge_hplc"], callouts=[L("Na stranici proizvoda piše: HPLC Tested, Pure composition", "C3")]),
                slide(5, "save", L("Spremite za sljedeću kupnju"), callouts=[L("Ocjena 4,8 na gymbeam.hr (stanje 27. 10. 2026.)", "C1")])],
            "save_trigger": "A four-step checklist for reading a pack", "people": people(), "packshot": packshot(),
            "caption_hr": L("Sitni tisak, velika razlika. Spremite objavu. ✨"), "cta": L("Link u opisu profila"), "hashtags": ["gymbeamhr", "gbig"],
            "distinct_from_others": "Typographic and explanatory with real crops; no scene, no storyline, built for saving.", "basis": [basis_v, basis_a]},
        "hero": {
            "post_id": "02", "objective": "product awareness and desirability", "concept_name": "Poluzaslon", "big_idea": "The pack as the only light",
            "creative_device": "one pack lit by a single warm beam on a dark plinth", "headline": L("SVAKA SERIJA POČINJE ODLUKOM."), "supporting_copy": [],
            "art_direction": "Museum-style still, one pack on a dark plinth", "lighting": "Single warm key from camera left, #ff8c32 gel on rim",
            "composition": "Pack on the lower-third line, 60% negative space", "layout": "Headline top-left on 8% margin",
            "background_palette": ["#0f0d0d", "#2d2a2b"], "people": people(), "packshot": packshot(),
            "caption_hr": L("Tišina je također poruka."), "cta": L("Pogledajte u trgovini"), "alt_text_hr": "Vrećica na tamnoj podlozi",
            "hashtags": ["gymbeamhr"], "distinct_from_others": "A single composed still: no steps, no motion, the pack is the whole idea.",
            "basis": [basis_m, basis_a]},
        "reel": {
            "post_id": "03", "objective": "engagement and storytelling", "concept_name": "Ritual u šest kadrova", "big_idea": "A morning told through hands and objects",
            "creative_device": "hands and shadows build the ritual, the pack arrives last", "hook": L("Prije nego grad ustane"),
            "beginning": {"shot_ns": [1, 2], "summary": "Dark kitchen, hands set a glass"}, "development": {"shot_ns": [3, 4], "summary": "Shadow on the wall, light moves"},
            "payoff": {"shot_ns": [5, 6], "summary": "Pack lands in frame, end card"},
            "shots": [shot(1, hands=True), shot(2, hands=True), shot(3, sil=True), shot(4, product=True), shot(5, product=True), shot(6, product=True)],
            "total_duration_s": 18, "pacing": "slow, then a hard cut on the beat",
            "sound_design": {"music": "sparse low pulse", "sfx": ["glass tap"], "voiceover_hr": [], "silence_moments": "shot 4"},
            "product_placement": ["Packshot enters in shot 4 as an unaltered cut-out composite over the counter plate"], "cover_frame": "shot 5",
            "people": people("hands_and_silhouette", "Hands anchor the ritual", "Anonymous faceless hands and a silhouette"),
            "packshot": packshot(), "caption_hr": L("Svako jutro isto. 🌅"), "cta": L("Link u opisu profila"), "alt_text_hr": "Jutarnji ritual",
            "hashtags": ["gymbeamhr", "gbig"], "distinct_from_others": "Moving, narrative, sound-led; the only post with hands and a silhouette.",
            "basis": [basis_m, basis_v]},
        "open_questions": ["Which variant size should be featured? The selected packshot prints none."],
    }


def mutated(fn):
    p = copy.deepcopy(valid_plan())
    fn(p)
    return p


def anthropic_reply(plan: dict, tin=18_000, tout=8_000, stop="tool_use", model="claude-sonnet-5-5") -> dict:
    return dict(method="POST", status=200, content_type="application/json", headers={"request-id": "req_plan_1"},
                body=json.dumps({"id": "msg_p", "model": model, "stop_reason": stop,
                                 "content": [{"type": "tool_use", "id": "tu_1", "name": "respond", "input": plan}],
                                 "usage": {"input_tokens": tin, "output_tokens": tout}}))
