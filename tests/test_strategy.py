"""Phase 3: content strategy, evidence integrity, human approval, revision. Recorded transports only: no network, no credits.

The plans below are TEST DATA (tests/strategy_fixtures.py). The real planning results are produced live and stored in plans/.
"""
import json
import shutil

import pytest
import yaml
from pydantic import ValidationError

from studio import cli
from studio.config import load_settings
from studio.contracts import BriefInput, Gate
from studio.contracts.strategy import CampaignPlan
from studio.cost import BudgetExceeded
from studio.nodes.planner_live import PlanInvalid
from studio.providers.base import ProviderResponseError
from studio.providers.live import ANTHROPIC_URL, AnthropicLLM, RequestLimitExceeded
from studio.strategy.dossier import build_dossier
from studio.strategy.validate import errors, validate_plan
from studio.strategy.workflow import NotAuthorised, PlanSession
from studio.tools.transport import GuardedTransport, RecordedTransport

from . import strategy_fixtures as sf

KEY = "sk-test-NOT-A-REAL-KEY-0123456789"
SETTINGS = load_settings(sf.ROOT / "config.yaml")


@pytest.fixture(scope="module")
def dos():
    return sf.dossier()


def codes(plan_dict, dos, *, flags=False):
    ps = validate_plan(CampaignPlan.model_validate(plan_dict), dos)
    return {p.code for p in (ps if flags else errors(ps))}


# ---------------------------------------------------------------------------------- structure / schema
def test_the_fixture_plan_is_valid_and_has_exactly_three_distinct_posts(dos):
    plan = CampaignPlan.model_validate(sf.valid_plan(dos))
    assert errors(validate_plan(plan, dos)) == []
    cp = plan.to_content_plan()
    assert [p.post_id for p in cp.posts] == ["01", "02", "03"]
    assert [p.format.value for p in cp.posts] == ["carousel", "hero", "reel"]
    assert len({p.hook for p in cp.posts}) == 3 and all(p.evidence_ids for p in cp.posts)


@pytest.mark.parametrize("drop", ["carousel", "hero", "reel"])
def test_a_plan_without_one_of_the_three_posts_is_not_valid_structured_output(drop):
    p = sf.valid_plan()
    del p[drop]
    with pytest.raises(ValidationError):
        CampaignPlan.model_validate(p)


def test_extra_posts_unknown_fields_and_missing_decisions_are_refused():
    p = sf.valid_plan()
    p["fourth_post"] = {}
    with pytest.raises(ValidationError):
        CampaignPlan.model_validate(p)
    for post in ("carousel", "hero", "reel"):
        p = sf.valid_plan()
        del p[post]["people"]
        with pytest.raises(ValidationError):
            CampaignPlan.model_validate(p)
    p = sf.valid_plan()
    p["hero"]["packshot"] = {"used": True, "packshot_ref": None, "treatment": None, "instructions": []}
    with pytest.raises(ValidationError, match="packshot_ref"):
        CampaignPlan.model_validate(p)
    p = sf.valid_plan()
    p["reel"]["people"]["treatment"] = "none"  # appear=true but treatment none
    with pytest.raises(ValidationError, match="treatment"):
        CampaignPlan.model_validate(p)


# ---------------------------------------------------------------------------------- claim / evidence integrity
def test_unknown_evidence_ids_are_rejected(dos):
    assert "unknown_evidence" in codes(sf.mutated(lambda p: p["claims"][0].update(evidence_ids=["E-doesnotexist"])), dos)
    assert "unknown_evidence" in codes(sf.mutated(lambda p: p["carousel"]["basis"][0].update(evidence_ids=["E-nope"])), dos)
    assert "unknown_evidence" in codes(sf.mutated(lambda p: p["deferred_claims"][0].update(evidence_ids=["E-nope"])), dos)


def test_a_basis_quote_that_is_not_in_the_evidence_is_rejected(dos):
    assert "basis_quote" in codes(sf.mutated(lambda p: p["claims"][1].update(basis_quote="100% Pure and strong")), dos)


def test_facts_of_a_different_product_and_unverified_or_old_pack_evidence_are_rejected(dos):
    assert "wrong_product" in codes(sf.mutated(lambda p: p["claims"][0].update(evidence_ids=[sf.CAPSULE_RATING], as_of="2026-10-27")), dos)
    assert "claim_type" in codes(sf.mutated(lambda p: p["claims"][0].update(evidence_ids=[sf.PACK], basis_quote="Made in Germany", text="x")), dos)
    assert "pack_text_origin" in codes(sf.mutated(lambda p: p["claims"][1].update(evidence_ids=[sf.OLD_PACK], basis_quote="NET WT. 250 g")), dos)  # the OLD pack is not the selected one


