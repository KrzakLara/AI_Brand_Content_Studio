"""Deterministic (no AI) checks of a CampaignPlan against the research dossier.

Returns Problems with a severity. ``error`` blocks the plan from reaching the human gate; ``flag`` is shown to the
human reviewer but does not block. Principle: a material claim must be traceable; health/performance statements about
the product are not publishable here (they are deferred for a separate compliance review); the protected packshot is
never redrawn; context decides (a word is only a problem when it is applied to the product), not a global word ban.
"""
import json
import re
from dataclasses import dataclass

from studio.contracts.strategy import CampaignPlan, CopyLine
from studio.strategy.dossier import FOCAL_NAME, FOCAL_SKU, HEX, Dossier


@dataclass(frozen=True)
class Problem:
    code: str
    where: str
    message: str
    severity: str = "error"  # "error" blocks; "flag" is for the human reviewer

    def __str__(self):
        return f"[{self.code}{'' if self.severity == 'error' else '/flag'}] {self.where}: {self.message}"


def errors(problems: list[Problem]) -> list[Problem]:
    return [p for p in problems if p.severity == "error"]


# Never acceptable anywhere (guarantees, cures, weight loss, clinical proof). Context-free on purpose: these are not ordinary words.
FORBIDDEN = re.compile(
    r"zajam[čc]en|garantir|klini[čc]ki dokaz|znanstveno dokaz|bez nuspojav|nema nuspojav|lije[čc]i|izlije[čc]|"
    r"gubitak (kilogram|masti|tjelesne)|izgubi\w* (kilogram|masti)|mr[šs]a(v|nj)|rezultati? u \d|"
    r"guarantee|clinically|proven|\bcure\b|miracle|no side effects|lose (weight|fat)", re.I)
# Context-dependent vocabulary: only an ERROR when it sits next to a reference to the product, otherwise a FLAG.
HEALTH_TOK = re.compile(r"^(izvedb\w*|u[čc]ink\w*|mi[šs][ić]\w*|snag\w*|snaž\w*|jakost\w*|oporav\w*|energi\w*|performans\w*|sprint\w*|"
                        r"ponavljanj\w*|apsorp\w*|zdrav\w*|muscle|strength|recovery|performance|absorption|energy)$")
NOVELTY_TOK = re.compile(r"^(nov(i|a|o|e|u|im|og|ih|ome)|najnovij\w*|prv(i|a|o|e)|jedin(i|a|o|e)|jedinstven\w*|revolucion\w*|inovativn\w*|"
                         r"napredn\w*|najbolj\w*|bolj(i|a|e|u)|bolje|najbrž\w*|nadmaš\w*|vrhunsk\w*|vodeć\w*|poboljšan\w*|"
                         r"new|best|better|first|only|advanced|improved|superior)$")
PRODUCT_TOK = re.compile(r"^(kreatin\w*|proizvod\w*|dodat(ak|ka|ku|kom|cima)|formul\w*|pakiranj\w*|vrećic\w*|prah\w*|prašak\w*|gymbeam)$")
HEALTH_DIST, NOVELTY_DIST = 6, 4
NEW_PACK = re.compile(r"nov(o|om|og)\s+pakiranj|nova\s+(generacij|ambalaž)|new pack", re.I)
QTY = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:g|kg|mg|ml|kapsul\w*|kaps|tablet\w*|posluživanj\w*|doz(?:a|e|u|i|ama))\b|"
                 r"\b(?:doza|doze|dozu|posluživanje|posluživanja|žlic\w*|žličic\w*|mjeric\w*|scoops?|servings?)\b", re.I)
INFORMAL = re.compile(r"\b(ti|tvoj\w*|tebe|tebi|tobom|budi|probaj|kreni)\b", re.I)
ENGLISH = re.compile(r"\b(the|and|your|with|for|you|is|are|of|this|that)\b", re.I)
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
COUNTER = re.compile(r"^\s*0?\d\s*/\s*0?\d\s*$")
WORD = re.compile(r"\w+", re.U)
SENT = re.compile(r"(?<=[.!?…])\s+|\n")
# Product-protection heuristic: a pack noun and a "drawn/made-up" word in one sentence, unless negated.
PACK_NOUN = re.compile(r"vrećic|pakiranj|pouch|\bpack\b|\bbag\b|etiket|naljepnic|\blabel\b|\bbadge|bedž", re.I)
REDRAW = re.compile(r"ilustrac|crtež|crtan|nacrt|iscrt|\bikon|stiliz|generir|redizajn|apstraktn|simbol|illustrat|redraw|\brender|vector|"
                    r"mock-?up|replik|imitir|simulir|re-?creat|ponovno (nacrt|stvor|generir)", re.I)
