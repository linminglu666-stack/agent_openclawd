from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncio
import uuid


@dataclass
class CognitiveDebtItem:
    debt_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    debt_type: str = ""
    score: float = 0.0
    trace_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "debt_id": self.debt_id,
            "debt_type": self.debt_type,
            "score": self.score,
            "trace_id": self.trace_id,
            "created_at": self.created_at.isoformat(),
            "details": self.details,
        }


class CognitiveDebtLedger:
    def __init__(self, max_items: int = 5000):
        self._max_items = int(max_items)
        self._items: List[CognitiveDebtItem] = []
        self._lock = asyncio.Lock()

    async def add(self, item: CognitiveDebtItem) -> str:
        async with self._lock:
            self._items.append(item)
            if len(self._items) > self._max_items:
                self._items = self._items[-self._max_items :]
        return item.debt_id

    async def list(self, limit: int = 100) -> List[Dict[str, Any]]:
        async with self._lock:
            return [i.to_dict() for i in self._items[-int(limit) :]]

    async def summarize(self) -> Dict[str, Any]:
        async with self._lock:
            items = list(self._items)
        by_type: Dict[str, float] = {}
        for it in items:
            by_type[it.debt_type] = by_type.get(it.debt_type, 0.0) + float(it.score)
        return {"count": len(items), "by_type": by_type}

