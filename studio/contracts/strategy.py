"""Phase 3 creative strategy contracts (schema CampaignPlan/2): one campaign, exactly three posts, every material claim
backed by evidence, product imagery only from the selected original packshot or unaltered crops of it.

Structure alone makes "exactly three, one per format" true (named fields, not a free list). Semantic rules (evidence
integrity, contextual claim screening, palette, address form, distinctness, product protection) live in
``studio.strategy.validate`` because they need the research dossier.
"""
from typing import Literal

from pydantic import Field, model_validator

from .base import Contract
from .enums import PostFormat
from .planning import ContentPlan, PostPlan

SCHEMA = "CampaignPlan/2"


class CopyLine(Contract):
    """One piece of exact Croatian text. Typeset by code (never drawn into a generated image)."""

    text: str = Field(min_length=1)
    claim_ids: list[str] = Field(default_factory=list, description="ids (C1, C2...) of campaign claims this text expresses")


class Claim(Contract):
    """A factual statement the campaign may make publicly. Must be traceable to evidence.

    page_fact = a dated fact from the official product page of the carousel product ("Na stranici proizvoda piše: ..."), e.g. a nutrition table value.
    pack_text = printed on the pouch itself ("Na pakiranju piše: ..."); page_graphic = a graphic in the official webshop image, not packaging print
    ("Na stranici proizvoda piše: ..."). Health or performance statements about the product are NOT publishable claims in this campaign: put them
    in ``deferred_claims`` for a separate compliance review."""

    claim_id: str = Field(pattern=r"^C\d+$")
    text: str = Field(min_length=1, description="the claim as it would be published (Croatian)")
    claim_type: Literal["rating", "variant", "pack_text", "page_graphic", "page_fact"]
    evidence_ids: list[str] = Field(min_length=1)
    basis_quote: str = Field(min_length=1, description="exact words copied from the cited evidence that support the claim")
    as_of: str | None = Field(default=None, description="snapshot date YYYY-MM-DD; required for rating")


class DeferredClaim(Contract):
    """A health/performance (or otherwise uncertain) statement the plan deliberately does NOT use."""

    text: str
    evidence_ids: list[str] = Field(min_length=1)
    why_deferred: str
    review_needed: list[str] = Field(min_length=1, description="must include 'conditions of use' for health/performance statements")


class BasisItem(Contract):
    """One research-grounded design decision, labelled by how well it is known."""

    statement: str
    status: Literal["verified", "manual", "assumption", "unavailable"]
    evidence_ids: list[str] = Field(default_factory=list, description="E-... evidence ids or O... observation ids")


class PeopleDecision(Contract):
    appear: bool
    treatment: Literal["none", "hands_only", "faceless_silhouette", "hands_and_silhouette", "fictional_model"]
    rationale: str
    casting_notes: str = Field(default="", description="if people appear: anonymous, faceless, no real or named persons")

    @model_validator(mode="after")
    def _consistent(self):
        if self.appear != (self.treatment != "none"):
            raise ValueError("people.appear must be true exactly when treatment is not 'none'")
        return self


class PackshotUse(Contract):
    used: bool
    packshot_ref: Literal["selected_packshot", "colla_flavour_packshots"] | None = None
    treatment: Literal["unaltered_cutout_composite"] | None = None
    instructions: list[str] = Field(default_factory=list, description="placement, scale, shadow, safe margins, allowed motion; never redraw the pack")

    @model_validator(mode="after")
    def _consistent(self):
        if self.used and (self.packshot_ref is None or self.treatment is None or not self.instructions):
            raise ValueError("a post that shows the product must set packshot_ref, treatment and instructions")
        if not self.used and (self.packshot_ref or self.treatment):
            raise ValueError("packshot_ref/treatment only when used=true")
        return self


class CropUse(Contract):
    crop_id: str = Field(description="id from dossier.label_crops (usable crops only)")
    purpose: str


class CampaignIdentity(Contract):
    campaign_name: str
    big_idea: str
    throughline: str = Field(description="what ties the three posts together")
    address_form: Literal["vi_plural"] = Field(description="Croatian address form; the research shows plural vi/vaš in 22 of 30 captions")
    voice_notes: str
    palette_use: list[str] = Field(min_length=2, description="hex colours with their role; only colours present in the research")
    typography: str
    shared_devices: list[str] = Field(min_length=2, description="recurring visual/verbal devices that make the three posts one family")
    basis: list[BasisItem] = Field(min_length=3)


class FocalProduct(Contract):
    sku: str
    name: str


class SlidePlan(Contract):
    n: int = Field(ge=1)
    role: str
    headline: CopyLine
    body: list[CopyLine] = Field(default_factory=list)
    label_crops: list[CropUse] = Field(default_factory=list, description="unaltered crops of the real label shown on this slide")
    callouts: list[CopyLine] = Field(default_factory=list, description="verified facts rendered by code as SEPARATE callouts beside/over the crop, never inside it")
    visual_composition: str
    people_in_frame: bool
    alt_text_hr: str


class FlavourAsset(Contract):
    name_hr: str
    printed_flavour: str
    variant_sku: str
    fruit: str
    packshot_file: str
    packshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    used_on_slides: list[int] = Field(min_length=1)


class CarouselProduct(Contract):
    """The product the carousel is about when it is not the campaign's focal product (Phase 5: BeastPink Colla Pink)."""

    sku: str
    name: str
    page_url: str
    jar_design: str = Field(description="what the official packshots establish about the pack design")
    flavours: list[FlavourAsset] = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)