NEGATION = re.compile(r"\b(bez|nikad\w*|ne|nije|nema|never|no|not|without|zabranjen\w*|ne smije|isključivo)\b", re.I)


def norm(s: str) -> str:
    return " ".join(re.findall(r"\w+|[%€#]", s.casefold(), re.U))


def _words(s: str) -> list[str]:
    return WORD.findall(s.casefold())


def _numbers(s: str) -> set[str]:
    out = set()
    for n in NUMBER.findall(s):
        n = n.replace(",", ".")
        out.add(n)
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", n):  # Croatian thousands separator: 8.291 == 8291
            out.add(n.replace(".", ""))
    return out


def _date_parts(e: dict) -> set[str]:
    """A snapshot date printed in copy (27. 10. 2026.) is backed by the evidence's retrieved_at, not by its quote."""
    y, m, d = (e.get("retrieved_at") or "0000-00-00")[:10].split("-")
    return {y, m, d, m.lstrip("0"), d.lstrip("0")} - {"", "0000", "00"}


def _evidence_text(e: dict) -> str:
    return " ".join([e["claim"], e["quote"], json.dumps(e.get("structured_value") or {}, ensure_ascii=False)])


def _near(sentence: str, term: re.Pattern, ref: re.Pattern, dist: int) -> tuple[bool, bool]:
    """(term present, term within ``dist`` tokens of a product reference)."""
    toks = _words(sentence)
    t = [i for i, w in enumerate(toks) if term.match(w)]
    r = [i for i, w in enumerate(toks) if ref.match(w)]
    return bool(t), any(abs(i - j) <= dist for i in t for j in r)


def lines_of(plan: CampaignPlan) -> list[tuple[str, CopyLine]]:
    """Every publishable text: copy, captions, callouts, voice-over and alt texts."""
    c, h, r = plan.carousel, plan.hero, plan.reel
    out = [("carousel.hook", c.hook), ("carousel.caption", c.caption_hr), ("carousel.cta", c.cta)]
    for s in c.slides:
        out += [(f"carousel.slide{s.n}.headline", s.headline)] + [(f"carousel.slide{s.n}.body{i}", b) for i, b in enumerate(s.body)]
        out += [(f"carousel.slide{s.n}.callout{i}", b) for i, b in enumerate(s.callouts)]
        out.append((f"carousel.slide{s.n}.alt", CopyLine(text=s.alt_text_hr)))
    out += [("hero.headline", h.headline), ("hero.caption", h.caption_hr), ("hero.cta", h.cta), ("hero.alt", CopyLine(text=h.alt_text_hr))]
    out += [(f"hero.support{i}", x) for i, x in enumerate(h.supporting_copy)]
    out += [("reel.hook", r.hook), ("reel.caption", r.caption_hr), ("reel.cta", r.cta), ("reel.alt", CopyLine(text=r.alt_text_hr))]
    for s in r.shots:
        out += [(f"reel.shot{s.n}.copy{i}", x) for i, x in enumerate(s.on_screen_copy)]
    out += [(f"reel.voiceover{i}", x) for i, x in enumerate(r.sound_design.voiceover_hr)]
    return out


def _visual_strings(plan: CampaignPlan) -> list[tuple[str, str]]:
    c, h, r = plan.carousel, plan.hero, plan.reel
    out = [(f"carousel.slide{s.n}.visual", s.visual_composition) for s in c.slides]
    out += [("hero.art_direction", h.art_direction), ("hero.composition", h.composition), ("hero.layout", h.layout), ("hero.lighting", h.lighting)]
    out += [(f"reel.shot{s.n}.visual", s.visual) for s in r.shots] + [(f"reel.placement{i}", t) for i, t in enumerate(r.product_placement)]
    out += [("reel.cover_frame", r.cover_frame)]
    return out


