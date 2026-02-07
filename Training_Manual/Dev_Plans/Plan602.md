# Plan602 Worker SDK 与默认 Worker

## 目标
统一 worker 接口，减少执行分歧。

## 代码（`src/workers/base.py`）
```python
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class WorkerResult:
    ok: bool
    output: dict[str, Any]
    error: str | None = None


class Worker(ABC):
    name: str

    @abstractmethod
    def run(self, payload: dict[str, Any]) -> WorkerResult:
        raise NotImplementedError


class EchoWorker(Worker):
    name = "echo"

    def run(self, payload: dict[str, Any]) -> WorkerResult:
        return WorkerResult(ok=True, output={"echo": payload})
```

## 验收
- `EchoWorker().run({...})` 返回结构化结果
