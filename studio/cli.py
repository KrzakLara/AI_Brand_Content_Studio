"""`studio` command line."""
import argparse
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import yaml
from pydantic import ValidationError

from studio.config import load_settings
from studio.cost import BudgetExceeded
from studio.contracts import ApprovalRecord, BriefInput, Gate, ProviderKind, RunStatus, SourceIndex
from studio.orchestrator import Orchestrator
from studio.nodes.research_live import ResearchFailed
from studio.providers.base import ProviderResponseError, ProviderUnavailable
from studio.providers.live import AnthropicLLM, ScriptedResearchPolicy, UnavailableProvider
from studio.providers.mock import SimulatedCrash, build_mock_providers
from studio.tools.instagram import ApifyInstagram, ManualImportInstagram
from studio.tools.toolset import ResearchToolset
from studio.tools.transport import GuardedTransport, RecordedTransport, UrllibTransport
from studio.tools.web import HttpClient

EXIT_OK, EXIT_ERROR, EXIT_PAUSED, EXIT_CRASH = 0, 2, 3, 4


def _parse_fail(items: list[str]) -> dict[str, int]:
    out = {}
    for it in items:
        post, _, n = it.partition("=")
        out[post] = int(n)
    return out


def load_brief(path: str) -> BriefInput:
    return BriefInput.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def load_approvals(path: str) -> list[ApprovalRecord]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return [ApprovalRecord.model_validate({"run_id": "replay", **r}) for r in data["approvals"]]


def cmd_run(a) -> int:
    if not a.mock:
        print("Live providers are not implemented until Phase 2. Re-run with --mock.", file=sys.stderr)
        return EXIT_ERROR
    settings = load_settings(a.config)
    strict = bool(a.approvals) or a.manual_approval
    orch = Orchestrator(
        settings, runs_dir=a.runs_dir, export_dir=a.export_dir,
        providers=build_mock_providers(settings, fail_rounds=_parse_fail(a.mock_fail),
                                       crash_post=a.mock_crash),
        auto_approve_mock=not strict,
        approvals=load_approvals(a.approvals) if a.approvals else None)
    brief = None
    is_new = a.run is None or not (Path(a.runs_dir or settings.runs_dir) / a.run / "state.db").exists()
    if is_new or a.brief:
        brief = load_brief(a.brief or settings.default_brief)
    try:
        res = orch.run(a.run, brief=brief, from_stage=a.from_stage, post=a.post)
    except SimulatedCrash as e:
        print(f"[simulated crash] {e}\nResume with: studio run --mock --run {a.run or '<RUN_ID>'}")
        return EXIT_CRASH
    except (ValueError, ValidationError) as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_ERROR
    print(f"run_id: {res.run_id}\nstatus: {res.status}")
    if res.paused_at:
        p = res.paused_at
        print(f"waiting for approval at gate '{p['gate']}' (fingerprint {p['fingerprint'][:12]})")
        if p.get("stale_approvals_ignored"):
            print("note: earlier approvals exist for a different version of this artifact and were ignored")
        print(f"approve with: studio approve --run {res.run_id} --gate {p['gate']}")
        print(f"then resume:  studio run --mock --run {res.run_id}" + (" --manual-approval" if strict else ""))
        return EXIT_PAUSED
    for pid, p in sorted(res.values.get("posts", {}).items()):
        print(f"  post {pid} [{p['format']}]: {p['status']} (repairs: {p['repair_attempts']})")
    if res.status in (RunStatus.COMPLETED.value, RunStatus.COMPLETED_WITH_ESCALATIONS.value):
        print(f"exported to: {orch.export_dir / res.run_id}")
    return EXIT_OK


def trace_from_ledger(ops) -> list[dict]:
    """Rebuild the real step sequence (model decision -> tool result) from the operation ledger."""
    steps: dict[int, dict] = {}
    for o in ops:
        part = o.idempotency_key.split("|")[-1]  # e.g. "s2:policy" or "s3:web_fetch"
        if not part.startswith("s") or ":" not in part:
            continue
        n, kind = part[1:].split(":", 1)
        st = steps.setdefault(int(n), {"step": int(n)})
        if kind == "policy":
            st["policy_status"] = o.status.value
            if o.error:
                st["policy_error"] = o.error[:200]
        else:
            st["tool_status"], st["tool_called"] = o.status.value, kind
    return [steps[k] for k in sorted(steps)]


