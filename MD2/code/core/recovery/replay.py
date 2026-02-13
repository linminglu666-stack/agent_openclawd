from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from core.persistence.jsonl_wal import JsonlWAL, WalRecord


@dataclass
class ReplayStats:
    total: int
    applied: int
    skipped: int


class WalReplayer:
    def __init__(self, wal: JsonlWAL):
        self._wal = wal
        self._handlers: Dict[str, Callable[[WalRecord], bool]] = {}

    def register(self, record_type: str, handler: Callable[[WalRecord], bool]) -> bool:
        self._handlers[str(record_type)] = handler
        return True

    def replay(self) -> ReplayStats:
        total = 0
        applied = 0
        skipped = 0
        for rec in self._wal.iter_records():
            total += 1
            handler = self._handlers.get(rec.type)
            if not handler:
                skipped += 1
                continue
            ok = handler(rec)
            if ok:
                applied += 1
            else:
                skipped += 1
        return ReplayStats(total=total, applied=applied, skipped=skipped)

