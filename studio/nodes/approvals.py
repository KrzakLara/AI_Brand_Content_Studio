"""Human approval gates.

An approval is honoured only if its fingerprint equals the fingerprint of the artifact
currently awaiting approval. With no matching approval the graph pauses via
``interrupt``. Automatic approval exists only for all-mock runs and is recorded as such.
"""
from langgraph.types import interrupt

from studio.contracts import (
    ApprovalRecord,
    ApprovalSource,
    Gate,
    RunStatus,
)
from studio.fingerprint import fingerprint
from studio.services import Services
from studio.store import is_approved


def resolve_approval(svc: Services, gate: Gate, fp: str, summary: dict) -> tuple[ApprovalRecord, list[str]]:
    events: list[str] = []
    rec = svc.store.find_approval(svc.run_id, gate, fp)
    stale = rec is None and svc.store.has_other_fingerprint(svc.run_id, gate, fp)
    if rec is None and svc.auto_approve_mock:
        if not svc.is_mock:
            raise RuntimeError("auto approval is only allowed with mock providers")
        rec = ApprovalRecord(
            run_id=svc.run_id, gate=gate, artifact_fingerprint=fp, approver="mock-auto",
            source=ApprovalSource.MOCK_AUTO, mock=True,
            note="automatic approval of MOCK artifacts; not a human decision")
        svc.store.add_approval(rec)
    if rec is None:
        # Pauses the graph. Re-running after `studio approve` finds the record above.
        # `stale`: approvals exist for an older version of this artifact and were ignored.
        interrupt({"gate": gate.value, "fingerprint": fp, "summary": summary,
                   "stale_approvals_ignored": stale})
        rec = svc.store.find_approval(svc.run_id, gate, fp)
        if rec is None:
            raise RuntimeError(f"resumed without a matching {gate.value} approval")
    events.append(f"approve_{gate.value}: {rec.decision.value} by {rec.approver} ({rec.source.value})")
    return rec, events


def approve_plan(svc: Services, state: dict) -> dict:
    fp = state["plan"]["fingerprint"]
    plan = state["plan"]["plan"]
    rec, events = resolve_approval(svc, Gate.PLAN, fp, {
        "posts": [{"post_id": p["post_id"], "format": p["format"], "hook": p["hook"]}
                  for p in plan["posts"]]})
    out = {"plan_approval": rec.dump(), "events": events}
    if not is_approved(rec):
        out["status"] = RunStatus.REJECTED.value
    return out


def final_fingerprint(posts: dict) -> str:
    return fingerprint(sorted(
        (pid, p["status"], p["production_fingerprint"], sorted(a["sha256"] for a in p["artifacts"]))
        for pid, p in posts.items()))


def approve_final(svc: Services, state: dict) -> dict:
    posts = state["posts"]
    fp = final_fingerprint(posts)
    rec, events = resolve_approval(svc, Gate.FINAL, fp, {
        "posts": [{"post_id": pid, "status": p["status"], "artifacts": len(p["artifacts"])}
                  for pid, p in sorted(posts.items())]})
    out = {"final_approval": rec.dump(), "events": events}
    if not is_approved(rec):
        out["status"] = RunStatus.REJECTED.value
    return out

