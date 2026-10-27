"""Status and category enums shared by all contracts."""
from enum import StrEnum


class PostFormat(StrEnum):
    CAROUSEL = "carousel"
    HERO = "hero"
    REEL = "reel"


class OperationStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"
    UNKNOWN = "unknown"


class PostStatus(StrEnum):
    PENDING = "pending"
    PRODUCING = "producing"
    VALIDATING = "validating"
    REVIEWING = "reviewing"
    REPAIRING = "repairing"
    PASSED = "passed"
    ESCALATE = "escalate"
    EXPORTED = "exported"


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    REJECTED = "rejected"
    COMPLETED = "completed"
    COMPLETED_WITH_ESCALATIONS = "completed_with_escalations"
    FAILED = "failed"


class Gate(StrEnum):
    PLAN = "plan"
    FINAL = "final"


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalSource(StrEnum):
    HUMAN_CLI = "human_cli"
    FIXTURE_FILE = "fixture_file"
    MOCK_AUTO = "mock_auto"


class Severity(StrEnum):
    INFO = "info"
    MINOR = "minor"
    MAJOR = "major"
    BLOCKER = "blocker"


class QAVerdict(StrEnum):
    PASS = "pass"
    REPAIR = "repair"
    ESCALATE = "escalate"


class ArtifactKind(StrEnum):
    IMAGE = "image"
    DOCUMENT = "document"
    VIDEO = "video"
    VIDEO_PLACEHOLDER = "video_placeholder"


class ProviderKind(StrEnum):
    LLM = "llm"
    VISION = "vision"
    IMAGE = "image"
    VIDEO = "video"
    RESEARCH = "research"
    INSTAGRAM = "instagram"
    NONE = "none"
