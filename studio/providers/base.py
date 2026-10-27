"""Provider protocols. Real providers (Phase 2) implement the same interfaces."""
from dataclasses import dataclass, field
from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel

from studio.contracts import ProviderKind
from studio.fingerprint import fingerprint

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class ProviderInfo:
    name: str
    kind: ProviderKind
    model_id: str
    is_mock: bool
    safe_to_retry: bool  # False for paid calls whose duplicate execution costs money
    config: dict = field(default_factory=dict)
    scoped_config: dict = field(default_factory=dict)  # per-scope (e.g. post id) behaviour switches

    def fingerprint(self, scope: str | None = None) -> str:
        """Identity of the provider; ``scope`` adds only that scope's own config."""
        return fingerprint(self.name, self.kind.value, self.model_id, self.is_mock, self.config,
                           self.scoped_config.get(scope))


class ProviderUnavailable(RuntimeError):
    """A provider cannot run (missing credentials, not implemented). Never silently mocked."""


class ProviderResponseError(RuntimeError):
    """A provider answered, but not with something we can use (HTTP error, malformed body)."""


class ResearchStep(BaseModel):
    """One decision of the research agent: call a tool or finish."""

    action: Literal["tool", "finish"]
    tool: str | None = None
    args: dict = {}
    rationale: str = ""


class ReviewIssue(BaseModel):
    severity: Literal["info", "minor", "major", "blocker"]
    category: str
    message: str


class ReviewResult(BaseModel):
    findings: list[ReviewIssue] = []
    mock: bool = False


class LLMProvider(Protocol):
    info: ProviderInfo

    def structured(self, schema: type[T], *, task: str, payload: dict) -> T: ...


class VisionResult(BaseModel):
    description: str
    observations: list[str]
    mock: bool = False


class VisionProvider(Protocol):
    info: ProviderInfo

    def describe(self, data: bytes, *, question: str, meta: dict) -> VisionResult: ...


class ImageProvider(Protocol):
    info: ProviderInfo

    def generate(self, *, prompt: str, width: int, height: int, seed: int, meta: dict) -> bytes: ...


class VideoProvider(Protocol):
    info: ProviderInfo

    def generate(self, *, storyboard: dict, duration_s: float, meta: dict) -> bytes: ...


class ResearchTools(Protocol):
    info: ProviderInfo
    tool_names: tuple[str, ...]

    def call(self, tool: str, args: dict) -> dict: ...

