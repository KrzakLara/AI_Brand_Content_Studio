"""Stage cache and approval records, in the same per-run SQLite file as the checkpoints.

A stage entry is valid only if (a) it was not invalidated and (b) its stored input
fingerprint equals the freshly computed one.
"""
import json
from pathlib import Path

from studio.contracts import ApprovalDecision, ApprovalRecord, Gate
from studio.db import connect

_SCHEMA = """
CREATE TABLE IF NOT EXISTS stage_cache (
  run_id TEXT NOT NULL, scope TEXT NOT NULL, stage TEXT NOT NULL,
  fingerprint TEXT NOT NULL, output_json TEXT NOT NULL,
  generation INTEGER NOT NULL DEFAULT 0, valid INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (run_id, scope, stage)
);
CREATE TABLE IF NOT EXISTS stage_generation (
  run_id TEXT NOT NULL, scope TEXT NOT NULL, stage TEXT NOT NULL,
  generation INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (run_id, scope, stage)
);
CREATE TABLE IF NOT EXISTS approvals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL, gate TEXT NOT NULL, fingerprint TEXT NOT NULL,
  record_json TEXT NOT NULL
);
"""

GLOBAL = "run"  # scope used for stages that are not per-post


class RunStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        with connect(db_path) as c:
            c.executescript(_SCHEMA)

    # -- stage cache --------------------------------------------------------
    def get_stage(self, run_id: str, scope: str, stage: str, fp: str) -> dict | None:
        with connect(self.db_path) as c:
            r = c.execute(
                "SELECT output_json FROM stage_cache WHERE run_id=? AND scope=? AND stage=? "
                "AND fingerprint=? AND valid=1", (run_id, scope, stage, fp)).fetchone()
        return json.loads(r["output_json"]) if r else None

    def put_stage(self, run_id: str, scope: str, stage: str, fp: str, output: dict) -> None:
        gen = self.generation(run_id, scope, stage)
        with connect(self.db_path) as c:
            c.execute("INSERT OR REPLACE INTO stage_cache VALUES (?,?,?,?,?,?,1)",
                      (run_id, scope, stage, fp, json.dumps(output), gen))

    def generation(self, run_id: str, scope: str, stage: str) -> int:
        with connect(self.db_path) as c:
            r = c.execute("SELECT generation FROM stage_generation WHERE run_id=? AND scope=? "
                          "AND stage=?", (run_id, scope, stage)).fetchone()
        return r["generation"] if r else 0

    def invalidate(self, run_id: str, *, prefixes: list[str], scope: str | None = None) -> int:
        """Force a redo of matching stages: drop the cache and bump their generation.

        The generation is part of every operation idempotency key, so a forced redo
        is a deliberate new operation, never a silent replay of the ledger.
        """
        n = 0
        with connect(self.db_path) as c:
            rows = c.execute("SELECT scope, stage FROM stage_cache WHERE run_id=?",
                             (run_id,)).fetchall()
            for r in rows:
                if scope is not None and r["scope"] != scope:
                    continue
                if not any(r["stage"].startswith(p) for p in prefixes):
                    continue
                c.execute("UPDATE stage_cache SET valid=0 WHERE run_id=? AND scope=? AND stage=?",
                          (run_id, r["scope"], r["stage"]))
                c.execute(
                    "INSERT INTO stage_generation VALUES (?,?,?,1) ON CONFLICT(run_id,scope,stage) "
                    "DO UPDATE SET generation=generation+1", (run_id, r["scope"], r["stage"]))
                n += 1
        return n

    # -- approvals ----------------------------------------------------------
    def add_approval(self, rec: ApprovalRecord) -> None:
        with connect(self.db_path) as c:
            c.execute("INSERT INTO approvals(run_id,gate,fingerprint,record_json) VALUES (?,?,?,?)",
                      (rec.run_id, rec.gate.value, rec.artifact_fingerprint, rec.model_dump_json()))

    def find_approval(self, run_id: str, gate: Gate, fp: str) -> ApprovalRecord | None:
        """Latest decision for exactly this artifact fingerprint; others never match."""
        with connect(self.db_path) as c:
            r = c.execute("SELECT record_json FROM approvals WHERE run_id=? AND gate=? AND "
                          "fingerprint=? ORDER BY id DESC LIMIT 1", (run_id, gate.value, fp)).fetchone()
        return ApprovalRecord.model_validate_json(r["record_json"]) if r else None

    def approvals(self, run_id: str) -> list[ApprovalRecord]:
        with connect(self.db_path) as c:
            rows = c.execute("SELECT record_json FROM approvals WHERE run_id=? ORDER BY id",
                             (run_id,)).fetchall()
        return [ApprovalRecord.model_validate_json(r["record_json"]) for r in rows]

    def has_other_fingerprint(self, run_id: str, gate: Gate, fp: str) -> bool:
        with connect(self.db_path) as c:
            r = c.execute("SELECT 1 FROM approvals WHERE run_id=? AND gate=? AND fingerprint<>? "
                          "LIMIT 1", (run_id, gate.value, fp)).fetchone()
        return r is not None


def is_approved(rec: ApprovalRecord | None) -> bool:
    return rec is not None and rec.decision == ApprovalDecision.APPROVED
