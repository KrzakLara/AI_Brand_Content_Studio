"""`studio` command line."""
import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import yaml
from pydantic import ValidationError

from studio.config import load_settings
from studio.contracts import ApprovalRecord, BriefInput, Gate, ProviderKind, RunStatus, SourceIndex
from studio.orchestrator import Orchestrator
from studio.providers.base import ProviderResponseError, ProviderUnavailable
from studio.providers.live import AnthropicLLM, ScriptedResearchPolicy, UnavailableProvider
from studio.providers.mock import SimulatedCrash, build_mock_providers
from studio.tools.instagram import ApifyInstagram, ManualImportInstagram
from studio.tools.toolset import ResearchToolset
from studio.tools.transport import RecordedTransport, UrllibTransport
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


def cmd_research(a) -> int:
    """Research workflow (research_agent -> brand_product_analyst) on the shared engine."""
    settings = load_settings(a.config)
    cfg = settings.research
    if a.mode == "live":
        transport, origin = UrllibTransport(), "live"
    else:
        if not a.fixtures:
            print("error: --mode fixture needs --fixtures DIR (containing transport.json)", file=sys.stderr)
            return EXIT_ERROR
        transport, origin = RecordedTransport.from_file(Path(a.fixtures) / "transport.json"), "fixture"
    if a.policy == "anthropic":
        llm = AnthropicLLM(settings.models.research_llm, transport, cfg.anthropic_max_tokens, origin)
        if not llm.api_key:
            print("error: --policy anthropic needs ANTHROPIC_API_KEY (not set). Nothing was run. Choose "
                  "--policy scripted explicitly to use the non-autonomous scripted crawl plan.", file=sys.stderr)
            return EXIT_ERROR
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
    except (ProviderUnavailable, ProviderResponseError, ValueError, ValidationError) as e:
        print(f"research failed: {type(e).__name__}: {e}", file=sys.stderr)
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
        "operations": ops, "estimated_cost_usd": cost, "trace": v["research"]["trace"]}
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
          f"estimated cost: ${cost:.4f}")
    if a.out:
        print(f"wrote: {a.out}")
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
    rs.add_argument("--out", help="copy brand_profile/evidence_registry/source_index JSON here")
    rs.set_defaults(fn=cmd_research)

    st = sub.add_parser("status", help="show run status, ledger summary and cost")
    st.add_argument("--run", required=True)
    st.set_defaults(fn=cmd_status)

    b = sub.add_parser("brief", help="interactively write a validated brief YAML")
    b.add_argument("--out", default="briefs/new_brief.yaml")
    b.add_argument("--force", action="store_true")
    b.set_defaults(fn=cmd_brief)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
