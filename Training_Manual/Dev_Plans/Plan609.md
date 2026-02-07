# Plan609 RBAC + Audit 中间件

## 目标
写操作统一鉴权和审计。

## 代码（`src/bff/security.py`）
```python
from __future__ import annotations

import json
import time
from functools import wraps
from pathlib import Path
from typing import Callable

from flask import Request, jsonify, request


ROLE_ORDER = {"viewer": 0, "operator": 1, "editor": 2, "admin": 3}


def _role_level(role: str) -> int:
    return ROLE_ORDER.get(role, -1)


def require_role(min_role: str) -> Callable:
    min_level = _role_level(min_role)

    def deco(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            role = request.headers.get("X-Role", "viewer")
            if _role_level(role) < min_level:
                return jsonify({"error": "forbidden", "required": min_role}), 403
            return fn(*args, **kwargs)

        return wrapper

    return deco


def write_audit(audit_dir: str, action: str, resource: str, status: str, req: Request | None = None) -> None:
    p = Path(audit_dir)
    p.mkdir(parents=True, exist_ok=True)
    line = {
        "ts": time.time(),
        "action": action,
        "resource": resource,
        "status": status,
        "role": req.headers.get("X-Role") if req else None,
        "path": req.path if req else None,
        "method": req.method if req else None,
    }
    with (p / "audit.log").open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
```

## 验收
- 非授权角色访问被拒绝