def _strip_product_name(t: str) -> str:
    return re.sub(re.escape(FOCAL_NAME), " ", t, flags=re.I).replace("100% Kreatin Monohidrat", " ")


def _windows(text: str, n: int = 4) -> set[str]:
    w = _words(text)
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def validate_plan(plan: CampaignPlan, d: Dossier) -> list[Problem]:
    P: list[Problem] = []

    def add(code, where, msg, sev="error"):
        P.append(Problem(code, where, msg, sev))

    reg = d.evidence

    # ---- structure the schema cannot express -----------------------------------------------------
    if plan.focal_product.sku != FOCAL_SKU:
        add("focal_product", "focal_product", f"focal product must be sku {FOCAL_SKU}, got {plan.focal_product.sku}")
    if [s.n for s in plan.carousel.slides] != list(range(1, len(plan.carousel.slides) + 1)):
        add("slides", "carousel", "slides must be numbered 1..n in order")
    shots = plan.reel.shots
    if [s.n for s in shots] != list(range(1, len(shots) + 1)):
        add("shots", "reel", "shots must be numbered 1..n in order")
    total = round(sum(s.duration_s for s in shots), 2)
    if abs(total - plan.reel.total_duration_s) > 0.05:
        add("duration", "reel", f"total_duration_s {plan.reel.total_duration_s} != sum of shot durations {total}")
    if not 12 <= total <= 30:
        add("duration", "reel", f"reel must run 12-30 s, storyboard sums to {total}")
    beats = [plan.reel.beginning.shot_ns, plan.reel.development.shot_ns, plan.reel.payoff.shot_ns]
    if sorted(n for b in beats for n in b) != [s.n for s in shots]:
        add("story", "reel", "beginning/development/payoff must partition every shot exactly once")
    elif max(beats[0]) >= min(beats[1]) or max(beats[1]) >= min(beats[2]):
        add("story", "reel", "beats must be consecutive: beginning < development < payoff")
    lock = d.constraints.get("hero_headline")
    if lock and plan.hero.headline.text.strip() != lock:
        add("locked_copy", "hero.headline", f"the human locked the hero headline as {lock!r}")

    # ---- people ------------------------------------------------------------------------------------
    flags = {"01": [s.people_in_frame for s in plan.carousel.slides], "03": [s.people_in_frame for s in shots]}
    for who, post in plan.posts().items():
        if who in flags and post.people.appear != any(flags[who]):
            add("people", who, f"people.appear={post.people.appear} contradicts the per-frame people flags")
        if who == "02" and post.people.appear:
            add("people", who, "the hero keeps the product alone (no people) in this campaign")
        if post.people.appear and not post.people.casting_notes.strip():
            add("people", who, "people appear but casting_notes is empty")
    r = plan.reel
    if not r.people.appear:
        add("people", "03", "the reel must show hands, movement or faceless silhouettes in selected shots (human decision)")
    want = {"hands_only": {"hands"}, "faceless_silhouette": {"faceless_silhouette"}, "hands_and_silhouette": {"hands", "faceless_silhouette"},
            "none": set()}[r.people.treatment]
    got = {s.people_treatment for s in shots} - {"none"}
    if got != want:
        add("people", "03", f"people.treatment {r.people.treatment!r} does not match the shots' people_treatment {sorted(got)}")
    if r.people.appear and all(s.people_in_frame for s in shots):
        add("people", "03", "people must appear only in SELECTED shots, not every shot")
    for s in shots:
        if s.people_in_frame != (s.people_treatment != "none"):
            add("people", f"reel.shot{s.n}", "people_in_frame disagrees with people_treatment")
        if s.product_visible != (s.product_treatment == "deterministic_composite"):
            add("product_protection", f"reel.shot{s.n}", "a visible product must use product_treatment=deterministic_composite (and only then)")
        if s.product_visible and s.people_in_frame and s.people_treatment != "faceless_silhouette":
            add("product_protection", f"reel.shot{s.n}", "hands must never share a shot with the protected product (no generated contact with the pack); "
                                                         "only a faceless background silhouette may")

    # ---- packshot / label crops ---------------------------------------------------------------------
    for who in ("02", "03"):
        if not plan.posts()[who].packshot.used:
            add("packshot", who, "this post must show the product using the selected original packshot")
    if not any(s.product_visible for s in shots):
        add("packshot", "03", "no reel shot shows the product")
    for s in plan.carousel.slides:
        for cu in s.label_crops:
            if cu.crop_id not in d.crops:
                add("label_crop", f"carousel.slide{s.n}", f"crop {cu.crop_id!r} is not an available label crop ({sorted(d.crops)})")
        for ln in [s.headline, *s.body]:
            if ln.claim_ids:
                add("fact_not_callout", f"carousel.slide{s.n}", f"verified fact {ln.text!r} must be rendered as a separate callout, not as headline/body text")
    for where, text in _visual_strings(plan) + [(f"{w}.instructions", i) for w, p in plan.posts().items() for i in p.packshot.instructions]:
        for sent in SENT.split(text):
            if PACK_NOUN.search(sent) and REDRAW.search(sent) and not NEGATION.search(sent):
                add("packaging_redraw", where, f"possible redrawn/imagined packaging: {sent.strip()[:90]!r} (only the selected packshot or unaltered crops may show packaging)")

    pr = plan.carousel.product
    if pr is not None:
        for eid in pr.evidence_ids:
            if eid not in reg:
                add("unknown_evidence", "carousel.product", f"evidence id {eid!r} is not in the evidence registry")
        for f in pr.flavours:
            if any(n < 1 or n > len(plan.carousel.slides) for n in f.used_on_slides):
                add("product", "carousel.product", f"flavour {f.name_hr!r} is assigned to a slide that does not exist")
        if plan.carousel.packshot.packshot_ref != "colla_flavour_packshots":
            add("packshot", "01", "a carousel about another product must use its own official flavour packshots (packshot_ref colla_flavour_packshots)")
    elif plan.carousel.packshot.packshot_ref == "colla_flavour_packshots":
        add("packshot", "01", "colla_flavour_packshots needs carousel.product")

    # ---- claims: evidence integrity --------------------------------------------------------------
    seen: set = set()
    for c in plan.claims:
        w = f"claim {c.claim_id}"
        if c.claim_id in seen:
            add("claim_dup", w, "duplicate claim id")
        seen.add(c.claim_id)
        evs = []
        for eid in c.evidence_ids:
            e = reg.get(eid)
            if e is None:
                add("unknown_evidence", w, f"evidence id {eid!r} is not in the evidence registry")
            else:
                evs.append(e)
        if len(evs) != len(c.evidence_ids):
            continue
        if any(e.get("mock") for e in evs):
            add("mock_evidence", w, "claim cites mock evidence")
        etxt = " ".join(_evidence_text(e) for e in evs)
        if norm(c.basis_quote) not in norm(etxt):
            add("basis_quote", w, "basis_quote is not found verbatim in the cited evidence")
        allowed = _numbers(etxt).union(*(_date_parts(e) for e in evs))
        def backed(x):  # 8.291 (hr thousands separator) is backed by 8291
            return x in allowed or (re.fullmatch(r"\d{1,3}(\.\d{3})+", x) is not None and x.replace(".", "") in allowed)
        for n in sorted(x for x in _numbers(_strip_product_name(c.text)) if not backed(x)):
            add("number_unsupported", w, f"number {n!r} does not appear in the cited evidence")
        subj = {e["subject"] for e in evs}
        if c.claim_type in ("variant", "rating"):
            kind = {"variant": "product_variant", "rating": "product_rating"}[c.claim_type]
            if subj != {kind}:
                add("claim_type", w, f"{c.claim_type} cannot rest on evidence of kind {sorted(subj)}")
            if not all(e["verification_status"] == "verified" for e in evs):
                add("claim_status", w, f"{c.claim_type} claims need VERIFIED evidence")
            if not all(d.family.get(e["evidence_id"]) == FOCAL_SKU for e in evs):
                add("wrong_product", w, f"evidence is not about the focal product sku {FOCAL_SKU}")
        elif c.claim_type == "pack_text":
            physical = all(e["subject"] == "packaging_observation" and "NEW pack" in e["claim"]
                           or e["subject"] == "label_crop" and (e.get("structured_value") or {}).get("origin") == "physical_packaging" for e in evs)
            if not subj <= {"packaging_observation", "label_crop"} or not physical:
                add("pack_text_origin", w, "pack_text ('Na pakiranju piše') may only rest on text PRINTED ON THE POUCH; webshop graphics and uncertain origins cannot")
            if not PACK_PREFIX.match(c.text):
                add("claim_prefix", w, "a pack_text claim must start with 'Na pakiranju piše:'")
        elif c.claim_type == "page_fact":
            if subj != {"colla_page_fact"} or not all(e["verification_status"] == "verified" and e["evidence_id"].startswith("E-colla-") for e in evs):
                add("page_fact_origin", w, "page_fact ('Na stranici proizvoda piše') may only rest on VERIFIED facts of the carousel product's official page (E-colla-*)")
            if not PAGE_PREFIX.match(c.text):
                add("claim_prefix", w, "a page_fact claim must start with 'Na stranici proizvoda piše:'")
            if any(e["evidence_id"] == "E-colla-health-wording" for e in evs):
                add("health_claim_not_publishable", w, "benefit wording of the product page is deferred for a compliance review, not publishable")
        else:  # page_graphic
            if subj != {"label_crop"} or not all((e.get("structured_value") or {}).get("origin") == "webshop_graphic" for e in evs):
                add("page_graphic_origin", w, "page_graphic ('Na stranici proizvoda piše') may only rest on verified webshop-graphic crops")
            if not PAGE_PREFIX.match(c.text):
                add("claim_prefix", w, "a page_graphic claim must start with 'Na stranici proizvoda piše:'")
        if c.claim_type == "rating" and c.as_of not in {e.get("retrieved_at", "")[:10] for e in evs}:
            add("rating_date", w, "rating claims need as_of equal to the snapshot date of the evidence")
        if any(HEALTH_TOK.match(t) for t in _words(c.text)):
            add("health_claim_not_publishable", w, "health/performance wording cannot be a publishable claim here: move it to deferred_claims")
        if FORBIDDEN.search(c.text):
            add("forbidden", w, "claim uses forbidden absolute/guarantee/cure wording")
    banned_windows: set[str] = set()
    for e in reg.values():
        if e["subject"] == "product_description":
            banned_windows |= _windows(e["quote"])
    for i, dc in enumerate(plan.deferred_claims):
        banned_windows |= _windows(dc.text)
        for eid in dc.evidence_ids:
            if eid not in reg:
                add("unknown_evidence", f"deferred claim {i}", f"evidence id {eid!r} is not in the evidence registry")
        if any(HEALTH_TOK.match(t) for t in _words(dc.text)) and not any(re.search(r"uvjet|conditions", x, re.I) for x in dc.review_needed):
            add("deferred_review", f"deferred claim {i}", "a health/performance claim's review_needed must include the conditions of use")

    # ---- copy: contextual screening ----------------------------------------------------------------
    claims = {c.claim_id: c for c in plan.claims}
    used: set = set()
    for where, ln in lines_of(plan):
        t = ln.text
        for cid in ln.claim_ids:
            used.add(cid)
            if cid not in claims:
                add("unknown_claim", where, f"references unknown claim {cid}")
        if FORBIDDEN.search(t):
            add("forbidden", where, f"forbidden wording in {t!r}")
        if INFORMAL.search(t):
            add("address", where, f"informal 2nd-person address in {t!r}; research shows plural vi/vaš")
        if NEW_PACK.search(t):
            add("unverified_new_pack", where, "which pack generation ships is unverified: no 'new packaging' statement")
        if QTY.search(t) and not any(claims[c].claim_type == "page_fact" for c in ln.claim_ids if c in claims):  # a dated page fact may carry its quantity
            add("quantity", where, f"quantity wording in {t!r}: the selected packshot prints no size, so no quantity can be matched to it")
        if _windows(t) & banned_windows:
            add("verbatim_product_claim", where, f"{t!r} reuses product-page health/performance wording; such claims need separate compliance review (deferred_claims)")
        for sent in SENT.split(t):
            has_h, near_h = _near(sent, HEALTH_TOK, PRODUCT_TOK, HEALTH_DIST)
            if near_h:
                add("health_claim_in_copy", where, f"health/performance wording applied to the product in {sent!r}: omit or defer for compliance review")
            elif has_h:
                add("health_term_context", where, f"health-related word in {sent!r} (not applied to the product): reviewer please confirm", "flag")
            has_n, near_n = _near(sent, NOVELTY_TOK, PRODUCT_TOK, NOVELTY_DIST)
            if near_n:
                add("unsupported_comparative", where, f"comparative/novelty wording applied to the product in {sent!r}: no evidence supports it")
            elif has_n:
                add("novelty_word_context", where, f"comparative/novelty word in {sent!r} (not applied to the product)", "flag")
        if COUNTER.match(t):
            continue
        if re.search(r"[€$]|\beur\b", t, re.I):
            add("price", where, "prices are snapshots and must not appear in copy")
        has = [claims[c] for c in ln.claim_ids if c in claims]
        # An alt text may TRANSCRIBE text printed on a real label crop shown on the same slide (it describes the original image,
        # it is not a claim). Numerals that are not printed on such a crop still need a claim.
        m = re.fullmatch(r"carousel\.slide(\d+)\.alt", where)
        printed: set[str] = set()
        if m:
            sl = next(s for s in plan.carousel.slides if s.n == int(m.group(1)))
            printed = _numbers(" ".join(" ".join(d.crops[cu.crop_id]["printed_text"]) for cu in sl.label_crops if cu.crop_id in d.crops))
        if (_numbers(_strip_product_name(t)) - printed) and not has:
            add("number_unbacked", where, f"number in {t!r} has no claim_ids")
        if ENGLISH.search(t) and not has:
            add("english_in_copy", where, f"English words in {t!r}: confirm this is intended Croatian copy", "flag")
    for cid in claims:
        if cid not in used:
            add("claim_unused", f"claim {cid}", "declared but no copy line uses it", "flag")

    pack_and_alt_checks(plan, d, add)

    # ---- copy must not be recycled between posts ---------------------------------------------------
    owner: dict[str, str] = {}
    for where, ln in lines_of(plan):
        if where.endswith((".cta", ".caption")) or ".alt" in where:
            continue
        k = norm(ln.text)
        if k in owner and owner[k].split(".")[0] != where.split(".")[0] and len(k.split()) >= 3:
            add("copy_reused", where, f"same copy line already used in {owner[k]}")
        owner.setdefault(k, where)

    # ---- identity: palette, hashtags, basis labels -----------------------------------------------
    text = json.dumps(plan.model_dump(mode="json"), ensure_ascii=False)
    for hx in sorted({h.lower() for h in HEX.findall(text)}):
        if hx not in d.hexes:
            add("palette", "plan", f"colour {hx} does not occur in the research palette")
    for who, post in plan.posts().items():
        for tag in post.hashtags:
            if tag.lstrip("#").lower() not in d.hashtags:
                add("hashtag", who, f"hashtag {tag!r} is not one the brand uses (observed in 30 posts)")
        for b in post.basis:
            _check_basis(b, f"{who}.basis", d, add)
    for b in plan.identity.basis:
        _check_basis(b, "identity.basis", d, add)

    # ---- distinctness ----------------------------------------------------------------------------
    if len({p.concept_name.casefold() for p in plan.posts().values()}) != 3:
        add("distinct", "plan", "concept names must differ")
    hooks = {"01": plan.carousel.hook.text, "02": plan.hero.headline.text, "03": plan.reel.hook.text}
    ideas = {k: {w for w in _words(f"{p.concept_name} {p.big_idea} {p.creative_device}") if len(w) > 3} for k, p in plan.posts().items()}
    ks = sorted(hooks)
    for i in range(3):
        for j in range(i + 1, 3):
            a, b = set(_words(hooks[ks[i]])), set(_words(hooks[ks[j]]))
            if a and b and len(a & b) / len(a | b) > 0.5:
                add("distinct", f"{ks[i]}/{ks[j]}", "hooks are near-duplicates")
            ia, ib = ideas[ks[i]], ideas[ks[j]]
            if ia and ib and len(ia & ib) / len(ia | ib) > 0.45:
                add("distinct", f"{ks[i]}/{ks[j]}", "concept/idea/device wording overlaps too much for distinct concepts")
    for who, post in plan.posts().items():
        if len(post.distinct_from_others.strip()) < 40:
            add("distinct", who, "distinct_from_others must explain the difference")
        if len(post.creative_device.strip()) < 15:
            add("distinct", who, "creative_device must name the post's signature mechanic")
    return P


