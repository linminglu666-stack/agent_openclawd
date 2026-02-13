from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from protocols.interfaces import IModule
from utils.logger import get_logger


@dataclass
class SchedulerConfig:
    tick_interval_ms: int = 1000
    max_schedules: int = 10000
    default_policy: str = "immediate"


@dataclass
class ScheduleEntry:
    schedule_id: str
    task_template: Dict[str, Any]
    policy: Dict[str, Any]
    enabled: bool = True
    next_fire_at: Optional[int] = None
    last_fire_at: Optional[int] = None
    fire_count: int = 0
    created_at: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))


@dataclass
class SchedulerHealth:
    state: str
    total_schedules: int
    enabled_schedules: int
    next_fire_in_ms: Optional[int]


class CentralBrainScheduler(IModule):
    def __init__(self, config: Optional[SchedulerConfig] = None):
        self._config = config or SchedulerConfig()
        self._schedules: Dict[str, ScheduleEntry] = {}
        self._initialized = False
        self._running = False
        self._logger = get_logger("central_brain.scheduler")
        self._schedule_counter = 0

    @property
    def name(self) -> str:
        return "central_brain_scheduler"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self, config: Dict[str, Any]) -> bool:
        if config.get("tick_interval_ms"):
            self._config.tick_interval_ms = config["tick_interval_ms"]
        if config.get("max_schedules"):
            self._config.max_schedules = config["max_schedules"]

        self._initialized = True
        self._running = True
        self._logger.info("Scheduler initialized", config=self._config.__dict__)
        return True

    async def shutdown(self) -> bool:
        self._running = False
        self._initialized = False
        self._logger.info("Scheduler shutdown")
        return True

    async def health_check(self) -> Dict[str, Any]:
        health = self.tick()
        return {
            "component": self.name,
            "initialized": self._initialized,
            "running": self._running,
            "state": health.state,
            "total_schedules": health.total_schedules,
            "enabled_schedules": health.enabled_schedules,
        }

    async def execute(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if command == "schedule":
            schedule_id = await self.create_schedule(args.get("task_template", {}), args.get("policy", {}))
            return {"schedule_id": schedule_id, "status": "created"}
        elif command == "cancel":
            success = await self.cancel_schedule(args.get("schedule_id", ""))
            return {"success": success}
        elif command == "enable":
            success = await self.enable_schedule(args.get("schedule_id", ""), args.get("enabled", True))
            return {"success": success}
        elif command == "list":
            schedules = self.list_schedules(args.get("enabled_only", False))
            return {"schedules": schedules}
        elif command == "tick":
            health = self.tick()
            return health.__dict__
        else:
            return {"error": f"Unknown command: {command}"}

    async def create_schedule(self, task_template: Dict[str, Any], policy: Dict[str, Any]) -> str:
        self._schedule_counter += 1
        schedule_id = f"schedule_{self._schedule_counter}"

        next_fire = self._calculate_next_fire(policy)

        entry = ScheduleEntry(
            schedule_id=schedule_id,
            task_template=task_template,
            policy=policy,
            next_fire_at=next_fire,
        )

        self._schedules[schedule_id] = entry
        self._logger.info("Schedule created", schedule_id=schedule_id, next_fire_at=next_fire)

        return schedule_id

    async def cancel_schedule(self, schedule_id: str) -> bool:
        if schedule_id in self._schedules:
            del self._schedules[schedule_id]
            self._logger.info("Schedule cancelled", schedule_id=schedule_id)
            return True
        return False

    async def enable_schedule(self, schedule_id: str, enabled: bool = True) -> bool:
        if schedule_id not in self._schedules:
            return False

        self._schedules[schedule_id].enabled = enabled
        self._logger.info("Schedule enabled/disabled", schedule_id=schedule_id, enabled=enabled)
        return True

    def tick(self, now: Optional[int] = None) -> SchedulerHealth:
        ts = now or int(datetime.now(tz=timezone.utc).timestamp())
        triggered = 0

        for schedule_id, entry in list(self._schedules.items()):
            if not entry.enabled:
                continue

            if entry.next_fire_at and entry.next_fire_at <= ts:
                self._fire_schedule(entry, ts)
                entry.next_fire_at = self._calculate_next_fire(entry.policy, ts)
                triggered += 1

        enabled_count = sum(1 for e in self._schedules.values() if e.enabled)
        next_fire = min(
            (e.next_fire_at for e in self._schedules.values() if e.enabled and e.next_fire_at),
            default=None,
        )

        next_fire_in_ms = None
        if next_fire:
            next_fire_in_ms = max(0, (next_fire - ts) * 1000)

        return SchedulerHealth(
            state="running" if self._running else "stopped",
            total_schedules=len(self._schedules),
            enabled_schedules=enabled_count,
            next_fire_in_ms=next_fire_in_ms,
        )

    def _fire_schedule(self, entry: ScheduleEntry, now: int) -> None:
        entry.last_fire_at = now
        entry.fire_count += 1
        self._logger.info(
            "Schedule fired",
            schedule_id=entry.schedule_id,
            fire_count=entry.fire_count,
        )

    def _calculate_next_fire(self, policy: Dict[str, Any], base_time: Optional[int] = None) -> Optional[int]:
        base = base_time or int(datetime.now(tz=timezone.utc).timestamp())
        policy_type = policy.get("type", self._config.default_policy)

        if policy_type == "immediate":
            return base

        elif policy_type == "delayed":
            delay_sec = policy.get("delay_sec", 60)
            return base + delay_sec

        elif policy_type == "interval":
            interval_sec = policy.get("interval_sec", 3600)
            return base + interval_sec

        elif policy_type == "cron":
            return self._parse_cron(policy.get("cron_expr", ""), base)

        elif policy_type == "once":
            scheduled_time = policy.get("scheduled_at")
            if scheduled_time:
                return int(scheduled_time)
            return base

        return base

    def _parse_cron(self, cron_expr: str, base_time: int) -> int:
        return base_time + 3600

    def list_schedules(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        schedules = []
        for entry in self._schedules.values():
            if enabled_only and not entry.enabled:
                continue
            schedules.append({
                "schedule_id": entry.schedule_id,
                "enabled": entry.enabled,
                "next_fire_at": entry.next_fire_at,
                "last_fire_at": entry.last_fire_at,
                "fire_count": entry.fire_count,
                "policy": entry.policy,
            })
        return schedules

    def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        entry = self._schedules.get(schedule_id)
        if not entry:
            return None
        return {
            "schedule_id": entry.schedule_id,
            "task_template": entry.task_template,
            "policy": entry.policy,
            "enabled": entry.enabled,
            "next_fire_at": entry.next_fire_at,
            "last_fire_at": entry.last_fire_at,
            "fire_count": entry.fire_count,
        }
