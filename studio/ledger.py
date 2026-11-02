"""Operation and cost ledger.

A LangGraph checkpoint does not guarantee that an external call ran exactly once
(a crash can happen between the call and the checkpoint write). The ledger records
``pending`` *before* each provider call and ``done`` after, keyed by an idempotency
key, so a resumed run can tell what happened.
"""
import json
import sqlite3
import uuid
from collections.abc import Callable
from pathlib import Path

from studio.contracts import (
    ArtifactReference,
    CostRecord,
    OperationRecord,
    OperationStatus,
    utcnow,
)
from studio.cost import CostEstimator
from studio.db import connect
from studio.providers.base import ProviderInfo

_SCHEMA = """
CREATE TABLE IF NOT EXISTS operations (
  operation_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  node TEXT NOT NULL,
  scope TEXT,
  provider TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  estimated_cost_usd REAL NOT NULL DEFAULT 0,
  artifact_json TEXT,
  result_json TEXT,
  error TEXT,
  mock INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_ops_key ON operations(run_id, idempotency_key);
CREATE TABLE IF NOT EXISTS costs (
  operation_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  record_json TEXT NOT NULL
);
"""


class NeedsReconciliation(RuntimeError):
    """An earlier attempt may have reached a non-retry-safe provider."""


class Ledger:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        with connect(db_path) as c:
            c.executescript(_SCHEMA)

    # -- writes -------------------------------------------------------------
    def begin(self, run_id, node, scope, provider: ProviderInfo, key) -> str:
        op_id = uuid.uuid4().hex
        with connect(self.db_path) as c:
            c.execute(
                "INSERT INTO operations(operation_id,run_id,node,scope,provider,idempotency_key,"
                "status,started_at,mock) VALUES (?,?,?,?,?,?,?,?,?)",
                (op_id, run_id, node, scope, provider.name, key,
                 OperationStatus.PENDING.value, utcnow().isoformat(), int(provider.is_mock)),
            )
        return op_id

    def complete(self, op_id: str, result: dict, artifact: dict | None, cost: CostRecord) -> None:
        with connect(self.db_path) as c:
            c.execute(
                "UPDATE operations SET status=?, finished_at=?, estimated_cost_usd=?, "
                "artifact_json=?, result_json=? WHERE operation_id=?",
                (OperationStatus.DONE.value, utcnow().isoformat(), cost.estimated_usd,
                 json.dumps(artifact) if artifact else None, json.dumps(result), op_id),
            )
            c.execute("INSERT OR REPLACE INTO costs VALUES (?,?,?)",
                      (op_id, cost.run_id, cost.model_dump_json()))

    def fail(self, op_id: str, error: str) -> None:
        with connect(self.db_path) as c:
            c.execute(
                "UPDATE operations SET status=?, finished_at=?, error=? WHERE operation_id=?",
                (OperationStatus.FAILED.value, utcnow().isoformat(), error[:2000], op_id),
            )

    def reconcile_pending(self, run_id: str) -> int:
        """Ops still ``pending`` when a run is re-entered were interrupted mid-call."""
        with connect(self.db_path) as c:
            cur = c.execute(
                "UPDATE operations SET status=?, error=COALESCE(error,'interrupted before completion') "
                "WHERE run_id=? AND status=?",
                (OperationStatus.UNKNOWN.value, run_id, OperationStatus.PENDING.value),
            )
            return cur.rowcount

    # -- reads --------------------------------------------------------------
    def latest(self, run_id: str, key: str) -> sqlite3.Row | None:
        with connect(self.db_path) as c:
            return c.execute(
                "SELECT * FROM operations WHERE run_id=? AND idempotency_key=? "
                "ORDER BY started_at DESC, rowid DESC LIMIT 1", (run_id, key)).fetchone()

    def list(self, run_id: str, *, status: OperationStatus | None = None,
             scope: str | None = None) -> list[OperationRecord]:
        q, args = "SELECT * FROM operations WHERE run_id=?", [run_id]
        if status:
            q += " AND status=?"
            args.append(status.value)
        if scope:
            q += " AND scope=?"
            args.append(scope)
        with connect(self.db_path) as c:
            rows = c.execute(q + " ORDER BY started_at, rowid", args).fetchall()
        return [self._record(r) for r in rows]

    def summary(self, run_id: str) -> dict[str, int]:
        out = {s.value: 0 for s in OperationStatus}
        with connect(self.db_path) as c:
            for r in c.execute("SELECT status, COUNT(*) n FROM operations WHERE run_id=? "
                               "GROUP BY status", (run_id,)):
                out[r["status"]] = r["n"]
        return out

    def total_cost(self, run_id: str) -> float:
        with connect(self.db_path) as c:
            r = c.execute("SELECT COALESCE(SUM(estimated_cost_usd),0) s FROM operations "
                          "WHERE run_id=? AND status=?",
                          (run_id, OperationStatus.DONE.value)).fetchone()
        return float(r["s"])

    @staticmethod
    def _record(r) -> OperationRecord:
        return OperationRecord(
            operation_id=r["operation_id"], run_id=r["run_id"], node=r["node"], scope=r["scope"],
            provider=r["provider"], idempotency_key=r["idempotency_key"],
            status=OperationStatus(r["status"]), started_at=r["started_at"],
            finished_at=r["finished_at"], estimated_cost_usd=r["estimated_cost_usd"],
            artifact=ArtifactReference.model_validate_json(r["artifact_json"])
            if r["artifact_json"] else None,
            error=r["error"], mock=bool(r["mock"]),
        )


