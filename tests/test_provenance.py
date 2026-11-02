"""Phase 3 provenance audit: which pixels of a label crop come from the printed pouch and which from a webshop graphic.

Rules under test: 'Na pakiranju piše' only for text printed on the pouch; 'Na stranici proizvoda piše' for webshop graphics; an uncertain origin
supports neither; tiny printed labels are never "clarified"; slides can be removed/renumbered; attribution corrections are append-only.
"""
import copy
import dataclasses
import json

import pytest
import yaml

from studio.contracts.strategy import CampaignPlan
from studio.strategy import provenance
from studio.strategy.edits import EditError
from studio.strategy.validate import errors, pack_text_audit, validate_plan

from . import strategy_fixtures as sf
from .test_edits import alt, codes, edits_file, gen, item, HERO_CAPTION  # noqa: F401  (gen is a fixture)
from .test_strategy import session


@pytest.fixture(scope="module")
def dos():
    return sf.dossier()


def test_every_crop_has_a_stated_origin_and_the_small_printed_badges_are_documented_as_unusable():
    doc = yaml.safe_load((sf.ROOT / "research" / "imports" / "label_crops_gymbeam_hr.yaml").read_text(encoding="utf-8"))
    assert set(doc["provenance"]["origin_values"]) == {"physical_packaging", "webshop_graphic", "uncertain"}
    by = {c["id"]: c for c in doc["crops"]}
    assert all(c["origin"] in doc["provenance"]["origin_values"] for c in doc["crops"])
    assert [by[i]["origin"] for i in ("label_name", "label_purity")] == ["physical_packaging"] * 2  # pouch print
    assert [by[i]["origin"] for i in ("badge_ifs", "badge_hplc", "badge_lab_tested", "badge_fast_absorption")] == ["webshop_graphic"] * 4
    for i in ("printed_badge_ifs", "printed_badge_hplc"):  # the same badges printed small on the pouch: too small to read, so never a crop
        assert by[i]["origin"] == "physical_packaging" and by[i]["usable"] is False and "legible" in by[i]["exclusion_reason"]
    assert all(c["origin_basis"] for c in doc["crops"] if c["usable"])


def test_pack_text_needs_printed_pouch_text_and_page_text_needs_a_webshop_graphic(dos):
    def as_pack(p):  # slide 3 shows the IFS webshop badge
        p["claims"][3].update(claim_type="pack_text", text="Na pakiranju piše: Produced in an IFS-certified facility")
        p["carousel"]["slides"][2]["callouts"] = [{"text": "Na pakiranju piše: Produced in an IFS-certified facility", "claim_ids": ["C4"]}]
    assert {"pack_text_origin", "pack_text_not_verified"} <= codes(sf.mutated(as_pack), dos)

    def page_on_physical(p):  # 'Na stranici proizvoda piše' on a crop that IS pouch print
        p["claims"][1].update(claim_type="page_graphic", text="Na stranici proizvoda piše: 100% Pure micronised")
        p["carousel"]["slides"][1]["callouts"] = [{"text": "Na stranici proizvoda piše: 100% Pure micronised", "claim_ids": ["C2"]}]
    assert "page_graphic_origin" in codes(sf.mutated(page_on_physical), dos)

    def wrong_prefix(p):
        p["claims"][2]["text"] = "Na pakiranju piše: HPLC Tested, Pure composition"
    assert "claim_prefix" in codes(sf.mutated(wrong_prefix), dos)

    def line_prefix_vs_type(p):
        p["carousel"]["slides"][3]["callouts"] = [{"text": "Na pakiranju piše: HPLC Tested, Pure composition", "claim_ids": ["C3"]}]
    assert "pack_text_not_verified" in codes(sf.mutated(line_prefix_vs_type), dos)
    assert codes(sf.valid_plan(), dos) == set()  # the correct attribution passes


def test_an_uncertain_origin_supports_neither_statement(dos):
    ev = copy.deepcopy(dos.evidence)
    ev["E-crop-badge_ifs"]["structured_value"]["origin"] = "uncertain"
    assert {"page_graphic_origin", "pack_text_not_verified"} & codes(sf.valid_plan(), dataclasses.replace(dos, evidence=ev))
    ev2 = copy.deepcopy(dos.evidence)
    ev2["E-crop-label_purity"]["structured_value"]["origin"] = "uncertain"
    assert {"pack_text_origin", "pack_text_not_verified"} & codes(sf.valid_plan(), dataclasses.replace(dos, evidence=ev2))


def test_alt_text_may_not_claim_packaging_for_a_slide_that_shows_only_a_webshop_graphic(dos):
    assert "alt_origin" in codes(sf.mutated(alt(2, "Izrez okrugle oznake s pakiranja")), dos)  # slide 3 = IFS webshop badge
    assert "alt_origin" in codes(sf.mutated(alt(3, "Okrugla oznaka na pakiranju")), dos)  # slide 4 = HPLC webshop badge
    assert "alt_origin" not in codes(sf.mutated(alt(1, "Izrez trake na pakiranju s tekstom 100% Pure micronised")), dos)  # slide 2 = pouch print