def _check_basis(b, where: str, d: Dossier, add) -> None:
    ids: list[str] = []
    for i in b.evidence_ids:
        if i.startswith("O"):
            if i not in d.obs_evidence:
                add("unknown_evidence", where, f"observation {i!r} does not exist")
            ids += d.obs_evidence.get(i, [])
        elif i in d.evidence:
            ids.append(i)
        else:
            add("unknown_evidence", where, f"evidence {i!r} does not exist")
    if b.status == "unavailable" and b.evidence_ids:
        add("basis_status", where, "'unavailable' items must not cite evidence")
    stat = {d.evidence[i]["verification_status"] for i in ids if i in d.evidence}
    if b.status == "verified" and (not ids or stat != {"verified"}):
        add("basis_status", where, f"'verified' basis {b.statement[:50]!r} must cite only verified evidence (found {sorted(stat)})")
    if b.status == "manual":
        if not ids or stat - {"manual", "verified"}:
            add("basis_status", where, f"'manual' basis {b.statement[:50]!r} must cite manual or verified evidence (found {sorted(stat)})")
        elif "manual" not in stat:  # under-claiming is harmless: the human just sees a conservative label
            add("basis_label", where, f"'manual' basis {b.statement[:50]!r} actually rests on verified evidence only", "flag")


