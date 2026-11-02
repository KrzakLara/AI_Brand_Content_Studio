"""Phase 3 workflow on the shared engine: plan -> human review -> approve / reject / revise -> export.

All state lives in the per-run SQLite file (checkpoints, ledger, stage cache, approvals). Approvals are bound to the
plan's content hash; any change to the plan produces a new hash and the old approval stops matching.
"""
import getpass
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from studio.config import Settings
from studio.contracts import ApprovalDecision, ApprovalRecord, ApprovalSource, Gate, ProviderKind
from studio.contracts.strategy import CampaignPlan
from studio.orchestrator import Orchestrator
from studio.providers.live import UnavailableProvider
from studio.strategy import render
from studio.strategy.dossier import build_dossier


class NotAuthorised(RuntimeError):
    """A decision was attempted without the human confirmation the gate requires."""


def make_providers(llm) -> SimpleNamespace:
    no = lambda k: UnavailableProvider(k, "not part of the planning workflow")  # noqa: E731
    return SimpleNamespace(llm=llm, vision=no(ProviderKind.VISION), image=no(ProviderKind.IMAGE), video=no(ProviderKind.VIDEO),
                           research=lambda run_dir: no(ProviderKind.RESEARCH))


class PlanSession:
    def __init__(self, settings: Settings, run_id: str, *, llm=None, runs_dir: Path | None = None):
        # read-only / decision use: an UnavailableProvider, so no model (and no mock) can ever be called through it
        providers = make_providers(llm or UnavailableProvider(ProviderKind.LLM, "this session cannot call a model"))
        self.orch = Orchestrator(settings, runs_dir=runs_dir, providers=providers, auto_approve_mock=False, until="plan")
        self.run_id = run_id

    # ---- generate / revise ------------------------------------------------------------------------
    def _invoke(self, payload: dict | None):
        with self.orch.open(self.run_id) as (svc, graph, cfg, _):
            graph.invoke(payload, cfg)
            return self.orch._result(self.run_id, graph, cfg)

    def generate(self, research_dir: Path, artifact_root: Path | None = None):
        d = build_dossier(research_dir, artifact_root=artifact_root)
        return self._invoke({"run_id": self.run_id, "status": "running", "plan_feedback": [], "plan_previous": None,
                             "strategy_inputs": {"research_dir": str(research_dir), "artifact_root": str(artifact_root) if artifact_root else None,
                                                 "dossier_fingerprint": d.fingerprint}})

    # ---- human edits ---------------------------------------------------------------------------------
    def edit_history_path(self) -> Path:
        return self.orch.run_dir(self.run_id) / "plan" / "edit_history.json"

    def edit_history(self) -> list[dict]:
        p = self.edit_history_path()
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else []

    def edit(self, edits_path, *, reason: str, applied_by: str = "Claude Code", dry_run: bool = False) -> dict:
        """Apply a human-confirmed edit file atomically (or preview it). Raises EditError and changes NOTHING unless every edit is valid."""
        from studio.nodes.planner_live import plan_fingerprint
        from studio.strategy import edits as E
        if not reason.strip():
            raise E.EditError(["a reason is required"])
        doc, _, d = self.current()
        ef = E.load_edit_file(edits_path)
        prepared = E.prepare(doc["campaign"], ef, current_hash=doc["plan_hash"], require_confirmation=not dry_run)
        new = E.apply_all(doc["campaign"], prepared)
        plan, flags = E.validated(new, d)
        new = plan.model_dump(mode="json")  # persist the validated canonical form (integers stay integers)
        new_hash = plan_fingerprint(new, doc["packshot"])
        if new_hash == doc["plan_hash"]:
            raise E.EditError(["the edits do not change the plan"])
        recs = E.records(prepared, new)
        result = {"dry_run": dry_run, "previous_plan_hash": doc["plan_hash"], "resulting_plan_hash": new_hash, "changes": recs, "flags": flags, "reason": reason,
                  "applied_by": None if dry_run else applied_by}
        if dry_run:
            return result
        hist = self.edit_history()
        entry = {"edit_id": len(hist) + 1, "applied_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "applied_by": applied_by, "reason": reason,
                 "previous_plan_hash": doc["plan_hash"], "previous_plan_file": f"plan/plan_{doc['plan_hash'][:12]}.json",
                 "resulting_plan_hash": new_hash, "resulting_plan_file": f"plan/plan_{new_hash[:12]}.json", "edits_file_base_hash": ef.base_plan_hash, "edits": recs}
        meta = {**doc["meta"], "edited_from": doc["plan_hash"], "edit_id": entry["edit_id"], "validation_flags": flags}
        plan_dir = self.orch.run_dir(self.run_id) / "plan"
        (plan_dir / f"plan_{new_hash[:12]}.json").write_text(json.dumps({"plan_hash": new_hash, "campaign": new, "packshot": doc["packshot"], "meta": meta},
                                                                       indent=2, ensure_ascii=False), encoding="utf-8")
        state_plan = {"plan": plan.to_content_plan().dump(), "campaign": new, "packshot": doc["packshot"], "meta": meta, "fingerprint": new_hash}
        with self.orch.open(self.run_id) as (svc, graph, cfg, _):  # same checkpointed graph: the plan changes, the gate re-opens on the NEW hash
            graph.update_state(cfg, {"plan": state_plan, "plan_approval": {}}, as_node="content_planner")
            graph.invoke(None, cfg)
        (plan_dir / "current.json").write_text(json.dumps({"plan_hash": new_hash, "file": f"plan_{new_hash[:12]}.json"}), encoding="utf-8")
        hist.append(entry)
        self.edit_history_path().write_text(json.dumps(hist, indent=2, ensure_ascii=False), encoding="utf-8")
        return result

    def attribution_path(self) -> Path:
        return self.orch.run_dir(self.run_id) / "plan" / "attribution_corrections.json"

    def attribution_corrections(self) -> list[dict]:
        p = self.attribution_path()
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else []

    def correct_attribution(self, *, edit_id: int, item_id: str, segments: list[dict], basis: str, corrected_by: str = "Claude Code") -> dict:
        """Append-only correction of who wrote which part of an already applied edit. The edit history itself is never rewritten.

        ``segments`` (in order, joined by a space) must reproduce the applied text exactly; each has an origin: ai_proposed,
        ai_proposed_modified_by_human or human_authored."""
        entry = next((e for e in self.edit_history() if e["edit_id"] == edit_id), None)
        rec = next((c for c in (entry or {}).get("edits", []) if c["id"] == item_id), None)
        if rec is None:
            raise ValueError(f"no applied edit {item_id} in edit entry {edit_id}")
        allowed = {"ai_proposed", "ai_proposed_modified_by_human", "human_authored"}
        if any(s["origin"] not in allowed for s in segments):
            raise ValueError(f"segment origin must be one of {sorted(allowed)}")
        if " ".join(s["text"] for s in segments) != rec["new_value"]:
            raise ValueError("segments do not reproduce the applied text exactly")
        origins = {s["origin"] for s in segments}
        out = {"correction_id": len(self.attribution_corrections()) + 1, "corrected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "corrected_by": corrected_by, "edit_id": edit_id, "edit_item_id": item_id, "text": rec["new_value"],
               "previously_recorded_authorship": rec["authorship"],
               "corrected_authorship": "human_authored" if origins == {"human_authored"} else "mixed_ai_proposed_and_human_authored",
               "segments": segments, "basis": basis}
        allc = self.attribution_corrections() + [out]
        self.attribution_path().write_text(json.dumps(allc, indent=2, ensure_ascii=False), encoding="utf-8")
        return out

    def resume(self):
        """Continue an interrupted/blocked run. Paid calls already recorded in the ledger are reused (no new request)."""
        res = self._invoke(None)
        hist = self.history()
        if hist and hist[-1]["new_plan_hash"] is None and "plan" in self.state():
            hist[-1]["new_plan_hash"] = self.state()["plan"]["fingerprint"]
            self.history_path().write_text(json.dumps(hist, indent=2, ensure_ascii=False), encoding="utf-8")
        return res

    def state(self) -> dict:
        with self.orch.open(self.run_id) as (svc, graph, cfg, _):
            return dict(graph.get_state(cfg).values)

    def history_path(self) -> Path:
        return self.orch.run_dir(self.run_id) / "plan" / "revision_history.json"

    def history(self) -> list[dict]:
        p = self.history_path()
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else []

    def revise(self, feedback: str, *, requested_by: str = "human", note: str = ""):
        """Same engine, research untouched: only the planner re-runs (new fingerprint => new model call).

        The previous plan stays on disk (plan_<hash>.json), the human's feedback is kept VERBATIM in revision_history.json (it is a
        revision request, NOT an approval or rejection record), and the dossier is rebuilt so human decisions recorded in the
        canonical brief since the first plan (confirmed product, locked copy, label crops) are used."""
        if not feedback.strip():
            raise ValueError("revision feedback must not be empty")
        v = self.state()
        if "plan" not in v:
            raise ValueError("this run has no plan to revise")
        si = dict(v["strategy_inputs"])
        d = build_dossier(Path(si["research_dir"]), artifact_root=Path(si["artifact_root"]) if si.get("artifact_root") else None)
        hist = self.history()
        entry = {"revision": len(hist) + 1, "requested_by": requested_by, "is_approval": False, "kind": "revision_request",
                 "feedback_verbatim": feedback, "note": note, "previous_plan_hash": v["plan"]["fingerprint"],
                 "previous_plan_file": f"plan/plan_{v['plan']['fingerprint'][:12]}.json", "dossier_before": si.get("dossier_fingerprint"),
                 "dossier_after": d.fingerprint, "requested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "new_plan_hash": None}
        hist.append(entry)
        self.history_path().parent.mkdir(parents=True, exist_ok=True)
        self.history_path().write_text(json.dumps(hist, indent=2, ensure_ascii=False), encoding="utf-8")
        si["dossier_fingerprint"] = d.fingerprint
        res = self._invoke({"run_id": self.run_id, "status": "running", "plan_feedback": [*v.get("plan_feedback", []), feedback.strip()],
                            "plan_previous": v["plan"]["campaign"], "strategy_inputs": si})
        entry["new_plan_hash"] = self.state()["plan"]["fingerprint"]
        self.history_path().write_text(json.dumps(hist, indent=2, ensure_ascii=False), encoding="utf-8")
        return res

    # ---- review -----------------------------------------------------------------------------------
    def current(self) -> tuple[dict, CampaignPlan, object]:
        v = self.state()
        p = v["plan"]
        doc = {"plan_hash": p["fingerprint"], "campaign": p["campaign"], "packshot": p["packshot"], "meta": p["meta"]}
        d = build_dossier(Path(v["strategy_inputs"]["research_dir"]), artifact_root=Path(a) if (a := v["strategy_inputs"].get("artifact_root")) else None)
        return doc, CampaignPlan.model_validate(p["campaign"]), d

    def approval_state(self) -> dict:
        """Does a human decision exist for EXACTLY the current plan hash?"""
        h = self.state()["plan"]["fingerprint"]
        with self.orch.open(self.run_id) as (svc, *_):
            rec = svc.store.find_approval(self.run_id, Gate.PLAN, h)
            stale = svc.store.has_other_fingerprint(self.run_id, Gate.PLAN, h)
        if rec is None:
            return {"decision": None, "hash": h, "stale_ignored": stale,
                    "text": "NONE for this plan hash" + (" (earlier decisions concern a different version and are ignored)" if stale else "")}
        return {"decision": rec.decision.value, "hash": h, "approver": rec.approver, "source": rec.source.value, "note": rec.note,
                "stale_ignored": stale, "text": f"{rec.decision.value.upper()} by {rec.approver} ({rec.source.value}) for this exact hash"
                                                + (f" - note: {rec.note}" if rec.note else "")}

    def review_text(self) -> str:
        doc, plan, d = self.current()
        return render.render_review(doc, plan, d, self.approval_state())

    # ---- decisions (human only) ---------------------------------------------------------------------
    def decide(self, *, approve: bool, comment: str, approver: str | None, confirmed_hash: str) -> ApprovalRecord:
        """Record a human decision for the plan CURRENTLY awaiting approval. ``confirmed_hash`` must be typed by the human."""
        h = self.state()["plan"]["fingerprint"]
        if not confirmed_hash or not h.startswith(confirmed_hash.strip().lower()) or len(confirmed_hash.strip()) < 12:
            raise NotAuthorised(f"confirmation does not match the current plan hash (expected the first 12 characters: {h[:12]})")
        if not approve and not comment.strip():
            raise ValueError("a rejection needs a comment explaining why")
        rec = self.orch.approve(self.run_id, Gate.PLAN, approver=approver or getpass.getuser(), reject=not approve, note=comment)
        assert rec.source == ApprovalSource.HUMAN_CLI and rec.artifact_fingerprint == h
        self._invoke(None)  # resume the paused graph so the run status reflects the decision
        return rec

    # ---- export -------------------------------------------------------------------------------------
    def export(self, out: Path) -> list[Path]:
        doc, plan, d = self.current()
        out = Path(out)
        (out / "briefs").mkdir(parents=True, exist_ok=True)
        v = self.state()
        em = render.evidence_map(plan, d)
        run_dir = self.orch.run_dir(self.run_id)
        usage, by_file = [], {}
        for up in sorted(run_dir.glob("api_usage*.jsonl")):  # one file per paid step (draft, revision tags): caps apply per step
            rows = [json.loads(x) for x in up.read_text(encoding="utf-8").splitlines() if x.strip()]
            usage += rows
            by_file[up.name] = round(sum(r.get("cost_usd") or 0 for r in rows if r.get("kind") == "usage"), 6)
        msgs = [u for u in usage if u.get("kind") == "usage"]
        with self.orch.open(self.run_id) as (svc, *_):
            ledger = {"operations": svc.ledger.summary(self.run_id), "ledger_cost_usd": svc.ledger.total_cost(self.run_id)}
        meta = {**doc["meta"], "plan_hash": doc["plan_hash"], "run_id": self.run_id,
                "approval": self.approval_state(),
                "usage": {"requests_total": sum(u.get("requests", 0) for u in usage),
                          "message_requests": sum(1 for u in usage if u.get("kind") == "message"),
                          "preflight_requests": sum(1 for u in usage if u.get("kind") == "preflight"),
                          "input_tokens": sum(u.get("input_tokens") or 0 for u in msgs), "output_tokens": sum(u.get("output_tokens") or 0 for u in msgs),
                          "cost_usd": round(sum(u.get("cost_usd") or 0 for u in msgs), 6), "cost_usd_by_usage_file": by_file, "calls": msgs},
                "ledger": ledger, "revision_history": self.history(), "edit_history": self.edit_history(), "attribution_corrections": self.attribution_corrections()}
        files = {
            "content_plan.json": {"plan_hash": doc["plan_hash"], "status": meta["approval"]["text"], "campaign": doc["campaign"],
                                  "packshot_reference": doc["packshot"], "content_plan_compact": v["plan"]["plan"]},
            "evidence_map.json": em, "plan_metadata.json": meta,
        }
        written = []
        for name, content in files.items():
            (out / name).write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")
            written.append(out / name)
        for name, text in (("campaign.md", render.brief_campaign(plan)), ("post_01_carousel.md", render.brief_carousel(plan)),
                           ("post_02_hero.md", render.brief_hero(plan)), ("post_03_reel.md", render.brief_reel(plan))):
            (out / "briefs" / name).write_text(text, encoding="utf-8")
            written.append(out / "briefs" / name)
        (out / "review.txt").write_text(render.render_review(doc, plan, d, self.approval_state()), encoding="utf-8")
        written.append(out / "review.txt")
        if self.history():
            (out / "revision_history.json").write_text(json.dumps(self.history(), indent=2, ensure_ascii=False), encoding="utf-8")
            written.append(out / "revision_history.json")
        if self.attribution_corrections():
            (out / "attribution_corrections.json").write_text(json.dumps(self.attribution_corrections(), indent=2, ensure_ascii=False), encoding="utf-8")
            written.append(out / "attribution_corrections.json")
        if self.edit_history():
            (out / "edit_history.json").write_text(json.dumps(self.edit_history(), indent=2, ensure_ascii=False), encoding="utf-8")
            written.append(out / "edit_history.json")
        versions = out / "history" / "plan_versions"  # every plan version ever produced stays available, byte for byte
        versions.mkdir(parents=True, exist_ok=True)
        for src in sorted((run_dir / "plan").glob("plan_*.json")):
            shutil.copy2(src, versions / src.name)
        for src in [*sorted(run_dir.glob("api_usage*.jsonl")), *sorted(run_dir.glob("api_requests*.log"))]:
            shutil.copy2(src, out / src.name)
            written.append(out / src.name)
        return written
