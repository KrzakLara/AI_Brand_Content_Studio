"""Runtime contracts: artifacts, ledger, approvals, QA, per-post and per-run state."""
from datetime import datetime, timezone

from pydantic import Field

from .base import Contract
from .enums import (
    ApprovalDecision,
    ApprovalSource,
    ArtifactKind,
    Gate,
    OperationStatus,
    PostFormat,
    PostStatus,
    ProviderKind,
    QAVerdict,
    RunStatus,
    Severity,
)
from .planning import CreativeSpec


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ArtifactReference(Contract):
    """Pointer to a file on disk. Bytes never enter graph state."""

    artifact_id: str
    kind: ArtifactKind
    relpath: str  # relative to the run directory
    sha256: str
    size_bytes: int = Field(ge=0)
    media_type: str
    post_id: str | None = None
    mock: bool = False
    metadata: dict = Field(default_factory=dict)


class OperationRecord(Contract):
    operation_id: str
    run_id: str
    node: str
    scope: str | None = None
    provider: str
    idempotency_key: str
    status: OperationStatus
    started_at: datetime
    finished_at: datetime | None = None
    estimated_cost_usd: float = 0.0
    artifact: ArtifactReference | None = None
    error: str | None = None
    mock: bool = False


class CostRecord(Contract):
    operation_id: str
    run_id: str
    node: str
    provider: str
    kind: ProviderKind
    model_id: str
    units: float
    unit: str
    estimated_usd: float
    mock: bool = False


class ApprovalRecord(Contract):
    run_id: str
    gate: Gate
    artifact_fingerprint: str
    decision: ApprovalDecision = ApprovalDecision.APPROVED
    approver: str
    source: ApprovalSource
    note: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    mock: bool = False


class QAFinding(Contract):
    finding_id: str
    post_id: str
    reviewer: str
    severity: Severity
    category: str
    message: str
    attempt: int = 0


class QADecision(Contract):
    post_id: str
    attempt: int
    verdict: QAVerdict
    finding_ids: list[str] = Field(default_factory=list)
    repair_target: str | None = None
    repair_instructions: list[str] = Field(default_factory=list)
    rationale: str = ""


class PostState(Contract):
    """Independent state of one post; repaired and resumed on its own."""

    post_id: str
    format: PostFormat
    status: PostStatus = PostStatus.PENDING
    spec_fingerprint: str = ""  # fingerprint of this post's plan entry
    production_fingerprint: str = ""  # fingerprint of the latest production
    creative_spec: CreativeSpec | None = None
    artifacts: list[ArtifactReference] = Field(default_factory=list)
    findings: list[QAFinding] = Field(default_factory=list)  # latest round
    decisions: list[QADecision] = Field(default_factory=list)  # all rounds
    repair_attempts: int = 0
    production_history: list[str] = Field(default_factory=list)
    mock: bool = False


class RunState(Contract):
    """Typed view of the run; the LangGraph state stores its parts as plain dicts."""

    run_id: str
    thread_id: str
    status: RunStatus = RunStatus.CREATED
    brief_fingerprint: str = ""
    plan_fingerprint: str = ""
    posts: dict[str, PostState] = Field(default_factory=dict)
    approvals: list[ApprovalRecord] = Field(default_factory=list)
    mock: bool = True


class ManifestArtifact(Contract):
    artifact: ArtifactReference
    exported_path: str


class ManifestPost(Contract):
    post_id: str
    format: PostFormat
    status: PostStatus
    spec_fingerprint: str
    production_fingerprint: str
    repair_attempts: int
    artifacts: list[ManifestArtifact] = Field(default_factory=list)


class Manifest(Contract):
    run_id: str
    generated_at: datetime = Field(default_factory=utcnow)
    mock: bool
    notice: str
    brief_fingerprint: str
    plan_fingerprint: str
    final_fingerprint: str
    run_status: RunStatus
    posts: list[ManifestPost]
    approvals: list[ApprovalRecord]
    operations: dict[str, int]
    total_estimated_cost_usd: float
