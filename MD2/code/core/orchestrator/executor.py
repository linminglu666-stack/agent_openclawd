from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import uuid

from core.persistence import JsonlWAL, SqliteStateStore

from .dag import DagSpec


class RunStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RunRecord:
    run_id: str
    dag: Dict[str, Any]
    status: RunStatus
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    node_status: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "dag": self.dag,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "node_status": self.node_status,
            "metadata": self.metadata,
        }


class DagExecutor:
    def __init__(self, state_store: SqliteStateStore, wal: JsonlWAL):
        self._state = state_store
        self._wal = wal

    def start(self, spec: DagSpec, metadata: Optional[Dict[str, Any]] = None) -> RunRecord:
        run_id = f"run-{uuid.uuid4().hex}"
        record = RunRecord(
            run_id=run_id,
            dag=spec.to_dict(),
            status=RunStatus.PENDING,
            metadata=metadata or {},
            node_status={n["node_id"]: "pending" for n in spec.to_dict()["nodes"]},
        )
        self._persist(record)
        self._wal.append("orchestrator_run_started", {"run_id": run_id, "dag_id": spec.dag_id})
        return record

    def load(self, run_id: str) -> Optional[RunRecord]:
        obj = self._state.get(f"orchestrator/run/{run_id}")
        if not obj:
            return None
        value = obj.get("value") or {}
        try:
            status = RunStatus(str(value.get("status", "pending")))
        except Exception:
            status = RunStatus.PENDING
        return RunRecord(
            run_id=str(value.get("run_id", run_id)),
            dag=dict(value.get("dag") or {}),
            status=status,
            created_at=str(value.get("created_at", "")),
            updated_at=str(value.get("updated_at", "")),
            node_status=dict(value.get("node_status") or {}),
            metadata=dict(value.get("metadata") or {}),
        )

    def mark_running(self, run_id: str) -> bool:
        rec = self.load(run_id)
        if not rec:
            return False
        rec.status = RunStatus.RUNNING
        rec.updated_at = datetime.utcnow().isoformat()
        self._persist(rec)
        self._wal.append("orchestrator_run_running", {"run_id": run_id})
        return True

    def mark_node(self, run_id: str, node_id: str, status: str) -> bool:
        rec = self.load(run_id)
        if not rec:
            return False
        rec.node_status[node_id] = status
        rec.updated_at = datetime.utcnow().isoformat()
        self._persist(rec)
        self._wal.append("orchestrator_node_status", {"run_id": run_id, "node_id": node_id, "status": status})
        return True

    def mark_completed(self, run_id: str, ok: bool) -> bool:
        rec = self.load(run_id)
        if not rec:
            return False
        rec.status = RunStatus.COMPLETED if ok else RunStatus.FAILED
        rec.updated_at = datetime.utcnow().isoformat()
        self._persist(rec)
        self._wal.append("orchestrator_run_completed", {"run_id": run_id, "ok": ok})
        return True

    def _persist(self, rec: RunRecord) -> bool:
        return self._state.put(f"orchestrator/run/{rec.run_id}", rec.to_dict())

