"""Team 1 (research) and team 2 (strategy) nodes."""
from pathlib import Path

from studio import prompts
from studio.contracts import (
    BrandProfile,
    BriefInput,
    ContentPlan,
    EvidenceItem,
    EvidenceRegistry,
    SourceIndex,
    SourceItem,
)
from studio.fingerprint import fingerprint, sha256_bytes
from studio.providers.base import ResearchStep
from studio.services import Services


def _ev(hit: bool, name: str) -> str:
    return f"{name}: stage cache {'hit' if hit else 'miss'}"


def research_agent(svc: Services, state: dict) -> dict:
    """Autonomous tool-calling loop (mock policy + mock tools in Phase 1).

    The policy decides each step; unknown tools are refused, never substituted.
    Every policy decision and tool call is an individual ledger operation.
    """
    if not svc.research.info.is_mock:  # real sources: bounded live agent (Phase 2)
        from studio.nodes.research_live import live_research_agent
        return live_research_agent(svc, state)
    brief = BriefInput.model_validate(state["brief"])
    fp = fingerprint(
        "research", brief.brand_name, brief.product_name, brief.website_url, brief.competitors,
        prompts.version("research_agent"), svc.llm.info.fingerprint(),
        svc.research.info.fingerprint(), svc.settings.research_max_steps)

    def compute() -> dict:
        history: list[dict] = []
        for i in range(svc.settings.research_max_steps):
            step = ResearchStep.model_validate(svc.op(
                node="research_agent", scope=svc.GLOBAL, stage="research", fp=fp,
                suffix=f"s{i}:policy", provider=svc.llm.info,
                fn=lambda: svc.llm.structured(
                    ResearchStep, task="research_policy",
                    payload={"brief": brief.dump(), "history": history}).model_dump()))
            if step.action == "finish":
                break
            if step.tool not in svc.research.tool_names:
                raise ValueError(f"research policy requested unknown tool {step.tool!r}")
            result = svc.op(
                node="research_agent", scope=svc.GLOBAL, stage="research", fp=fp,
                suffix=f"s{i}:{step.tool}", provider=svc.research.info,
                fn=lambda: svc.research.call(step.tool, step.args))
            history.append({"tool": step.tool, "args": step.args, "result": result})
        return _collect(history)

    out, hit = svc.stage(svc.GLOBAL, "research", fp, compute)
    return {"research": {**out, "fingerprint": fp}, "events": [_ev(hit, "research_agent")]}


def _collect(history: list[dict]) -> dict:
    sources, items, seen = [], [], {}
    for h in history:
        if h["tool"] != "fetch_page":
            continue
        r = h["result"]
        if r["url"] in seen:
            continue
        sid = f"S{len(sources) + 1}"
        seen[r["url"]] = sid
        sources.append(SourceItem(
            source_id=sid, url=r["url"], title=r["title"],
            content_sha256=sha256_bytes(r["text"].encode()), mock=r["title"].startswith("[MOCK]")))
        for f in r["facts"]:
            items.append(EvidenceItem(
                evidence_id=f"E{len(items) + 1}", claim=f["claim"], source_id=sid,
                quote=f["quote"], confidence=0.5, mock=sources[-1].mock))
    index, registry = SourceIndex(sources=sources), EvidenceRegistry(items=items)
    registry.check_sources(index)
    if not items:
        raise ValueError("research produced no evidence")
    return {"source_index": index.dump(), "evidence": registry.dump(), "trace": history}


def brand_product_analyst(svc: Services, state: dict) -> dict:
    if not svc.research.info.is_mock:  # real sources: evidence-verified analysis (Phase 2)
        from studio.nodes.analyst_live import live_analyst
        return live_analyst(svc, state)
    brief = BriefInput.model_validate(state["brief"])
    images = []
    for p in brief.image_paths:
        path = Path(p)
        if path.is_file():
            images.append((p, path.read_bytes()))
    fp = fingerprint(
        "analyst", state["research"]["fingerprint"], brief.brand_name, brief.product_name,
        brief.audience, brief.tone, [sha256_bytes(b) for _, b in images],
        prompts.version("brand_analyst"), svc.llm.info.fingerprint(), svc.vision.info.fingerprint())

    def compute() -> dict:
        observations = []
        for p, data in images:
            r = svc.op(
                node="brand_product_analyst", scope=svc.GLOBAL, stage="analyst", fp=fp,
                suffix=f"img:{sha256_bytes(data)[:8]}", provider=svc.vision.info,
                fn=lambda: svc.vision.describe(
                    data, question="Describe the product and brand cues", meta={"path": p}).model_dump())
            observations += r["observations"]
        profile = svc.op(
            node="brand_product_analyst", scope=svc.GLOBAL, stage="analyst", fp=fp, suffix="profile",
            provider=svc.llm.info,
            fn=lambda: svc.llm.structured(BrandProfile, task="brand_profile", payload={
                "brief": brief.dump(), "vision_observations": observations,
                "evidence_ids": [i["evidence_id"] for i in state["research"]["evidence"]["items"]],
            }).model_dump())
        return {"profile": BrandProfile.model_validate(profile).dump()}

    out, hit = svc.stage(svc.GLOBAL, "analyst", fp, compute)
    return {"brand_profile": {**out, "fingerprint": fp}, "events": [_ev(hit, "brand_product_analyst")]}


def content_planner(svc: Services, state: dict) -> dict:
    brief = BriefInput.model_validate(state["brief"])
    fp = fingerprint(
        "plan", state["brand_profile"]["fingerprint"], brief.brand_name, brief.product_name,
        brief.campaign_goal, brief.audience, prompts.version("content_planner"),
        svc.llm.info.fingerprint())

    def compute() -> dict:
        plan = svc.op(
            node="content_planner", scope=svc.GLOBAL, stage="plan", fp=fp, suffix="plan",
            provider=svc.llm.info,
            fn=lambda: svc.llm.structured(ContentPlan, task="content_plan", payload={
                "brief": brief.dump(),
                "evidence_ids": state["brand_profile"]["profile"]["product_fact_ids"],
            }).model_dump())
        return {"plan": ContentPlan.model_validate(plan).dump()}

    out, hit = svc.stage(svc.GLOBAL, "plan", fp, compute)
    # approval fingerprint = content of the plan itself, independent of how it was derived
    return {"plan": {**out, "fingerprint": fingerprint(out["plan"])}, "events": [_ev(hit, "content_planner")]}
