from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncio
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocols.interfaces import IAuditSink
from utils.serializer import Serializer


@dataclass
class AuditRecord:
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"timestamp": self.timestamp.isoformat(), "event": self.event}


class InMemoryAuditSink(IAuditSink):
    def __init__(self, max_records: int = 10000, jsonl_path: Optional[str] = None):
        self._max_records = int(max_records)
        self._records: List[AuditRecord] = []
        self._lock = asyncio.Lock()
        self._jsonl_path = jsonl_path

    async def emit(self, event: Dict[str, Any]) -> bool:
        record = AuditRecord(event=event or {})
        async with self._lock:
            self._records.append(record)
            if len(self._records) > self._max_records:
                self._records = self._records[-self._max_records :]

        if self._jsonl_path:
            path = Path(self._jsonl_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            line = Serializer.to_json(record.to_dict()) + "\n"
            path.open("a", encoding="utf-8").write(line)

        return True

    async def list(self, limit: int = 100) -> List[Dict[str, Any]]:
        async with self._lock:
            return [r.to_dict() for r in self._records[-int(limit) :]]

