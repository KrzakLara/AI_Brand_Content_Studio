from pydantic import Field, field_validator

from .base import Contract


class FocalProductConfirmation(Contract):
    sku: str
    name: str
    confirmed_by: str
    confirmed_on: str
    note: str = ""


class BriefInput(Contract):
    brand_name: str = Field(min_length=1)
    product_name: str = Field(min_length=1)
    campaign_goal: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    tone: str = "confident, friendly"
    language: str = "en"
    website_url: str | None = None
    competitors: list[str] = Field(default_factory=list)
    image_paths: list[str] = Field(default_factory=list)
    notes: str = ""
    # --- Phase 2 research hints (all optional) ---
    instagram_handle: str | None = None
    seed_urls: list[str] = Field(default_factory=list)  # official pages to start from
    focus_keywords: list[str] = Field(default_factory=list)  # e.g. ["kreatin"]
    manual_observations_path: str | None = None  # operator-attested observations (with provenance)
    seed_images: list[str] = Field(default_factory=list)  # operator-listed packshot candidates (allow-listed hosts)
    visual_observations_path: str | None = None  # operator-labelled Instagram cover analysis (with provenance)
    # --- Phase 3 human decisions (all optional) ---
    confirmed_focal_product: FocalProductConfirmation | None = None
    label_crops_path: str | None = None  # operator-labelled crops of the selected original packshot
    locked_copy: dict[str, str] = Field(default_factory=dict)  # copy the human fixed, e.g. {"hero_headline": "Samo bitno."}
    campaign_constraints: list[str] = Field(default_factory=list)
    extra_evidence_paths: list[str] = Field(default_factory=list)  # focused research on another product (e.g. the Phase 5 carousel): evidence + colours

    @field_validator("website_url")
    @classmethod
    def _http_url(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("website_url must start with http:// or https://")
        return v