class CarouselPost(Contract):
    post_id: Literal["01"] = "01"
    objective: str
    concept_name: str
    big_idea: str
    creative_device: str = Field(description="the one signature mechanic that makes this post unlike the other two")
    hook: CopyLine
    narrative_arc: str
    product: CarouselProduct | None = Field(default=None, description="set when the carousel is about a product other than the focal product")
    slides: list[SlidePlan] = Field(min_length=5, max_length=8)
    save_trigger: str = Field(description="why a viewer would save this post")
    people: PeopleDecision
    packshot: PackshotUse
    caption_hr: CopyLine
    cta: CopyLine
    hashtags: list[str] = Field(default_factory=list, max_length=5)
    distinct_from_others: str
    basis: list[BasisItem] = Field(min_length=2)


class HeroPost(Contract):
    post_id: Literal["02"] = "02"
    objective: str
    concept_name: str
    big_idea: str
    creative_device: str
    headline: CopyLine
    supporting_copy: list[CopyLine] = Field(default_factory=list, max_length=3)
    art_direction: str
    lighting: str
    composition: str
    layout: str = Field(description="text zones, safe margins, hierarchy; 4:5 feed format")
    background_palette: list[str] = Field(min_length=2, description="hex colours from the research only")
    people: PeopleDecision
    packshot: PackshotUse
    caption_hr: CopyLine
    cta: CopyLine
    alt_text_hr: str
    hashtags: list[str] = Field(default_factory=list, max_length=5)
    distinct_from_others: str
    basis: list[BasisItem] = Field(min_length=2)


class Shot(Contract):
    n: int = Field(ge=1)
    duration_s: float = Field(gt=0, le=8)
    visual: str
    camera_movement: str
    transition_out: str
    on_screen_copy: list[CopyLine] = Field(default_factory=list)
    sound: str
    product_visible: bool
    product_treatment: Literal["none", "deterministic_composite"] = Field(
        description="deterministic_composite = the protected packshot placed by code (scale/translate/light only); required whenever product_visible")
    people_in_frame: bool
    people_treatment: Literal["none", "hands", "faceless_silhouette"]


class StoryBeat(Contract):
    shot_ns: list[int] = Field(min_length=1)
    summary: str


class SoundDesign(Contract):
    music: str
    sfx: list[str] = Field(default_factory=list)
    voiceover_hr: list[CopyLine] = Field(default_factory=list, description="empty = no voice-over")
    silence_moments: str = ""


class ReelPost(Contract):
    post_id: Literal["03"] = "03"
    objective: str
    concept_name: str
    big_idea: str
    creative_device: str
    hook: CopyLine
    beginning: StoryBeat
    development: StoryBeat
    payoff: StoryBeat
    shots: list[Shot] = Field(min_length=5, max_length=10)
    total_duration_s: float
    pacing: str
    sound_design: SoundDesign
    product_placement: list[str] = Field(min_length=1)
    cover_frame: str
    people: PeopleDecision
    packshot: PackshotUse
    caption_hr: CopyLine
    cta: CopyLine
    alt_text_hr: str
    hashtags: list[str] = Field(default_factory=list, max_length=5)
    distinct_from_others: str
    basis: list[BasisItem] = Field(min_length=2)


class CampaignPlan(Contract):
    """What the content planner returns (LLM output). Packshot provenance is added by code, not by the model."""

    brand: str
    instagram_handle: str
    focal_product: FocalProduct
    identity: CampaignIdentity
    claims: list[Claim] = Field(default_factory=list)
    deferred_claims: list[DeferredClaim] = Field(default_factory=list)
    carousel: CarouselPost
    hero: HeroPost
    reel: ReelPost
    open_questions: list[str] = Field(default_factory=list, description="things the human must decide or that research could not establish")

    def posts(self) -> dict:
        return {"01": self.carousel, "02": self.hero, "03": self.reel}

    def claim(self, claim_id: str) -> Claim | None:
        return next((c for c in self.claims if c.claim_id == claim_id), None)

    def to_content_plan(self) -> ContentPlan:
        """Compact plan consumed by the (unchanged) production workflow: objective, hook, message, evidence, CTA."""
        def ev(lines) -> list[str]:
            ids: list[str] = []
            for ln in lines:
                for cid in ln.claim_ids:
                    c = self.claim(cid)
                    ids += [e for e in (c.evidence_ids if c else []) if e not in ids]
            return ids

        c, h, r = self.carousel, self.hero, self.reel
        car = [c.hook, c.caption_hr, c.cta] + [x for s in c.slides for x in [s.headline, *s.body, *s.callouts]]
        reel = [r.hook, r.caption_hr, r.cta] + [x for s in r.shots for x in s.on_screen_copy]
        fallback = [e for cl in self.claims for e in cl.evidence_ids][:1] or ["E-18591d8b"]  # the selected packshot evidence: the only product imagery the plan uses
        return ContentPlan(posts=[
            PostPlan(post_id="01", format=PostFormat.CAROUSEL, objective=c.objective, hook=c.hook.text,
                     key_message=c.big_idea, evidence_ids=ev(car) or fallback, cta=c.cta.text),
            PostPlan(post_id="02", format=PostFormat.HERO, objective=h.objective, hook=h.headline.text,
                     key_message=h.big_idea, evidence_ids=ev([h.headline, *h.supporting_copy, h.caption_hr, h.cta]) or fallback,
                     cta=h.cta.text),
            PostPlan(post_id="03", format=PostFormat.REEL, objective=r.objective, hook=r.hook.text,
                     key_message=r.big_idea, evidence_ids=ev(reel) or fallback, cta=r.cta.text),
        ])