class OperationRunner:
    """Wraps every provider call: idempotency check, budget guard, ledger bookkeeping."""

    def __init__(self, ledger: Ledger, estimator: CostEstimator, run_id: str):
        self.ledger, self.estimator, self.run_id = ledger, estimator, run_id

    def run(
        self,
        *,
        node: str,
        scope: str | None,
        provider: ProviderInfo,
        key: str,
        fn: Callable[[], dict],
        units: float = 1.0,
        artifact_of: Callable[[dict], dict | None] | None = None,
        verify: Callable[[dict], bool] | None = None,
        actual_cost: Callable[[dict], float] | None = None,
    ) -> dict:
        """Run ``fn`` (returns a small JSON dict) at most once per idempotency key.

        ``verify`` lets the caller reject a recorded result (e.g. artifact file vanished).
        """
        prev = self.ledger.latest(self.run_id, key)
        if prev is not None:
            status = OperationStatus(prev["status"])
            if status == OperationStatus.DONE:
                result = json.loads(prev["result_json"])
                if verify is None or verify(result):
                    return result
            elif status in (OperationStatus.PENDING, OperationStatus.UNKNOWN):
                if not provider.safe_to_retry:
                    raise NeedsReconciliation(
                        f"{node}: previous attempt {prev['operation_id']} is {status.value} "
                        f"on non-retry-safe provider {provider.name}; reconcile manually")
        usd, unit = self.estimator.estimate(provider.kind, units, mock=provider.is_mock)
        self.estimator.check_budget(self.ledger.total_cost(self.run_id), usd)
        op_id = self.ledger.begin(self.run_id, node, scope, provider, key)
        try:
            result = fn()
        except Exception as e:  # BaseException (crash/kill) deliberately leaves it pending
            self.ledger.fail(op_id, f"{type(e).__name__}: {e}")
            raise
        if actual_cost is not None:  # paid LLM calls: record what the response's usage block really cost
            usd = round(float(actual_cost(result)), 6)
        cost = CostRecord(
            operation_id=op_id, run_id=self.run_id, node=node, provider=provider.name,
            kind=provider.kind, model_id=provider.model_id, units=units, unit=unit,
            estimated_usd=usd, mock=provider.is_mock)
        self.ledger.complete(op_id, result, artifact_of(result) if artifact_of else None, cost)
        return result

