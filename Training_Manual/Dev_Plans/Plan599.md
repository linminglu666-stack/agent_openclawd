# Plan599 事件存储与状态仓储

## 目标
实现 append-only 事件写入 + SQLite 状态仓储。

## 代码（`src/shared/store.py`）
```python
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from threading import Lock
from typing import Any


class EventStore:
    """Append-only JSONL event store."""

    def __init__(self, event_dir: str | Path):
        self.event_dir = Path(event_dir)
        self.event_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def append(self, stream: str, event: str, payload: dict[str, Any]) -> None:
        line = {
            "ts": time.time(),
            "stream": stream,
            "event": event,
            "payload": payload,
        }
        p = self.event_dir / f"{stream}.jsonl"
        with self._lock:
            with p.open("a", encoding="utf-8") as f:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")


class StateDB:
    """SQLite state storage with basic upsert operations."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                version TEXT NOT NULL,
                status TEXT NOT NULL,
                schedule_id TEXT,
                metadata_json TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS node_runs (
                node_run_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                status TEXT NOT NULL,
                attempt INTEGER NOT NULL,
                metadata_json TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    @staticmethod
    def _to_json(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False)

    def upsert_run(self, run_id: str, workflow_id: str, version: str, status: str, schedule_id: str | None = None, metadata: dict[str, Any] | None = None) -> None:
        self.conn.execute(
            """
            INSERT INTO runs (run_id, workflow_id, version, status, schedule_id, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                workflow_id=excluded.workflow_id,
                version=excluded.version,
                status=excluded.status,
                schedule_id=excluded.schedule_id,
                metadata_json=excluded.metadata_json
            """,
            (run_id, workflow_id, version, status, schedule_id, self._to_json(metadata or {})),
        )
        self.conn.commit()

    def upsert_node_run(self, node_run_id: str, run_id: str, node_id: str, status: str, attempt: int = 1, metadata: dict[str, Any] | None = None) -> None:
        self.conn.execute(
            """
            INSERT INTO node_runs (node_run_id, run_id, node_id, status, attempt, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(node_run_id) DO UPDATE SET
                run_id=excluded.run_id,
                node_id=excluded.node_id,
                status=excluded.status,
                attempt=excluded.attempt,
                metadata_json=excluded.metadata_json
            """,
            (node_run_id, run_id, node_id, status, attempt, self._to_json(metadata or {})),
        )
        self.conn.commit()

    def list_runs(self) -> list[dict[str, Any]]:
        cur = self.conn.execute("SELECT run_id, workflow_id, version, status, schedule_id, metadata_json FROM runs ORDER BY rowid DESC")
        rows = []
        for row in cur.fetchall():
            rows.append(
                {
                    "run_id": row[0],
                    "workflow_id": row[1],
                    "version": row[2],
                    "status": row[3],
                    "schedule_id": row[4],
                    "metadata": json.loads(row[5]),
                }
            )
        return rows

    def close(self) -> None:
        self.conn.close()
```

## 验收
- 能写入 `data/events/*.jsonl`
- SQLite 中可查到 run 状态