def test_numbers_dates_and_snapshot_are_checked_but_croatian_formats_pass(dos):
    assert "number_unsupported" in codes(sf.mutated(lambda p: p["claims"][0].update(text="Ocjena 4,9 na gymbeam.hr")), dos)
    assert "rating_date" in codes(sf.mutated(lambda p: p["claims"][0].update(as_of="2026-01-01")), dos)

    def thousands(p):  # 8.291 (hr thousands separator) == 8291 in the registry
        p["claims"][0]["text"] = "Ocjena 4,8 iz 8.291 recenzija (stanje 27. 10. 2026.)"
        p["carousel"]["slides"][4]["callouts"][0]["text"] = "Ocjena 4,8 iz 8.291 recenzija (stanje 27. 10. 2026.)"
    assert "number_unsupported" not in codes(sf.mutated(thousands), dos)


# ---------------------------------------------------------------------------------- contextual claim screening
def test_health_wording_about_the_product_is_rejected_anywhere_but_the_same_word_elsewhere_is_only_flagged(dos):
    def about_product(p):
        p["hero"]["caption_hr"] = {"text": "Kreatin za bolju izvedbu.", "claim_ids": []}
    assert {"health_claim_in_copy", "unsupported_comparative"} & codes(sf.mutated(about_product), dos)

    def elsewhere(p):
        p["reel"]["caption_hr"] = {"text": "Mirna energija jutra. 🌅", "claim_ids": []}
    assert "health_claim_in_copy" not in codes(sf.mutated(elsewhere), dos)
    assert "health_term_context" in codes(sf.mutated(elsewhere), dos, flags=True)  # shown to the reviewer, not blocking


def test_product_page_health_sentences_are_never_reused_and_claims_cannot_carry_health_wording(dos):
    def reuse(p):  # the old plan's C1 inside the hero
        p["hero"]["supporting_copy"] = [{"text": "učinkovit je dodatak za povećanje fizičke izvedbe", "claim_ids": []}]
    assert "verbatim_product_claim" in codes(sf.mutated(reuse), dos)

    def as_claim(p):
        p["claims"][1].update(text="Na pakiranju piše: 100% Pure micronised za bolju izvedbu")
    assert "health_claim_not_publishable" in codes(sf.mutated(as_claim), dos)
    assert "deferred_review" in codes(sf.mutated(lambda p: p["deferred_claims"][0].update(review_needed=["pravni pregled"])), dos)

    def use_deferred(p):  # deferred wording must not leak into copy
        p["reel"]["shots"][0]["on_screen_copy"] = [{"text": "dodatak za povećanje fizičke izvedbe svaki dan", "claim_ids": []}]
    assert {"verbatim_product_claim", "health_claim_in_copy"} & codes(sf.mutated(use_deferred), dos)


def test_novelty_and_comparative_words_are_contextual_not_banned_globally(dos):
    def ordinary(p):
        p["reel"]["hook"] = {"text": "Prije nego počne novi dan", "claim_ids": []}
    assert codes(sf.mutated(ordinary), dos) == set()  # 'novi dan' is ordinary Croatian
    assert "novelty_word_context" in codes(sf.mutated(ordinary), dos, flags=True)
    for bad in ("Novo pakiranje kreatina", "Najbolji kreatin", "Napredniji proizvod za vas"):
        def f(p, bad=bad):
            p["hero"]["caption_hr"] = {"text": bad, "claim_ids": []}
        assert {"unverified_new_pack", "unsupported_comparative"} & codes(sf.mutated(f), dos), bad


def test_numbers_prices_quantities_guarantees_and_informal_address_are_rejected(dos):
    cases = {
        "number_unbacked": lambda p: p["hero"].update(caption_hr={"text": "5 minuta tišine", "claim_ids": []}),
        "price": lambda p: p["hero"].update(caption_hr={"text": "Samo uz popust od 10 €", "claim_ids": ["C1"]}),
        "quantity": lambda p: p["hero"].update(caption_hr={"text": "Jedna mjerica svaki dan", "claim_ids": []}),
        "forbidden": lambda p: p["hero"].update(caption_hr={"text": "Zajamčeni rezultati", "claim_ids": []}),
        "address": lambda p: p["hero"].update(caption_hr={"text": "Ti to možeš", "claim_ids": []}),
        "unknown_claim": lambda p: p["hero"].update(caption_hr={"text": "Jedno", "claim_ids": ["C99"]}),
    }
    for want, mutate in cases.items():
        assert want in codes(sf.mutated(mutate), dos), want
    assert "quantity" in codes(sf.mutated(lambda p: p["hero"].update(caption_hr={"text": "Vrećica od 500 g", "claim_ids": []})), dos)


