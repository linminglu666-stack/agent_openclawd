# Plan598 数据契约与对象模型

## 目标
统一 Workflow/Schedule/Run/NodeRun 契约。

## 代码（`src/shared/models.py`）
```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

RunStatus = Literal["scheduled", "running", "success", "failed", "canceled", "timeout", "lost"]
NodeStatus = Literal["queued", "running", "success", "failed", "canceled", "skipped"]


@dataclass
class WorkflowRef:
    workflow_id: str
    version: str


@dataclass
class Schedule:
    schedule_id: str
    workflow: WorkflowRef
    cron: str
    timezone: str = "UTC"
    enabled: bool = True


@dataclass
class Run:
    run_id: str
    workflow_id: str
    version: str
    status: RunStatus = "scheduled"
    schedule_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NodeRun:
    node_run_id: str
    run_id: str
    node_id: str
    status: NodeStatus = "queued"
    attempt: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)
```

## 验收
- `python -c "from src.shared.models import Run; print(Run.model_json_schema()['title'])"`
