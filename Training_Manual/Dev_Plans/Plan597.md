# Plan597 统一配置与环境加载

## 目标
统一配置入口，避免硬编码。

## 代码（`src/shared/config.py`）
```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v is not None and v != "" else default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    env: str
    data_root: Path
    db_path: Path
    event_dir: Path
    index_dir: Path
    audit_dir: Path
    review_dir: Path
    host: str
    port: int
    log_level: str

    @staticmethod
    def load() -> "Settings":
        data_root = Path(_env("OPENCLAW_DATA_ROOT", "data"))
        db_path = Path(_env("OPENCLAW_DB", str(data_root / "state" / "openclaw.db")))
        event_dir = Path(_env("OPENCLAW_EVENTS", str(data_root / "events")))
        index_dir = Path(_env("OPENCLAW_INDEX", str(data_root / "index")))
        audit_dir = Path(_env("OPENCLAW_AUDIT", str(data_root / "audit")))
        review_dir = Path(_env("OPENCLAW_REVIEW", str(data_root / "review")))

        for p in [data_root, db_path.parent, event_dir, index_dir, audit_dir, review_dir]:
            p.mkdir(parents=True, exist_ok=True)

        return Settings(
            env=_env("OPENCLAW_ENV", "dev"),
            data_root=data_root,
            db_path=db_path,
            event_dir=event_dir,
            index_dir=index_dir,
            audit_dir=audit_dir,
            review_dir=review_dir,
            host=_env("OPENCLAW_HOST", "0.0.0.0"),
            port=_env_int("OPENCLAW_PORT", 8080),
            log_level=_env("OPENCLAW_LOG_LEVEL", "INFO").upper(),
        )


settings = Settings.load()
```

## 验收
- `python -c "from src.shared.config import settings; print(settings.env)"`