def test_unused_claims_palette_and_hashtags_are_checked(dos):
    def unused(p):
        p["claims"].append({"claim_id": "C5", "text": "Ocjena 4,8 na gymbeam.hr", "claim_type": "rating", "evidence_ids": [sf.RATING],
                            "basis_quote": "4.8", "as_of": "2026-10-27"})
    assert "claim_unused" in codes(sf.mutated(unused), dos, flags=True) and "claim_unused" not in codes(sf.mutated(unused), dos)
    assert "palette" in codes(sf.mutated(lambda p: p["hero"].update(background_palette=["#0f0d0d", "#123456"])), dos)
    assert "hashtag" in codes(sf.mutated(lambda p: p["hero"].update(hashtags=["fitnessmotivation"])), dos)


def test_basis_labels_must_not_overclaim_but_underclaiming_is_only_a_flag(dos):
    assert "basis_status" in codes(sf.mutated(lambda p: p["hero"]["basis"].__setitem__(0, {"statement": "x", "status": "verified", "evidence_ids": ["E-13e05eb8"]})), dos)
    assert "basis_status" in codes(sf.mutated(lambda p: p["hero"]["basis"].__setitem__(0, {"statement": "x", "status": "unavailable", "evidence_ids": ["E-13e05eb8"]})), dos)
    under = sf.mutated(lambda p: p["hero"]["basis"].__setitem__(0, {"statement": "x", "status": "manual", "evidence_ids": ["E-8e56e0ab"]}))
    assert "basis_status" not in codes(under, dos) and "basis_label" in codes(under, dos, flags=True)


# ---------------------------------------------------------------------------------- product protection, labels, people
def test_label_crops_must_exist_and_verified_facts_must_be_separate_callouts(dos):
    assert "label_crop" in codes(sf.mutated(lambda p: p["carousel"]["slides"][1]["label_crops"].append({"crop_id": "badge_fast_absorption", "purpose": "x"})), dos)
    assert "label_crop" in codes(sf.mutated(lambda p: p["carousel"]["slides"][1]["label_crops"].append({"crop_id": "made_in_germany", "purpose": "x"})), dos)

    def fact_in_body(p):
        p["carousel"]["slides"][3]["body"] = [{"text": "Na stranici proizvoda piše: HPLC Tested, Pure composition", "claim_ids": ["C3"]}]
    assert "fact_not_callout" in codes(sf.mutated(fact_in_body), dos)


def test_redrawn_or_imagined_packaging_is_rejected_but_negated_instructions_pass(dos):
    def redraw(p):
        p["carousel"]["slides"][0]["visual_composition"] = "Dvije grafičke vrećice kao ilustracija pakiranja u sivoj boji"
    assert "packaging_redraw" in codes(sf.mutated(redraw), dos)

    def negated(p):
        p["carousel"]["slides"][0]["visual_composition"] = "Tamna ploha; pakiranje se nikada ne crta niti ilustrira"
    assert "packaging_redraw" not in codes(sf.mutated(negated), dos)


def test_reel_people_rules_protect_the_product(dos):
    assert "people" in codes(sf.mutated(lambda p: p["reel"].update(people=sf.people())), dos)  # human asked for hands/silhouettes

    def hands_with_pack(p):
        p["reel"]["shots"][3].update(people_in_frame=True, people_treatment="hands")
        p["reel"]["people"] = sf.people("hands_and_silhouette", "x", "faceless")
    assert "product_protection" in codes(sf.mutated(hands_with_pack), dos)

    def sil_with_pack(p):  # a distant faceless silhouette may share a shot with the composite
        p["reel"]["shots"][3].update(people_in_frame=True, people_treatment="faceless_silhouette")
    assert "product_protection" not in codes(sf.mutated(sil_with_pack), dos)

    def untreated(p):
        p["reel"]["shots"][3]["product_treatment"] = "none"
    assert "product_protection" in codes(sf.mutated(untreated), dos)

    def everyone(p):
        for s in p["reel"]["shots"]:
            s.update(people_in_frame=True, people_treatment="hands", product_visible=False, product_treatment="none")
        p["reel"]["people"] = sf.people("hands_only", "x", "faceless")
    assert "people" in codes(sf.mutated(everyone), dos)
    assert "people" in codes(sf.mutated(lambda p: p["hero"].update(people=sf.people("hands_only", "x", "hands"))), dos)


def test_alt_text_may_transcribe_crop_text_but_other_numerals_still_need_a_claim(dos):
    def on_crop(p):  # slide 2 shows the crop 'label_purity' (100% Pure micronised)
        p["carousel"]["slides"][1]["alt_text_hr"] = "Izrez trake pakiranja s tekstom 100% Pure micronised"
    assert "number_unbacked" not in codes(sf.mutated(on_crop), dos)

    def other_number(p):
        p["carousel"]["slides"][1]["alt_text_hr"] = "Izrez trake pakiranja s brojem 250"
    assert "number_unbacked" in codes(sf.mutated(other_number), dos)

    def no_crop(p):  # slide 4 shows no crop: a numeral in its alt text is not a transcription
        p["carousel"]["slides"][3]["alt_text_hr"] = "Kartica s tekstom 100% Pure micronised"
    assert "number_unbacked" in codes(sf.mutated(no_crop), dos)


