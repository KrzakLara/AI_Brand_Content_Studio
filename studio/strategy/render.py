"""Human-readable views of a plan: review text, per-post creative briefs/storyboards, evidence map."""
from studio.contracts.strategy import CampaignPlan, CopyLine
from studio.strategy.dossier import Dossier


def _ev_detail(d: Dossier, eid: str) -> dict:
    e = d.evidence[eid]
    quote = e["quote"] if e["subject"] in ("product_description", "instagram_post") else e["claim"]
    return {"evidence_id": eid, "status": e["verification_status"], "kind": e["subject"], "source_url": e.get("source_url"),
            "retrieved_at": e.get("retrieved_at"), "sku_family": d.family.get(eid), "text": " ".join(quote.split())}


def evidence_map(plan: CampaignPlan, d: Dossier) -> dict:
    claims = []
    for c in plan.claims:
        uses = [w for w, ln in _lines(plan) if c.claim_id in ln.claim_ids]
        claims.append({"claim_id": c.claim_id, "text": c.text, "type": c.claim_type, "as_of": c.as_of, "basis_quote": c.basis_quote,
                       "used_in": uses, "evidence": [_ev_detail(d, e) for e in c.evidence_ids]})
    basis = []
    for scope, items in [("identity", plan.identity.basis)] + [(k, p.basis) for k, p in plan.posts().items()]:
        for b in items:
            ids = [x for i in b.evidence_ids for x in (d.obs_evidence.get(i, []) if i.startswith("O") else [i])]
            basis.append({"scope": scope, "statement": b.statement, "claimed_status": b.status, "cites": b.evidence_ids,
                          "resolved_evidence_statuses": sorted({d.evidence[i]["verification_status"] for i in ids if i in d.evidence})})
    from studio.strategy.validate import pack_text_audit
    return {"claims": claims, "basis": basis, "pack_text_audit": pack_text_audit(plan, d), "packshot": d.packshot}


def _lines(plan: CampaignPlan):
    from studio.strategy.validate import lines_of
    return lines_of(plan)


def _cl(ln: CopyLine) -> str:
    return f"“{ln.text}”" + (f"  [{', '.join(ln.claim_ids)}]" if ln.claim_ids else "")


def _people(p) -> str:
    return f"{'YES (' + p.people.treatment + ')' if p.people.appear else 'NO'} - {p.people.rationale}" + (f" (casting: {p.people.casting_notes})" if p.people.casting_notes else "")


def _packshot(p) -> list[str]:
    if not p.packshot.used:
        return ["- Product packshot: not used in this post"]
    return [f"- Product packshot: **selected original** (`{p.packshot.packshot_ref}`, {p.packshot.treatment})"] + [f"  - {i}" for i in p.packshot.instructions]


def _basis(items) -> list[str]:
    return [f"- [{b.status}] {b.statement}  ({', '.join(b.evidence_ids) or 'no evidence'})" for b in items]


def brief_carousel(plan: CampaignPlan) -> str:
    c = plan.carousel
    L = [f"# Post 01 - Educational carousel: {c.concept_name}", "", f"**Objective:** {c.objective}", f"**Big idea:** {c.big_idea}",
         f"**Creative device:** {c.creative_device}", f"**Hook:** {_cl(c.hook)}", f"**Narrative arc:** {c.narrative_arc}", f"**Why it gets saved:** {c.save_trigger}",
         f"**People:** {_people(c)}", *_packshot(c), "", "## Slides"]
    for s in c.slides:
        L += [f"### Slide {s.n} - {s.role}", f"- Headline: {_cl(s.headline)}", *[f"- Body: {_cl(b)}" for b in s.body],
              *[f"- REAL LABEL CROP (unaltered): `{x.crop_id}` - {x.purpose}" for x in s.label_crops],
              *[f"- Code-generated callout: {_cl(b)}" for b in s.callouts], f"- Visual: {s.visual_composition}", f"- People in frame: {'yes' if s.people_in_frame else 'no'}", f"- Alt text (hr): {s.alt_text_hr}"]
    L += ["", "## Caption and CTA", f"- Caption (hr): {_cl(c.caption_hr)}", f"- CTA: {_cl(c.cta)}", f"- Hashtags: {' '.join('#' + h.lstrip('#') for h in c.hashtags)}",
          "", f"**Different from the other posts:** {c.distinct_from_others}", "", "## Research basis", *_basis(c.basis)]
    return "\n".join(L) + "\n"


def brief_hero(plan: CampaignPlan) -> str:
    h = plan.hero
    L = [f"# Post 02 - Product hero: {h.concept_name}", "", f"**Objective:** {h.objective}", f"**Big idea:** {h.big_idea}",
         f"**Creative device:** {h.creative_device}", f"**Headline:** {_cl(h.headline)}", *[f"**Supporting copy:** {_cl(x)}" for x in h.supporting_copy], "",
         f"**Art direction:** {h.art_direction}", f"**Lighting:** {h.lighting}", f"**Composition:** {h.composition}", f"**Layout (4:5):** {h.layout}",
         f"**Background palette:** {', '.join(h.background_palette)}", f"**People:** {_people(h)}", *_packshot(h), "",
         f"**Caption (hr):** {_cl(h.caption_hr)}", f"**CTA:** {_cl(h.cta)}", f"**Alt text (hr):** {h.alt_text_hr}",
         f"**Hashtags:** {' '.join('#' + t.lstrip('#') for t in h.hashtags)}", "", f"**Different from the other posts:** {h.distinct_from_others}",
         "", "## Research basis", *_basis(h.basis)]
    return "\n".join(L) + "\n"