def _write_failure_report(orch, a, llm, exc) -> None:
    """Persist what really happened in a failed paid run: decisions (with the model's reasons), tool results, usage."""
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    decisions, results = [], []
    with orch.open(a.run) as (svc, *_):
        ops = svc.ledger.list(a.run)
        import sqlite3
        conn = sqlite3.connect(svc.ledger.db_path)
        rows = conn.execute("SELECT idempotency_key, status, result_json FROM operations ORDER BY started_at, rowid").fetchall()
        conn.close()
    for key, status, res in rows:
        part = key.split("|")[-1]
        if status != "done" or not res or ":" not in part:
            continue
        doc = json.loads(res)
        if part.endswith(":policy"):
            decisions.append({"step": part, "action": doc.get("action"), "tool": doc.get("tool"), "args": doc.get("args"),
                              "reason": doc.get("rationale")})
        else:
            results.append({"step": part, "ok": doc.get("ok"), "error": doc.get("error"),
                            "urls": [s["url"] for s in doc.get("sources", [])]})
    partial = getattr(exc, "partial", {}) or {}
    report = {"status": "failed", "failure": f"{type(exc).__name__}: {str(exc)[:400]}", "model": llm.model_id,
              "stop_reason": partial.get("stop_reason"), "sources_recorded": partial.get("sources", []),
              "agent_trace": partial.get("trace", []),
              "policy_autonomous": True, "mode": a.mode, "model_decisions": decisions, "tool_results": results,
              "ledger_steps": trace_from_ledger(ops), "api": llm.accounting()}
    (out / "run_summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    src = Path(llm.usage_path) if llm.usage_path else None
    if src and src.is_file():
        (out / "api_usage.jsonl").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        guard_log = src.parent / "api_requests.log"
        if guard_log.is_file():
            (out / "api_requests.log").write_text(guard_log.read_text(encoding="utf-8"), encoding="utf-8")


def cmd_research(a) -> int:
    """Research workflow (research_agent -> brand_product_analyst) on the shared engine."""
    settings = load_settings(a.config)
    if a.max_steps is not None:
        settings = settings.model_copy(update={"research": settings.research.model_copy(update={"max_steps": a.max_steps})})
    cfg = settings.research
    if a.mode == "live":
        transport, origin = UrllibTransport(), "live"
    else:
        if not a.fixtures:
            print("error: --mode fixture needs --fixtures DIR (containing transport.json)", file=sys.stderr)
            return EXIT_ERROR
        transport, origin = RecordedTransport.from_file(Path(a.fixtures) / "transport.json"), "fixture"
    if a.policy == "anthropic":
        model = a.model or settings.models.research_llm
        run_dir = (Path(a.runs_dir or settings.runs_dir) / a.run) if a.run else None
        llm_transport = transport
        if a.max_requests is not None and run_dir is not None:  # independent hard cap at the transport level
            llm_transport = GuardedTransport(transport, limit=a.max_requests, hosts=("api.anthropic.com",),
                                             log_path=run_dir / "api_requests.log")
        price = settings.anthropic_pricing.get(model)
        llm = AnthropicLLM(model, llm_transport, cfg.anthropic_max_tokens, origin,
                           input_usd_per_mtok=price.input_usd_per_mtok if price else None,
                           output_usd_per_mtok=price.output_usd_per_mtok if price else None,
                           max_prompt_tokens=price.max_prompt_tokens if price else 100_000,
                           budget_usd=a.max_api_spend_usd, max_requests=a.max_requests,
                           usage_path=(Path(a.runs_dir or settings.runs_dir) / a.run / "api_usage.jsonl") if a.run else None)
        if not llm.api_key:
            print("error: --policy anthropic needs ANTHROPIC_API_KEY (not set). Nothing was run. Choose "
                  "--policy scripted explicitly to use the non-autonomous scripted crawl plan.", file=sys.stderr)
            return EXIT_ERROR
        if a.mode == "live" and a.max_requests is None:
            print("error: a real Anthropic run needs an explicit --max-requests (preflight, messages and retries all "
                  "count). Nothing was run.", file=sys.stderr)
            return EXIT_ERROR
        if a.mode == "live" and a.max_api_spend_usd is None:
            print("error: a real Anthropic run needs an explicit --max-api-spend-usd. Nothing was run.", file=sys.stderr)
            return EXIT_ERROR
        if a.mode == "live" and price is None:
            print(f"error: anthropic_pricing in config.yaml has no entry for model '{model}'; add its per-million-token "
                  "prices from the official pricing page so the spend cap can be enforced. Nothing was run.", file=sys.stderr)
            return EXIT_ERROR
        if a.mode == "live" and not a.run:
            print("error: a real Anthropic run needs --run RUN_ID (its request/spend accounting is persisted per run). "
                  "Nothing was run.", file=sys.stderr)
            return EXIT_ERROR
        if a.skip_preflight:
            print(f"preflight skipped by request; already used {llm.api_requests} of {llm.max_requests} API requests")
        else:
            try:  # free call (no tokens): is the key valid and the model accessible?
                pf = llm.preflight()
            except (ProviderUnavailable, BudgetExceeded) as e:
                print(f"error: {e}. Nothing was run.", file=sys.stderr)
                return EXIT_ERROR
            print(f"preflight ok: model {pf['model']} accessible; budget {llm.budget_usd} USD, max steps {cfg.max_steps}, "
                  f"max API requests {llm.max_requests} (preflight counted: {llm.api_requests} used)")
        if a.preflight_only:
            return EXIT_OK
    else:
        llm = ScriptedResearchPolicy()
    if a.instagram == "apify":
        ig = ApifyInstagram(transport, origin=origin, price_per_post=settings.pricing["instagram"].usd_per_unit)
    elif a.instagram == "import":
        if not a.instagram_import:
            print("error: --instagram import needs --instagram-import FILE", file=sys.stderr)
            return EXIT_ERROR
        ig = ManualImportInstagram(Path(a.instagram_import))
    else:
        ig = None
    http = HttpClient(transport, cfg)
    no = lambda k: UnavailableProvider(k, "not part of the research workflow")  # noqa: E731
    providers = SimpleNamespace(
        llm=llm, vision=no(ProviderKind.VISION), image=no(ProviderKind.IMAGE), video=no(ProviderKind.VIDEO),
        research=lambda run_dir: ResearchToolset(run_dir, http, cfg, origin=origin, instagram=ig))
    orch = Orchestrator(settings, runs_dir=a.runs_dir, providers=providers, auto_approve_mock=False, until="analyst")
    try:
        res = orch.run(a.run, brief=load_brief(a.brief))
    except (ProviderUnavailable, ProviderResponseError, ResearchFailed, ValueError, ValidationError) as e:
        print(f"research failed: {type(e).__name__}: {e}", file=sys.stderr)
        if a.policy == "anthropic":  # spending and the real tool sequence are never lost, even on failure
            acc = llm.accounting()
            print(f"api accounting: {acc['api_requests']}/{acc['max_requests']} requests, {acc['input_tokens']} in / "
                  f"{acc['output_tokens']} out tokens, spent {acc['spent_usd']} of {acc['budget_usd']} USD", file=sys.stderr)
            if a.out and a.run:
                _write_failure_report(orch, a, llm, e)
        return EXIT_ERROR
    v = res.values
    index = SourceIndex.model_validate(v["research"]["source_index"])
    origins = Counter(s.origin for s in index.sources if s.retrieval_status == "ok")
    ev = v["research"]["evidence"]["items"]
    with orch.open(res.run_id) as (svc, *_):
        ops, cost = svc.ledger.summary(res.run_id), svc.ledger.total_cost(res.run_id)
    summary = {
        "run_id": res.run_id, "mode": a.mode, "policy": llm.info.name, "policy_autonomous": a.policy == "anthropic",
        "instagram_provider": ig.name if ig else None, "data_origins_ok_sources": dict(origins),
        "stop_reason": v["research"]["stop_reason"], "counts": v["research"]["counts"],
        "evidence": dict(Counter(e["verification_status"] for e in ev)),
        "analysis_mode": v["brand_profile"]["profile"]["analysis_mode"],
        "operations": ops, "tool_cost_usd": cost,
        "estimated_cost_usd": round(cost + (llm.spent_usd if a.policy == "anthropic" else 0.0), 6),
        "trace": v["research"]["trace"],
        "tools_selected": dict(Counter(t["tool"] for t in v["research"]["trace"])),
        "api": (llm.accounting() | {"http_requests": llm.http_requests} if a.policy == "anthropic" else None)}
    run_research = Path(orch.run_dir(res.run_id)) / "research"
    (run_research / "run_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    if a.out:  # JSON only; raw third-party artifacts stay in the run directory
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        for name in ("brand_profile.json", "evidence_registry.json", "source_index.json", "run_summary.json"):
            shutil.copy2(run_research / name, out / name)
    print(f"run_id: {res.run_id}\nstatus: {res.status}\npolicy: {llm.info.name} "
          f"(autonomous: {a.policy == 'anthropic'}); instagram: {ig.name if ig else 'none'}")
    print(f"sources ok by origin: {dict(origins)}; stop_reason: {summary['stop_reason']}")
    print(f"evidence: {summary['evidence']}; analysis_mode: {summary['analysis_mode']}; "
          f"estimated cost: ${summary['estimated_cost_usd']:.6f}"
          + (f" (API {llm.api_requests}/{llm.max_requests} requests, {llm.accounting()['input_tokens']} in / "
             f"{llm.accounting()['output_tokens']} out tokens)" if a.policy == "anthropic" else ""))
    if a.out:
        print(f"wrote: {a.out}")
    return EXIT_OK


def _load_research(d: Path) -> dict:
    out = {n: json.loads((d / f"{n}.json").read_text(encoding="utf-8"))
           for n in ("source_index", "evidence_registry", "brand_profile")}
    summ = d / "run_summary.json"
    out["summary"] = json.loads(summ.read_text(encoding="utf-8")) if summ.is_file() else {}
    return out


def compare_research(a: dict, b: dict, label_a: str, label_b: str) -> str:
    """Human-readable diff of two research outputs: what each found that the other did not."""
    def urls(r, ok_only=True):
        return {s["url"] for s in r["source_index"]["sources"] if not ok_only or s["retrieval_status"] == "ok"}

    def skus(r):
        return {p["sku"] for p in r["brand_profile"]["product_catalog"]}

    def ev(r):
        return Counter(i["verification_status"] for i in r["evidence_registry"]["items"])

    lines = [f"# Research comparison: {label_a} vs {label_b}", ""]
    for name, fa, fb in (("sources (ok)", urls(a), urls(b)), ("products (sku)", skus(a), skus(b))):
        lines += [f"## {name}", f"- both: {len(fa & fb)}", f"- only {label_a}: {len(fa - fb)}", f"- only {label_b}: {len(fb - fa)}"]
        lines += [f"  - {label_a} only: {x}" for x in sorted(fa - fb)[:25]] + [f"  - {label_b} only: {x}" for x in sorted(fb - fa)[:25]]
    lines += ["", "## evidence by verification status", f"- {label_a}: {dict(ev(a))}", f"- {label_b}: {dict(ev(b))}", "",
              "## provenance and cost"]
    for lab, r in ((label_a, a), (label_b, b)):
        s = r["summary"]
        lines.append(f"- {lab}: policy={s.get('policy')} autonomous={s.get('policy_autonomous')} mode={s.get('mode')} "
                     f"stop={s.get('stop_reason')} steps={s.get('counts', {}).get('steps')} "
                     f"cost_usd={s.get('estimated_cost_usd')} analysis={r['brand_profile'].get('analysis_mode')}")
    return "\n".join(lines) + "\n"


def cmd_compare(a) -> int:
    try:
        ra, rb = _load_research(Path(a.a)), _load_research(Path(a.b))
    except (OSError, ValueError, KeyError) as e:
        print(f"error: cannot read research outputs: {e}", file=sys.stderr)
        return EXIT_ERROR
    text = compare_research(ra, rb, a.label_a, a.label_b)
    print(text)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    return EXIT_OK


def cmd_approve(a) -> int:
    settings = load_settings(a.config)
    orch = Orchestrator(settings, runs_dir=a.runs_dir, auto_approve_mock=False)
    try:
        rec = orch.approve(a.run, Gate(a.gate), approver=a.approver, reject=a.reject, note=a.note)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_ERROR
    print(f"recorded {rec.decision.value} for gate {rec.gate.value} "
          f"(fingerprint {rec.artifact_fingerprint[:12]}) by {rec.approver}")
    return EXIT_OK


def cmd_export_approvals(a) -> int:
    settings = load_settings(a.config)
    orch = Orchestrator(settings, runs_dir=a.runs_dir, auto_approve_mock=False)
    with orch.open(a.run) as (svc, *_):
        recs = svc.store.approvals(a.run)
    data = {"approvals": [{k: v for k, v in r.dump().items() if k not in ("run_id", "created_at")}
                          for r in recs]}
    Path(a.out).write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    print(f"wrote {len(recs)} approval record(s) to {a.out}")
    return EXIT_OK


def cmd_status(a) -> int:
    settings = load_settings(a.config)
    orch = Orchestrator(settings, runs_dir=a.runs_dir, auto_approve_mock=False)
    with orch.open(a.run) as (svc, graph, cfg, _):
        res = orch._result(a.run, graph, cfg)
        print(json.dumps({
            "run_id": a.run, "status": res.status, "paused_at": res.paused_at,
            "posts": {k: v["status"] for k, v in res.values.get("posts", {}).items()},
            "operations": svc.ledger.summary(a.run),
            "estimated_cost_usd": svc.ledger.total_cost(a.run)}, indent=2))
    return EXIT_OK


def cmd_brief(a) -> int:
    print("Create a brief (required fields marked *). Empty answer keeps the default.")
    fields = [("brand_name*", "brand_name", None), ("product_name*", "product_name", None),
              ("campaign_goal*", "campaign_goal", None), ("audience*", "audience", None),
              ("tone", "tone", "confident, friendly"), ("language", "language", "en"),
              ("website_url", "website_url", None)]
    data: dict = {}
    for label, key, default in fields:
        while True:
            val = input(f"{label}{f' [{default}]' if default else ''}: ").strip() or (default or "")
            if val or not label.endswith("*"):
                break
            print("  required")
        if val:
            data[key] = val
    try:
        brief = BriefInput.model_validate(data)
    except ValidationError as e:
        print(f"invalid brief: {e}", file=sys.stderr)
        return EXIT_ERROR
    out = Path(a.out)
    if out.exists() and not a.force:
        print(f"{out} exists; use --force to overwrite", file=sys.stderr)
        return EXIT_ERROR
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(brief.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
                   encoding="utf-8")
    print(f"wrote {out}")
    return EXIT_OK



# ---- Phase 3: content strategy + human approval ------------------------------------------------------
def _planner_llm(settings, a, run_dir: Path):
    """The ONE place a paid planner model is built; same guards as the research agent (request cap, spend cap, usage log)."""
    model = a.model or settings.models.planner_llm
    tag = f"_{a.usage_tag}" if getattr(a, "usage_tag", None) else ""  # a separate request/money allowance per paid step (e.g. rev1)
    price = settings.anthropic_pricing.get(model)
    for flag, val in (("--max-requests", a.max_requests), ("--max-api-spend-usd", a.max_api_spend_usd)):
        if val is None:
            raise ProviderUnavailable(f"a real planning run needs an explicit {flag}. Nothing was run")
    if price is None:
        raise ProviderUnavailable(f"anthropic_pricing in config.yaml has no entry for '{model}'; the spend cap cannot be enforced. Nothing was run")
    transport = GuardedTransport(UrllibTransport(), limit=a.max_requests, hosts=("api.anthropic.com",),
                                 log_path=run_dir / f"api_requests{tag}.log")
    llm = AnthropicLLM(model, transport, 16000, "live", input_usd_per_mtok=price.input_usd_per_mtok,  # 16000 = TASK_MAX_TOKENS["content_plan"]
                       output_usd_per_mtok=price.output_usd_per_mtok, max_prompt_tokens=price.max_prompt_tokens,
                       budget_usd=a.max_api_spend_usd, max_requests=a.max_requests, usage_path=run_dir / f"api_usage{tag}.jsonl",
                       forced_tool_choice=price.forced_tool_choice, output_effort=price.effort)
    if not llm.api_key:
        raise ProviderUnavailable("ANTHROPIC_API_KEY is not set. Nothing was run")
    return llm


def _plan_session(a, *, live: bool):
    from studio.strategy.workflow import PlanSession
    settings = load_settings(a.config)
    run_dir = Path(a.runs_dir or settings.runs_dir) / a.run
    llm = _planner_llm(settings, a, run_dir) if live else None
    return PlanSession(settings, a.run, llm=llm, runs_dir=Path(a.runs_dir) if a.runs_dir else None), llm


def _print_plan_result(res, llm) -> None:
    print(f"run_id: {res.run_id}\nstatus: {res.status}")
    if llm is not None:
        acc = llm.accounting()
        print(f"model: {llm.model_id}; API {acc['api_requests']}/{acc['max_requests']} requests, {acc['input_tokens']} in / "
              f"{acc['output_tokens']} out tokens, spent {acc['spent_usd']} of {acc['budget_usd']} USD")
    if res.paused_at:
        print(f"waiting for YOUR decision on plan hash {res.paused_at['fingerprint']}")
        print(f"review:  studio plan review --run {res.run_id}")
        print(f"decide:  studio plan approve --run {res.run_id} --comment ...   |   studio plan reject --run {res.run_id} --comment ...")
        print(f"or:      studio plan revise --run {res.run_id} --feedback ... (needs the same --max-requests/--max-api-spend-usd flags)")


def _live_plan_errors(fn):
    from studio.ledger import NeedsReconciliation
    from studio.nodes.planner_live import PlanInvalid
    try:
        return fn()
    except PlanInvalid as e:
        print(f"plan rejected by the deterministic validator after the allowed repair:\n  " + "\n  ".join(str(p) for p in e.problems), file=sys.stderr)
    except (ProviderUnavailable, ProviderResponseError, BudgetExceeded, NeedsReconciliation, ValueError, ValidationError) as e:
        print(f"planning failed: {type(e).__name__}: {e}", file=sys.stderr)
    return None


def cmd_plan_generate(a) -> int:
    try:
        sess, llm = _plan_session(a, live=True)
    except ProviderUnavailable as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_ERROR
    if not a.skip_preflight:
        try:
            pf = llm.preflight()
        except (ProviderUnavailable, BudgetExceeded) as e:
            print(f"error: {e}. Nothing was run.", file=sys.stderr)
            return EXIT_ERROR
        print(f"preflight ok: {pf['model']} accessible ({llm.api_requests} of {llm.max_requests} requests used)")
    if a.preflight_only:
        return EXIT_OK
    res = _live_plan_errors(lambda: sess.generate(Path(a.research_dir), Path(a.artifact_root) if a.artifact_root else None))
    if res is None:
        acc = llm.accounting()
        print(f"api accounting: {acc['api_requests']}/{acc['max_requests']} requests, spent {acc['spent_usd']} of {acc['budget_usd']} USD", file=sys.stderr)
        return EXIT_ERROR
    _print_plan_result(res, llm)
    return EXIT_PAUSED if res.paused_at else EXIT_OK


def cmd_plan_revise(a) -> int:
    try:
        sess, llm = _plan_session(a, live=True)
    except ProviderUnavailable as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_ERROR
    text = Path(a.feedback_file).read_text(encoding="utf-8") if a.feedback_file else a.feedback
    if not text:
        print("error: give --feedback or --feedback-file. Nothing was run.", file=sys.stderr)
        return EXIT_ERROR
    res = _live_plan_errors(lambda: sess.revise(text, requested_by="human (verbatim, relayed by the operator session)"))
    if res is None:
        return EXIT_ERROR
    _print_plan_result(res, llm)
    return EXIT_PAUSED if res.paused_at else EXIT_OK


def cmd_plan_resume(a) -> int:
    """Continue a blocked/interrupted planning step; paid calls already in the ledger are NOT repeated."""
    try:
        sess, llm = _plan_session(a, live=True)
    except ProviderUnavailable as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_ERROR
    res = _live_plan_errors(sess.resume)
    if res is None:
        return EXIT_ERROR
    _print_plan_result(res, llm)
    return EXIT_PAUSED if res.paused_at else EXIT_OK


def _edit_new_value(c: dict) -> str:
    if c["op"] == "replace":
        return c["new_value"]
    if c["op"] == "add_slide":
        return f"(new slide) {c['new_value'].get('headline', {}).get('text')}"
    return "(whole block replaced)" if c["op"] == "set_block" else "(removed)"


def cmd_plan_edit(a) -> int:
    """Apply a human-confirmed field-level edit file atomically (or --dry-run). No model is ever called."""
    from studio.strategy.edits import EditError
    sess, _ = _plan_session(a, live=False)
    try:
        r = sess.edit(a.edits, reason=a.reason, applied_by=a.applied_by, dry_run=a.dry_run)
    except EditError as e:
        print("edit REJECTED - nothing was changed:", file=sys.stderr)
        for p in e.problems:
            print(f"  - {p}", file=sys.stderr)
        return EXIT_ERROR
    print(f"{'DRY RUN (nothing written)' if r['dry_run'] else 'APPLIED'}: {len(r['changes'])} edit(s); plan {r['previous_plan_hash'][:12]} -> {r['resulting_plan_hash'][:12]}")
    for c in r["changes"]:
        where = f"{c['post']}{'/slide ' + str(c['slide']) if c['slide'] else ''}{'/shot ' + str(c['shot']) if c['shot'] else ''} {c['path']}"
        print(f"  [{c['id']}] {c['op']} {where}  ({c['authorship']})")
        print(f"      - {c['old_value']}")
        print(f"      + {_edit_new_value(c)}")
        print(f"      reason: {c['reason']}")
    for f in r["flags"]:
        print(f"  flag: {f}")
    if not r["dry_run"]:
        print(f"approval attached to the old hash no longer counts; review again: studio plan review --run {a.run}")
    return EXIT_OK


def cmd_plan_review(a) -> int:
    sess, _ = _plan_session(a, live=False)
    try:
        text = sess.review_text()
    except (KeyError, ValueError) as e:
        print(f"error: nothing to review in run {a.run}: {e}", file=sys.stderr)
        return EXIT_ERROR
    print(text)
    return EXIT_OK


def _decide(a, approve: bool) -> int:
    from studio.strategy.workflow import NotAuthorised
    sess, _ = _plan_session(a, live=False)
    h = sess.state()["plan"]["fingerprint"]
    confirm = a.confirm
    if not confirm:
        if not sys.stdin.isatty():
            print("error: a plan decision must be made by a human at a terminal (or with --confirm <first 12 hash chars> typed by "
                  "you). Nothing was recorded.", file=sys.stderr)
            return EXIT_ERROR
        print(f"You are about to {'APPROVE' if approve else 'REJECT'} plan {h}")
        confirm = input("Type the first 12 characters of the plan hash to confirm: ").strip()
    try:
        rec = sess.decide(approve=approve, comment=a.comment or "", approver=a.approver, confirmed_hash=confirm)
    except (NotAuthorised, ValueError) as e:
        print(f"error: {e}. Nothing was recorded.", file=sys.stderr)
        return EXIT_ERROR
    print(f"recorded {rec.decision.value} for plan hash {rec.artifact_fingerprint[:12]} by {rec.approver} ({rec.source.value})")
    return EXIT_OK


def cmd_plan_approve(a) -> int:
    return _decide(a, True)


def cmd_plan_reject(a) -> int:
    return _decide(a, False)


def cmd_plan_export(a) -> int:
    sess, _ = _plan_session(a, live=False)
    for p in sess.export(Path(a.out)):
        print(f"wrote {p}")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="studio", description="AI Brand Content Studio (Phase 1: mock only)")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--runs-dir", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run, resume or partially redo a workflow")
    r.add_argument("--mock", action="store_true", help="use mock providers (required in Phase 1)")
    r.add_argument("--brief", help="brief YAML (default: config default_brief)")
    r.add_argument("--run", help="existing run id to resume or redo")
    r.add_argument("--from", dest="from_stage", choices=["research", "analyst", "plan", "produce", "qa", "export"],
                   help="force redo from this stage (needs --run)")
    r.add_argument("--post", help="redo only this post, e.g. 03 (needs --run)")
    r.add_argument("--approvals", help="replay approvals from FILE (matched by fingerprint only)")
    r.add_argument("--manual-approval", action="store_true",
                   help="do not auto-approve mock artifacts; pause at each gate")
    r.add_argument("--export-dir", default=None)
    r.add_argument("--mock-fail", action="append", default=[], metavar="POST=N",
                   help="mock only: make QA reject post POST for its first N rounds")
    r.add_argument("--mock-crash", metavar="POST", help="mock only: simulate a process crash in POST's video call")
    r.set_defaults(fn=cmd_run)

    ap = sub.add_parser("approve", help="record a human decision for the gate a run is waiting at")
    ap.add_argument("--run", required=True)
    ap.add_argument("--gate", choices=[g.value for g in Gate], required=True)
    ap.add_argument("--approver", default="human")
    ap.add_argument("--reject", action="store_true")
    ap.add_argument("--note", default="")
    ap.set_defaults(fn=cmd_approve)

    ea = sub.add_parser("export-approvals", help="write a run's approval records to a replay file")
    ea.add_argument("--run", required=True)
    ea.add_argument("--out", required=True)
    ea.set_defaults(fn=cmd_export_approvals)

    rs = sub.add_parser("research", help="run the research workflow (research agent + brand analyst) on real sources")
    rs.add_argument("--brief", default="briefs/gymbeam_hr.yaml")
    rs.add_argument("--mode", choices=["live", "fixture"], default="live",
                    help="live = real HTTP; fixture = recorded responses from --fixtures")
    rs.add_argument("--policy", choices=["scripted", "anthropic"], default="anthropic",
                    help="anthropic = autonomous LLM agent (needs ANTHROPIC_API_KEY); scripted = fixed crawl plan, NOT autonomous")
    rs.add_argument("--instagram", choices=["apify", "import", "none"], default="apify")
    rs.add_argument("--instagram-import", help="manual import YAML (with provenance)")
    rs.add_argument("--fixtures", help="directory with transport.json (fixture mode)")
    rs.add_argument("--run", help="existing run id to resume or reuse the cache of")
    rs.add_argument("--max-steps", type=int, help="override research.max_steps for this run (e.g. 5)")
    rs.add_argument("--max-api-spend-usd", type=float,
                    help="hard cap on Anthropic spend; REQUIRED for a real run; checked before every request")
    rs.add_argument("--model", help="Anthropic model id (default: config models.research_llm), e.g. claude-haiku-5-5")
    rs.add_argument("--max-requests", type=int,
                    help="cap on ALL API requests incl. the preflight and retries (a real run should set it)")
    rs.add_argument("--skip-preflight", action="store_true",
                    help="skip the preflight (it counts as an API request); only after a previous preflight succeeded")
    rs.add_argument("--preflight-only", action="store_true",
                    help="verify key + model access (free) and exit without researching")
    rs.add_argument("--out", help="copy brand_profile/evidence_registry/source_index JSON here")
    rs.set_defaults(fn=cmd_research)

    cp = sub.add_parser("compare-research", help="diff two research output folders (e.g. autonomous agent vs manual)")
    cp.add_argument("--a", required=True, help="folder with brand_profile/evidence_registry/source_index JSON")
    cp.add_argument("--b", required=True)
    cp.add_argument("--label-a", default="A")
    cp.add_argument("--label-b", default="B")
    cp.add_argument("--out", help="also write the report (markdown) here")
    cp.set_defaults(fn=cmd_compare)

    pl = sub.add_parser("plan", help="Phase 3: content strategy with human approval (generate / review / approve / reject / revise / export)")
    ps = pl.add_subparsers(dest="plan_cmd", required=True)

    def live_flags(x):
        x.add_argument("--model", help="Anthropic model id (default: config models.planner_llm)")
        x.add_argument("--max-requests", type=int, help="hard cap on ALL API requests incl. preflight and retries (REQUIRED)")
        x.add_argument("--max-api-spend-usd", type=float, help="hard cap on Anthropic spend, checked before every request (REQUIRED)")
        x.add_argument("--usage-tag", help="own usage/request log (and therefore own caps) for this step, e.g. rev1")

    g = ps.add_parser("generate", help="plan three posts from the verified research with a real model, then wait for approval")
    g.add_argument("--run", required=True)
    g.add_argument("--research-dir", default="research/gymbeam_hr")
    g.add_argument("--artifact-root", default="runs/research-gymbeam-hr-live", help="run folder holding the stored packshot files (hash-checked)")
    live_flags(g)
    g.add_argument("--skip-preflight", action="store_true")
    g.add_argument("--preflight-only", action="store_true")
    g.set_defaults(fn=cmd_plan_generate)
    rv = ps.add_parser("revise", help="request changes: re-runs ONLY the planner on the same research")
    rv.add_argument("--run", required=True)
    rv.add_argument("--feedback", help="the revision request text")
    rv.add_argument("--feedback-file", help="UTF-8 file with the human's feedback, stored verbatim")
    live_flags(rv)
    rv.set_defaults(fn=cmd_plan_revise)
    rs_ = ps.add_parser("resume", help="continue a blocked/interrupted planning step (recorded paid calls are reused, not repeated)")
    rs_.add_argument("--run", required=True)
    live_flags(rs_)
    rs_.set_defaults(fn=cmd_plan_resume)
    ed = ps.add_parser("edit", help="apply human-confirmed field-level edits (exact match, atomic, validated, audited); no model call")
    ed.add_argument("--run", required=True)
    ed.add_argument("--edits", required=True, help="edits YAML (base_plan_hash + edits[])")
    ed.add_argument("--reason", required=True)
    ed.add_argument("--dry-run", action="store_true", help="preview and validate; write nothing (unconfirmed edits are allowed here)")
    ed.add_argument("--applied-by", default="Claude Code", help="who ran the command (recorded; not the author of the wording)")
    ed.set_defaults(fn=cmd_plan_edit)
    rw = ps.add_parser("review", help="show all three concepts, the exact evidence behind every claim, and the approval state")
    rw.add_argument("--run", required=True)
    rw.set_defaults(fn=cmd_plan_review)
    for name, fn, h in (("approve", cmd_plan_approve, "record YOUR approval for the exact plan hash on screen"),
                        ("reject", cmd_plan_reject, "record YOUR rejection (comment required)")):
        d = ps.add_parser(name, help=h)
        d.add_argument("--run", required=True)
        d.add_argument("--comment", default="")
        d.add_argument("--approver", help="default: your OS user name")
        d.add_argument("--confirm", help="first 12 characters of the plan hash (otherwise asked interactively)")
        d.set_defaults(fn=fn)
    ex = ps.add_parser("export", help="write content_plan.json, briefs, evidence map and metadata")
    ex.add_argument("--run", required=True)
    ex.add_argument("--out", default="plans/gymbeam_hr")
    ex.set_defaults(fn=cmd_plan_export)

    st = sub.add_parser("status", help="show run status, ledger summary and cost")
    st.add_argument("--run", required=True)
    st.set_defaults(fn=cmd_status)

    b = sub.add_parser("brief", help="interactively write a validated brief YAML")
    b.add_argument("--out", default="briefs/new_brief.yaml")
    b.add_argument("--force", action="store_true")
    b.set_defaults(fn=cmd_brief)
    return p


def load_dotenv(path: Path = Path(".env")) -> list[str]:
    """Minimal .env reader: sets variables that are NOT already in the environment. Returns the NAMES it set.

    Values are never printed or returned. Skipped when STUDIO_NO_DOTENV=1 (the test suite sets it so a real
    key on a developer machine can never reach a test)."""
    if os.environ.get("STUDIO_NO_DOTENV") == "1" or not path.is_file():
        return []
    set_names = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.removeprefix("export ").partition("=")
        name, value = name.strip(), value.strip().strip("\"'")
        if name.isidentifier() and value and name not in os.environ:
            os.environ[name] = value
            set_names.append(name)
    return set_names


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