def test_the_hero_headline_is_locked_and_structure_rules_hold(dos):
    assert "locked_copy" in codes(sf.mutated(lambda p: p["hero"].update(headline={"text": "Samo suština.", "claim_ids": []})), dos)
    assert "packshot" in codes(sf.mutated(lambda p: p["hero"].update(packshot=sf.NO_PACK)), dos)
    assert "duration" in codes(sf.mutated(lambda p: p["reel"].update(total_duration_s=40)), dos)
    assert "story" in codes(sf.mutated(lambda p: p["reel"]["development"].update(shot_ns=[3])), dos)
    assert "focal_product" in codes(sf.mutated(lambda p: p["focal_product"].update(sku="120100")), dos)


def test_concepts_must_be_distinct_and_copy_must_not_be_recycled(dos):
    assert "distinct" in codes(sf.mutated(lambda p: p["hero"].update(concept_name=p["reel"]["concept_name"])), dos)
    assert "distinct" in codes(sf.mutated(lambda p: p["reel"].update(hook={"text": "Što sve piše na pakiranju?", "claim_ids": []})), dos)
    assert "distinct" in codes(sf.mutated(lambda p: p["hero"].update(creative_device=p["carousel"]["creative_device"],
                                                                       big_idea=p["carousel"]["big_idea"], concept_name="Drugo ime")), dos)

    def recycled(p):
        p["reel"]["shots"][0]["on_screen_copy"] = [{"text": "Pronađite sitni tisak", "claim_ids": []}]
    assert "copy_reused" in codes(sf.mutated(recycled), dos)


# ---------------------------------------------------------------------------------- dossier / brief / packshot provenance
def test_the_dossier_keeps_status_labels_crops_constraints_and_the_selected_packshot(dos):
    assert {"verified", "manual", "assumption", "unknown"} <= {o["status"] for o in dos.payload["observations"]}
    assert dos.packshot["original_sha256"] == "99543edff63b17e355cd7bfcc734ef364ae81f08304e561e6a347c09e8954f1c"
    assert dos.packshot["cutout_sha256"].startswith("86613b3f") and "manual" in dos.packshot["status"]
    assert set(dos.crops) == {"label_name", "label_purity", "badge_ifs", "badge_hplc"}
    excluded = {c["id"]: c["reason"] for c in dos.payload["label_crops_excluded"]}
    assert {"badge_lab_tested", "badge_fast_absorption", "made_in_germany", "wordmark", "printed_badge_ifs", "printed_badge_hplc"} == set(excluded)
    assert {k: v["origin"] for k, v in dos.crops.items()} == {"label_name": "physical_packaging", "label_purity": "physical_packaging",
                                                               "badge_ifs": "webshop_graphic", "badge_hplc": "webshop_graphic"}
    assert "guarantee" in excluded["badge_lab_tested"].lower() and "performance" in excluded["badge_fast_absorption"].lower()
    assert dos.constraints["hero_headline"] == "SVAKA SERIJA POČINJE ODLUKOM." and dos.selected_variant["size_g"] is None
    assert "CONFIRMED by the human" in dos.payload["frame"]["focal_product"]["basis"]
    assert sf.build_dossier(sf.RESEARCH).fingerprint == dos.fingerprint  # deterministic
    assert len(json.dumps(dos.payload).encode()) < 60_000  # keeps the worst-case price estimate inside the caps


def test_the_canonical_brief_records_the_human_decision_and_no_legacy_brief_is_referenced():
    brief = BriefInput.model_validate(yaml.safe_load((sf.ROOT / "briefs" / "gymbeam_hr.yaml").read_text(encoding="utf-8")))
    c = brief.confirmed_focal_product
    assert c.sku == "3885" and c.confirmed_on == "2026-10-28" and "human" in c.confirmed_by
    assert brief.locked_copy == {"hero_headline": "SVAKA SERIJA POČINJE ODLUKOM."} and brief.language == "hr"
    assert load_settings(sf.ROOT / "config.yaml").default_brief == "briefs/gymbeam_hr.yaml"
    assert not (sf.ROOT / "briefs" / "gymbeam.yaml").exists()
    stale = []
    for path in [*sf.ROOT.glob("*.md"), *sf.ROOT.glob("*.yaml"), *(sf.ROOT / "studio").rglob("*.py"), *(sf.ROOT / "tests").glob("*.py"), *(sf.ROOT / "docs").glob("*.md")]:
        text = path.read_text(encoding="utf-8")
        if "briefs/gymbeam.yaml" in text and path.name not in ("WORKLOG.md", "test_strategy.py"):
            stale.append(path.name)
    assert stale == []


