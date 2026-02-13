from __future__ import annotations

from typing import Any, Dict

from core.runtime import build_runtime_container
from core.growth_loop import GrowthLoop
from services.service_base import ServiceBase, ServiceConfig


class GrowthLoopService(ServiceBase):
    def __init__(self):
        super().__init__(ServiceConfig(name="growth_loop", tick_interval_sec=10.0))
        self._rt = build_runtime_container()
        self._loop = GrowthLoop(state_db=self._rt.state_db, wal=self._rt.wal)

    async def initialize(self) -> bool:
        ok = await super().initialize()
        if not ok:
            return False
        self._rt.paths.ensure()
        return True

    async def tick(self) -> None:
        health = self._loop.tick()
        payload = {"component": "growth_loop", "state": health.state, "idle_agents": health.idle_agents, "reports_written": health.reports_written}
        self._rt.state_store.put("growth_loop/health", payload)
        self._rt.wal.append("growth_loop_tick", payload)

    async def health(self) -> Dict[str, Any]:
        obj = self._rt.state_store.get("growth_loop/health") or {}
        return obj.get("value") or {"component": "growth_loop", "state": "unknown"}


def main() -> int:
    return GrowthLoopService.main(GrowthLoopService())


if __name__ == "__main__":
    raise SystemExit(main())

