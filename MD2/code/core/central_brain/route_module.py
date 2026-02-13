from __future__ import annotations

from typing import Any, Dict, Optional

from protocols.interfaces import IModule


class RouteModule(IModule):
    def __init__(self):
        self._initialized = False

    @property
    def name(self) -> str:
        return "router"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self, config: Dict[str, Any]) -> bool:
        self._initialized = True
        return True

    async def shutdown(self) -> bool:
        self._initialized = False
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {"component": self.name, "initialized": self._initialized}

    async def execute(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        task_data = args.get("task_data")
        if isinstance(task_data, dict) and "input" not in task_data:
            return {"input": task_data, "context": args.get("context", {})}
        if isinstance(task_data, dict):
            return task_data
        return {"input": task_data, "context": args.get("context", {})}