def test_a_label_crops_file_for_another_image_is_refused(tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(sf.ROOT / "research", root / "research")
    shutil.copytree(sf.ROOT / "briefs", root / "briefs")
    f = root / "research" / "imports" / "label_crops_gymbeam_hr.yaml"
    f.write_text(f.read_text(encoding="utf-8").replace("99543edff63b17e3", "0" * 16), encoding="utf-8")
    with pytest.raises(ValueError, match="sha256"):
        build_dossier(root / "research" / "gymbeam_hr")


def test_a_tampered_packshot_file_is_detected(tmp_path, dos):
    src = sf.ROOT / "runs" / "research-gymbeam-hr-live"
    if not (src / dos.packshot["original_run_path"]).is_file():
        pytest.skip("stored packshot not present in this checkout (runs/ is untracked)")
    root = tmp_path / "run"
    for rel in (dos.packshot["original_run_path"], dos.packshot["cutout_run_path"]):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, root / rel)
    assert build_dossier(sf.RESEARCH, artifact_root=root).packshot["file_hash_verified_on_disk"] == {"original": True, "cutout": True}
    (root / dos.packshot["cutout_run_path"]).write_bytes(b"not the packshot")
    assert build_dossier(sf.RESEARCH, artifact_root=root).packshot["file_hash_verified_on_disk"]["cutout"] is False


def test_label_crop_boxes_lie_inside_the_original_image_and_never_overlap_excluded_badges():
    doc = yaml.safe_load((sf.ROOT / "research" / "imports" / "label_crops_gymbeam_hr.yaml").read_text(encoding="utf-8"))
    usable = [c for c in doc["crops"] if c["usable"]]
    for c in doc["crops"]:
        x0, y0, x1, y1 = c["box"]
        assert 0 <= x0 < x1 <= 1080 and 0 <= y0 < y1 <= 1080
    for u in usable:
        for c in (c for c in doc["crops"] if not c["usable"] and c["id"].startswith("badge_")):
            ux0, uy0, ux1, uy1 = u["box"]
            cx0, cy0, cx1, cy1 = c["box"]
            assert ux1 <= cx0 or cx1 <= ux0 or uy1 <= cy0 or cy1 <= uy0, f"{u['id']} overlaps excluded {c['id']}"


# ---------------------------------------------------------------------------------- adapter
def _llm(transport, tmp_path, *, budget=0.5, requests=3, model="claude-sonnet-5-5", tag="", **kw):
    price = SETTINGS.anthropic_pricing[model]
    g = GuardedTransport(transport, limit=requests, hosts=("api.anthropic.com",), log_path=tmp_path / f"api_requests{tag}.log")
    return AnthropicLLM(model, g, 16000, "fixture", api_key=KEY, sleep=lambda s: None, input_usd_per_mtok=price.input_usd_per_mtok,
                        output_usd_per_mtok=price.output_usd_per_mtok, max_prompt_tokens=price.max_prompt_tokens, budget_usd=budget,
                        max_requests=requests, usage_path=tmp_path / f"api_usage{tag}.jsonl", forced_tool_choice=price.forced_tool_choice,
                        output_effort=price.effort, **kw)


def test_sonnet_requests_use_auto_tool_choice_and_effort_while_haiku_keeps_the_forced_tool(tmp_path):
    t = RecordedTransport().add(ANTHROPIC_URL, **sf.anthropic_reply(sf.valid_plan()))
    _llm(t, tmp_path).structured(CampaignPlan, task="content_plan", payload={"dossier": {}})
    body = json.loads(t.bodies[0])
    assert body["model"] == "claude-sonnet-5-5" and body["tool_choice"]["type"] == "auto" and body["output_config"] == {"effort": "medium"}
    assert body["max_tokens"] == 16000 and "MUST call it" in body["messages"][0]["content"]
    h = RecordedTransport().add(ANTHROPIC_URL, **sf.anthropic_reply(sf.valid_plan(), model="claude-haiku-5-5"))
    _llm(h, tmp_path / "h", model="claude-haiku-5-5").structured(CampaignPlan, task="content_plan", payload={})
    hb = json.loads(h.bodies[0])
    assert hb["tool_choice"]["type"] == "tool" and "output_config" not in hb


@pytest.mark.parametrize("stop", ["max_tokens", "refusal"])
def test_truncated_or_refused_answers_are_never_parsed(tmp_path, stop):
    t = RecordedTransport().add(ANTHROPIC_URL, **sf.anthropic_reply(sf.valid_plan(), stop=stop))
    with pytest.raises(ProviderResponseError, match=stop):
        _llm(t, tmp_path).structured(CampaignPlan, task="content_plan", payload={})


