# Plan600 Scheduler 服务实现

## 目标
提供调度触发与 misfire 基础能力。

## 代码（`src/scheduler/service.py`）
```python
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from src.shared.store import EventStore, StateDB


@dataclass
class SchedulerService:
    event_store: EventStore
    state_db: StateDB

    def schedule_run(self, workflow_id: str, version: str, schedule_id: str | None = None, metadata: dict[str, Any] | None = None) -> str:
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        meta = metadata or {}
        self.state_db.upsert_run(run_id, workflow_id, version, "scheduled", schedule_id=schedule_id, metadata=meta)
        self.event_store.append("scheduler", "run_scheduled", {"run_id": run_id, "workflow_id": workflow_id, "version": version})
        return run_id

    def mark_running(self, run_id: str, workflow_id: str, version: str, schedule_id: str | None = None) -> None:
        self.state_db.upsert_run(run_id, workflow_id, version, "running", schedule_id=schedule_id, metadata={})
        self.event_store.append("scheduler", "run_started", {"run_id": run_id})
```

## 验收
- 调用 trigger 后事件和状态都更新
