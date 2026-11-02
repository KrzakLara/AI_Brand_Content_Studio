"""Phase 3 final review: `studio plan edit` (exact-match, atomic, audited, honestly attributed) and the label-text safeguards.

Recorded transports only (no network, no API credits). Plans are TEST DATA from tests/strategy_fixtures.py.
"""
import json

import pytest
import yaml

from studio import cli
from studio.contracts import Gate
from studio.contracts.strategy import CampaignPlan
from studio.strategy.edits import EditError, EditItem, authorship
from studio.strategy.validate import errors, pack_text_audit, validate_plan
from studio.strategy.workflow import PlanSession

from . import strategy_fixtures as sf
from .test_strategy import FEEDBACK, SETTINGS, _llm, session
from studio.providers.live import ANTHROPIC_URL


def item(id, post, path, expected, replacement, *, confirmed=True, proposed="ai:Claude Code", op="replace", **kw):
    d = {"id": id, "op": op, "post": post, "path": path, "expected": expected, "reason": "test reason", "proposed_by": proposed}
    if op == "replace":
        d["replacement"] = replacement
    if confirmed:
        d.update(confirmed_by="Lara", confirmation_source="test: confirmed in the review conversation")
    d.update(kw)
    return d


def edits_file(tmp_path, h, items, name="edits.yaml"):
    p = tmp_path / name
    p.write_text(yaml.safe_dump({"base_plan_hash": h, "edits": items}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return p


HERO_CAPTION = "Tišina je također poruka."


@pytest.fixture
def gen(tmp_path):
    s, llm, t = session(tmp_path, [sf.anthropic_reply(sf.valid_plan())])
    h = s.generate(sf.RESEARCH).paused_at["fingerprint"]
    return s, h, tmp_path


def snapshot(tmp_path):
    plan_dir = tmp_path / "run1" / "plan"
    return {p.name: p.read_bytes() for p in plan_dir.glob("*")}


# ------------------------------------------------------------------------------------------- exact match / stale / atomic
def test_an_exact_match_edit_changes_the_plan_recalculates_the_hash_and_keeps_the_old_plan(gen):
    s, h1, tmp = gen
    before = snapshot(tmp)
    f = edits_file(tmp, h1, [item("E1", "02", "caption_hr.text", HERO_CAPTION, "Tišina govori sama.")])
    r = s.edit(f, reason="Human copy review")
    h2 = r["resulting_plan_hash"]
    assert h2 != h1 and s.state()["plan"]["fingerprint"] == h2
    assert s.state()["plan"]["campaign"]["hero"]["caption_hr"]["text"] == "Tišina govori sama."
    assert (tmp / "run1" / "plan" / f"plan_{h1[:12]}.json").read_bytes() == before[f"plan_{h1[:12]}.json"]  # original preserved byte for byte
    assert json.loads((tmp / "run1" / "plan" / "current.json").read_text())["plan_hash"] == h2
    assert s.edit_history()[0]["resulting_plan_hash"] == h2


def test_a_stale_original_or_stale_base_hash_is_rejected_and_nothing_changes(gen):
    s, h1, tmp = gen
    before, state_before = snapshot(tmp), s.state()["plan"]["fingerprint"]
    with pytest.raises(EditError, match="stale/mismatched original"):
        s.edit(edits_file(tmp, h1, [item("E1", "02", "caption_hr.text", "Tišina je poruka.", "x y")]), reason="r")
    with pytest.raises(EditError, match="stale edit file"):
        s.edit(edits_file(tmp, "0" * 12, [item("E1", "02", "caption_hr.text", HERO_CAPTION, "Tišina govori sama.")]), reason="r")
    assert snapshot(tmp) == before and s.state()["plan"]["fingerprint"] == state_before and s.edit_history() == []


def test_a_second_edit_file_prepared_for_the_old_hash_is_stale_after_the_first_was_applied(gen):
    s, h1, tmp = gen
    s.edit(edits_file(tmp, h1, [item("E1", "02", "caption_hr.text", HERO_CAPTION, "Tišina govori sama.")], "a.yaml"), reason="first")
    with pytest.raises(EditError, match="stale edit file"):
        s.edit(edits_file(tmp, h1, [item("E1", "02", "cta.text", "Pogledajte u trgovini", "Pogledajte ponudu")], "b.yaml"), reason="second")
    assert len(s.edit_history()) == 1


def test_edits_are_atomic_one_bad_edit_means_none_are_applied(gen):
    s, h1, tmp = gen
    before = snapshot(tmp)
    good = item("E1", "02", "caption_hr.text", HERO_CAPTION, "Tišina govori sama.")
    bad = item("E2", "02", "cta.text", "Pogledajte u trgovini", "Najbolji kreatin za vas")  # violates the evidence/safety validator
    with pytest.raises(EditError, match="fails validation"):
        s.edit(edits_file(tmp, h1, [good, bad]), reason="r")
    wrong = item("E3", "02", "cta.text", "nije to", "Pogledajte ponudu")
    with pytest.raises(EditError):
        s.edit(edits_file(tmp, h1, [good, wrong]), reason="r")
    assert snapshot(tmp) == before and s.state()["plan"]["campaign"]["hero"]["caption_hr"]["text"] == HERO_CAPTION and s.edit_history() == []


def test_conflicting_edits_are_rejected(gen):
    s, h1, tmp = gen
    a = item("E1", "02", "caption_hr.text", HERO_CAPTION, "Tišina govori sama.")
    b = item("E2", "02", "caption_hr.text", HERO_CAPTION, "Tišina je glasna.")
    with pytest.raises(EditError, match="conflicting"):
        s.edit(edits_file(tmp, h1, [a, b]), reason="r")
    r1 = item("E5", "01", "callouts[0]", "Na pakiranju piše: 100% Pure micronised", None, op="remove", slide=2)
    r2 = item("E6", "01", "callouts[0].text", "Na pakiranju piše: 100% Pure micronised", "Na pakiranju piše: Pure", slide=2)
    with pytest.raises(EditError, match="conflicting"):
        s.edit(edits_file(tmp, h1, [r1, r2]), reason="r")


def test_dry_run_previews_and_validates_but_writes_nothing_and_allows_unconfirmed_edits(gen, monkeypatch, capsys):
    s, h1, tmp = gen
    before = snapshot(tmp)
    f = edits_file(tmp, h1, [item("E1", "02", "caption_hr.text", HERO_CAPTION, "Tišina govori sama.", confirmed=False)])
    r = s.edit(f, reason="preview", dry_run=True)
    assert r["dry_run"] is True and r["resulting_plan_hash"] != h1 and r["changes"][0]["authorship"] == "ai_suggestion_UNCONFIRMED"
    assert snapshot(tmp) == before and s.edit_history() == [] and s.state()["plan"]["fingerprint"] == h1
    with pytest.raises(EditError, match="not confirmed by a human"):  # the same file cannot be APPLIED
        s.edit(f, reason="apply")
    monkeypatch.chdir(sf.ROOT)  # CLI: dry run exits 0 and prints, a real run of unconfirmed edits is refused with exit 2 and no change
    assert cli.main(["--runs-dir", str(tmp), "plan", "edit", "--run", "run1", "--edits", str(f), "--reason", "preview", "--dry-run"]) == cli.EXIT_OK
    assert "DRY RUN (nothing written)" in capsys.readouterr().out
    assert cli.main(["--runs-dir", str(tmp), "plan", "edit", "--run", "run1", "--edits", str(f), "--reason", "apply"]) == cli.EXIT_ERROR
    assert "nothing was changed" in capsys.readouterr().err and snapshot(tmp) == before


def test_removal_of_a_list_element_works_and_indices_refer_to_the_original_plan(gen):
    s, h1, tmp = gen
    a = item("E1", "01", "callouts[0]", "Na pakiranju piše: 100% Pure micronised", None, op="remove", slide=2)
    b = item("E2", "01", "headline.text", "Prvo pročitajte traku", "Prvo pročitajte traku s nazivom", slide=2)
    r = s.edit(edits_file(tmp, h1, [a, b]), reason="r")
    sl = s.state()["plan"]["campaign"]["carousel"]["slides"][1]
    assert sl["callouts"] == [] and sl["headline"]["text"] == "Prvo pročitajte traku s nazivom"
    assert {c["op"] for c in r["changes"]} == {"remove", "replace"}


# ------------------------------------------------------------------------------------------- history, hash, approvals
def test_the_revision_history_records_old_new_reason_proposer_timestamp_and_resulting_hash(gen):
    s, h1, tmp = gen
    f = edits_file(tmp, h1, [item("E1", "02", "caption_hr.text", HERO_CAPTION, "Tišina govori sama.", reason="grammar fix", proposed="ai:Claude Code (Sonnet 5.5)")])
    r = s.edit(f, reason="Human copy review", applied_by="Claude Code")
    e = s.edit_history()[0]
    assert e["reason"] == "Human copy review" and e["applied_by"] == "Claude Code" and e["applied_at"].endswith("+00:00")
    assert e["previous_plan_hash"] == h1 and e["resulting_plan_hash"] == r["resulting_plan_hash"] and e["edits_file_base_hash"] == h1
    c = e["edits"][0]
    assert (c["old_value"], c["new_value"], c["reason"], c["path"], c["post"]) == (HERO_CAPTION, "Tišina govori sama.", "grammar fix", "caption_hr.text", "02")
    assert c["proposed_by"] == "ai:Claude Code (Sonnet 5.5)" and c["confirmed_by"] == "Lara"
    assert e["resulting_plan_file"] != e["previous_plan_file"]


def test_an_edit_invalidates_the_approval_attached_to_the_old_hash(gen):
    s, h1, tmp = gen
    s.decide(approve=True, comment="ok", approver="lara", confirmed_hash=h1[:12])
    assert s.approval_state()["decision"] == "approved"
    r = s.edit(edits_file(tmp, h1, [item("E1", "02", "caption_hr.text", HERO_CAPTION, "Tišina govori sama.")]), reason="late fix")
    st = s.approval_state()
    assert st["hash"] == r["resulting_plan_hash"] and st["decision"] is None and st["stale_ignored"] and "different version" in st["text"]
    assert s.state()["plan_approval"] == {}  # the in-state approval is cleared too
    with s.orch.open("run1") as (svc, graph, cfg, _):
        assert svc.store.find_approval("run1", Gate.PLAN, h1).decision.value == "approved"  # history kept, bound to the old hash only
    with pytest.raises(Exception):  # the old hash can no longer be confirmed
        s.decide(approve=True, comment="old", approver="lara", confirmed_hash=h1[:12])


# ------------------------------------------------------------------------------------------- honest attribution
def test_ai_proposed_wording_is_never_recorded_as_human_authored(gen):
    s, h1, tmp = gen
    f = edits_file(tmp, h1, [item("E1", "02", "caption_hr.text", HERO_CAPTION, "Tišina govori sama.", proposed="ai:Claude Code")])
    s.edit(f, reason="r", applied_by="Claude Code")
    c = s.edit_history()[0]["edits"][0]
    assert c["authorship"] == "ai_suggestion_confirmed_by_human" and c["proposed_by"].startswith("ai:") and c["confirmed_by"] == "Lara"
    assert s.edit_history()[0]["applied_by"] == "Claude Code"
    assert "human_authored" not in json.dumps(s.edit_history())


def test_authorship_labels_and_confirmation_rules():
    base = dict(id="E", post="02", path="x", expected="a", replacement="b", reason="why")
    assert authorship(EditItem(**base, proposed_by="ai:Claude Code")) == "ai_suggestion_UNCONFIRMED"
    assert authorship(EditItem(**base, proposed_by="ai:Claude Code", confirmed_by="Lara", confirmation_source="chat")) == "ai_suggestion_confirmed_by_human"
    assert authorship(EditItem(**base, proposed_by="human:Lara", confirmed_by="Lara", confirmation_source="her wording")) == "human_authored"
    assert authorship(EditItem(**base, proposed_by="human:Lara")) == "human_authored_UNCONFIRMED"
    rem = dict(id="E", post="02", path="supporting_copy[0]", expected="a", reason="why", op="remove", proposed_by="ai:Claude Code", requested_by="human:Lara")
    assert authorship(EditItem(**rem)) == "human_requested_removal_PENDING_CONFIRMATION"
    assert authorship(EditItem(**rem, confirmed_by="Lara", confirmation_source="her instruction")) == "human_requested_removal"
    with pytest.raises(ValueError):
        EditItem(**base, proposed_by="Claude")  # actor must be explicit: ai:<who> or human:<who>


def test_confirmation_must_name_a_human_and_a_source_and_match_the_author_of_human_wording(gen):
    s, h1, tmp = gen
    base = item("E1", "02", "caption_hr.text", HERO_CAPTION, "Tišina govori sama.")
    nosrc = {**base, "confirmation_source": None}
    with pytest.raises(EditError, match="not confirmed"):
        s.edit(edits_file(tmp, h1, [nosrc]), reason="r")
    other = {**base, "proposed_by": "human:Lara", "confirmed_by": "Claude Code"}  # an assistant cannot confirm a human's wording
    with pytest.raises(EditError, match="same human"):
        s.edit(edits_file(tmp, h1, [other]), reason="r")
    assert s.edit_history() == []


# ------------------------------------------------------------------------------------------- validation is never weakened
def test_unsupported_claims_numbers_locked_copy_and_protected_fields_are_rejected_through_edits(gen):
    s, h1, tmp = gen
    cases = {
        "fails validation": item("E1", "02", "caption_hr.text", HERO_CAPTION, "Kreatin za bolju izvedbu."),
        "fails validation ": item("E1", "02", "caption_hr.text", HERO_CAPTION, "Samo 5 minuta dnevno."),
        "locked": item("E1", "02", "headline.text", "SVAKA SERIJA POČINJE ODLUKOM.", "Samo suština."),
        "protected": item("E1", "01", "callouts[0].claim_ids[0]", "C2", "C1", slide=2),
        "protected ": item("E1", "01", "packshot.treatment", "unaltered_cutout_composite", "x"),
        "does not exist": item("E1", "02", "nope.text", "a", "b"),
        "bad path": item("E1", "02", "caption_hr..text", "a", "b"),
        "not a text field": item("E1", "02", "people.appear", "False", "True"),
    }
    for want, it in cases.items():
        with pytest.raises(EditError):
            s.edit(edits_file(tmp, h1, [it]), reason="r")
    assert s.edit_history() == [] and s.state()["plan"]["fingerprint"] == h1
    with pytest.raises(EditError, match="locked"):
        s.edit(edits_file(tmp, h1, [cases["locked"]]), reason="r")
    with pytest.raises(EditError, match="protected"):
        s.edit(edits_file(tmp, h1, [cases["protected"]]), reason="r")


def test_an_edit_cannot_make_a_verified_callout_unprintable_or_inject_wording_beyond_the_crop(gen):
    s, h1, tmp = gen
    bad = item("E1", "01", "callouts[0].text", "Na pakiranju piše: 100% Pure micronised", "Na pakiranju piše: 100% Pure organic", slide=2)
    with pytest.raises(EditError, match="pack_text_not_verified"):
        s.edit(edits_file(tmp, h1, [bad]), reason="r")
    assert s.edit_history() == []


# ------------------------------------------------------------------------------------------- label text / alt text safeguards
@pytest.fixture(scope="module")
def dos():
    return sf.dossier()


def codes(plan, dos):
    return {p.code for p in errors(validate_plan(CampaignPlan.model_validate(plan), dos))}


def alt(slide_idx, text):
    def f(p):
        p["carousel"]["slides"][slide_idx]["alt_text_hr"] = text
    return f


def test_the_alt_text_exception_works_only_for_wording_really_printed_on_the_crop_of_that_slide(dos):
    ok = sf.mutated(alt(1, "Izrez trake pakiranja s tekstom 100% Pure micronised"))  # slide 2 shows label_purity
    assert codes(ok, dos) == set()
    assert any(p.code == "alt_text_transcription" for p in validate_plan(CampaignPlan.model_validate(ok), dos))  # still flagged for the human
    # invented packaging information, each in a different way
    assert "alt_text_unverified_packaging_text" in codes(sf.mutated(alt(1, "Izrez trake s certificiranim sastojcima")), dos)       # asserts certification not on this crop
    assert "alt_text_unverified_packaging_text" in codes(sf.mutated(alt(1, "Izrez trake, testirano u laboratoriju")), dos)           # asserts testing not on this crop
    assert "alt_text_unverified_packaging_text" in codes(sf.mutated(alt(1, "Izrez trake s natpisom „100% organic“")), dos)            # quoted wording not printed
    assert "alt_text_unverified_packaging_text" in codes(sf.mutated(alt(1, "Izrez trake with natural ingredients")), dos)             # English wording not printed
    assert "alt_text_unverified_packaging_text" in codes(sf.mutated(alt(1, "Izrez trake, brza apsorpcija")), dos)                     # performance wording the crop does not carry
    assert "number_unbacked" in codes(sf.mutated(alt(1, "Izrez trake s oznakom 250")), dos)                                          # numeral not printed on the crop
    assert "label_crop" in codes(sf.mutated(lambda p: p["carousel"]["slides"][1]["label_crops"].append({"crop_id": "badge_fast_absorption", "purpose": "x"})), dos)


def test_the_exception_does_not_apply_to_a_slide_without_that_crop_or_to_other_posts(dos):
    assert "alt_text_unverified_packaging_text" in codes(sf.mutated(alt(1, "Izrez s oznakom IFS")), dos)      # IFS crop is on slide 3, not slide 2
    assert "number_unbacked" in codes(sf.mutated(alt(0, "Kartica s tekstom 100% Pure micronised")), dos)     # slide 1 shows no crop
    assert "alt_text_unverified_packaging_text" in codes(sf.mutated(alt(0, "Kartica s HPLC oznakom")), dos)
    assert "alt_text_unverified_packaging_text" in codes(sf.mutated(lambda p: p["hero"].update(alt_text_hr="Vrećica s certificiranim sadržajem")), dos)
    assert "alt_text_unverified_packaging_text" in codes(sf.mutated(lambda p: p["reel"].update(alt_text_hr="Ruke, pa čisti kreatin na polici")), dos)
    assert "forbidden" in codes(sf.mutated(alt(1, "Izrez trake, zajamčena kvaliteta")), dos)                  # promotional guarantee is rejected on its own


def test_na_pakiranju_pise_must_be_printed_on_the_crop_shown_on_that_exact_slide(dos):
    ok = CampaignPlan.model_validate(sf.valid_plan())
    rows = pack_text_audit(ok, dos)
    assert len(rows) == 3 and all(r["status"].startswith("verified") for r in rows)

    def other_crop(p):  # slide 3 shows badge_ifs; the purity claim (crop label_purity) is not printed on it
        p["carousel"]["slides"][2]["callouts"] = [{"text": "Na pakiranju piše: 100% Pure micronised", "claim_ids": ["C2"]}]
    assert "pack_text_not_verified" in codes(sf.mutated(other_crop), dos)

    def no_crop(p):  # a slide without any crop cannot say 'on the packaging it says'
        p["carousel"]["slides"][3]["label_crops"] = []
    assert "pack_text_not_verified" in codes(sf.mutated(no_crop), dos)

    def extra_words(p):
        p["carousel"]["slides"][1]["callouts"] = [{"text": "Na pakiranju piše: 100% Pure micronised, Premium", "claim_ids": ["C2"]}]
    assert "pack_text_not_verified" in codes(sf.mutated(extra_words), dos)


# ------------------------------------------------------------------------------------------- earlier revisions stay preserved
def test_earlier_plans_revisions_and_edits_all_stay_preserved_and_exported(tmp_path):
    revised = sf.mutated(lambda p: p["hero"].update(caption_hr={"text": "Tišina govori sama.", "claim_ids": []}))
    s, llm, t = session(tmp_path, [sf.anthropic_reply(sf.valid_plan()), sf.anthropic_reply(revised)])
    h1 = s.generate(sf.RESEARCH).paused_at["fingerprint"]
    v1 = (tmp_path / "run1" / "plan" / f"plan_{h1[:12]}.json").read_bytes()
    s2 = PlanSession(SETTINGS, "run1", llm=_llm(t, tmp_path / "run1", tag="_rev1"), runs_dir=tmp_path)
    h2 = s2.revise(FEEDBACK).paused_at["fingerprint"]
    v2 = (tmp_path / "run1" / "plan" / f"plan_{h2[:12]}.json").read_bytes()
    s3 = PlanSession(SETTINGS, "run1", runs_dir=tmp_path)  # no model attached: editing never needs one
    r = s3.edit(edits_file(tmp_path, h2, [item("E1", "02", "cta.text", "Pogledajte u trgovini", "Pogledajte ponudu")]), reason="copy review")
    h3 = r["resulting_plan_hash"]
    assert len({h1, h2, h3}) == 3 and len(t.calls) == 2  # the edit sent no API request
    plan_dir = tmp_path / "run1" / "plan"
    assert (plan_dir / f"plan_{h1[:12]}.json").read_bytes() == v1 and (plan_dir / f"plan_{h2[:12]}.json").read_bytes() == v2
    assert [h["new_plan_hash"] for h in s3.history()] == [h2] and s3.edit_history()[0]["previous_plan_hash"] == h2
    out = tmp_path / "plans"
    s3.export(out)
    kept = {p.name for p in (out / "history" / "plan_versions").glob("plan_*.json")}
    assert {f"plan_{h[:12]}.json" for h in (h1, h2, h3)} <= kept
    assert (out / "edit_history.json").is_file() and (out / "revision_history.json").is_file()
    assert json.loads((out / "plan_metadata.json").read_text(encoding="utf-8"))["usage"]["message_requests"] == 2


def test_editing_uses_no_model_even_when_the_session_has_none(gen):
    s, h1, tmp = gen
    sess = PlanSession(SETTINGS, "run1", runs_dir=tmp)  # an UnavailableProvider as llm: any model call would raise
    r = sess.edit(edits_file(tmp, h1, [item("E1", "02", "caption_hr.text", HERO_CAPTION, "Tišina govori sama.")]), reason="r")
    assert r["resulting_plan_hash"] != h1
    assert (tmp / "run1" / "api_requests.log").read_text().count("\n") == 1  # only the original generation request exists


# ------------------------------------------------------------------------------------------- shot timing, decision-scope confirmation, manifest
def test_shot_timing_can_be_edited_but_the_duration_validators_still_apply(gen):
    s, h1, tmp = gen
    shots = [x for x in sf.valid_plan()["reel"]["shots"]]
    assert [x["duration_s"] for x in shots] == [3] * 6
    ok = [item(f"T{i}", "03", "duration_s", "3", "2.5", shot=i) for i in range(1, 7)] + [item("TT", "03", "total_duration_s", "18", "15")]
    r = s.edit(edits_file(tmp, h1, ok), reason="rhythm")
    reel = s.state()["plan"]["campaign"]["reel"]
    assert [x["duration_s"] for x in reel["shots"]] == [2.5] * 6 and reel["total_duration_s"] == 15.0
    assert {c["new_value"] for c in r["changes"]} == {"2.5", "15"}


def test_inconsistent_or_out_of_range_timing_edits_are_rejected(gen):
    s, h1, tmp = gen
    with pytest.raises(EditError, match="duration"):  # total no longer equals the sum
        s.edit(edits_file(tmp, h1, [item("T1", "03", "duration_s", "3", "2", shot=1)]), reason="r")
    with pytest.raises(EditError, match="duration"):  # reel shorter than 12 s
        s.edit(edits_file(tmp, h1, [item(f"T{i}", "03", "duration_s", "3", "1", shot=i) for i in range(1, 7)] + [item("TT", "03", "total_duration_s", "18", "6")]), reason="r")
    with pytest.raises(EditError):  # not a number
        s.edit(edits_file(tmp, h1, [item("T1", "03", "duration_s", "3", "brzo", shot=1)]), reason="r")
    with pytest.raises(EditError, match="stale/mismatched"):
        s.edit(edits_file(tmp, h1, [item("T1", "03", "duration_s", "4", "2", shot=1)]), reason="r")
    assert s.edit_history() == []


def test_decision_scope_confirmation_is_recorded_as_ai_wording_not_as_human_wording(gen):
    s, h1, tmp = gen
    it = item("D1", "02", "caption_hr.text", HERO_CAPTION, "Tišina govori sama.", confirmation_scope="decision")
    s.edit(edits_file(tmp, h1, [it]), reason="decision")
    c = s.edit_history()[0]["edits"][0]
    assert c["authorship"] == "ai_wording_implementing_human_decision" and c["confirmation_scope"] == "decision" and c["proposed_by"].startswith("ai:")
    assert "human_authored" not in json.dumps(s.edit_history())
    base = dict(id="E", post="02", path="x", expected="a", replacement="b", reason="why", proposed_by="ai:Claude Code", confirmed_by="Lara", confirmation_source="c")
    assert authorship(EditItem(**base)) == "ai_suggestion_confirmed_by_human"
    assert authorship(EditItem(**base, confirmation_scope="decision")) == "ai_wording_implementing_human_decision"
    assert authorship(EditItem(**{**base, "proposed_by": "human:Lara"}, confirmation_scope="decision")) == "human_authored"


def test_the_asset_manifest_records_pending_logo_and_audio_requirements_and_the_packshot_hash(dos):
    m = yaml.safe_load((sf.ROOT / "plans" / "gymbeam_hr" / "asset_manifest.yaml").read_text(encoding="utf-8"))
    assert m["packshot"]["sha256"] == dos.packshot["original_sha256"] and m["packshot"]["cutout"]["sha256"] == dos.packshot["cutout_sha256"]
    logo, audio = m["logo"], m["audio"]
    assert logo["status"].startswith("pending") and {"source_url", "retrieved_at", "sha256"} <= set(logo) and logo["sha256"] is None
    assert audio["tracks"] == [] and audio["status"] == "none_selected"
    assert any("licence" in r and "permits" in r for r in audio["rules"]) and any("sha256" in r for r in audio["rules"])


def test_add_slide_and_set_block_are_validated_like_any_ai_written_content(gen):
    s, h, tmp = gen
    plan = s.current()[0]["campaign"]
    slide = dict(plan["carousel"]["slides"][0], n=6)
    ok = item("S1", "01", "slides", "", None, op="add_slide", value_json=slide)
    ok.pop("replacement", None)
    with pytest.raises(EditError):  # six slides are fine, but a slide with an invalid shape is rejected before anything changes
        bad = dict(ok, id="S2", value_json={"n": 7})
        s.edit(edits_file(tmp, h, [bad]), reason="bad slide")
    blk = item("B1", "01", "packshot", "", None, op="set_block", value_json={"used": True, "packshot_ref": None, "treatment": None, "instructions": []})
    blk.pop("replacement", None)
    with pytest.raises(EditError):  # the schema still forbids a product post without its protected packshot settings
        s.edit(edits_file(tmp, h, [blk], "b.yaml"), reason="bad block")
    assert s.current()[0]["plan_hash"] == h