# ---------------------------------------------------------------------------------- workflow: cache, approval, revision
def session(tmp_path, replies, **kw):
    t = RecordedTransport()
    for r in replies:
        t.add(ANTHROPIC_URL, **r)
    llm = _llm(t, tmp_path / "run1", **kw)
    return PlanSession(SETTINGS, "run1", llm=llm, runs_dir=tmp_path), llm, t


def test_generate_pauses_for_a_human_and_records_actual_cost_in_the_ledger(tmp_path):
    s, llm, t = session(tmp_path, [sf.anthropic_reply(sf.valid_plan(), tin=20_000, tout=10_000)])
    res = s.generate(sf.RESEARCH)
    assert res.status == "awaiting_approval" and res.paused_at["gate"] == "plan"
    h = res.paused_at["fingerprint"]
    assert s.state()["plan"]["fingerprint"] == h and len(t.calls) == 1
    assert llm.accounting()["spent_usd"] == pytest.approx(20_000 * 2e-6 + 10_000 * 10e-6)
    with s.orch.open("run1") as (svc, *_):
        assert svc.ledger.total_cost("run1") == pytest.approx(0.14)
        assert svc.store.approvals("run1") == []  # nothing is ever approved automatically
    assert s.approval_state()["decision"] is None


def test_resume_and_rerun_reuse_the_cache_and_make_no_second_request(tmp_path):
    s, llm, t = session(tmp_path, [sf.anthropic_reply(sf.valid_plan())])
    s.generate(sf.RESEARCH)
    s.generate(sf.RESEARCH)
    s2 = PlanSession(SETTINGS, "run1", llm=_llm(t, tmp_path / "run1"), runs_dir=tmp_path)
    s2.generate(sf.RESEARCH)
    assert len(t.calls) == 1 and s2.state()["plan"]["fingerprint"] == s.state()["plan"]["fingerprint"]


def test_approval_binds_to_the_plan_hash_and_needs_a_human_confirmation(tmp_path):
    s, _, _ = session(tmp_path, [sf.anthropic_reply(sf.valid_plan())])
    h = s.generate(sf.RESEARCH).paused_at["fingerprint"]
    for bad in ("", "abc", h[:11], "0" * 12):
        with pytest.raises(NotAuthorised):
            s.decide(approve=True, comment="", approver="lara", confirmed_hash=bad)
    assert s.approval_state()["decision"] is None
    rec = s.decide(approve=True, comment="looks good", approver="lara", confirmed_hash=h[:12])
    assert rec.artifact_fingerprint == h and rec.source.value == "human_cli"
    st = s.approval_state()
    assert st["decision"] == "approved" and st["hash"] == h and "exact hash" in st["text"]
    assert s.state()["status"] != "rejected" and s.state()["plan_approval"]["decision"] == "approved"


def test_the_cli_refuses_to_decide_without_a_terminal_or_typed_confirmation(tmp_path, monkeypatch, capsys):
    s, _, _ = session(tmp_path, [sf.anthropic_reply(sf.valid_plan())])
    s.generate(sf.RESEARCH)
    monkeypatch.chdir(sf.ROOT)
    assert cli.main(["--runs-dir", str(tmp_path), "plan", "approve", "--run", "run1"]) == cli.EXIT_ERROR
    assert "human at a terminal" in capsys.readouterr().err
    assert cli.main(["--runs-dir", str(tmp_path), "plan", "approve", "--run", "run1", "--confirm", "deadbeefdead"]) == cli.EXIT_ERROR
    assert s.approval_state()["decision"] is None


def test_rejection_requires_a_comment_and_is_stored_for_this_hash(tmp_path):
    s, _, _ = session(tmp_path, [sf.anthropic_reply(sf.valid_plan())])
    h = s.generate(sf.RESEARCH).paused_at["fingerprint"]
    with pytest.raises(ValueError, match="comment"):
        s.decide(approve=False, comment="  ", approver="lara", confirmed_hash=h[:12])
    s.decide(approve=False, comment="hero is too quiet", approver="lara", confirmed_hash=h[:12])
    st = s.approval_state()
    assert st["decision"] == "rejected" and st["note"] == "hero is too quiet" and s.state()["status"] == "rejected"


FEEDBACK = "1. Carousel: use actual label crops only where original label imagery is available.\n2. Reel: show hands or faceless silhouettes."


