from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import json
import sqlite3
import uuid

from .state_store import StateStore


class SqliteStateStore(StateStore):
    def __init__(self, db_path: str):
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, version TEXT, value_json TEXT, updated_at TEXT)"
        )
        self._conn.commit()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        cur = self._conn.execute("SELECT version, value_json FROM state WHERE key = ?", (key,))
        row = cur.fetchone()
        if not row:
            return None
        version, value_json = row
        try:
            value = json.loads(value_json)
        except Exception:
            value = {}
        return {"key": key, "version": version, "value": value}

    def put(self, key: str, value: Dict[str, Any]) -> bool:
        version = uuid.uuid4().hex
        self._conn.execute(
            "INSERT OR REPLACE INTO state(key, version, value_json, updated_at) VALUES(?,?,?,?)",
            (key, version, json.dumps(value, ensure_ascii=False), datetime.utcnow().isoformat()),
        )
        self._conn.commit()
        return True

    def delete(self, key: str) -> bool:
        self._conn.execute("DELETE FROM state WHERE key = ?", (key,))
        self._conn.commit()
        return True

    def compare_and_swap(self, key: str, expected_version: Optional[str], value: Dict[str, Any]) -> bool:
        current = self.get(key)
        if current is None:
            if expected_version is not None:
                return False
            return self.put(key, value)
        if expected_version is None:
            return False
        if str(current.get("version")) != str(expected_version):
            return False
        return self.put(key, value)

