# Plan611 Observability 组件

## 目标
统一日志与指标输出。

## 代码（`src/shared/obs.py`）
```python
from __future__ import annotations

import json
import logging
from typing import Any


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("openclaw")


def metric(name: str, value: float, labels: dict[str, Any] | None = None) -> None:
    payload = {
        "type": "metric",
        "name": name,
        "value": value,
        "labels": labels or {},
    }
    logger.info(json.dumps(payload, ensure_ascii=False))
```

## 验收
- 关键路径有日志和指标
