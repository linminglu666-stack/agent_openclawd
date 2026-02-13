from __future__ import annotations

from typing import Any, Dict

from core.eval_gate import EvalGateModule
from services.service_base import ServiceBase, ServiceConfig


class EvalService(ServiceBase):
    def __init__(self):
        super().__init__(ServiceConfig(name="eval", tick_interval_sec=5.0))
        self._gate = EvalGateModule()

    async def initialize(self) -> bool:
        ok = await super().initialize()
        if not ok:
            return False
        return await self._gate.initialize({})

    async def shutdown(self) -> bool:
        await self._gate.shutdown()
        return await super().shutdown()

    async def tick(self) -> None:
        _ = await self._gate.health_check()

    async def health(self) -> Dict[str, Any]:
        return await self._gate.health_check()


def main() -> int:
    return EvalService.main(EvalService())


if __name__ == "__main__":
    raise SystemExit(main())

