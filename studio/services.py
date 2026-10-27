"""Dependency container handed to every node. Nothing is global."""
import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from studio.config import Settings
from studio.contracts import ArtifactKind, ArtifactReference
from studio.fingerprint import sha256_bytes, sha256_file
from studio.ledger import Ledger, OperationRunner
from studio.providers.base import ProviderInfo
from studio.store import GLOBAL, RunStore


@dataclass
class Services:
    settings: Settings
    run_id: str
    run_dir: Path
    export_dir: Path
    llm: object
    vision: object
    image: object
    video: object
    research: object
    ledger: Ledger
    store: RunStore
    runner: OperationRunner
    auto_approve_mock: bool  # only ever True when all providers are mock

    GLOBAL = GLOBAL

    @property
    def providers(self) -> list:
        return [self.llm, self.vision, self.image, self.video, self.research]

    @property
    def is_mock(self) -> bool:
        return all(p.info.is_mock for p in self.providers)

    # -- stage cache --------------------------------------------------------
    def stage(self, scope: str, stage: str, fp: str, compute: Callable[[], dict]) -> tuple[dict, bool]:
        """Return (output, cache_hit). Reuse only when the input fingerprint matches."""
        hit = self.store.get_stage(self.run_id, scope, stage, fp)
        if hit is not None:
            return hit, True
        out = compute()
        self.store.put_stage(self.run_id, scope, stage, fp, out)
        return out, False

    def key(self, scope: str, stage: str, fp: str, suffix: str = "") -> str:
        gen = self.store.generation(self.run_id, scope, stage)
        return f"{scope}|{stage}|{fp}|g{gen}|{suffix}"

    def op(self, *, node: str, scope: str, stage: str, fp: str, suffix: str, provider: ProviderInfo,
           fn: Callable[[], dict], units: float = 1.0, artifact_of=None, verify=None) -> dict:
        return self.runner.run(
            node=node, scope=scope, provider=provider, key=self.key(scope, stage, fp, suffix),
            fn=fn, units=units, artifact_of=artifact_of, verify=verify)

    # -- artifacts ----------------------------------------------------------
    def write_artifact(self, post_id: str, fp: str, name: str, data: bytes, kind: ArtifactKind,
                       media_type: str, mock: bool, metadata: dict | None = None) -> ArtifactReference:
        rel = f"artifacts/post_{post_id}/{fp[:12]}/{name}"
        path = self.run_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return ArtifactReference(
            artifact_id=hashlib.sha256(f"{post_id}|{fp}|{name}".encode()).hexdigest()[:16],
            kind=kind, relpath=rel, sha256=sha256_bytes(data), size_bytes=len(data),
            media_type=media_type, post_id=post_id, mock=mock, metadata=metadata or {})

    def artifact_ok(self, ref: dict) -> bool:
        p = self.run_dir / ref["relpath"]
        return p.is_file() and sha256_file(p) == ref["sha256"]
