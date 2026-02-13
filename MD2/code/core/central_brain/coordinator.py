from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from protocols.interfaces import IModule
from utils.logger import get_logger
from .router import TaskRouter, RoutingResult
from .model_router import ModelRouter, RouteDecision


@dataclass
class CoordinatorConfig:
    max_concurrent_tasks: int = 100
    task_timeout_sec: int = 300
    retry_attempts: int = 3
    retry_delay_sec: int = 5
    enable_priority_queue: bool = True


@dataclass
class TaskContext:
    task_id: str
    trace_id: str
    status: str = "pending"
    priority: int = 0
    created_at: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))
    started_at: Optional[int] = None
    completed_at: Optional[int] = None
    assigned_agent: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0


class CentralBrainCoordinator(IModule):
    def __init__(self, config: Optional[CoordinatorConfig] = None):
        self._config = config or CoordinatorConfig()
        self._task_router = TaskRouter()
        self._model_router = ModelRouter()
        self._tasks: Dict[str, TaskContext] = {}
        self._pending_queue: List[str] = []
        self._running_tasks: Dict[str, str] = {}
        self._initialized = False
        self._logger = get_logger("central_brain.coordinator")
        self._task_counter = 0

    @property
    def name(self) -> str:
        return "central_brain_coordinator"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self, config: Dict[str, Any]) -> bool:
        if config.get("max_concurrent_tasks"):
            self._config.max_concurrent_tasks = config["max_concurrent_tasks"]
        if config.get("task_timeout_sec"):
            self._config.task_timeout_sec = config["task_timeout_sec"]
        if config.get("retry_attempts"):
            self._config.retry_attempts = config["retry_attempts"]

        self._initialized = True
        self._logger.info("Coordinator initialized", config=self._config.__dict__)
        return True

    async def shutdown(self) -> bool:
        self._initialized = False
        self._logger.info("Coordinator shutdown")
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {
            "component": self.name,
            "initialized": self._initialized,
            "pending_tasks": len(self._pending_queue),
            "running_tasks": len(self._running_tasks),
            "total_tasks": len(self._tasks),
            "config": self._config.__dict__,
        }

    async def execute(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if command == "submit":
            task_id = await self.submit_task(args.get("task", {}), args.get("context", {}))
            return {"task_id": task_id, "status": "submitted"}
        elif command == "status":
            status = self.get_task_status(args.get("task_id", ""))
            return status or {"error": "task not found"}
        elif command == "route":
            result = await self.route_task(args.get("task", {}))
            return result.to_dict()
        elif command == "list":
            tasks = self.list_tasks(args.get("status"), args.get("limit", 100))
            return {"tasks": tasks}
        else:
            return {"error": f"Unknown command: {command}"}

    async def submit_task(self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        self._task_counter += 1
        task_id = f"task_{self._task_counter}"
        trace_id = context.get("trace_id") if context else None

        ctx = TaskContext(
            task_id=task_id,
            trace_id=trace_id or task_id,
            priority=task.get("priority", 0),
        )

        self._tasks[task_id] = ctx

        if self._config.enable_priority_queue:
            inserted = False
            for i, tid in enumerate(self._pending_queue):
                if self._tasks[tid].priority < ctx.priority:
                    self._pending_queue.insert(i, task_id)
                    inserted = True
                    break
            if not inserted:
                self._pending_queue.append(task_id)
        else:
            self._pending_queue.append(task_id)

        self._logger.info("Task submitted", task_id=task_id, priority=ctx.priority)
        return task_id

    async def route_task(self, task: Dict[str, Any]) -> RoutingResult:
        model_decision = self._model_router.decide(task)
        task_routing = self._task_router.route(task)

        result = RoutingResult(
            task_id=task.get("task_id", ""),
            target_agent=task_routing.target_agent,
            reason=task_routing.reason,
            confidence=max(model_decision.confidence, task_routing.confidence),
            alternatives=task_routing.alternatives,
        )

        self._logger.info(
            "Task routed",
            task_id=result.task_id,
            target=result.target_agent,
            confidence=result.confidence,
        )

        return result

    async def dispatch_task(self, task_id: str, agent_id: str) -> bool:
        if task_id not in self._tasks:
            return False

        ctx = self._tasks[task_id]
        ctx.status = "running"
        ctx.started_at = int(datetime.now(tz=timezone.utc).timestamp())
        ctx.assigned_agent = agent_id

        if task_id in self._pending_queue:
            self._pending_queue.remove(task_id)
        self._running_tasks[task_id] = agent_id

        self._logger.info("Task dispatched", task_id=task_id, agent=agent_id)
        return True

    async def complete_task(self, task_id: str, result: Dict[str, Any]) -> bool:
        if task_id not in self._tasks:
            return False

        ctx = self._tasks[task_id]
        ctx.status = "completed"
        ctx.completed_at = int(datetime.now(tz=timezone.utc).timestamp())
        ctx.result = result

        if task_id in self._running_tasks:
            del self._running_tasks[task_id]

        self._logger.info("Task completed", task_id=task_id)
        return True

    async def fail_task(self, task_id: str, error: str) -> bool:
        if task_id not in self._tasks:
            return False

        ctx = self._tasks[task_id]
        ctx.error = error

        if ctx.retry_count < self._config.retry_attempts:
            ctx.retry_count += 1
            ctx.status = "pending"
            self._pending_queue.append(task_id)
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]
            self._logger.warn("Task failed, retrying", task_id=task_id, retry_count=ctx.retry_count)
        else:
            ctx.status = "failed"
            ctx.completed_at = int(datetime.now(tz=timezone.utc).timestamp())
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]
            self._logger.error("Task failed permanently", task_id=task_id, error=error)

        return True

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        ctx = self._tasks.get(task_id)
        if not ctx:
            return None

        return {
            "task_id": ctx.task_id,
            "trace_id": ctx.trace_id,
            "status": ctx.status,
            "priority": ctx.priority,
            "assigned_agent": ctx.assigned_agent,
            "retry_count": ctx.retry_count,
            "created_at": ctx.created_at,
            "started_at": ctx.started_at,
            "completed_at": ctx.completed_at,
            "error": ctx.error,
        }

    def get_next_pending_task(self) -> Optional[str]:
        if self._pending_queue:
            return self._pending_queue[0]
        return None

    def list_tasks(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        tasks = []
        for ctx in self._tasks.values():
            if status and ctx.status != status:
                continue
            tasks.append({
                "task_id": ctx.task_id,
                "status": ctx.status,
                "priority": ctx.priority,
                "assigned_agent": ctx.assigned_agent,
            })
            if len(tasks) >= limit:
                break
        return tasks

    def get_stats(self) -> Dict[str, Any]:
        status_counts: Dict[str, int] = {}
        for ctx in self._tasks.values():
            status_counts[ctx.status] = status_counts.get(ctx.status, 0) + 1

        return {
            "total_tasks": len(self._tasks),
            "pending": len(self._pending_queue),
            "running": len(self._running_tasks),
            "status_distribution": status_counts,
        }
