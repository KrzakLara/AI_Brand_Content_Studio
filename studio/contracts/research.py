import re
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .base import Contract

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


Origin = Literal["live", "fixture", "manual_import", "mock"]


class SourceItem(Contract):
    """One entry of the source index. ``kind`` is the source type."""

    source_id: str
    url: str
    title: str
    kind: str = "web_page"
    content_sha256: str = ""
    mock: bool = False
    origin: Origin = "mock"
    retrieval_status: str = "ok"  # ok | failed | blocked | skipped | not_collected
    retrieved_at: datetime | None = None
    artifact_path: str | None = None  # relative to the run directory
    artifact_sha256: str | None = None
    record_sha256: str | None = None  # hash of one record inside a shared artifact
    access_limitations: str = ""
    flags: list[str] = Field(default_factory=list)  # e.g. possible_prompt_injection
    provenance: dict = Field(default_factory=dict)


class SourceIndex(Contract):
    sources: list[SourceItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique(self):
        ids = [s.source_id for s in self.sources]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate source_id")
        return self


class EvidenceItem(Contract):
    evidence_id: str
    claim: str
    source_id: str
    quote: str
    confidence: float = Field(ge=0.0, le=1.0)
    mock: bool = False
    origin: Origin = "mock"
    subject: str = ""  # product_variant | product_description | instagram_post | ...
    source_url: str = ""
    retrieved_at: datetime | None = None
    # verified = excerpt re-found in the stored artifact; manual = operator-attested with provenance
    verification_status: Literal["verified", "manual", "unverified", "failed"] = "unverified"
    verification_note: str = ""
    packaging_variant: str | None = None  # exact variant key; never merged across variants
    structured_value: dict = Field(default_factory=dict)


class EvidenceRegistry(Contract):
    items: list[EvidenceItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique(self):
        ids = [i.evidence_id for i in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate evidence_id")
        return self

    def ids(self) -> set[str]:
        return {i.evidence_id for i in self.items}

    def check_sources(self, index: SourceIndex) -> None:
        known = {s.source_id for s in index.sources}
        missing = {i.source_id for i in self.items} - known
        if missing:
            raise ValueError(f"evidence references unknown sources: {sorted(missing)}")


class Observation(Contract):
    """A statement about the brand, with how much we know about it."""

    statement: str
    status: Literal["verified", "manual", "assumption", "unknown"]
    basis: str = ""  # how it was established (e.g. "computed from 10 imported posts")
    evidence_ids: list[str] = Field(default_factory=list)
    post_urls: list[str] = Field(default_factory=list)  # the concrete posts this conclusion rests on


class ExamplePost(Contract):
    source_id: str
    url: str
    shortcode: str
    post_type: str
    posted_at: datetime
    caption_excerpt: str
    hashtags: list[str] = Field(default_factory=list)
    likes: int | None = None  # None = hidden/unknown; never invented
    comments: int | None = None
    metrics_collected_at: datetime | None = None
    evidence_id: str = ""
    origin: Origin = "mock"


class VariantEntry(Contract):
    sku: str
    name: str
    size: str = ""
    flavor: str = ""
    price: float | None = None
    currency: str = ""
    gtin13: str = ""
    availability: str = ""
    price_retrieved_at: datetime | None = None  # when this price was read from the shop
    evidence_id: str = ""
    packaging_generation: Literal["unverified"] = "unverified"  # not knowable from text data


class PackagingObservation(Contract):
    """What a gallery image shows about the pack. Operator-attested, never auto-verified."""

    generation: Literal["old", "new", "split_comparison"]
    view: str = ""  # front | back | lifestyle | comparison
    size: str = ""
    flavor: str = ""
    image_source_id: str
    evidence_id: str
    includes_gift_merchandise: bool = False


class ProductEntry(Contract):
    brand: str = ""
    product_family: str  # one product page; variants are never merged across pages
    url: str
    sku: str
    name: str
    description_excerpt: str = ""
    image_source_ids: list[str] = Field(default_factory=list)
    alias_urls: list[str] = Field(default_factory=list)  # other URLs serving the same sku
    packaging_observations: list[PackagingObservation] = Field(default_factory=list)
    variants: list[VariantEntry] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ColorEntry(Contract):
    hex: str
    scope: str  # "website" - not Instagram
    basis: str
    frequency: int | None = None
    status: Literal["verified", "manual", "assumption"] = "verified"
    post_urls: list[str] = Field(default_factory=list)  # posts this colour was measured in (Instagram scope)


class FontEntry(Contract):
    family: str
    scope: str
    basis: str
    frequency: int
    status: Literal["verified", "assumption"] = "verified"


class PackshotSelection(Contract):
    """The packshot chosen to represent the CURRENT pack, with how and when it was obtained."""

    source_id: str
    url: str
    retrieved_at: datetime | None = None
    last_modified: str | None = None  # server's Last-Modified header = when the file was published
    pack_generation: str
    view: str
    format: str
    width: int | None = None
    height: int | None = None
    meets_min_resolution: bool
    alpha_capable: bool
    has_transparency: bool
    transparent_background: bool
    background_hex: str | None = None
    selection_basis: list[str] = Field(default_factory=list)
    rejected: list[dict] = Field(default_factory=list)  # [{url, reasons}]
    corroborating_post_urls: list[str] = Field(default_factory=list)
    cutout_source_id: str | None = None  # derived transparent PNG, when one was needed
    cutout: dict | None = None
    status: Literal["manual", "assumption"] = "manual"  # generation/view are operator-attested
    evidence_id: str = ""


class FontChoice(Contract):
    family: str
    status: Literal["verified", "assumption"]  # is this really the brand's (web) font?
    basis: str
    recommended_use: str
    recommended_use_status: Literal["verified", "assumption"] = "assumption"
    license_note: str = ""
    fallbacks: list[str] = Field(default_factory=list)
    logotype_note: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    observed_in_posts: list[str] = Field(default_factory=list)


class BrandProfile(Contract):
    brand_name: str
    positioning: str
    voice: str
    palette: list[str] = Field(default_factory=list)
    dos: list[str] = Field(default_factory=list)
    donts: list[str] = Field(default_factory=list)
    banned_phrases: list[str] = Field(default_factory=list)
    product_fact_ids: list[str] = Field(default_factory=list)
    audience_summary: str
    image_observations: list[str] = Field(default_factory=list)
    mock: bool = False
    # --- Phase 2 (real analysis); all optional so Phase 1 mock profiles stay valid ---
    analysis_mode: str = "mock"  # mock | heuristic_only | llm_assisted
    data_origins: dict[str, int] = Field(default_factory=dict)  # origin -> number of sources
    identity: list[Observation] = Field(default_factory=list)
    communication_tone: list[Observation] = Field(default_factory=list)
    audience: list[Observation] = Field(default_factory=list)
    visual_style: list[Observation] = Field(default_factory=list)
    colors: list[ColorEntry] = Field(default_factory=list)
    typography: list[FontEntry] = Field(default_factory=list)
    content_formats: list[Observation] = Field(default_factory=list)
    example_posts: list[ExamplePost] = Field(default_factory=list)
    product_catalog: list[ProductEntry] = Field(default_factory=list)
    assumptions: list[Observation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    selected_packshot: PackshotSelection | None = None
    selected_font: FontChoice | None = None
    visual_analysis_post_urls: list[str] = Field(default_factory=list)  # posts whose covers were analysed

    @field_validator("palette")
    @classmethod
    def _hex(cls, v: list[str]) -> list[str]:
        for c in v:
            if not _HEX.match(c):
                raise ValueError(f"palette colour must be #RRGGBB, got {c!r}")
        return v
