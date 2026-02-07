# Plan603 Memory Castle 服务

## 目标
实现记忆写入与检索最小闭环。

## 代码（`src/memory/service.py`）
```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MemoryCastleService:
    def __init__(self, root: str = "data/memory_castle"):
        self.root = Path(root)
        self.workshop = self.root / "workshop"
        self.workshop.mkdir(parents=True, exist_ok=True)

    def write_plan_lesson(self, plan_id: int, summary: str, lessons: dict[str, Any]) -> None:
        (self.workshop / f"plan_{plan_id}_summary.md").write_text(summary, encoding="utf-8")
        (self.workshop / f"plan_{plan_id}_lessons.json").write_text(
            json.dumps(lessons, ensure_ascii=False, indent=2), encoding="utf-8"
        )
```

## 验收
- 产出 `data/memory_castle/workshop/*`
