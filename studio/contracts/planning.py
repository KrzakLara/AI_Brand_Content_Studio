from pydantic import Field, model_validator

from .base import Contract
from .enums import PostFormat

POST_IDS = ("01", "02", "03")
POST_FORMATS = {"01": PostFormat.CAROUSEL, "02": PostFormat.HERO, "03": PostFormat.REEL}


class PostPlan(Contract):
    post_id: str = Field(pattern=r"^0[1-3]$")
    format: PostFormat
    objective: str
    hook: str
    key_message: str
    evidence_ids: list[str] = Field(min_length=1)
    cta: str


class ContentPlan(Contract):
    posts: list[PostPlan]
    mock: bool = False

    @model_validator(mode="after")
    def _three_posts(self):
        ids = [p.post_id for p in self.posts]
        if sorted(ids) != list(POST_IDS):
            raise ValueError(f"plan must contain exactly posts {POST_IDS}, got {ids}")
        for p in self.posts:
            if POST_FORMATS[p.post_id] != p.format:
                raise ValueError(f"post {p.post_id} must be {POST_FORMATS[p.post_id]}")
        return self

    def post(self, post_id: str) -> PostPlan:
        return next(p for p in self.posts if p.post_id == post_id)


class SlideSpec(Contract):
    title: str
    body: str


class ClaimRef(Contract):
    text: str
    evidence_id: str


class CreativeSpec(Contract):
    post_id: str
    format: PostFormat
    headline: str
    body: str
    cta: str
    visual_prompt: str
    aspect_ratio: str = "4:5"
    slides: list[SlideSpec] = Field(default_factory=list)
    duration_s: float | None = None
    claims: list[ClaimRef] = Field(default_factory=list)
    mock: bool = False

    @model_validator(mode="after")
    def _format_rules(self):
        if self.format == PostFormat.CAROUSEL and len(self.slides) < 3:
            raise ValueError("carousel needs at least 3 slides")
        if self.format == PostFormat.REEL and not self.duration_s:
            raise ValueError("reel needs duration_s")
        return self