# ---- pack-text and alt-text safeguards ---------------------------------------------------------------------------------------------
PACK_PREFIX = re.compile(r"^\s*Na pakiranju piše:\s*", re.I)
PAGE_PREFIX = re.compile(r"^\s*Na stranici proizvoda piše:\s*", re.I)
# Alt-text vocabulary that ASSERTS something about packaging wording or quality. Each needs its printed counterpart on a crop
# shown on the SAME slide; otherwise the alt text would smuggle in packaging information the image does not contain.
ALT_PACK_TERMS = [
    (re.compile(r"^(certific\w*|certified)$"), {"certified"}), (re.compile(r"^(testiran\w*|ispitan\w*|tested)$"), {"tested"}),
    (re.compile(r"^(čist\w*|pure)$"), {"pure"}), (re.compile(r"^(jamstv\w*|jamč\w*|garanc\w*|guaranteed)$"), {"guaranteed"}),
    (re.compile(r"^(kvalitet\w*|quality)$"), {"quality"}), (re.compile(r"^(apsorp\w*|absorption)$"), {"absorption"}),
    (re.compile(r"^(brz\w*|rapid|fast|effect|učink\w*)$"), {"rapid", "fast", "effect"}), (re.compile(r"^(micronised|mikroniz\w*)$"), {"micronised"}),
    (re.compile(r"^(njemačk\w*|germany)$"), {"germany"}), (re.compile(r"^(laboratorij\w*|lab)$"), {"lab"}),
    (re.compile(r"^hplc$"), {"hplc"}), (re.compile(r"^ifs$"), {"ifs"})]