def test_the_real_final_plan_obeys_the_provenance_rules_and_the_reel_caption_is_exact():
    f = sf.ROOT / "plans" / "gymbeam_hr" / "content_plan.json"
    if not f.is_file():
        pytest.skip("plan not exported in this checkout")
    plan = CampaignPlan.model_validate(json.loads(f.read_text(encoding="utf-8"))["campaign"])
    d = sf.dossier()
    assert errors(validate_plan(plan, d)) == []
    assert [s.n for s in plan.carousel.slides] == [1, 2, 3, 4, 5, 6]  # art-direction revision: six mixed-media elements
    for r in pack_text_audit(plan, d):
        assert r["status"].startswith("verified") and (r["statement_type"] == "pack_text") == (r["origins"] == ["physical_packaging"])
    assert plan.reel.caption_hr.text == "Patent, kvaka, vezica. \U0001F3A7 Tri sitna zvuka prije izlaska. A koji je vaš mali ritual prije treninga?"


@pytest.mark.skipif(not (sf.ROOT / "runs" / "research-gymbeam-hr-live").is_dir(), reason="stored packshot not present (runs/ is untracked)")
def test_the_contact_sheet_is_built_from_the_hash_checked_original_and_refuses_another_image(tmp_path):
    img = sf.ROOT / "runs" / "research-gymbeam-hr-live" / "research" / "raw" / "99543edff63b17e3.jpg"
    crops = sf.ROOT / "research" / "imports" / "label_crops_gymbeam_hr.yaml"
    out = provenance.contact_sheet(img, crops, tmp_path / "sheet.png")
    from PIL import Image
    assert out.is_file() and Image.open(out).size[0] > 1000
    other = tmp_path / "other.jpg"
    other.write_bytes(b"not the packshot")
    with pytest.raises(ValueError, match="sha256"):
        provenance.contact_sheet(other, crops, tmp_path / "x.png")


def six_slide_plan():
    p = sf.valid_plan()
    p["carousel"]["slides"].append(sf.slide(6, "extra", sf.L("Dodatni slajd")))
    return p


def test_a_slide_can_be_removed_and_the_rest_renumbered_in_one_atomic_edit(tmp_path):
    s, llm, t = session(tmp_path, [sf.anthropic_reply(six_slide_plan())])
    h1 = s.generate(sf.RESEARCH).paused_at["fingerprint"]
    rm = item("Q1", "01", "slides[3]", "Pronađite sitni tisak", None, op="remove")
    n5 = item("Q2", "01", "n", "5", "4", slide=5)
    n6 = item("Q3", "01", "n", "6", "5", slide=6)
    s.edit(edits_file(tmp_path, h1, [rm, n5, n6]), reason="provenance")
    slides = s.state()["plan"]["campaign"]["carousel"]["slides"]
    assert [x["n"] for x in slides] == [1, 2, 3, 4, 5] and "Pronađite sitni tisak" not in json.dumps(slides, ensure_ascii=False)
    h2 = s.state()["plan"]["fingerprint"]
    with pytest.raises(EditError, match="edited plan"):  # a removal that breaks the slide count or numbering is rejected
        s.edit(edits_file(tmp_path, h2, [item("Q4", "01", "slides[2]", "Pogledajte oznaku proizvodnje", None, op="remove")], "b.yaml"), reason="r")


def test_attribution_corrections_are_append_only_and_must_reproduce_the_applied_text(gen):
    s, h1, tmp = gen
    new = "Tišina govori sama. 🧡 Jedna rečenica više."
    s.edit(edits_file(tmp, h1, [item("E1", "02", "caption_hr.text", HERO_CAPTION, new, proposed="human:Lara")]), reason="r")
    before = json.dumps(s.edit_history())
    seg = [{"text": "Tišina govori sama.", "origin": "human_authored"}, {"text": "🧡", "origin": "ai_proposed"}, {"text": "Jedna rečenica više.", "origin": "human_authored"}]
    c = s.correct_attribution(edit_id=1, item_id="E1", segments=seg, basis="emoji came from the AI-written caption")
    assert c["previously_recorded_authorship"] == "human_authored" and c["corrected_authorship"] == "mixed_ai_proposed_and_human_authored"
    assert json.dumps(s.edit_history()) == before  # the original record is never rewritten
    with pytest.raises(ValueError, match="reproduce"):
        s.correct_attribution(edit_id=1, item_id="E1", segments=seg[:2], basis="x")
    with pytest.raises(ValueError, match="origin"):
        s.correct_attribution(edit_id=1, item_id="E1", segments=[{"text": new, "origin": "lara"}], basis="x")
    with pytest.raises(ValueError, match="no applied edit"):
        s.correct_attribution(edit_id=9, item_id="E1", segments=seg, basis="x")
    out = tmp / "plans"
    s.export(out)
    assert len(json.loads((out / "attribution_corrections.json").read_text(encoding="utf-8"))) == 1


def test_the_recorded_attribution_corrections_of_the_real_plan_reproduce_the_applied_wording():
    f = sf.ROOT / "plans" / "gymbeam_hr" / "attribution_corrections.json"
    h = sf.ROOT / "plans" / "gymbeam_hr" / "edit_history.json"
    if not (f.is_file() and h.is_file()):
        pytest.skip("not exported in this checkout")
    applied = {(e["edit_id"], c["id"]): c["new_value"] for e in json.loads(h.read_text(encoding="utf-8")) for c in e["edits"]}
    for c in json.loads(f.read_text(encoding="utf-8")):
        assert " ".join(s["text"] for s in c["segments"]) == applied[(c["edit_id"], c["edit_item_id"])]
        assert c["corrected_authorship"] == "mixed_ai_proposed_and_human_authored" and c["previously_recorded_authorship"] == "human_authored"
