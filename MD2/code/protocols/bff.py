from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .api import PageRequest
from .workflow import ScheduleRecord, RunRecord, NodeRunRecord, WorkItemRecord


@dataclass
class CreateScheduleRequest:
    workflow_id: str
    version: str
    enabled: bool
    policy: Dict[str, Any]


@dataclass
class CreateScheduleResponse:
    schedule: ScheduleRecord


@dataclass
class UpdateScheduleRequest:
    schedule_id: str
    enabled: Optional[bool] = None
    policy: Optional[Dict[str, Any]] = None


@dataclass
class UpdateScheduleResponse:
    schedule: ScheduleRecord


@dataclass
class GetScheduleResponse:
    schedule: Optional[ScheduleRecord]


@dataclass
class ListSchedulesRequest:
    page: PageRequest = field(default_factory=PageRequest)
    workflow_id: str = ""


@dataclass
class ListSchedulesResponse:
    schedules: List[ScheduleRecord] = field(default_factory=list)
    next_cursor: str = ""


@dataclass
class TriggerRunRequest:
    workflow_id: str
    schedule_id: str = ""
    reason: str = ""
    config_snapshot: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TriggerRunResponse:
    run: RunRecord


@dataclass
class GetRunResponse:
    run: Optional[RunRecord]
    nodes: List[NodeRunRecord] = field(default_factory=list)


@dataclass
class ListRunsRequest:
    page: PageRequest = field(default_factory=PageRequest)
    workflow_id: str = ""


@dataclass
class ListRunsResponse:
    runs: List[RunRecord] = field(default_factory=list)
    next_cursor: str = ""


@dataclass
class EnqueueWorkItemRequest:
    task_id: str
    priority: int
    payload: Dict[str, Any] = field(default_factory=dict)
    idempotency_key: str = ""


@dataclass
class EnqueueWorkItemResponse:
    work_item: WorkItemRecord


@dataclass
class ClaimWorkItemRequest:
    agent_id: str
    max_priority: int = 10
    lease_ttl_sec: int = 60


@dataclass
class ClaimWorkItemResponse:
    work_item: Optional[WorkItemRecord]


@dataclass
class AckWorkItemRequest:
    task_id: str
    agent_id: str
    ok: bool
    result: Dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass
class AckWorkItemResponse:
    updated: bool