def test_a_revision_keeps_the_original_records_the_feedback_and_invalidates_any_approval(tmp_path):
    revised = sf.mutated(lambda p: p["hero"].update(caption_hr={"text": "Tišina govori sama.", "claim_ids": []}))
    s, llm, t = session(tmp_path, [sf.anthropic_reply(sf.valid_plan()), sf.anthropic_reply(revised)])
    h1 = s.generate(sf.RESEARCH).paused_at["fingerprint"]
    original = (tmp_path / "run1" / "plan" / f"plan_{h1[:12]}.json").read_bytes()
    s.decide(approve=True, comment="ok for now", approver="lara", confirmed_hash=h1[:12])
    s2 = PlanSession(SETTINGS, "run1", llm=_llm(t, tmp_path / "run1", tag="_rev1"), runs_dir=tmp_path)  # own allowance for the revision
    res = s2.revise(FEEDBACK, requested_by="human (verbatim)")
    h2 = res.paused_at["fingerprint"]
    assert h2 != h1 and res.status == "awaiting_approval" and len(t.calls) == 2  # one extra model call, no research request
    st = s2.approval_state()
    assert st["decision"] is None and st["stale_ignored"] and "different version" in st["text"]
    assert (tmp_path / "run1" / "plan" / f"plan_{h1[:12]}.json").read_bytes() == original  # the original plan is preserved untouched
    hist = s2.history()
    assert len(hist) == 1 and hist[0]["feedback_verbatim"] == FEEDBACK and hist[0]["is_approval"] is False
    assert hist[0]["previous_plan_hash"] == h1 and hist[0]["new_plan_hash"] == h2 and hist[0]["dossier_after"]
    sent = json.loads(t.bodies[1])["messages"][0]["content"]
    assert "actual label crops" in sent and "previous_plan" in sent
    s2.decide(approve=True, comment="ok v2", approver="lara", confirmed_hash=h2[:12])
    with s2.orch.open("run1") as (svc, *_):
        assert svc.store.find_approval("run1", Gate.PLAN, h1).decision.value == "approved"  # history kept, bound to v1 only
    out = tmp_path / "plans"
    s2.export(out)
    meta = json.loads((out / "plan_metadata.json").read_text(encoding="utf-8"))
    assert set(meta["usage"]["cost_usd_by_usage_file"]) == {"api_usage.jsonl", "api_usage_rev1.jsonl"}  # separate allowances, summed in the report
    assert meta["usage"]["message_requests"] == 2 and (out / "revision_history.json").is_file() and (out / "api_requests_rev1.log").is_file()


def test_a_blocked_revision_resumes_from_the_ledger_without_a_second_paid_call(tmp_path):
    """Draft blocked by the validator, repair refused by the money guard; after the rule is fixed, resume reuses the paid draft."""
    draft = sf.mutated(lambda p: p["carousel"]["slides"][3].update(alt_text_hr="Kartica s brojem 250"))  # invalid under the current rules
    s, _, t0 = session(tmp_path, [sf.anthropic_reply(sf.valid_plan())])
    s.generate(sf.RESEARCH)
    t = RecordedTransport().add(ANTHROPIC_URL, **sf.anthropic_reply(draft, tin=33_000, tout=10_000))
    mk = lambda: PlanSession(SETTINGS, "run1", llm=_llm(t, tmp_path / "run1", budget=0.40, requests=2, tag="_rev1"), runs_dir=tmp_path)  # noqa: E731
    with pytest.raises(BudgetExceeded):
        mk().revise(FEEDBACK)
    assert len(t.calls) == 1
    import studio.nodes.planner_live as pl
    real = pl.validate_plan
    pl.validate_plan = lambda plan, d: []  # stands in for "the rule was corrected"; the ledger already holds the paid draft
    try:
        res = mk().resume()
    finally:
        pl.validate_plan = real
    assert res.status == "awaiting_approval" and len(t.calls) == 1  # NO second request was sent
    hist = mk().history()
    assert hist[-1]["new_plan_hash"] == res.paused_at["fingerprint"]


def test_an_edited_plan_file_cannot_ride_on_an_old_approval(tmp_path):
    s, _, _ = session(tmp_path, [sf.anthropic_reply(sf.valid_plan())])
    h = s.generate(sf.RESEARCH).paused_at["fingerprint"]
    s.decide(approve=True, comment="ok", approver="lara", confirmed_hash=h[:12])
    from studio.nodes.planner_live import plan_fingerprint
    doc = json.loads((tmp_path / "run1" / "plan" / f"plan_{h[:12]}.json").read_text(encoding="utf-8"))
    assert plan_fingerprint(doc["campaign"], doc["packshot"]) == h
    doc["campaign"]["hero"]["caption_hr"]["text"] = "Zajamčeni rezultati"
    assert plan_fingerprint(doc["campaign"], doc["packshot"]) != h


