from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.logger import get_logger


class AgentState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    FAILED = "failed"
    BLOCKED = "blocked"
    LEARNING = "learning"


@dataclass
class AgentHeartbeat:
    agent_id: str
    status: AgentState
    cpu: float
    mem: float
    queue_depth: int
    last_task: Optional[str]
    trace_id: Optional[str]
    timestamp: int
    version: str
    skills: List[str]
    metrics: Dict[str, Any] = field(default_factory=dict)
    health: Dict[str, Any] = field(default_factory=dict)
    resource_limits: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentSnapshot:
    snapshot_id: str
    agent_id: str
    state: AgentState
    task_id: Optional[str]
    memory_state: Dict[str, Any] = field(default_factory=dict)
    created_at: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))


@dataclass
class AgentConfig:
    agent_id: str
    skills: List[str] = field(default_factory=list)
    max_concurrent_tasks: int = 5
    heartbeat_interval_sec: int = 10
    idle_timeout_sec: int = 60
    max_retries: int = 3
    resource_limits: Dict[str, Any] = field(default_factory=dict)


class Agent:
    def __init__(self, config: AgentConfig):
        self._config = config
        self._state = AgentState.IDLE
        self._current_task: Optional[str] = None
        self._snapshot: Optional[AgentSnapshot] = None
        self._last_heartbeat: Optional[AgentHeartbeat] = None
        self._metrics: Dict[str, Any] = {
            "success_rate": 0.9,
            "avg_latency_ms": 1000,
            "total_tasks": 0,
            "failed_tasks": 0,
        }
        self._consecutive_failures = 0
        self._idle_since: Optional[int] = None
        self._logger = get_logger(f"agent.{config.agent_id}")

    @property
    def agent_id(self) -> str:
        return self._config.agent_id

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def skills(self) -> List[str]:
        return self._config.skills

    @property
    def current_task(self) -> Optional[str]:
        return self._current_task

    def assign_task(self, task_id: str) -> bool:
        if self._state not in (AgentState.IDLE, AgentState.LEARNING):
            return False

        self._create_snapshot()
        self._state = AgentState.RUNNING
        self._current_task = task_id
        self._idle_since = None

        self._logger.info("Task assigned", task_id=task_id)
        return True

    def complete_task(self, success: bool = True, result: Optional[Dict[str, Any]] = None) -> None:
        if success:
            self._metrics["total_tasks"] += 1
            self._consecutive_failures = 0
        else:
            self._metrics["total_tasks"] += 1
            self._metrics["failed_tasks"] += 1
            self._consecutive_failures += 1

        self._current_task = None
        self._state = AgentState.IDLE
        self._idle_since = int(datetime.now(tz=timezone.utc).timestamp())

        success_rate = (
            (self._metrics["total_tasks"] - self._metrics["failed_tasks"])
            / self._metrics["total_tasks"]
            if self._metrics["total_tasks"] > 0
            else 0.9
        )
        self._metrics["success_rate"] = success_rate

        self._logger.info("Task completed", success=success, total=self._metrics["total_tasks"])

    def fail(self, error: str) -> None:
        self._state = AgentState.FAILED
        self._metrics["failed_tasks"] += 1
        self._consecutive_failures += 1

        self._logger.error("Agent failed", error=error, consecutive_failures=self._consecutive_failures)

    def block(self, reason: str) -> None:
        self._state = AgentState.BLOCKED
        self._logger.warn("Agent blocked", reason=reason)

    def unblock(self) -> None:
        if self._state == AgentState.BLOCKED:
            self._state = AgentState.IDLE
            self._logger.info("Agent unblocked")

    def start_learning(self) -> bool:
        if self._state != AgentState.IDLE:
            return False

        self._state = AgentState.LEARNING
        self._logger.info("Agent started learning")
        return True

    def complete_learning(self) -> None:
        if self._state == AgentState.LEARNING:
            self._state = AgentState.IDLE
            self._idle_since = int(datetime.now(tz=timezone.utc).timestamp())
            self._logger.info("Agent completed learning")

    def rollback(self) -> bool:
        if not self._snapshot:
            return False

        self._state = self._snapshot.state
        self._current_task = self._snapshot.task_id
        self._logger.info("Agent rolled back", snapshot_id=self._snapshot.snapshot_id)
        return True

    def _create_snapshot(self) -> AgentSnapshot:
        import hashlib
        import time

        snap_id = hashlib.sha256(f"{self.agent_id}{time.time()}".encode()).hexdigest()[:16]

        self._snapshot = AgentSnapshot(
            snapshot_id=snap_id,
            agent_id=self.agent_id,
            state=self._state,
            task_id=self._current_task,
        )

        return self._snapshot

    def heartbeat(self) -> AgentHeartbeat:
        now = int(datetime.now(tz=timezone.utc).timestamp())

        heartbeat = AgentHeartbeat(
            agent_id=self.agent_id,
            status=self._state,
            cpu=0.1,
            mem=0.2,
            queue_depth=0,
            last_task=self._current_task,
            trace_id=None,
            timestamp=now,
            version="1.0.0",
            skills=self._config.skills,
            metrics=dict(self._metrics),
            health={
                "is_healthy": self._consecutive_failures < 3,
                "last_error": None,
                "consecutive_failures": self._consecutive_failures,
            },
            resource_limits=self._config.resource_limits,
        )

        self._last_heartbeat = heartbeat
        return heartbeat

    def get_idle_duration(self, now: Optional[int] = None) -> int:
        if self._idle_since is None:
            return 0
        return (now or int(datetime.now(tz=timezone.utc).timestamp())) - self._idle_since

    def should_start_learning(self, now: Optional[int] = None) -> bool:
        if self._state != AgentState.IDLE:
            return False

        idle_duration = self.get_idle_duration(now)
        return idle_duration >= self._config.idle_timeout_sec

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "state": self._state.value,
            "skills": self._config.skills,
            "current_task": self._current_task,
            "metrics": self._metrics,
            "consecutive_failures": self._consecutive_failures,
            "idle_since": self._idle_since,
        }
