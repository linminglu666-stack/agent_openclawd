# Plan604 Knowledge Graph 服务

## 目标
写入节点边并输出索引。

## 代码（`src/kg/service.py`）
```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class KGService:
    def __init__(self, root: str = "data/kg"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write_graph(self, plan_id: int, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> None:
        target = self.root / f"plan_{plan_id}_nodes_edges.json"
        target.write_text(json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2), encoding="utf-8")
```

## 验收
- 图谱文件可生成且 JSON 有效