def test_one_automatic_repair_then_a_hard_stop(tmp_path):
    bad = sf.mutated(lambda p: p["claims"][0].update(evidence_ids=["E-doesnotexist"]))
    s, llm, t = session(tmp_path, [sf.anthropic_reply(bad), sf.anthropic_reply(sf.valid_plan())], requests=4)
    res = s.generate(sf.RESEARCH)
    assert res.status == "awaiting_approval" and len(t.calls) == 2
    assert "E-doesnotexist" in json.loads(t.bodies[1])["messages"][0]["content"]
    s2, _, t2 = session(tmp_path / "x", [sf.anthropic_reply(bad)], requests=4)
    with pytest.raises(PlanInvalid) as e:
        s2.generate(sf.RESEARCH)
    assert len(t2.calls) == 2 and any(p.code == "unknown_evidence" for p in e.value.problems)
    assert not (tmp_path / "x" / "run1" / "plan" / "current.json").exists()  # an invalid plan never reaches the gate


def test_flags_do_not_block_and_are_stored_for_the_reviewer(tmp_path):
    s, _, _ = session(tmp_path, [sf.anthropic_reply(sf.valid_plan())])
    s.generate(sf.RESEARCH)
    flags = s.state()["plan"]["meta"]["validation_flags"]
    assert any("novelty_word_context" in f for f in flags)


def test_request_limit_stops_the_repair_call_and_nothing_extra_is_sent(tmp_path):
    bad = sf.mutated(lambda p: p["claims"][0].update(evidence_ids=["E-doesnotexist"]))
    s, llm, t = session(tmp_path, [sf.anthropic_reply(bad), sf.anthropic_reply(sf.valid_plan())], requests=1)
    with pytest.raises(RequestLimitExceeded):
        s.generate(sf.RESEARCH)
    assert len(t.calls) == 1 and (tmp_path / "run1" / "api_requests.log").read_text().count("\n") == 1


def test_the_money_cap_refuses_before_any_request_is_sent(tmp_path):
    s, llm, t = session(tmp_path, [sf.anthropic_reply(sf.valid_plan())], budget=0.05)
    with pytest.raises(BudgetExceeded, match="request NOT sent"):
        s.generate(sf.RESEARCH)
    assert t.calls == []
    s2, llm2, t2 = session(tmp_path / "ok", [sf.anthropic_reply(sf.valid_plan())], budget=0.50)
    assert s2.generate(sf.RESEARCH).status == "awaiting_approval" and len(t2.calls) == 1


def test_a_revision_call_fits_the_040_cap_but_a_repair_after_it_would_not(tmp_path):
    """The revision payload (dossier + previous plan) is admitted under 0.40 USD; after a realistic first call the guard refuses a second."""
    s, _, _ = session(tmp_path, [sf.anthropic_reply(sf.valid_plan())])
    s.generate(sf.RESEARCH)
    bad = sf.mutated(lambda p: p["claims"][0].update(evidence_ids=["E-doesnotexist"]))
    t = RecordedTransport().add(ANTHROPIC_URL, **sf.anthropic_reply(bad, tin=33_000, tout=10_000)).add(ANTHROPIC_URL, **sf.anthropic_reply(sf.valid_plan()))
    s2 = PlanSession(SETTINGS, "run1", llm=_llm(t, tmp_path / "run1", budget=0.40, requests=2, tag="_rev1"), runs_dir=tmp_path)
    with pytest.raises(BudgetExceeded, match="request NOT sent"):  # the guard is NOT bypassed
        s2.revise(FEEDBACK)
    assert len(t.calls) == 1


def test_export_writes_every_deliverable(tmp_path):
    s, llm, _ = session(tmp_path, [sf.anthropic_reply(sf.valid_plan())])
    s.generate(sf.RESEARCH)
    out = tmp_path / "plans"
    names = {p.name for p in s.export(out)}
    assert {"content_plan.json", "evidence_map.json", "plan_metadata.json", "campaign.md", "post_01_carousel.md", "post_02_hero.md",
            "post_03_reel.md", "review.txt", "api_usage.jsonl", "api_requests.log"} <= names
    cp = json.loads((out / "content_plan.json").read_text(encoding="utf-8"))
    assert cp["status"].startswith("NONE") and cp["packshot_reference"]["original_sha256"].startswith("99543edf")
    em = json.loads((out / "evidence_map.json").read_text(encoding="utf-8"))
    assert {c["claim_id"] for c in em["claims"]} == {"C1", "C2", "C3", "C4"} and em["claims"][0]["evidence"][0]["status"] == "verified"
    meta = json.loads((out / "plan_metadata.json").read_text(encoding="utf-8"))
    assert meta["model"] == "claude-sonnet-5-5" and meta["usage"]["message_requests"] == 1 and meta["usage"]["cost_usd"] > 0
    review = s.review_text()
    assert "EVIDENCE BEHIND EVERY CLAIM" in review and "APPROVAL: NONE" in review and "Na pakiranju piše: 100% Pure micronised" in review
