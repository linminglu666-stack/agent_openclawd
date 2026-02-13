from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class EntropyCategory(str, Enum):
    INPUT = "input"
    EVOLUTION = "evolution"
    OBSERVABILITY = "observability"
    STRUCTURE = "structure"
    BEHAVIOR = "behavior"
    DATA = "data"


class TaskStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    DOING = "doing"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    ARCHIVED = "archived"


@dataclass
class TaskReport:
    completed: str
    next_steps: str
    blockers: str
    risks: str
    confidence: Optional[str] = None
    timestamp: datetime = field(default_factory=utc_now)


@dataclass
class DeliverableCard:
    summary: str
    scope: str
    conclusions: List[str] = field(default_factory=list)
    version: str = "v1"
    deliverable_date: datetime = field(default_factory=utc_now)
    adr_refs: List[str] = field(default_factory=list)
    output_path: str = ""


@dataclass
class ADRRecord:
    adr_id: str
    background: str
    decision: str
    alternatives: List[str] = field(default_factory=list)
    impact: str = ""
    owner: str = ""
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class TaskRecord:
    task_id: str
    owner: str
    project: str
    output_path: str
    summary: str
    status: TaskStatus = TaskStatus.DRAFT
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    reports: List[TaskReport] = field(default_factory=list)
    deliverable: Optional[DeliverableCard] = None
    adr_ids: List[str] = field(default_factory=list)


@dataclass
class InboxItem:
    item_id: str
    title: str
    owner: str
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class OutputRecord:
    output_id: str
    task_id: str
    project: str
    topic: str
    path: str
    is_source_of_truth: bool = True
    indexed: bool = False
    created_at: datetime = field(default_factory=utc_now)
    superseded_by: Optional[str] = None


@dataclass
class EntropyConfig:
    inbox_ttl_days: int = 7
    max_retrieval_samples: int = 200
    stale_threshold_days: int = 14
    rework_window_days: int = 30


@dataclass
class EntropyMetrics:
    retrieval_time_avg_min: float
    inbox_stale_count: int
    unindexed_outputs: int
    duplicate_topics: int
    rework_events_30d: int
    by_category: Dict[EntropyCategory, Dict[str, float]] = field(default_factory=dict)


@dataclass
class EntropyHistory:
    timestamp: datetime
    metrics: EntropyMetrics


