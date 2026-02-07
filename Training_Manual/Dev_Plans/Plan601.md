# Plan601 Orchestrator 编排执行

## 目标
支持按节点推进 Run。

## 代码（`src/orchestrator/service.py`）
```python
from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.shared.store import EventStore, StateDB
from src.workers.base import EchoWorker, Worker


@dataclass
class OrchestratorService:
    event_store: EventStore
    state_db: StateDB
    worker: Worker

    @staticmethod
    def with_default_worker(event_store: EventStore, state_db: StateDB) -> "OrchestratorService":
        return OrchestratorService(event_store=event_store, state_db=state_db, worker=EchoWorker())

    def run_single_node(self, run_id: str, workflow_id: str, version: str, node_id: str, payload: dict) -> dict:
        node_run_id = f"nr_{uuid.uuid4().hex[:10]}"

        self.state_db.upsert_node_run(node_run_id, run_id, node_id, "running", attempt=1, metadata={})
        self.event_store.append("orchestrator", "node_started", {"run_id": run_id, "node_run_id": node_run_id, "node_id": node_id})

        result = self.worker.run(payload)

        if result.ok:
            self.state_db.upsert_node_run(node_run_id, run_id, node_id, "success", attempt=1, metadata=result.output)
            self.event_store.append("orchestrator", "node_finished", {"run_id": run_id, "node_run_id": node_run_id, "status": "success"})
            self.state_db.upsert_run(run_id, workflow_id, version, "success", metadata={"last_node": node_id})
            self.event_store.append("orchestrator", "run_finished", {"run_id": run_id, "status": "success"})
        else:
            self.state_db.upsert_node_run(node_run_id, run_id, node_id, "failed", attempt=1, metadata={"error": result.error})
            self.event_store.append("orchestrator", "node_finished", {"run_id": run_id, "node_run_id": node_run_id, "status": "failed"})
            self.state_db.upsert_run(run_id, workflow_id, version, "failed", metadata={"last_node": node_id})
            self.event_store.append("orchestrator", "run_finished", {"run_id": run_id, "status": "failed"})

        return {
            "run_id": run_id,
            "node_run_id": node_run_id,
            "ok": result.ok,
            "output": result.output,
            "error": result.error,
        }
```

## 验收
- 运行节点有 started/finished 事件
