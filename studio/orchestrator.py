"""Opens a run (per-run SQLite file, providers, graph) and drives start / resume / redo.

Layout: ``<runs_dir>/<run_id>/state.db`` holds LangGraph checkpoints, the operation
ledger, the stage cache and approvals; ``<runs_dir>/<run_id>/artifacts`` holds media.
The LangGraph thread id is the run id, so it is stable across processes.
"""
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from studio.config import Settings
from studio.contracts import (
    POST_IDS,
    ApprovalDecision,
    ApprovalRecord,
    ApprovalSource,
    BriefInput,
    Gate,
    RunStatus,
)
from studio.cost import CostEstimator
from studio.graph import build_graph
from studio.ledger import Ledger, OperationRunner
from studio.providers.mock import MockProviders, build_mock_providers
from studio.services import Services
from studio.store import RunStore

# stage prefixes to invalidate when redoing from a stage
REDO = {
    "research": ["research", "analyst", "plan", "produce", "review", "judge"],
    "analyst": ["analyst", "plan", "produce", "review", "judge"],
    "plan": ["plan", "produce", "review", "judge"],
    "produce": ["produce", "review", "judge"],
    "qa": ["review", "judge"],
    "export": [],
}


@dataclass
class RunResult:
    run_id: str
    status: str
    paused_at: dict | None = None  # {"gate", "fingerprint", "summary"} when awaiting approval
    values: dict = field(default_factory=dict)


def new_run_id() -> str:
    return f"run-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"


class Orchestrator:
    def __init__(self, settings: Settings, *, runs_dir: Path | None = None,
                 export_dir: Path | None = None, providers: MockProviders | None = None,
                 auto_approve_mock: bool = True, approvals: list[ApprovalRecord] | None = None,
                 until: str | None = None):
        self.settings = settings
        self.runs_dir = Path(runs_dir or settings.runs_dir)
        self.export_dir = Path(export_dir or settings.export_dir)
        self.providers = providers or build_mock_providers(settings)
        self.auto_approve_mock = auto_approve_mock
        self.approval_candidates = approvals or []
        self.until = until  # None = full workflow; "analyst" = research workflow only

    def run_dir(self, run_id: str) -> Path:
        return self.runs_dir / run_id

    @contextmanager
    def open(self, run_id: str):
        run_dir = self.run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        db = run_dir / "state.db"
        ledger, store = Ledger(db), RunStore(db)
        n = ledger.reconcile_pending(run_id)  # earlier crash left calls in doubt
        p = self.providers
        svc = Services(
            settings=self.settings, run_id=run_id, run_dir=run_dir, export_dir=self.export_dir,
            llm=p.llm, vision=p.vision, image=p.image, video=p.video,
            research=p.research(run_dir) if callable(p.research) else p.research,
            ledger=ledger, store=store,
            runner=OperationRunner(ledger, CostEstimator(self.settings), run_id),
            auto_approve_mock=self.auto_approve_mock)
        if not svc.is_mock and self.auto_approve_mock:
            raise RuntimeError("auto approval requested with non-mock providers")
        for rec in self.approval_candidates:  # replay: stored, but only matched by fingerprint
            if store.find_approval(run_id, rec.gate, rec.artifact_fingerprint) is None:
                store.add_approval(rec.model_copy(update={
                    "run_id": run_id, "source": ApprovalSource.FIXTURE_FILE}))
        conn = sqlite3.connect(db, check_same_thread=False, timeout=30)
        try:
            saver = SqliteSaver(conn)
            yield svc, build_graph(svc, saver, self.until), {"configurable": {"thread_id": run_id}}, n
        finally:
            conn.close()

    # -- main entry ---------------------------------------------------------
    def run(self, run_id: str | None = None, *, brief: BriefInput | None = None,
            from_stage: str | None = None, post: str | None = None) -> RunResult:
        """Start a run, resume an interrupted one, or redo part of a finished one."""
        run_id = run_id or new_run_id()
        if post is not None and post not in POST_IDS:
            raise ValueError(f"unknown post {post!r}; expected one of {POST_IDS}")
        if from_stage is not None and from_stage not in REDO:
            raise ValueError(f"unknown stage {from_stage!r}; expected one of {sorted(REDO)}")
        with self.open(run_id) as (svc, graph, cfg, _):
            snap = graph.get_state(cfg)
            existing = snap.values.get("brief")
            fresh = brief is not None or from_stage is not None or post is not None
            if existing is None and brief is None:
                raise ValueError(f"run {run_id} has no brief; pass one to start it")
            if fresh:
                if from_stage:
                    svc.store.invalidate(run_id, prefixes=REDO[from_stage])
                if post:
                    svc.store.invalidate(run_id, prefixes=REDO["produce"], scope=post)
                graph.invoke({
                    "run_id": run_id, "brief": (brief.dump() if brief else existing),
                    "only_posts": [post] if post else None, "status": RunStatus.RUNNING.value,
                }, cfg)
            elif snap.next:
                graph.invoke(None, cfg)  # continue the interrupted / crashed execution
            res = self._result(run_id, graph, cfg)
            if self.until and not res.paused_at and res.status == RunStatus.RUNNING.value:
                res.status = "research_completed"
            return res

    @staticmethod
    def _result(run_id, graph, cfg) -> RunResult:
        snap = graph.get_state(cfg)
        paused = None
        for t in snap.tasks:
            if t.interrupts:
                paused = t.interrupts[0].value
        status = (RunStatus.AWAITING_APPROVAL.value if paused
                  else snap.values.get("status", RunStatus.CREATED.value))
        return RunResult(run_id=run_id, status=status, paused_at=paused, values=snap.values)

    # -- approvals ----------------------------------------------------------
    def approve(self, run_id: str, gate: Gate, *, approver: str, reject: bool = False,
                note: str = "") -> ApprovalRecord:
        """Record a human decision for the fingerprint that is *currently* awaiting approval."""
        with self.open(run_id) as (svc, graph, cfg, _):
            paused = self._result(run_id, graph, cfg).paused_at
            if not paused or paused["gate"] != gate.value:
                raise ValueError(f"run {run_id} is not waiting at gate {gate.value!r}")
            rec = ApprovalRecord(
                run_id=run_id, gate=gate, artifact_fingerprint=paused["fingerprint"],
                decision=ApprovalDecision.REJECTED if reject else ApprovalDecision.APPROVED,
                approver=approver, source=ApprovalSource.HUMAN_CLI, note=note)
            svc.store.add_approval(rec)
            return rec
