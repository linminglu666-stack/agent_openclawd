from __future__ import annotations

from typing import Any, Dict

from core.memory_hub import LayeredMemoryHub
from services.service_base import ServiceBase, ServiceConfig


class MemoryIndexerService(ServiceBase):
    def __init__(self):
        super().__init__(ServiceConfig(name="memory_indexer", tick_interval_sec=2.0))
        self._hub = LayeredMemoryHub()

    async def initialize(self) -> bool:
        ok = await super().initialize()
        if not ok:
            return False
        return await self._hub.initialize({})

    async def shutdown(self) -> bool:
        await self._hub.shutdown()
        return await super().shutdown()

    async def tick(self) -> None:
        _ = await self._hub.health_check()

    async def health(self) -> Dict[str, Any]:
        return await self._hub.health_check()


def main() -> int:
    return MemoryIndexerService.main(MemoryIndexerService())


if __name__ == "__main__":
    raise SystemExit(main())

