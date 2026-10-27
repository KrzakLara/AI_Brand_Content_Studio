"""Deterministic artifact export and manifest."""
import json
import shutil
from pathlib import Path

from studio.contracts import (
    ApprovalRecord,
    Manifest,
    ManifestArtifact,
    ManifestPost,
    PostState,
    PostStatus,
    RunStatus,
)
from studio.fingerprint import fingerprint, sha256_file
from studio.nodes.approvals import final_fingerprint
from studio.services import Services

MOCK_NOTICE = (
    "MOCK DELIVERABLES\n"
    "Produced by deterministic mock providers (Phase 1 walking skeleton).\n"
    "Images are solid-colour placeholders with a warning banner; the 'reel' is a JSON\n"
    "placeholder, not a video. No AI model, paid API, or FFmpeg was used.\n")


def exporter(svc: Services, state: dict) -> dict:
    out_root: Path = svc.export_dir / svc.run_id
    if out_root.exists():
        shutil.rmtree(out_root)  # our own previous export of this run id
    out_root.mkdir(parents=True)

    posts = {pid: PostState.model_validate(p) for pid, p in sorted(state["posts"].items())}
    manifest_posts: list[ManifestPost] = []
    for pid, ps in posts.items():
        entries: list[ManifestArtifact] = []
        folder = out_root / f"post_{pid}_{ps.format.value}"
        if ps.status == PostStatus.ESCALATE:
            folder.mkdir()
            (folder / "ESCALATED.json").write_text(json.dumps({
                "post_id": pid, "reason": ps.decisions[-1].rationale,
                "findings": [f.dump() for f in ps.findings]}, indent=2), encoding="utf-8")
        else:
            for a in ps.artifacts:
                src = svc.run_dir / a.relpath
                if sha256_file(src) != a.sha256:
                    raise RuntimeError(f"artifact {a.relpath} changed since validation; refusing to export")
                dst = folder / Path(a.relpath).name
                folder.mkdir(exist_ok=True)
                shutil.copy2(src, dst)
                entries.append(ManifestArtifact(artifact=a, exported_path=dst.relative_to(out_root).as_posix()))
            ps = ps.model_copy(update={"status": PostStatus.EXPORTED})
            posts[pid] = ps
        manifest_posts.append(ManifestPost(
            post_id=pid, format=ps.format, status=ps.status, spec_fingerprint=ps.spec_fingerprint,
            production_fingerprint=ps.production_fingerprint, repair_attempts=ps.repair_attempts,
            artifacts=entries))

    escalated = any(p.status == PostStatus.ESCALATE for p in posts.values())
    run_status = RunStatus.COMPLETED_WITH_ESCALATIONS if escalated else RunStatus.COMPLETED
    approvals: list[ApprovalRecord] = svc.store.approvals(svc.run_id)
    manifest = Manifest(
        run_id=svc.run_id, mock=svc.is_mock,
        notice=MOCK_NOTICE.strip() if svc.is_mock else "",
        brief_fingerprint=fingerprint(state["brief"]), plan_fingerprint=state["plan"]["fingerprint"],
        final_fingerprint=final_fingerprint(state["posts"]), run_status=run_status,
        posts=manifest_posts, approvals=approvals, operations=svc.ledger.summary(svc.run_id),
        total_estimated_cost_usd=svc.ledger.total_cost(svc.run_id))
    (out_root / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    if svc.is_mock:
        (out_root / "MOCK_NOTICE.txt").write_text(MOCK_NOTICE, encoding="utf-8")
    return {
        "posts": {pid: p.dump() for pid, p in posts.items()},
        "manifest": manifest.dump(), "status": run_status.value,
        "events": [f"exporter: wrote {out_root}"],
    }

