from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class SchedulePolicyType(Enum):
    AT = "at"
    INTERVAL = "interval"
    WINDOW = "window"


@dataclass
class SchedulePolicyAt:
    type: str = SchedulePolicyType.AT.value
    at: str = ""


@dataclass
class SchedulePolicyInterval:
    type: str = SchedulePolicyType.INTERVAL.value
    every_sec: int = 0
    jitter_sec: int = 0


@dataclass
class SchedulePolicyWindow:
    type: str = SchedulePolicyType.WINDOW.value
    start: str = ""
    end: str = ""
    interval_sec: int = 0
    timezone: str = "UTC"


@dataclass
class ScheduleRecord:
    id: str
    workflow_id: str
    version: str
    enabled: bool
    policy_json: Dict[str, Any] = field(default_factory=dict)
    next_fire_at: int = 0


class RunStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    BLOCKED = "blocked"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class NodeRunStatus(Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    SKIPPED = "skipped"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class WorkItemStatus(Enum):
    CREATED = "created"
    CLAIMED = "claimed"
    RUNNING = "running"
    ACKED = "acked"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass
class RunRecord:
    run_id: str
    trace_id: str
    workflow_id: str
    status: RunStatus
    config_snapshot: Dict[str, Any] = field(default_factory=dict)
    started_at: int = 0
    ended_at: int = 0


@dataclass
class NodeRunRecord:
    node_id: str
    run_id: str
    status: NodeRunStatus
    snapshot: Dict[str, Any] = field(default_factory=dict)
    started_at: int = 0
    ended_at: int = 0


@dataclass
class WorkItemRecord:
    task_id: str
    agent_id: str
    priority: int
    payload: Dict[str, Any] = field(default_factory=dict)
    status: WorkItemStatus = WorkItemStatus.CREATED
    lease_owner: str = ""
    lease_expires_at: int = 0
    idempotency_key: str = ""
    created_at: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))
    updated_at: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))


def now_unix() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp())


def schedule_policy_validate(policy: Dict[str, Any]) -> Tuple[bool, str]:
    t = str(policy.get("type", "")).strip()
    if t not in {e.value for e in SchedulePolicyType}:
        return False, "invalid_policy_type"
    if t == SchedulePolicyType.AT.value:
        if not str(policy.get("at", "")).strip():
            return False, "missing_at"
    if t == SchedulePolicyType.INTERVAL.value:
        every_sec = int(policy.get("every_sec", 0) or 0)
        if every_sec <= 0:
            return False, "every_sec_must_be_positive"
    if t == SchedulePolicyType.WINDOW.value:
        if not str(policy.get("start", "")).strip() or not str(policy.get("end", "")).strip():
            return False, "missing_window_bounds"
        interval_sec = int(policy.get("interval_sec", 0) or 0)
        if interval_sec <= 0:
            return False, "interval_sec_must_be_positive"
    return True, ""


RUN_TRANSITIONS: Dict[RunStatus, List[RunStatus]] = {
    RunStatus.PENDING: [RunStatus.QUEUED, RunStatus.CANCELED],
    RunStatus.QUEUED: [RunStatus.RUNNING, RunStatus.CANCELED],
    RunStatus.RUNNING: [RunStatus.BLOCKED, RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELED],
    RunStatus.BLOCKED: [RunStatus.RUNNING, RunStatus.CANCELED, RunStatus.FAILED],
    RunStatus.SUCCEEDED: [],
    RunStatus.FAILED: [],
    RunStatus.CANCELED: [],
}


NODE_TRANSITIONS: Dict[NodeRunStatus, List[NodeRunStatus]] = {
    NodeRunStatus.PENDING: [NodeRunStatus.READY, NodeRunStatus.CANCELED],
    NodeRunStatus.READY: [NodeRunStatus.RUNNING, NodeRunStatus.WAITING_APPROVAL, NodeRunStatus.SKIPPED, NodeRunStatus.CANCELED],
    NodeRunStatus.WAITING_APPROVAL: [NodeRunStatus.RUNNING, NodeRunStatus.SKIPPED, NodeRunStatus.CANCELED],
    NodeRunStatus.RUNNING: [NodeRunStatus.SUCCEEDED, NodeRunStatus.FAILED, NodeRunStatus.CANCELED],
    NodeRunStatus.SKIPPED: [],
    NodeRunStatus.SUCCEEDED: [],
    NodeRunStatus.FAILED: [],
    NodeRunStatus.CANCELED: [],
}


WORK_ITEM_TRANSITIONS: Dict[WorkItemStatus, List[WorkItemStatus]] = {
    WorkItemStatus.CREATED: [WorkItemStatus.CLAIMED, WorkItemStatus.DEAD_LETTER],
    WorkItemStatus.CLAIMED: [WorkItemStatus.RUNNING, WorkItemStatus.CREATED, WorkItemStatus.DEAD_LETTER],
    WorkItemStatus.RUNNING: [WorkItemStatus.ACKED, WorkItemStatus.FAILED, WorkItemStatus.DEAD_LETTER],
    WorkItemStatus.ACKED: [],
    WorkItemStatus.FAILED: [WorkItemStatus.CREATED, WorkItemStatus.DEAD_LETTER],
    WorkItemStatus.DEAD_LETTER: [],
}

