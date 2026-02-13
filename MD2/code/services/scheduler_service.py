from __future__ import annotations

from typing import Any, Dict

from core.runtime import build_runtime_container
from core.scheduler import ScheduleOnlyScheduler
from services.service_base import ServiceBase, ServiceConfig


class SchedulerService(ServiceBase):
    def __init__(self):
        super().__init__(ServiceConfig(name="scheduler", tick_interval_sec=1.0))
        self._rt = build_runtime_container()
        self._scheduler = ScheduleOnlyScheduler(state_db=self._rt.state_db, wal=self._rt.wal)

    async def initialize(self) -> bool:
        ok = await super().initialize()
        if not ok:
            return False
        self._rt.paths.ensure()
        return True

    async def shutdown(self) -> bool:
        return await super().shutdown()

    async def tick(self) -> None:
        health = self._scheduler.tick()
        payload = {"component": "scheduler", "state": health.state, "due_checked": health.due_checked, "triggered": health.triggered}
        self._rt.state_store.put("scheduler/health", payload)
        self._rt.wal.append("scheduler_tick", payload)

    async def health(self) -> Dict[str, Any]:
        obj = self._rt.state_store.get("scheduler/health") or {}
        return obj.get("value") or {"component": "scheduler", "state": "unknown"}


def main() -> int:
    return SchedulerService.main(SchedulerService())


if __name__ == "__main__":
    raise SystemExit(main())
