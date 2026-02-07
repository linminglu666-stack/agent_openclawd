# Plan606 Browser Extension Manager

## 目标
实现扩展安装/启停/回滚记录。

## 代码（`src/plugins/extension_manager.py`）
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExtensionState:
    ext_id: str
    version: str
    enabled: bool


class ExtensionManager:
    def __init__(self) -> None:
        self._registry: dict[str, ExtensionState] = {}

    def install(self, ext_id: str, version: str) -> None:
        self._registry[ext_id] = ExtensionState(ext_id=ext_id, version=version, enabled=True)

    def enable(self, ext_id: str) -> None:
        if ext_id in self._registry:
            self._registry[ext_id].enabled = True

    def disable(self, ext_id: str) -> None:
        if ext_id in self._registry:
            self._registry[ext_id].enabled = False

    def list(self) -> list[ExtensionState]:
        return list(self._registry.values())
```

## 验收
- 扩展状态可查询