def brief_reel(plan: CampaignPlan) -> str:
    r = plan.reel
    L = [f"# Post 03 - Cinematic reel: {r.concept_name}", "", f"**Objective:** {r.objective}", f"**Big idea:** {r.big_idea}", f"**Creative device:** {r.creative_device}", f"**Hook:** {_cl(r.hook)}",
         f"**Total duration:** {r.total_duration_s:g} s ({len(r.shots)} shots)", f"**Pacing:** {r.pacing}", f"**Cover frame:** {r.cover_frame}",
         f"**People:** {_people(r)}", *_packshot(r), "", "## Story",
         f"- Beginning (shots {r.beginning.shot_ns}): {r.beginning.summary}", f"- Development (shots {r.development.shot_ns}): {r.development.summary}",
         f"- Payoff (shots {r.payoff.shot_ns}): {r.payoff.summary}", "", "## Storyboard"]
    t = 0.0
    for s in r.shots:
        L += [f"### Shot {s.n}  ({t:g}-{t + s.duration_s:g} s, {s.duration_s:g} s)", f"- Visual: {s.visual}", f"- Camera: {s.camera_movement}",
              f"- Transition out: {s.transition_out}", f"- Sound: {s.sound}", *[f"- On-screen: {_cl(x)}" for x in s.on_screen_copy],
              f"- Product: {s.product_treatment if s.product_visible else 'not visible'}; people: {s.people_treatment}"]
        t += s.duration_s
    sd = r.sound_design
    L += ["", "## Sound design", f"- Music: {sd.music}", *[f"- SFX: {x}" for x in sd.sfx], *[f"- Voice-over (hr): {_cl(x)}" for x in sd.voiceover_hr],
          f"- Silence: {sd.silence_moments or '-'}", "", "## Product placement", *[f"- {x}" for x in r.product_placement], "",
          f"**Caption (hr):** {_cl(r.caption_hr)}", f"**CTA:** {_cl(r.cta)}", f"**Alt text (hr):** {r.alt_text_hr}",
          f"**Hashtags:** {' '.join('#' + t.lstrip('#') for t in r.hashtags)}", "", f"**Different from the other posts:** {r.distinct_from_others}",
          "", "## Research basis", *_basis(r.basis)]
    return "\n".join(L) + "\n"


def brief_campaign(plan: CampaignPlan) -> str:
    i = plan.identity
    return "\n".join([f"# Campaign: {i.campaign_name}", "", f"**Brand:** {plan.brand} (@{plan.instagram_handle}); focal product: {plan.focal_product.name} (sku {plan.focal_product.sku})",
                      f"**Big idea:** {i.big_idea}", f"**Throughline:** {i.throughline}", f"**Address form:** {i.address_form}", f"**Voice:** {i.voice_notes}",
                      f"**Typography:** {i.typography}", "**Palette use:**", *[f"- {x}" for x in i.palette_use], "**Shared devices:**",
                      *[f"- {x}" for x in i.shared_devices], "", "## Research basis", *_basis(i.basis), "",
                      "## Deferred claims (NOT used anywhere; need separate compliance review)",
                      *[f"- “{x.text}” ({', '.join(x.evidence_ids)}) - {x.why_deferred}; review: {'; '.join(x.review_needed)}" for x in plan.deferred_claims], "",
                      "## Open questions", *[f"- {q}" for q in plan.open_questions]]) + "\n"


def render_review(doc: dict, plan: CampaignPlan, d: Dossier, approval: dict) -> str:
    """Everything the human needs to decide: all three concepts, the exact evidence behind each claim, the approval state."""
    em = evidence_map(plan, d)
    flags = doc["meta"].get("validation_flags") or []
    L = [f"PLAN HASH: {doc['plan_hash']}", f"APPROVAL: {approval['text']}",
         "VALIDATION FLAGS (non-blocking, for you): " + (" | ".join(flags) if flags else "none"), f"MODEL: {doc['meta']['model']}  prompt v{doc['meta']['prompt_version']}  "
         f"calls: {len(doc['meta']['calls'])}", "=" * 78, brief_campaign(plan), "=" * 78, brief_carousel(plan), "=" * 78, brief_hero(plan), "=" * 78,
         brief_reel(plan), "=" * 78, "EVIDENCE BEHIND EVERY CLAIM"]
    for c in em["claims"]:
        L += ["", f"{c['claim_id']} [{c['type']}] {c['text']}" + (f"  (as of {c['as_of']})" if c["as_of"] else ""), f"  basis quote: “{c['basis_quote']}”",
              f"  used in: {', '.join(c['used_in'])}"]
        for e in c["evidence"]:
            L += [f"  - {e['evidence_id']} [{e['status']}] {e['kind']} {e['source_url'] or ''}", f"      {e['text'][:300]}"]
    L += ["", "PACKSHOT (code-injected, not model output)", f"  original: {d.packshot['original_url']}", f"  original sha256: {d.packshot['original_sha256']}",
          f"  cut-out sha256: {d.packshot['cutout_sha256']}", f"  status: {d.packshot['status']}", f"  limitation: {d.packshot['known_limitation']}",
          f"  files verified on disk: {d.packshot['file_hash_verified_on_disk']}"]
    return "\n".join(L) + "\n"