QUOTED = re.compile(r"[„\"“«]([^„\"“”»]{2,})[“\"”»]")


def _printed_words(d: Dossier, crop_ids) -> set[str]:
    return {w for cid in crop_ids if cid in d.crops for t in d.crops[cid]["printed_text"] for w in _words(t)}


def pack_text_audit(plan: CampaignPlan, d: Dossier) -> list[dict]:
    """Every 'Na pakiranju piše: ...' statement and where its wording is really printed. Used by the validator and exported."""
    rows = []
    claims = {c.claim_id: c for c in plan.claims}
    slide_of = {f"carousel.slide{s.n}": s for s in plan.carousel.slides}
    for where, ln in lines_of(plan):
        pack, page = PACK_PREFIX.match(ln.text), PAGE_PREFIX.match(ln.text)
        if not (pack or page) or any(claims[c].claim_type == "page_fact" for c in ln.claim_ids if c in claims):  # page_fact is checked in validate_plan
            continue
        rest = (PACK_PREFIX if pack else PAGE_PREFIX).sub("", ln.text)
        cs = [claims[c] for c in ln.claim_ids if c in claims]
        want = "pack_text" if pack else "page_graphic"
        type_ok = bool(cs) and all(c.claim_type == want for c in cs)
        ev_words = {w for c in cs for e in c.evidence_ids if e in d.evidence for w in _words(_evidence_text(d.evidence[e]))}
        slide = slide_of.get(where.rsplit(".", 1)[0]) if where.startswith("carousel.slide") else None
        slide_crops = [cu.crop_id for cu in slide.label_crops] if slide else []
        slide_words = _printed_words(d, slide_crops)
        in_ev = set(_words(rest)) <= ev_words if cs else False
        on_slide = (set(_words(rest)) <= slide_words) if slide else None
        cites_slide_crop = any(f"E-crop-{c}" in cl.evidence_ids for c in slide_crops for cl in cs) if slide else None
        origins = {(d.evidence[e].get("structured_value") or {}).get("origin", "physical_packaging") for c in cs for e in c.evidence_ids if e in d.evidence}
        origin_ok = origins <= ({"physical_packaging"} if pack else {"webshop_graphic"}) and bool(origins)
        ok = in_ev and type_ok and origin_ok and (on_slide and cites_slide_crop if slide else True)
        visible = ("crop(s) on this slide: " + ", ".join(slide_crops)) if slide and slide_crops else ("NO crop on this slide" if slide else "selected packshot (original image)")
        rows.append({"location": where, "text": ln.text, "claims": ln.claim_ids, "visible_on": visible, "statement_type": want, "origins": sorted(origins),
                     "status": "verified against crop/evidence text" if ok else "NOT VERIFIED",
                     "evidence": sorted({e for c in cs for e in c.evidence_ids}), "evidence_status": "manual (operator-labelled)"})
    return rows


