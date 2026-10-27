"""Team 4 (QA): independent reviewers and the judge that routes repairs."""
from collections.abc import Callable

from studio import prompts
from studio.contracts import PostStatus, QADecision, QAFinding, QAVerdict
from studio.fingerprint import fingerprint
from studio.nodes.producers import PRODUCER_NAME
from studio.providers.base import ReviewResult
from studio.services import Services


def make_reviewer(svc: Services, name: str, task: str, primary_formats: set[str],
                  use_vision: bool = False) -> Callable[[dict], dict]:
    def node(s: dict) -> dict:
        attempt, post_id = s.get("attempt", 0), s["post_id"]
        stage = f"review.{name}#{attempt}"
        fp = fingerprint("review", name, s["production_fp"], prompts.version(name),
                         svc.llm.info.fingerprint(post_id), svc.vision.info.fingerprint() if use_vision else "",
                         attempt)

        def compute() -> dict:
            res = svc.op(
                node=name, scope=post_id, stage=stage, fp=fp, suffix="llm", provider=svc.llm.info,
                fn=lambda: svc.llm.structured(ReviewResult, task=task, payload={
                    "post_id": post_id, "attempt": attempt, "spec": s["creative_spec"],
                    "primary": s["plan_post"]["format"] in primary_formats,
                    "artifact_hashes": [a["sha256"] for a in s["artifacts"]],
                }).model_dump())
            notes: list[str] = []
            if use_vision:
                for a in (x for x in s["artifacts"] if x["kind"] == "image"):
                    data = (svc.run_dir / a["relpath"]).read_bytes()
                    r = svc.op(
                        node=name, scope=post_id, stage=stage, fp=fp, suffix=f"vision:{a['artifact_id']}",
                        provider=svc.vision.info,
                        fn=lambda: svc.vision.describe(
                            data, question="Assess visual quality", meta={"artifact": a["relpath"]}).model_dump())
                    notes.append(r["description"])
            return {"issues": res["findings"], "vision_notes": notes}

        out, _ = svc.stage(post_id, stage, fp, compute)
        findings = [QAFinding(
            finding_id=f"{post_id}-{name}-a{attempt}-{i}", post_id=post_id, reviewer=name,
            severity=f["severity"], category=f["category"], message=f["message"], attempt=attempt).dump()
            for i, f in enumerate(out["issues"])]
        return {"reviews": {name: findings}}  # only its own key: reviewers run in parallel

    node.__name__ = name
    return node


def make_judge(svc: Services) -> Callable[[dict], dict]:
    def node(s: dict) -> dict:
        attempt, post_id = s.get("attempt", 0), s["post_id"]
        findings = list(s.get("gate_findings", []))
        for rv in s.get("reviews", {}).values():
            findings += [f for f in rv if f["attempt"] == attempt]  # ignore stale rounds
        findings.sort(key=lambda f: f["finding_id"])
        stage = f"judge#{attempt}"
        fp = fingerprint("judge", findings, attempt, prompts.version("qa_judge"),
                         svc.llm.info.fingerprint(), svc.settings.max_repairs)

        def compute() -> dict:
            raw = svc.op(
                node="qa_judge", scope=post_id, stage=stage, fp=fp, suffix="llm", provider=svc.llm.info,
                fn=lambda: svc.llm.structured(QADecision, task="qa_judge", payload={
                    "post_id": post_id, "attempt": attempt, "findings": findings,
                    "producer": PRODUCER_NAME[s["plan_post"]["format"]]}).model_dump())
            return {"decision": raw}

        out, _ = svc.stage(post_id, stage, fp, compute)
        decision = QADecision.model_validate(out["decision"])
        # Escalation is deterministic policy, not an LLM opinion.
        if decision.verdict == QAVerdict.REPAIR and attempt >= svc.settings.max_repairs:
            decision = decision.model_copy(update={
                "verdict": QAVerdict.ESCALATE,
                "rationale": f"still failing after {attempt} repair attempts; escalating to a human"})
        status = {QAVerdict.PASS: PostStatus.PASSED, QAVerdict.ESCALATE: PostStatus.ESCALATE,
                  QAVerdict.REPAIR: PostStatus.REPAIRING}[decision.verdict]
        return {"decision": decision.dump(), "decisions": [*s.get("decisions", []), decision.dump()],
                "findings": findings, "status": status.value}

    node.__name__ = "qa_judge"
    return node


def repair(s: dict) -> dict:
    """Targeted repair: bump the attempt and hand the judge's instructions to the producer."""
    d = s["decision"]
    return {"attempt": s.get("attempt", 0) + 1, "repair_instructions": d["repair_instructions"],
            "gate_findings": [], "status": PostStatus.PRODUCING.value}
