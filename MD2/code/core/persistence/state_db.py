from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import sqlite3
import threading
import time
import uuid

from utils.serializer import Serializer

from protocols.workflow import (
    ScheduleRecord,
    RunRecord,
    NodeRunRecord,
    WorkItemRecord,
    RunStatus,
    NodeRunStatus,
    WorkItemStatus,
    now_unix,
    schedule_policy_validate,
    RUN_TRANSITIONS,
    NODE_TRANSITIONS,
    WORK_ITEM_TRANSITIONS,
)
from protocols.approvals import ApprovalStatus, ApprovalRequest, ApprovalDecision
from protocols.workflows import WorkflowDefinition
from protocols.learning import LearningReport

from .schema import ALL_MIGRATIONS


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _normalize_risk_factors(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for it in items or []:
        if not isinstance(it, dict):
            out.append({"factor": str(it), "score": 0.0, "weight": 0.0})
            continue
        factor = it.get("factor") or it.get("name") or it.get("type") or it.get("reason") or ""
        score = _coerce_float(it.get("score"), 0.0)
        weight = _coerce_float(it.get("weight"), 0.0)
        details = {k: v for k, v in it.items() if k not in {"factor", "name", "type", "reason", "score", "weight"}}
        payload: Dict[str, Any] = {"factor": str(factor), "score": score, "weight": weight}
        if details:
            payload["details"] = details
        out.append(payload)
    return out


def _normalize_risk_score(value: Any) -> float:
    score = _coerce_float(value, 0.0)
    if score <= 1.0:
        score = score * 100.0
    if score > 100.0:
        score = 100.0
    if score < 0.0:
        score = 0.0
    return score


def _flatten_learning_content(entry: Dict[str, Any]) -> Dict[str, Any]:
    content = dict(entry.get("content") or {})
    merged = dict(entry)
    merged["summary"] = content.get("summary", "")
    merged["new_skills"] = content.get("new_skills") or []
    merged["memory_delta"] = content.get("memory_delta") or []
    merged["validation"] = content.get("validation") or {}
    merged["rollback_info"] = content.get("rollback_info") or {}
    return merged


def _can_transition(current, target, transitions: Dict[Any, List[Any]]) -> bool:
    if current == target:
        return True
    return target in (transitions.get(current) or [])


@dataclass
class DbConfig:
    path: str


class StateDB:
    def __init__(self, config: DbConfig):
        self._path = Path(config.path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._configure()
        self.migrate()

    def _configure(self) -> None:
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.commit()

    def migrate(self) -> None:
        with self._lock:
            self._conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at INTEGER NOT NULL)")
            cur = self._conn.execute("SELECT version FROM schema_migrations")
            applied = {int(r["version"]) for r in cur.fetchall()}

            for m in ALL_MIGRATIONS:
                if m.version in applied:
                    continue
                for stmt in m.ddl:
                    self._conn.execute(stmt)
                self._conn.execute("INSERT INTO schema_migrations(version, applied_at) VALUES(?, ?)", (m.version, int(time.time())))
                self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def create_schedule(self, workflow_id: str, version: str, enabled: bool, policy: Dict[str, Any]) -> ScheduleRecord:
        ok, err = schedule_policy_validate(policy)
        if not ok:
            raise ValueError(err)
        schedule_id = f"sch-{uuid.uuid4().hex}"
        next_fire_at = 0
        with self._lock:
            self._conn.execute(
                "INSERT INTO schedules(id, workflow_id, version, enabled, policy_json, next_fire_at) VALUES(?,?,?,?,?,?)",
                (schedule_id, workflow_id, version, 1 if enabled else 0, Serializer.to_json(policy), int(next_fire_at)),
            )
            self._conn.commit()
        return ScheduleRecord(id=schedule_id, workflow_id=workflow_id, version=version, enabled=enabled, policy_json=policy, next_fire_at=next_fire_at)

    def set_schedule_next_fire_at(self, schedule_id: str, next_fire_at: int) -> bool:
        with self._lock:
            cur = self._conn.execute("UPDATE schedules SET next_fire_at = ? WHERE id = ?", (int(next_fire_at), schedule_id))
            self._conn.commit()
            return cur.rowcount > 0

    def add_schedule_trigger(self, schedule_id: str, fire_at: int, run_id: str, status: str) -> bool:
        now = now_unix()
        with self._lock:
            self._conn.execute(
                "INSERT INTO schedule_triggers(schedule_id, fire_at, run_id, status, created_at) VALUES(?,?,?,?,?)",
                (schedule_id, int(fire_at), str(run_id), str(status), int(now)),
            )
            self._conn.commit()
        return True

    def list_schedule_triggers(self, schedule_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT schedule_id, fire_at, run_id, status, created_at FROM schedule_triggers WHERE schedule_id = ? ORDER BY fire_at DESC LIMIT ?",
                (schedule_id, int(limit)),
            ).fetchall()
        return [{"schedule_id": str(r["schedule_id"]), "fire_at": int(r["fire_at"]), "run_id": str(r["run_id"]), "status": str(r["status"]), "created_at": int(r["created_at"])} for r in rows]

    def get_schedule(self, schedule_id: str) -> Optional[ScheduleRecord]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,))
            row = cur.fetchone()
            if not row:
                return None
            return ScheduleRecord(
                id=str(row["id"]),
                workflow_id=str(row["workflow_id"]),
                version=str(row["version"]),
                enabled=bool(row["enabled"]),
                policy_json=Serializer.from_json(str(row["policy_json"])),
                next_fire_at=int(row["next_fire_at"]),
            )

    def update_schedule(self, schedule_id: str, enabled: Optional[bool] = None, policy: Optional[Dict[str, Any]] = None) -> Optional[ScheduleRecord]:
        current = self.get_schedule(schedule_id)
        if not current:
            return None
        next_enabled = current.enabled if enabled is None else bool(enabled)
        next_policy = current.policy_json if policy is None else policy
        ok, err = schedule_policy_validate(next_policy)
        if not ok:
            raise ValueError(err)
        with self._lock:
            self._conn.execute(
                "UPDATE schedules SET enabled = ?, policy_json = ? WHERE id = ?",
                (1 if next_enabled else 0, Serializer.to_json(next_policy), schedule_id),
            )
            self._conn.commit()
        return ScheduleRecord(
            id=current.id,
            workflow_id=current.workflow_id,
            version=current.version,
            enabled=next_enabled,
            policy_json=next_policy,
            next_fire_at=current.next_fire_at,
        )

    def list_schedules(self, workflow_id: str = "", limit: int = 50, cursor: str = "") -> Tuple[List[ScheduleRecord], str]:
        where = ""
        params: List[Any] = []
        if workflow_id:
            where = "WHERE workflow_id = ?"
            params.append(workflow_id)
        if cursor:
            where = (where + " AND " if where else "WHERE ") + "id > ?"
            params.append(cursor)
        sql = f"SELECT * FROM schedules {where} ORDER BY id ASC LIMIT ?"
        params.append(int(limit))
        with self._lock:
            rows = self._conn.execute(sql, tuple(params)).fetchall()
        items = [
            ScheduleRecord(
                id=str(r["id"]),
                workflow_id=str(r["workflow_id"]),
                version=str(r["version"]),
                enabled=bool(r["enabled"]),
                policy_json=Serializer.from_json(str(r["policy_json"])),
                next_fire_at=int(r["next_fire_at"]),
            )
            for r in rows
        ]
        next_cursor = items[-1].id if len(items) == limit else ""
        return items, next_cursor

    def list_due_schedules(self, now: int, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM schedules WHERE enabled = 1 AND (next_fire_at <= ? OR next_fire_at = 0) ORDER BY next_fire_at ASC LIMIT ?",
                (int(now), int(limit)),
            ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": str(r["id"]),
                    "workflow_id": str(r["workflow_id"]),
                    "version": str(r["version"]),
                    "enabled": bool(r["enabled"]),
                    "policy_json": Serializer.from_json(str(r["policy_json"])),
                    "next_fire_at": int(r["next_fire_at"]),
                }
            )
        return out

    def upsert_run(self, run: RunRecord) -> RunRecord:
        with self._lock:
            self._conn.execute(
                "INSERT INTO runs(run_id, trace_id, workflow_id, status, config_snapshot, started_at, ended_at) VALUES(?,?,?,?,?,?,?) "
                "ON CONFLICT(run_id) DO UPDATE SET trace_id=excluded.trace_id, workflow_id=excluded.workflow_id, status=excluded.status, "
                "config_snapshot=excluded.config_snapshot, started_at=excluded.started_at, ended_at=excluded.ended_at",
                (
                    run.run_id,
                    run.trace_id,
                    run.workflow_id,
                    run.status.value,
                    Serializer.to_json(run.config_snapshot),
                    int(run.started_at),
                    int(run.ended_at),
                ),
            )
            self._conn.commit()
        return run

    def update_run_status(self, run_id: str, status: RunStatus, ended_at: Optional[int] = None) -> bool:
        end = int(ended_at if ended_at is not None else 0)
        with self._lock:
            row = self._conn.execute("SELECT status FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if not row:
                return False
            current = RunStatus(str(row["status"]))
            if not _can_transition(current, status, RUN_TRANSITIONS):
                return False
            cur = self._conn.execute("UPDATE runs SET status = ?, ended_at = ? WHERE run_id = ?", (status.value, end, run_id))
            self._conn.commit()
            return cur.rowcount > 0

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if not row:
            return None
        return RunRecord(
            run_id=str(row["run_id"]),
            trace_id=str(row["trace_id"]),
            workflow_id=str(row["workflow_id"]),
            status=RunStatus(str(row["status"])),
            config_snapshot=Serializer.from_json(str(row["config_snapshot"])),
            started_at=int(row["started_at"]),
            ended_at=int(row["ended_at"]),
        )

    def list_runs(self, workflow_id: str = "", limit: int = 50, cursor: str = "") -> Tuple[List[RunRecord], str]:
        where = ""
        params: List[Any] = []
        if workflow_id:
            where = "WHERE workflow_id = ?"
            params.append(workflow_id)
        if cursor:
            where = (where + " AND " if where else "WHERE ") + "run_id > ?"
            params.append(cursor)
        sql = f"SELECT * FROM runs {where} ORDER BY run_id ASC LIMIT ?"
        params.append(int(limit))
        with self._lock:
            rows = self._conn.execute(sql, tuple(params)).fetchall()
        runs = [
            RunRecord(
                run_id=str(r["run_id"]),
                trace_id=str(r["trace_id"]),
                workflow_id=str(r["workflow_id"]),
                status=RunStatus(str(r["status"])),
                config_snapshot=Serializer.from_json(str(r["config_snapshot"])),
                started_at=int(r["started_at"]),
                ended_at=int(r["ended_at"]),
            )
            for r in rows
        ]
        next_cursor = runs[-1].run_id if len(runs) == limit else ""
        return runs, next_cursor

    def list_runs_by_status(self, statuses: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        st = [str(s) for s in (statuses or [])]
        if not st:
            return []
        q = ",".join(["?"] * len(st))
        sql = f"SELECT run_id, trace_id, workflow_id, status, config_snapshot, started_at, ended_at FROM runs WHERE status IN ({q}) ORDER BY started_at ASC LIMIT ?"
        with self._lock:
            rows = self._conn.execute(sql, (*st, int(limit))).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "run_id": str(r["run_id"]),
                    "trace_id": str(r["trace_id"]),
                    "workflow_id": str(r["workflow_id"]),
                    "status": str(r["status"]),
                    "config_snapshot": Serializer.from_json(str(r["config_snapshot"])),
                    "started_at": int(r["started_at"]),
                    "ended_at": int(r["ended_at"]),
                }
            )
        return out

    def upsert_node_run(self, node: NodeRunRecord) -> NodeRunRecord:
        with self._lock:
            self._conn.execute(
                "INSERT INTO node_runs(run_id, node_id, status, snapshot, started_at, ended_at) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(run_id, node_id) DO UPDATE SET status=excluded.status, snapshot=excluded.snapshot, started_at=excluded.started_at, ended_at=excluded.ended_at",
                (
                    node.run_id,
                    node.node_id,
                    node.status.value,
                    Serializer.to_json(node.snapshot),
                    int(node.started_at),
                    int(node.ended_at),
                ),
            )
            self._conn.commit()
        return node

    def update_node_status(self, run_id: str, node_id: str, status: NodeRunStatus, snapshot: Optional[Dict[str, Any]] = None, ended_at: Optional[int] = None) -> bool:
        now = now_unix()
        snap = snapshot if snapshot is not None else {}
        end = int(ended_at if ended_at is not None else 0)
        with self._lock:
            row = self._conn.execute("SELECT status FROM node_runs WHERE run_id = ? AND node_id = ?", (run_id, node_id)).fetchone()
            if row:
                current = NodeRunStatus(str(row["status"]))
                if not _can_transition(current, status, NODE_TRANSITIONS):
                    return False
            cur = self._conn.execute(
                "INSERT INTO node_runs(run_id, node_id, status, snapshot, started_at, ended_at) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(run_id, node_id) DO UPDATE SET status=excluded.status, snapshot=excluded.snapshot, ended_at=excluded.ended_at",
                (run_id, node_id, status.value, Serializer.to_json(snap), int(now), int(end)),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def list_node_runs(self, run_id: str) -> List[NodeRunRecord]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM node_runs WHERE run_id = ? ORDER BY node_id ASC", (run_id,)).fetchall()
        return [
            NodeRunRecord(
                node_id=str(r["node_id"]),
                run_id=str(r["run_id"]),
                status=NodeRunStatus(str(r["status"])),
                snapshot=Serializer.from_json(str(r["snapshot"])),
                started_at=int(r["started_at"]),
                ended_at=int(r["ended_at"]),
            )
            for r in rows
        ]

    def enqueue_work_item(self, task_id: str, priority: int, payload: Dict[str, Any], idempotency_key: str = "") -> WorkItemRecord:
        idem = idempotency_key or f"wi:{task_id}"
        now = now_unix()
        record = WorkItemRecord(task_id=task_id, agent_id="", priority=int(priority), payload=payload, status=WorkItemStatus.CREATED, lease_owner="", lease_expires_at=0, idempotency_key=idem, created_at=now, updated_at=now)
        with self._lock:
            self._conn.execute(
                "INSERT INTO work_items(task_id, agent_id, priority, payload, status, lease_owner, lease_expires_at, idempotency_key, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (record.task_id, record.agent_id, record.priority, Serializer.to_json(record.payload), record.status.value, record.lease_owner, int(record.lease_expires_at), record.idempotency_key, int(record.created_at), int(record.updated_at)),
            )
            self._conn.commit()
        return record

    def list_work_items(self, status: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            if status:
                rows = self._conn.execute(
                    "SELECT * FROM work_items WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, int(limit)),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM work_items ORDER BY created_at DESC LIMIT ?",
                    (int(limit),),
                ).fetchall()
        
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "task_id": str(r["task_id"]),
                    "agent_id": str(r["agent_id"]),
                    "priority": int(r["priority"]),
                    "payload": Serializer.from_json(str(r["payload"])),
                    "status": str(r["status"]),
                    "lease_owner": str(r["lease_owner"]),
                    "lease_expires_at": int(r["lease_expires_at"]),
                    "idempotency_key": str(r["idempotency_key"]),
                    "created_at": int(r["created_at"]),
                    "updated_at": int(r["updated_at"]),
                }
            )
        return out

    def get_work_item(self, task_id: str) -> Optional[WorkItemRecord]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM work_items WHERE task_id = ?", (task_id,)).fetchone()
        if not row:
            return None
        return WorkItemRecord(
            task_id=str(row["task_id"]),
            agent_id=str(row["agent_id"]),
            priority=int(row["priority"]),
            payload=Serializer.from_json(str(row["payload"])),
            status=WorkItemStatus(str(row["status"])),
            lease_owner=str(row["lease_owner"]),
            lease_expires_at=int(row["lease_expires_at"]),
            idempotency_key=str(row["idempotency_key"]),
            created_at=int(row["created_at"]),
            updated_at=int(row["updated_at"]),
        )

    def mark_work_item_running(self, task_id: str, agent_id: str) -> bool:
        now = now_unix()
        with self._lock:
            row = self._conn.execute("SELECT status FROM work_items WHERE task_id = ? AND agent_id = ?", (task_id, agent_id)).fetchone()
            if not row:
                return False
            current = WorkItemStatus(str(row["status"]))
            if not _can_transition(current, WorkItemStatus.RUNNING, WORK_ITEM_TRANSITIONS):
                return False
            cur = self._conn.execute(
                "UPDATE work_items SET status=?, updated_at=? WHERE task_id=? AND agent_id=? AND status IN (?,?)",
                (WorkItemStatus.RUNNING.value, int(now), task_id, agent_id, WorkItemStatus.CLAIMED.value, WorkItemStatus.RUNNING.value),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def reclaim_expired_leases(self, now: Optional[int] = None, limit: int = 100) -> int:
        ts = int(now if now is not None else now_unix())
        with self._lock:
            rows = self._conn.execute(
                "SELECT task_id FROM work_items WHERE status=? AND lease_expires_at > 0 AND lease_expires_at <= ? ORDER BY lease_expires_at ASC LIMIT ?",
                (WorkItemStatus.CLAIMED.value, ts, int(limit)),
            ).fetchall()
            task_ids = [str(r["task_id"]) for r in rows]
            if not task_ids:
                return 0
            q = ",".join(["?"] * len(task_ids))
            cur = self._conn.execute(
                f"UPDATE work_items SET status=?, agent_id=?, lease_owner=?, lease_expires_at=?, updated_at=? WHERE task_id IN ({q})",
                (WorkItemStatus.CREATED.value, "", "", 0, ts, *task_ids),
            )
            self._conn.commit()
            return cur.rowcount

    def claim_work_item(self, agent_id: str, max_priority: int = 10, lease_ttl_sec: int = 60) -> Optional[WorkItemRecord]:
        now = now_unix()
        lease_expires_at = now + int(lease_ttl_sec)
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM work_items WHERE status = ? AND priority <= ? ORDER BY priority DESC, created_at ASC LIMIT 1",
                (WorkItemStatus.CREATED.value, int(max_priority)),
            ).fetchone()
            if not row:
                return None
            task_id = str(row["task_id"])
            updated_at = now
            self._conn.execute(
                "UPDATE work_items SET status=?, agent_id=?, lease_owner=?, lease_expires_at=?, updated_at=? WHERE task_id=? AND status=?",
                (WorkItemStatus.CLAIMED.value, agent_id, agent_id, int(lease_expires_at), int(updated_at), task_id, WorkItemStatus.CREATED.value),
            )
            self._conn.commit()
            row2 = self._conn.execute("SELECT * FROM work_items WHERE task_id = ?", (task_id,)).fetchone()
        if not row2:
            return None
        return WorkItemRecord(
            task_id=str(row2["task_id"]),
            agent_id=str(row2["agent_id"]),
            priority=int(row2["priority"]),
            payload=Serializer.from_json(str(row2["payload"])),
            status=WorkItemStatus(str(row2["status"])),
            lease_owner=str(row2["lease_owner"]),
            lease_expires_at=int(row2["lease_expires_at"]),
            idempotency_key=str(row2["idempotency_key"]),
            created_at=int(row2["created_at"]),
            updated_at=int(row2["updated_at"]),
        )

    def ack_work_item(self, task_id: str, agent_id: str, ok: bool) -> bool:
        now = now_unix()
        new_status = WorkItemStatus.ACKED.value if ok else WorkItemStatus.FAILED.value
        with self._lock:
            row = self._conn.execute("SELECT status FROM work_items WHERE task_id = ? AND agent_id = ?", (task_id, agent_id)).fetchone()
            if not row:
                return False
            current = WorkItemStatus(str(row["status"]))
            if not _can_transition(current, WorkItemStatus(new_status), WORK_ITEM_TRANSITIONS):
                return False
            cur = self._conn.execute(
                "UPDATE work_items SET status=?, updated_at=? WHERE task_id=? AND agent_id=?",
                (new_status, int(now), task_id, agent_id),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def write_agent_heartbeat(self, agent_id: str, status: str, cpu: float, mem: float, queue_depth: int, skills: List[str], metrics: Dict[str, Any]) -> bool:
        now = now_unix()
        with self._lock:
            self._conn.execute(
                "INSERT INTO agent_heartbeats(agent_id, status, cpu, mem, queue_depth, skills_json, metrics_json, last_seen) VALUES(?,?,?,?,?,?,?,?) "
                "ON CONFLICT(agent_id) DO UPDATE SET status=excluded.status, cpu=excluded.cpu, mem=excluded.mem, queue_depth=excluded.queue_depth, "
                "skills_json=excluded.skills_json, metrics_json=excluded.metrics_json, last_seen=excluded.last_seen",
                (agent_id, str(status), float(cpu), float(mem), int(queue_depth), Serializer.to_json(list(skills)), Serializer.to_json(dict(metrics or {})), int(now)),
            )
            self._conn.commit()
        return True

    def list_idle_agents(self, idle_before: int, max_queue_depth: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM agent_heartbeats WHERE last_seen <= ? AND queue_depth <= ? ORDER BY last_seen ASC LIMIT ?",
                (int(idle_before), int(max_queue_depth), int(limit)),
            ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "agent_id": str(r["agent_id"]),
                    "status": str(r["status"]),
                    "cpu": float(r["cpu"]),
                    "mem": float(r["mem"]),
                    "queue_depth": int(r["queue_depth"]),
                    "skills": Serializer.from_json(str(r["skills_json"])),
                    "metrics": Serializer.from_json(str(r["metrics_json"])),
                    "last_seen": int(r["last_seen"]),
                }
            )
        return out

    def list_all_agents(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM agent_heartbeats ORDER BY last_seen DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "agent_id": str(r["agent_id"]),
                    "status": str(r["status"]),
                    "cpu": float(r["cpu"]),
                    "mem": float(r["mem"]),
                    "queue_depth": int(r["queue_depth"]),
                    "skills": Serializer.from_json(str(r["skills_json"])),
                    "metrics": Serializer.from_json(str(r["metrics_json"])),
                    "last_seen": int(r["last_seen"]),
                }
            )
        return out

    def upsert_workflow(self, wf: WorkflowDefinition) -> WorkflowDefinition:
        with self._lock:
            self._conn.execute(
                "INSERT INTO workflows(workflow_id, version, dag_json, metadata_json, created_at) VALUES(?,?,?,?,?) "
                "ON CONFLICT(workflow_id, version) DO UPDATE SET dag_json=excluded.dag_json, metadata_json=excluded.metadata_json",
                (wf.workflow_id, wf.version, Serializer.to_json(wf.dag), Serializer.to_json(wf.metadata), int(wf.created_at)),
            )
            self._conn.commit()
        return wf

    def get_workflow(self, workflow_id: str, version: str) -> Optional[WorkflowDefinition]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM workflows WHERE workflow_id = ? AND version = ?", (workflow_id, version)).fetchone()
        if not row:
            return None
        return WorkflowDefinition(
            workflow_id=str(row["workflow_id"]),
            version=str(row["version"]),
            dag=Serializer.from_json(str(row["dag_json"])),
            metadata=Serializer.from_json(str(row["metadata_json"])),
            created_at=int(row["created_at"]),
        )

    def get_latest_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT workflow_id, version, dag_json, metadata_json, created_at FROM workflows WHERE workflow_id = ? ORDER BY created_at DESC LIMIT 1",
                (workflow_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "workflow_id": str(row["workflow_id"]),
            "version": str(row["version"]),
            "dag": Serializer.from_json(str(row["dag_json"])),
            "metadata": Serializer.from_json(str(row["metadata_json"])),
            "created_at": int(row["created_at"]),
        }

    def create_approval(self, task_id: str, risk_score: float, risk_factors: List[Dict[str, Any]], requester: Dict[str, Any], expires_at: int) -> ApprovalRequest:
        approval_id = f"apr-{uuid.uuid4().hex}"
        now = now_unix()
        req = ApprovalRequest(
            approval_id=approval_id,
            task_id=task_id,
            risk_score=_normalize_risk_score(risk_score),
            risk_factors=_normalize_risk_factors(list(risk_factors)),
            requester=dict(requester or {}),
            status=ApprovalStatus.PENDING,
            expires_at=int(expires_at),
            created_at=int(now),
        )
        with self._lock:
            self._conn.execute(
                "INSERT INTO approvals(approval_id, task_id, status, risk_score, risk_factors_json, requester_json, expires_at, decision_json, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (req.approval_id, req.task_id, req.status.value, float(req.risk_score), Serializer.to_json(req.risk_factors), Serializer.to_json(req.requester), int(req.expires_at), Serializer.to_json({}), int(req.created_at), int(now)),
            )
            self._conn.commit()
        return req

    def get_approval(self, approval_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)).fetchone()
        if not row:
            return None
        return {
            "approval_id": str(row["approval_id"]),
            "task_id": str(row["task_id"]),
            "status": str(row["status"]),
            "risk_score": _normalize_risk_score(row["risk_score"]),
            "risk_factors": _normalize_risk_factors(Serializer.from_json(str(row["risk_factors_json"]))),
            "requester": Serializer.from_json(str(row["requester_json"])),
            "expires_at": int(row["expires_at"]),
            "decision": Serializer.from_json(str(row["decision_json"])),
            "created_at": int(row["created_at"]),
            "updated_at": int(row["updated_at"]),
        }

    def list_approvals(self, status: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        where = ""
        params: List[Any] = []
        if status:
            where = "WHERE status = ?"
            params.append(str(status))
        sql = f"SELECT * FROM approvals {where} ORDER BY created_at DESC LIMIT ?"
        params.append(int(limit))
        with self._lock:
            rows = self._conn.execute(sql, tuple(params)).fetchall()
        return [
            {
                "approval_id": str(r["approval_id"]),
                "task_id": str(r["task_id"]),
                "status": str(r["status"]),
                "risk_score": _normalize_risk_score(r["risk_score"]),
                "risk_factors": _normalize_risk_factors(Serializer.from_json(str(r["risk_factors_json"]))),
                "requester": Serializer.from_json(str(r["requester_json"])),
                "expires_at": int(r["expires_at"]),
                "decision": Serializer.from_json(str(r["decision_json"])),
                "created_at": int(r["created_at"]),
                "updated_at": int(r["updated_at"]),
            }
            for r in rows
        ]

    def decide_approval(self, approval_id: str, decision: ApprovalDecision, new_status: ApprovalStatus) -> bool:
        now = now_unix()
        with self._lock:
            cur = self._conn.execute(
                "UPDATE approvals SET status=?, decision_json=?, updated_at=? WHERE approval_id=? AND status=?",
                (new_status.value, Serializer.to_json(decision.__dict__), int(now), approval_id, ApprovalStatus.PENDING.value),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def write_learning_report(self, report: LearningReport) -> bool:
        with self._lock:
            self._conn.execute(
                "INSERT INTO learning_reports(report_id, agent_id, content_json, created_at) VALUES(?,?,?,?)",
                (report.report_id, report.agent_id, Serializer.to_json(report.__dict__), int(report.created_at)),
            )
            self._conn.commit()
        return True

    def list_learning_reports(self, agent_id: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        where = ""
        params: List[Any] = []
        if agent_id:
            where = "WHERE agent_id = ?"
            params.append(agent_id)
        sql = f"SELECT report_id, agent_id, content_json, created_at FROM learning_reports {where} ORDER BY created_at DESC LIMIT ?"
        params.append(int(limit))
        with self._lock:
            rows = self._conn.execute(sql, tuple(params)).fetchall()
        items = [{"report_id": str(r["report_id"]), "agent_id": str(r["agent_id"]), "content": Serializer.from_json(str(r["content_json"])), "created_at": int(r["created_at"])} for r in rows]
        return [_flatten_learning_content(it) for it in items]

    def get_event_offset(self, subscriber_id: str, topic: str) -> int:
        with self._lock:
            row = self._conn.execute("SELECT offset FROM event_offsets WHERE subscriber_id=? AND topic=?", (subscriber_id, topic)).fetchone()
        if not row:
            return 0
        return int(row["offset"])

    def set_event_offset(self, subscriber_id: str, topic: str, offset: int) -> bool:
        now = now_unix()
        with self._lock:
            self._conn.execute(
                "INSERT INTO event_offsets(subscriber_id, topic, offset, updated_at) VALUES(?,?,?,?) "
                "ON CONFLICT(subscriber_id, topic) DO UPDATE SET offset=excluded.offset, updated_at=excluded.updated_at",
                (subscriber_id, topic, int(offset), int(now)),
            )
            self._conn.commit()
        return True

    def add_evidence(self, trace_id: str, evidence_type: str, content: Dict[str, Any], content_hash: str) -> str:
        evidence_id = f"ev-{uuid.uuid4().hex}"
        created_at = now_unix()
        with self._lock:
            self._conn.execute(
                "INSERT INTO evidence(evidence_id, trace_id, type, content, hash, created_at) VALUES(?,?,?,?,?,?)",
                (evidence_id, trace_id, str(evidence_type), Serializer.to_json(content), str(content_hash), int(created_at)),
            )
            self._conn.commit()
        return evidence_id

    def list_evidence(self, trace_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT evidence_id, trace_id, type, content, hash, created_at FROM evidence WHERE trace_id = ? ORDER BY created_at DESC LIMIT ?",
                (trace_id, int(limit)),
            ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "evidence_id": str(r["evidence_id"]),
                    "trace_id": str(r["trace_id"]),
                    "type": str(r["type"]),
                    "content": Serializer.from_json(str(r["content"])),
                    "hash": str(r["hash"]),
                    "created_at": int(r["created_at"]),
                }
            )
        return out

    def add_audit_log(self, trace_id: str, actor: str, action: str, resource: str, result: Dict[str, Any], timestamp: Optional[int] = None) -> str:
        audit_id = f"au-{uuid.uuid4().hex}"
        ts = int(timestamp if timestamp is not None else now_unix())
        with self._lock:
            self._conn.execute(
                "INSERT INTO audit_logs(audit_id, trace_id, actor, action, resource, result, timestamp) VALUES(?,?,?,?,?,?,?)",
                (audit_id, trace_id, str(actor), str(action), str(resource), Serializer.to_json(result), int(ts)),
            )
            self._conn.commit()
        return audit_id

    def list_audit_logs(self, trace_id: str = "", limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            if trace_id:
                rows = self._conn.execute(
                    "SELECT audit_id, trace_id, actor, action, resource, result, timestamp FROM audit_logs WHERE trace_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (trace_id, int(limit)),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT audit_id, trace_id, actor, action, resource, result, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT ?",
                    (int(limit),),
                ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "audit_id": str(r["audit_id"]),
                    "trace_id": str(r["trace_id"]),
                    "actor": str(r["actor"]),
                    "action": str(r["action"]),
                    "resource": str(r["resource"]),
                    "result": Serializer.from_json(str(r["result"])),
                    "timestamp": int(r["timestamp"]),
                }
            )
        return out

    def list_workflows(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT workflow_id, version, created_at FROM workflows ORDER BY created_at DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [{"workflow_id": str(r["workflow_id"]), "version": str(r["version"]), "created_at": int(r["created_at"])} for r in rows]

    def upsert_memory_unit(self, memory_id: str, content: str, keywords: List[str], category: str, scope: str, confidence: float) -> str:
        mem_id = memory_id or f"mem-{uuid.uuid4().hex}"
        updated_at = now_unix()
        payload_keywords = Serializer.to_json(list(keywords))
        with self._lock:
            self._conn.execute(
                "INSERT INTO memory_units(memory_id, content, keywords, category, scope, confidence, updated_at) VALUES(?,?,?,?,?,?,?) "
                "ON CONFLICT(memory_id) DO UPDATE SET content=excluded.content, keywords=excluded.keywords, category=excluded.category, scope=excluded.scope, confidence=excluded.confidence, updated_at=excluded.updated_at",
                (mem_id, str(content), payload_keywords, str(category), str(scope), float(confidence), int(updated_at)),
            )
            self._conn.commit()
        return mem_id