def pack_and_alt_checks(plan: CampaignPlan, d: Dossier, add) -> None:
    for r in pack_text_audit(plan, d):
        if r["status"] == "NOT VERIFIED":
            add("pack_text_not_verified", r["location"], f"{r['text']!r}: wording is not verified for {r['visible_on']} (origin {r['origins']}, statement type "
                                                         f"{r['statement_type']}): 'Na pakiranju piše' needs text printed on the pouch, 'Na stranici proizvoda piše' needs a webshop graphic")
    slides = {s.n: s for s in plan.carousel.slides}
    alts = [(f"carousel.slide{n}.alt", s.alt_text_hr, [cu.crop_id for cu in s.label_crops]) for n, s in slides.items()]
    alts += [("hero.alt", plan.hero.alt_text_hr, []), ("reel.alt", plan.reel.alt_text_hr, [])]
    for where, alt, crops in alts:
        origins = {d.crops[c]["origin"] for c in crops if c in d.crops}
        if origins == {"webshop_graphic"} and re.search(r"\bpakiranj\w*", alt, re.I):
            add("alt_origin", where, "this slide shows only a webshop graphic: alt text must not say it is from/on the packaging")
        printed = _printed_words(d, crops)
        asserted = False
        for tok in _words(alt):
            for rx, need in ALT_PACK_TERMS:
                if rx.match(tok):
                    asserted = True
                    if not (need & printed):
                        add("alt_text_unverified_packaging_text", where, f"alt text uses {tok!r}, which is not printed on a crop shown on this slide "
                                                                         f"(crops: {crops or 'none'}); alt text may only transcribe what the crop really shows")
        for q in QUOTED.findall(alt):
            asserted = True
            if not set(_words(q)) <= printed:
                add("alt_text_unverified_packaging_text", where, f"quoted wording {q!r} is not printed on a crop shown on this slide")
        for w in ENGLISH.findall(alt):
            asserted = True
            if w.lower() not in printed:
                add("alt_text_unverified_packaging_text", where, f"English wording {w!r} in alt text is not printed on a crop shown on this slide")
        if asserted or (crops and NUMBER.search(alt)):
            add("alt_text_transcription", where, "alt text transcribes label wording; verified against the operator-labelled crop text, "
                                                 "the human should still compare it with the crop image", "flag")
