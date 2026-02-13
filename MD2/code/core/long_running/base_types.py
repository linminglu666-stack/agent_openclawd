from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class SessionState(Enum):
    PENDING = "pending"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOVERING = "recovering"


class SessionType(Enum):
    INITIALIZER = "initializer"
    CODING = "coding"
    TESTING = "testing"
    REVIEW = "review"
    CLEANUP = "cleanup"


class FeatureStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"


class RecoveryStrategy(Enum):
    ROLLBACK = "rollback"
    RESTART = "restart"
    SKIP = "skip"
    ESCALATE = "escalate"
    COMPENSATE = "compensate"


class Priority(Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    DEFERRED = 4


@dataclass
class Feature:
    feature_id: str
    category: str
    description: str
    steps: List[str] = field(default_factory=list)
    status: FeatureStatus = FeatureStatus.PENDING
    priority: Priority = Priority.MEDIUM
    dependencies: List[str] = field(default_factory=list)
    test_criteria: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))
    updated_at: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))

    def mark_passed(self) -> None:
        self.status = FeatureStatus.PASSED
        self.updated_at = int(datetime.now(tz=timezone.utc).timestamp())

    def mark_failed(self) -> None:
        self.status = FeatureStatus.FAILED
        self.updated_at = int(datetime.now(tz=timezone.utc).timestamp())

    def start_work(self) -> None:
        self.status = FeatureStatus.IN_PROGRESS
        self.updated_at = int(datetime.now(tz=timezone.utc).timestamp())


@dataclass
class ProgressEntry:
    entry_id: str
    session_id: str
    timestamp: int
    action: str
    description: str
    feature_id: Optional[str] = None
    files_changed: List[str] = field(default_factory=list)
    commit_hash: Optional[str] = None
    test_results: Optional[Dict[str, Any]] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    next_steps: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "action": self.action,
            "description": self.description,
            "feature_id": self.feature_id,
            "files_changed": self.files_changed,
            "commit_hash": self.commit_hash,
            "test_results": self.test_results,
            "metrics": self.metrics,
            "next_steps": self.next_steps,
            "blockers": self.blockers,
        }


@dataclass
class SessionContext:
    session_id: str
    session_type: SessionType
    state: SessionState
    project_root: str
    start_time: int
    feature_list_path: str = "feature_list.json"
    progress_file_path: str = "progress.jsonl"
    init_script_path: str = "init.sh"
    current_feature: Optional[str] = None
    context_window_usage: float = 0.0
    parent_session: Optional[str] = None
    config_snapshot: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None

    def is_context_exhausted(self, threshold: float = 0.85) -> bool:
        return self.context_window_usage >= threshold


@dataclass
class CheckpointData:
    checkpoint_id: str
    session_id: str
    timestamp: int
    feature_states: Dict[str, FeatureStatus]
    progress_summary: str
    pending_tasks: List[str]
    files_snapshot: Dict[str, str]
    git_status: Dict[str, Any]
    health_metrics: Dict[str, float]
    recovery_hint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "feature_states": {k: v.value for k, v in self.feature_states.items()},
            "progress_summary": self.progress_summary,
            "pending_tasks": self.pending_tasks,
            "files_snapshot": self.files_snapshot,
            "git_status": self.git_status,
            "health_metrics": self.health_metrics,
            "recovery_hint": self.recovery_hint,
        }


@dataclass
class EnvironmentSetup:
    project_root: str
    feature_list: List[Feature]
    init_script_content: str
    initial_commit_hash: str
    config_files: Dict[str, str]
    dependencies: List[str]
    setup_timestamp: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_root": self.project_root,
            "feature_list": [f.__dict__ for f in self.feature_list],
            "init_script_content": self.init_script_content,
            "initial_commit_hash": self.initial_commit_hash,
            "config_files": self.config_files,
            "dependencies": self.dependencies,
            "setup_timestamp": self.setup_timestamp,
        }


@dataclass
class IncrementalProgress:
    session_id: str
    feature_id: str
    previous_state: FeatureStatus
    new_state: FeatureStatus
    changes_made: List[str]
    tests_passed: bool
    commit_hash: str
    progress_entry: ProgressEntry
    context_health: float
    ready_for_next: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "feature_id": self.feature_id,
            "previous_state": self.previous_state.value,
            "new_state": self.new_state.value,
            "changes_made": self.changes_made,
            "tests_passed": self.tests_passed,
            "commit_hash": self.commit_hash,
            "context_health": self.context_health,
            "ready_for_next": self.ready_for_next,
        }


@dataclass
class BridgedContext:
    source_session: str
    target_session: str
    feature_list: List[Feature]
    recent_progress: List[ProgressEntry]
    last_checkpoint: Optional[CheckpointData]
    git_history: List[Dict[str, Any]]
    environment_state: Dict[str, Any]
    recommendations: List[str]
    urgent_issues: List[str]

    def get_next_feature(self) -> Optional[Feature]:
        for feature in sorted(self.feature_list, key=lambda f: f.priority.value):
            if feature.status in (FeatureStatus.PENDING, FeatureStatus.FAILED):
                return feature
        return None

    def get_active_blockers(self) -> List[str]:
        blockers = []
        for entry in self.recent_progress:
            blockers.extend(entry.blockers)
        return list(set(blockers))
