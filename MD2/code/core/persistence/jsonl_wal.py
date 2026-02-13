from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Optional

import json
import os
import threading


@dataclass
class WalRecord:
    ts: str
    type: str
    data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {"ts": self.ts, "type": self.type, "data": self.data}


class JsonlWAL:
    def __init__(self, wal_path: str):
        self._path = Path(wal_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append(self, record_type: str, data: Dict[str, Any]) -> bool:
        rec = WalRecord(ts=datetime.utcnow().isoformat(), type=str(record_type), data=data or {})
        line = json.dumps(rec.to_dict(), ensure_ascii=False)
        with self._lock:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
                os.fsync(f.fileno())
        return True

    def iter_records(self) -> Iterator[WalRecord]:
        if not self._path.exists():
            return iter(())
        def _iter() -> Iterator[WalRecord]:
            with self._path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        yield WalRecord(ts=str(obj.get("ts", "")), type=str(obj.get("type", "")), data=dict(obj.get("data") or {}))
                    except Exception:
                        continue
        return _iter()