class EntropyControlCenter:
    def __init__(self, inbox_ttl_days: int = 7, max_retrieval_samples: int = 200):
        self._tasks: Dict[str, TaskRecord] = {}
        self._adrs: Dict[str, ADRRecord] = {}
        self._outputs: Dict[str, OutputRecord] = {}
        self._topic_index: Dict[str, List[str]] = {}
        self._inbox: Dict[str, InboxItem] = {}
        self._rework_events: List[datetime] = []
        self._retrieval_samples: List[float] = []
        self._history: List[EntropyHistory] = []
        
        self._config = EntropyConfig(
            inbox_ttl_days=int(inbox_ttl_days),
            max_retrieval_samples=int(max_retrieval_samples)
        )

    @property
    def config(self) -> EntropyConfig:
        return self._config

    @property
    def history(self) -> List[EntropyHistory]:
        return self._history

    def register_task(self, task_id: str, owner: str, project: str, output_path: str, summary: str) -> TaskRecord:
        if task_id in self._tasks:
            raise ValueError(f"task already exists: {task_id}")
        record = TaskRecord(
            task_id=task_id,
            owner=owner,
            project=project,
            output_path=output_path,
            summary=summary,
        )
        self._tasks[task_id] = record
        return record

    def update_status(self, task_id: str, status: TaskStatus, report: Optional[TaskReport] = None) -> TaskRecord:
        record = self._require_task(task_id)
        record.status = TaskStatus(status)
        record.updated_at = utc_now()
        if report:
            record.reports.append(report)
        return record

    def add_report(self, task_id: str, report: TaskReport) -> TaskRecord:
        record = self._require_task(task_id)
        record.reports.append(report)
        record.updated_at = utc_now()
        return record

    def attach_deliverable(self, task_id: str, deliverable: DeliverableCard) -> TaskRecord:
        record = self._require_task(task_id)
        record.deliverable = deliverable
        record.output_path = deliverable.output_path or record.output_path
        record.updated_at = utc_now()
        return record

    def add_adr(self, task_id: str, adr: ADRRecord) -> ADRRecord:
        record = self._require_task(task_id)
        self._adrs[adr.adr_id] = adr
        if adr.adr_id not in record.adr_ids:
            record.adr_ids.append(adr.adr_id)
        record.updated_at = utc_now()
        return adr

    def register_output(self, output: OutputRecord) -> OutputRecord:
        self._outputs[output.output_id] = output
        topic_key = output.topic.strip().lower()
        if topic_key not in self._topic_index:
            self._topic_index[topic_key] = []
        if output.output_id not in self._topic_index[topic_key]:
            self._topic_index[topic_key].append(output.output_id)
        return output

    def mark_output_indexed(self, output_id: str, indexed: bool = True) -> OutputRecord:
        output = self._outputs.get(output_id)
        if not output:
            raise ValueError(f"output not found: {output_id}")
        output.indexed = bool(indexed)
        return output

    def supersede_output(self, output_id: str, new_output_id: str) -> OutputRecord:
        output = self._outputs.get(output_id)
        if not output:
            raise ValueError(f"output not found: {output_id}")
        output.is_source_of_truth = False
        output.superseded_by = new_output_id
        return output

    def register_inbox_item(self, item: InboxItem) -> InboxItem:
        self._inbox[item.item_id] = item
        return item

    def resolve_inbox_item(self, item_id: str) -> Optional[InboxItem]:
        return self._inbox.pop(item_id, None)

    def record_rework(self, when: Optional[datetime] = None) -> None:
        self._rework_events.append(when or utc_now())

    def add_retrieval_time(self, minutes: float) -> None:
        self._retrieval_samples.append(float(minutes))
        if len(self._retrieval_samples) > self._config.max_retrieval_samples:
            self._retrieval_samples = self._retrieval_samples[-self._config.max_retrieval_samples :]

    def compute_metrics(self, now: Optional[datetime] = None) -> EntropyMetrics:
        now = now or utc_now()
        retrieval_avg = sum(self._retrieval_samples) / len(self._retrieval_samples) if self._retrieval_samples else 0.0
        stale_cutoff = now - timedelta(days=self._config.inbox_ttl_days)
        inbox_stale = sum(1 for item in self._inbox.values() if item.created_at < stale_cutoff)
        unindexed = sum(1 for output in self._outputs.values() if not output.indexed)
        duplicates = 0
        for outputs in self._topic_index.values():
            source_count = sum(1 for oid in outputs if self._outputs.get(oid, None) and self._outputs[oid].is_source_of_truth)
            if source_count > 1:
                duplicates += 1
        rework_cutoff = now - timedelta(days=self._config.rework_window_days)
        rework_30d = sum(1 for t in self._rework_events if t >= rework_cutoff)
        
        metrics = EntropyMetrics(
            retrieval_time_avg_min=round(retrieval_avg, 2),
            inbox_stale_count=inbox_stale,
            unindexed_outputs=unindexed,
            duplicate_topics=duplicates,
            rework_events_30d=rework_30d,
            by_category={
                EntropyCategory.INPUT: {"inbox_stale": float(inbox_stale)},
                EntropyCategory.EVOLUTION: {"rework_events": float(rework_30d)},
                EntropyCategory.OBSERVABILITY: {"unindexed_outputs": float(unindexed)},
                EntropyCategory.STRUCTURE: {"duplicate_topics": float(duplicates)},
                EntropyCategory.BEHAVIOR: {"retrieval_time_avg": round(retrieval_avg, 2)},
                EntropyCategory.DATA: {},
            }
        )
        return metrics

    def snapshot_metrics(self) -> EntropyHistory:
        metrics = self.compute_metrics()
        history = EntropyHistory(timestamp=utc_now(), metrics=metrics)
        self._history.append(history)
        return history

    def validate_task(self, task_id: str) -> List[str]:
        record = self._require_task(task_id)
        violations = []
        if record.status in {TaskStatus.DONE, TaskStatus.ARCHIVED}:
            if not record.deliverable:
                violations.append("missing_deliverable")
            if not record.adr_ids:
                violations.append("missing_adr")
            if not record.output_path:
                violations.append("missing_output_path")
        return violations

    def plan_entropy_sweep(self, now: Optional[datetime] = None) -> List[str]:
        metrics = self.compute_metrics(now)
        actions: List[str] = []
        if metrics.inbox_stale_count > 0:
            actions.append("clear_inbox_stale_items")
        if metrics.unindexed_outputs > 0:
            actions.append("index_missing_outputs")
        if metrics.duplicate_topics > 0:
            actions.append("merge_duplicate_topics")
        if metrics.rework_events_30d > 0:
            actions.append("review_rework_causes")
        for task_id, record in self._tasks.items():
            if record.status in {TaskStatus.DONE, TaskStatus.ARCHIVED}:
                if self.validate_task(task_id):
                    actions.append(f"complete_task_archive:{task_id}")
        if not actions:
            actions.append("entropy_within_threshold")
        return actions

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[TaskRecord]:
        if status is None:
            return list(self._tasks.values())
        return [t for t in self._tasks.values() if t.status == status]

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        return self._tasks.get(task_id)

    def get_output(self, output_id: str) -> Optional[OutputRecord]:
        return self._outputs.get(output_id)

    def get_adr(self, adr_id: str) -> Optional[ADRRecord]:
        return self._adrs.get(adr_id)

    def _require_task(self, task_id: str) -> TaskRecord:
        record = self._tasks.get(task_id)
        if not record:
            raise ValueError(f"task not found: {task_id}")
        return record
