"""Live content planner (Phase 3): real Anthropic structured output -> validated CampaignPlan.

Flow: dossier (verified research, loaded from disk and hash-checked) -> ONE model call -> schema validation ->
deterministic evidence/safety validation -> at most ONE automatic repair call -> stage cache. Every model call is a
ledger operation (idempotent, actual cost recorded). A revision re-uses the same dossier: no research is repeated.
"""
import json
from pathlib import Path

from studio import prompts
from studio.contracts.strategy import SCHEMA, CampaignPlan
from studio.fingerprint import fingerprint
from studio.services import Services
from studio.strategy.dossier import Dossier, build_dossier
from studio.strategy.validate import Problem, errors, validate_plan

MAX_REPAIRS = 1


class PlanInvalid(RuntimeError):
    """The model answered, but the plan violates evidence/safety rules even after the allowed repair."""

    def __init__(self, problems: list[Problem], plan: dict):
        self.problems, self.plan = problems, plan
        super().__init__(f"plan failed validation with {len(problems)} problem(s): " + "; ".join(str(p) for p in problems[:6]))


def load_dossier(inputs: dict) -> Dossier:
    root = Path(inputs["artifact_root"]) if inputs.get("artifact_root") else None
    d = build_dossier(Path(inputs["research_dir"]), artifact_root=root)
    if inputs.get("dossier_fingerprint") and inputs["dossier_fingerprint"] != d.fingerprint:
        raise ValueError("the research files changed since this run started (dossier fingerprint differs); start a new run")
    return d


def plan_fingerprint(campaign: dict, packshot: dict) -> str:
    """Content hash of the plan. Approvals bind to this; it excludes usage/cost metadata on purpose."""
    return fingerprint("campaign-plan", campaign, packshot)


def _dump(plan: CampaignPlan) -> dict:
    return plan.model_dump(mode="json")


def live_content_planner(svc: Services, state: dict) -> dict:
    inputs = state["strategy_inputs"]
    dossier = load_dossier(inputs)
    feedback = list(state.get("plan_feedback") or [])
    previous = state.get("plan_previous")
    fp = fingerprint("plan-live", dossier.fingerprint, prompts.version("content_planner"), svc.llm.info.fingerprint(),
                     feedback, previous)
    plan_dir = svc.run_dir / "plan"
    calls: list[dict] = []

    def call(suffix: str, prev: dict | None, revision: str | None) -> CampaignPlan:
        def fn() -> dict:
            payload = {"dossier": dossier.payload}
            if prev is not None:
                payload |= {"previous_plan": prev, "revision": revision}
            plan = svc.llm.structured(CampaignPlan, task="content_plan", payload=payload)
            usage = dict(svc.llm.usage_log[-1]) if getattr(svc.llm, "usage_log", None) else {}
            return {"plan": _dump(plan), "usage": usage}

        out = svc.op(node="content_planner", scope=svc.GLOBAL, stage="plan", fp=fp, suffix=suffix, provider=svc.llm.info,
                     fn=fn, actual_cost=lambda r: (r.get("usage") or {}).get("cost_usd") or 0.0)
        calls.append({"call": suffix, **(out.get("usage") or {})})
        return CampaignPlan.model_validate(out["plan"])

    def keep(plan: CampaignPlan, name: str) -> None:
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / name).write_text(json.dumps(_dump(plan), indent=2, ensure_ascii=False), encoding="utf-8")

    def compute() -> dict:
        revising = bool(previous and feedback)
        plan = call("revise" if revising else "draft", previous if revising else None, feedback[-1] if revising else None)
        allp = validate_plan(plan, dossier)
        problems = errors(allp)
        for i in range(MAX_REPAIRS):
            if not problems:
                break
            keep(plan, f"invalid_{fp[:12]}_try{i}.json")
            note = ("VALIDATION FAILED. Fix exactly these problems, change nothing else, return the full plan:\n"
                    + "\n".join(f"- {p}" for p in problems))
            plan = call(f"repair{i + 1}", _dump(plan), note)
            allp = validate_plan(plan, dossier)
            problems = errors(allp)
        if problems:
            keep(plan, f"invalid_{fp[:12]}_final.json")
            raise PlanInvalid(problems, _dump(plan))
        return {"campaign": _dump(plan), "packshot": dossier.packshot,
                "meta": {"model": svc.llm.info.model_id, "prompt": "content_planner",
                         "prompt_version": prompts.version("content_planner"), "dossier_fingerprint": dossier.fingerprint,
                         "schema": SCHEMA, "validation": "passed (no blocking problems)",
                         "validation_flags": [str(p) for p in allp if p.severity == "flag"], "calls": calls, "feedback_history": feedback}}

    out, hit = svc.stage(svc.GLOBAL, "plan", fp, compute)
    campaign = CampaignPlan.model_validate(out["campaign"])  # re-validate whatever came out of the cache
    phash = plan_fingerprint(out["campaign"], out["packshot"])
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / f"plan_{phash[:12]}.json").write_text(json.dumps({"plan_hash": phash, **out}, indent=2, ensure_ascii=False), encoding="utf-8")
    (plan_dir / "current.json").write_text(json.dumps({"plan_hash": phash, "file": f"plan_{phash[:12]}.json"}), encoding="utf-8")
    return {"plan": {"plan": campaign.to_content_plan().dump(), "campaign": out["campaign"], "packshot": out["packshot"],
                     "meta": out["meta"], "fingerprint": phash},
            "events": [f"content_planner(live): stage cache {'hit' if hit else 'miss'}"]}
