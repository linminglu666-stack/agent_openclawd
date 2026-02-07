# Plan607 Plugin Sandbox Runtime

## 目标
限制插件权限与资源。

## 代码（`src/plugins/sandbox.py`）
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PluginPolicy:
    allow_network: bool = False
    timeout_sec: int = 10
    max_memory_mb: int = 128


class SandboxRunner:
    def run(self, plugin_name: str, policy: PluginPolicy, payload: dict) -> dict:
        # Replace with isolated process/container runtime.
        return {
            "plugin": plugin_name,
            "status": "ok",
            "policy": policy.__dict__,
            "payload_keys": sorted(payload.keys()),
        }
```

## 验收
- 插件执行受策略约束
