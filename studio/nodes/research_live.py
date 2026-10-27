"""Bounded research agent for real sources (Phase 2).

Same node name and graph position as the mock agent; ``research_agent`` dispatches here
when the research toolset is not a mock. The loop is hard-bounded (steps, fetches, cost),
every policy decision and tool call is a ledger operation, tool failures are recorded as
failed sources rather than hidden, and fetched content only reaches the policy as
sanitised, wrapped data.
"""
from studio import prompts
from studio.cost import BudgetExceeded
from studio.contracts import BriefInput, EvidenceRegistry, SourceIndex, SourceItem
from studio.fingerprint import canonical, fingerprint
from studio.providers.base import ResearchStep
from studio.services import Services
from studio.tools import extract
from studio.tools.toolset import now, source_id


class ResearchFailed(RuntimeError):
    pass


def _limits(cfg) -> dict:
    return {"max_steps": cfg.max_steps, "max_fetches": cfg.max_fetches, "max_cost_usd": cfg.max_cost_usd,
            "max_product_pages": cfg.max_product_pages, "max_images": cfg.max_images,
            "instagram_limit": cfg.instagram_limit}


def _view(history: list[dict]) -> list[dict]:
    """What the policy may see: structure and URLs, with page titles wrapped as untrusted data."""
    return [{**h, "titles": [extract.untrusted(t, 120) for t in h.get("titles", [])]} for h in history]
    # (links are URLs on allow-listed hosts only; free text never reaches the policy unwrapped)


def live_research_agent(svc: Services, state: dict) -> dict:
    brief = BriefInput.model_validate(state["brief"])
    cfg, tools = svc.settings.research, svc.research
    limits = _limits(cfg)
    fp = fingerprint(
        "research-live", brief.brand_name, brief.website_url, brief.instagram_handle, brief.seed_urls,
        brief.focus_keywords, brief.seed_images, cfg, prompts.version("research_agent"), svc.llm.info.fingerprint(),
        tools.info.fingerprint(), tools.info_for("instagram_fetch").fingerprint())

    def compute() -> dict:
        history: list[dict] = []
        trace: list[dict] = []
        sources: dict[str, dict] = {}
        seen: set[str] = set()
        fetches, stop = 0, "max_steps"
        for i in range(cfg.max_steps):
            try:
                step = ResearchStep.model_validate(svc.op(
                    node="research_agent", scope=svc.GLOBAL, stage="research", fp=fp, suffix=f"s{i}:policy",
                    provider=svc.llm.info,
                    fn=lambda: svc.llm.structured(ResearchStep, task="research_policy", payload={
                        "brief": brief.dump(), "history": _view(history), "limits": limits}).model_dump()))
            except BudgetExceeded:  # raised BEFORE any request is sent: stop safely with what was collected
                stop = "max_api_budget"
                break
            if step.action == "finish":
                stop = "policy_finished"
                break
            entry = {"i": i, "tool": step.tool, "args": step.args, "why": extract.sanitize(step.rationale, 160)}
            err = _refuse(step, tools.tool_names, seen)
            if err:
                trace.append({**entry, "ok": False, "error": err})
                history.append({"tool": step.tool, "args": step.args, "ok": False, "error": err})
                continue
            seen.add(canonical([step.tool, step.args]))
            if step.tool != "instagram_fetch":
                if fetches >= cfg.max_fetches:
                    stop = "max_fetches"
                    break
                fetches += 1
            units = tools.units(step.tool, step.args)
            est, _ = svc.runner.estimator.estimate(tools.info_for(step.tool).kind, units, mock=False)
            if svc.ledger.total_cost(svc.run_id) + est > cfg.max_cost_usd:
                stop = "max_cost"
                break
            result = svc.op(
                node="research_agent", scope=svc.GLOBAL, stage="research", fp=fp, suffix=f"s{i}:{step.tool}",
                provider=tools.info_for(step.tool), units=units, verify=tools.artifact_ok,
                fn=lambda: tools.call(step.tool, step.args))
            for s in result["sources"]:
                prev = sources.get(s["source_id"])
                if prev is None or prev["retrieval_status"] != "ok":
                    sources[s["source_id"]] = s
            history.append({
                "tool": step.tool, "args": step.args, "ok": result["ok"], "error": result.get("error"),
                "links": result.get("links", []), "stylesheets": result.get("stylesheets", []),
                "images": result.get("images", []), "product_count": result.get("product_count", 0),
                "product_urls": result.get("product_urls", []),
                "titles": [s["title"] for s in result["sources"][:3] if s["title"]]})
            trace.append({**entry, "ok": result["ok"], "error": result.get("error"),
                          "source_ids": [s["source_id"] for s in result["sources"]][:12]})
        if brief.instagram_handle and not any(h["tool"] == "instagram_fetch" for h in history):
            url = f"https://www.instagram.com/{brief.instagram_handle}/"
            sources.setdefault(source_id(url), SourceItem(
                source_id=source_id(url), url=url, title="", kind="instagram_profile", origin=tools.origin,
                retrieval_status="not_collected", retrieved_at=now(),
                access_limitations="agent did not attempt Instagram collection within its limits").dump())
        if not any(s["retrieval_status"] == "ok" for s in sources.values()):
            raise ResearchFailed("no source could be retrieved: " + "; ".join(
                f"{s['url']} ({s['access_limitations']})" for s in sources.values())[:600])
        index = SourceIndex(sources=[SourceItem.model_validate(s) for s in sources.values()])
        return {"source_index": index.dump(), "evidence": EvidenceRegistry().dump(), "trace": trace,
                "stop_reason": stop, "limits": limits,
                "counts": {"steps": len(trace), "fetches": fetches,
                           "ok": sum(s.retrieval_status == "ok" for s in index.sources),
                           "not_ok": sum(s.retrieval_status != "ok" for s in index.sources)}}

    out, hit = svc.stage(svc.GLOBAL, "research", fp, compute)
    return {"research": {**out, "fingerprint": fp},
            "events": [f"research_agent(live): stage cache {'hit' if hit else 'miss'}, "
                       f"stop={out['stop_reason']}, sources ok={out['counts']['ok']} not_ok={out['counts']['not_ok']}"]}


def _refuse(step: ResearchStep, names: tuple[str, ...], seen: set[str]) -> str | None:
    if step.tool not in names:
        return f"unknown tool {step.tool!r}"  # never substituted
    key = "handle" if step.tool == "instagram_fetch" else "url"
    if not isinstance(step.args.get(key), str) or not step.args[key]:
        return f"missing argument {key!r}"
    if canonical([step.tool, step.args]) in seen:
        return "duplicate call refused"
    return None

