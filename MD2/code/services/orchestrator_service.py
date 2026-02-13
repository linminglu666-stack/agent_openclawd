from __future__ import annotations

from typing import Any, Dict

from core.runtime import build_runtime_container
from core.orchestrator import RunEngine
from services.service_base import ServiceBase, ServiceConfig


class OrchestratorService(ServiceBase):
    def __init__(self):
        super().__init__(ServiceConfig(name="orchestrator", tick_interval_sec=1.0))
        self._rt = build_runtime_container()
        self._engine = RunEngine(state_db=self._rt.state_db, wal=self._rt.wal)

    async def initialize(self) -> bool:
        ok = await super().initialize()
        if not ok:
            return False
        self._rt.paths.ensure()
        return True

    async def shutdown(self) -> bool:
        return await super().shutdown()

    async def tick(self) -> None:
        health = self._engine.tick()
        payload = {"component": "orchestrator", "state": health.state, "scanned_runs": health.scanned_runs, "progressed_nodes": health.progressed_nodes}
        self._rt.state_store.put("orchestrator/health", payload)
        self._rt.wal.append("orchestrator_tick", payload)

    async def health(self) -> Dict[str, Any]:
        obj = self._rt.state_store.get("orchestrator/health") or {}
        return obj.get("value") or {"component": "orchestrator", "state": "unknown"}


def main() -> int:
    return OrchestratorService.main(OrchestratorService())


if __name__ == "__main__":
    raise SystemExit(main())
