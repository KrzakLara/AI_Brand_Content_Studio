from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class Models(BaseModel):
    model_config = ConfigDict(extra="forbid")
    llm: str
    vision: str
    image: str
    video: str
    research_llm: str = "claude-sonnet-5-5"  # live research/analysis model id (configurable)


class Price(BaseModel):
    model_config = ConfigDict(extra="forbid")
    unit: str
    usd_per_unit: float = Field(ge=0)


class ResearchConfig(BaseModel):
    """Hard bounds and policy for the live research agent."""

    model_config = ConfigDict(extra="forbid")
    max_steps: int = Field(default=30, ge=1)
    max_fetches: int = Field(default=40, ge=0)
    max_cost_usd: float = Field(default=0.25, ge=0)
    max_bytes: int = Field(default=4_000_000, ge=1)
    timeout_s: float = Field(default=20.0, gt=0)
    retries: int = Field(default=2, ge=0)
    backoff_s: float = Field(default=1.0, ge=0)
    respect_robots: bool = True
    allowed_hosts: list[str] = Field(default_factory=lambda: ["gymbeam.hr"])
    user_agent: str = "AIBrandContentStudio-research/0.2 (take-home project; honours robots.txt)"
    max_product_pages: int = Field(default=8, ge=0)
    max_images: int = Field(default=16, ge=0)
    instagram_limit: int = Field(default=30, ge=1)
    anthropic_max_tokens: int = Field(default=4096, ge=1)


class ModelPrice(BaseModel):
    """USD per million tokens for ONE model, valid for prompts up to ``max_prompt_tokens`` (higher tier = refused).
    A model without an entry cannot be run with a spend cap, so the adapter refuses to run it."""

    model_config = ConfigDict(extra="forbid")
    input_usd_per_mtok: float = Field(ge=0)
    output_usd_per_mtok: float = Field(ge=0)
    max_prompt_tokens: int = Field(default=100_000, ge=1)
    source_url: str = ""
    verified_on: str = ""


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    runs_dir: str = "runs"
    export_dir: str = "submission"
    default_brief: str = "briefs/gymbeam.yaml"
    max_repairs: int = Field(default=2, ge=0)
    budget_usd: float = Field(default=5.0, ge=0)
    research_max_steps: int = Field(default=6, ge=1)  # mock research loop
    research: ResearchConfig = Field(default_factory=ResearchConfig)
    models: Models
    pricing: dict[str, Price] = Field(default_factory=dict)  # keyed by provider kind
    anthropic_pricing: dict[str, ModelPrice] = Field(default_factory=dict)  # keyed by model id


def load_settings(path: str | Path = "config.yaml") -> Settings:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Settings.model_validate(data)
