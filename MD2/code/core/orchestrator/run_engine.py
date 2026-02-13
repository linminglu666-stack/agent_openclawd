from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from core.persistence import StateDB
from core.persistence import JsonlWAL

from protocols.workflow import RunStatus, NodeRunStatus, WorkItemStatus, now_unix
from protocols.approvals import ApprovalDecision, ApprovalStatus


@dataclass
class OrchestratorHealth:
    state: str
    scanned_runs: int
    progressed_nodes: int


class RunEngine:
    def __init__(self, state_db: StateDB, wal: JsonlWAL):
        self._db = state_db
        self._wal = wal

    def tick(self, now: Optional[int] = None, limit_runs: int = 50) -> OrchestratorHealth:
        ts = int(now if now is not None else now_unix())
        progressed = 0
        runs = self._db.list_runs_by_status(statuses=[RunStatus.QUEUED.value, RunStatus.RUNNING.value, RunStatus.BLOCKED.value], limit=limit_runs)
        for run in runs:
            run_id = str(run["run_id"])
            workflow_id = str(run["workflow_id"])
            status = str(run["status"])
            if status == RunStatus.BLOCKED.value:
                if self._try_unblock(run_id, ts):
                    self._db.update_run_status(run_id, RunStatus.RUNNING)
                else:
                    continue
            if status == RunStatus.QUEUED.value:
                self._db.update_run_status(run_id, RunStatus.RUNNING)

            wf = self._db.get_latest_workflow(workflow_id)
            if not wf:
                self._db.update_run_status(run_id, RunStatus.FAILED, ended_at=ts)
                self._wal.append("orchestrator_missing_workflow", {"run_id": run_id, "workflow_id": workflow_id})
                continue

            progressed += self._progress_run(run_id=run_id, workflow=wf, ts=ts)

        return OrchestratorHealth(state="running", scanned_runs=len(runs), progressed_nodes=progressed)

    def _progress_run(self, run_id: str, workflow: Dict[str, Any], ts: int) -> int:
        dag = dict(workflow.get("dag") or {})
        nodes = list(dag.get("nodes") or [])
        edges = list(dag.get("edges") or [])

        node_by_id = {str(n.get("node_id")): dict(n) for n in nodes if n.get("node_id")}
        deps = _deps(edges)

        node_runs = {nr.node_id: nr for nr in self._db.list_node_runs(run_id)}

        progressed = 0
        for node_id, node in node_by_id.items():
            if node_id not in node_runs:
                self._db.update_node_status(run_id, node_id, NodeRunStatus.PENDING, snapshot={"node": node})
                node_runs[node_id] = self._db.list_node_runs(run_id)[-1]

        for node_id, node in node_by_id.items():
            nr = node_runs.get(node_id)
            if not nr:
                continue
            if nr.status in {NodeRunStatus.SUCCEEDED, NodeRunStatus.SKIPPED, NodeRunStatus.CANCELED}:
                continue
            if not _deps_satisfied(node_id, deps, node_runs):
                if nr.status == NodeRunStatus.PENDING:
                    self._db.update_node_status(run_id, node_id, NodeRunStatus.PENDING, snapshot=nr.snapshot)
                continue

            ntype = str(node.get("type") or "task")
            if ntype == "approval":
                if nr.status not in {NodeRunStatus.WAITING_APPROVAL, NodeRunStatus.SUCCEEDED}:
                    approval_id = self._db.create_approval(
                        task_id=f"{run_id}:{node_id}",
                        risk_score=float(node.get("risk_score", 0.0) or 0.0),
                        risk_factors=list(node.get("risk_factors") or []),
                        requester={"workflow_id": workflow.get("workflow_id"), "run_id": run_id},
                        expires_at=int(ts + int(node.get("expires_sec", 3600) or 3600)),
                    ).approval_id
                    snap = dict(nr.snapshot or {})
                    snap["approval_id"] = approval_id
                    self._db.update_node_status(run_id, node_id, NodeRunStatus.WAITING_APPROVAL, snapshot=snap)
                    self._db.update_run_status(run_id, RunStatus.BLOCKED)
                    self._wal.append("orchestrator_waiting_approval", {"run_id": run_id, "node_id": node_id, "approval_id": approval_id})
                    progressed += 1
                continue

            if ntype == "eval":
                self._db.update_node_status(run_id, node_id, NodeRunStatus.SUCCEEDED, snapshot={"eval": "skipped"})
                progressed += 1
                continue

            task_id = f"wi-{run_id}-{node_id}"
            existing = self._db.get_work_item(task_id)
            if not existing:
                payload = {
                    "task_type": str(node.get("task_type") or "default"),
                    "task_data": dict(node.get("task_data") or {}),
                    "context": {"run_id": run_id, "node_id": node_id, "workflow_id": workflow.get("workflow_id")},
                }
                self._db.enqueue_work_item(task_id=task_id, priority=int(node.get("priority", 0) or 0), payload=payload, idempotency_key=str(node.get("idempotency_key") or task_id))
                self._db.update_node_status(run_id, node_id, NodeRunStatus.RUNNING, snapshot={"work_item": task_id})
                self._wal.append("orchestrator_dispatched_work_item", {"run_id": run_id, "node_id": node_id, "task_id": task_id})
                progressed += 1
                continue

            if existing.status == WorkItemStatus.ACKED:
                self._db.update_node_status(run_id, node_id, NodeRunStatus.SUCCEEDED, snapshot={"work_item": task_id})
                progressed += 1
                continue
            if existing.status in {WorkItemStatus.FAILED, WorkItemStatus.DEAD_LETTER}:
                self._db.update_node_status(run_id, node_id, NodeRunStatus.FAILED, snapshot={"work_item": task_id})
                self._db.update_run_status(run_id, RunStatus.FAILED, ended_at=ts)
                self._wal.append("orchestrator_node_failed", {"run_id": run_id, "node_id": node_id, "task_id": task_id})
                progressed += 1
                return progressed

        if all(nr.status == NodeRunStatus.SUCCEEDED for nr in self._db.list_node_runs(run_id)):
            self._db.update_run_status(run_id, RunStatus.SUCCEEDED, ended_at=ts)
            self._wal.append("orchestrator_run_succeeded", {"run_id": run_id})
        return progressed

    def _try_unblock(self, run_id: str, ts: int) -> bool:
        nodes = self._db.list_node_runs(run_id)
        waiting = [n for n in nodes if n.status == NodeRunStatus.WAITING_APPROVAL]
        if not waiting:
            return True
        for n in waiting:
            approval_id = str((n.snapshot or {}).get("approval_id") or "")
            if not approval_id:
                continue
            appr = self._db.get_approval(approval_id)
            if not appr:
                continue
            if str(appr.get("status")) == ApprovalStatus.APPROVED.value:
                self._db.update_node_status(run_id, n.node_id, NodeRunStatus.SUCCEEDED, snapshot=n.snapshot)
                continue
            if str(appr.get("status")) in {ApprovalStatus.REJECTED.value, ApprovalStatus.EXPIRED.value, ApprovalStatus.CANCELED.value}:
                self._db.update_node_status(run_id, n.node_id, NodeRunStatus.FAILED, snapshot=n.snapshot)
                self._db.update_run_status(run_id, RunStatus.FAILED, ended_at=ts)
                return False
            return False
        return True


def _deps(edges: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    d: Dict[str, Set[str]] = {}
    for e in edges:
        src = str(e.get("from_node") or "")
        dst = str(e.get("to_node") or "")
        if not src or not dst:
            continue
        if dst not in d:
            d[dst] = set()
        d[dst].add(src)
    return d


def _deps_satisfied(node_id: str, deps: Dict[str, Set[str]], node_runs: Dict[str, Any]) -> bool:
    required = deps.get(node_id) or set()
    for dep_id in required:
        nr = node_runs.get(dep_id)
        if not nr:
            return False
        if nr.status != NodeRunStatus.SUCCEEDED:
            return False
    return True

