from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.persistence import StateDB, JsonlWAL
from protocols.workflow import now_unix


@dataclass
class RecoverySummary:
    reclaimed_leases: int
    timestamp: int

    def to_dict(self) -> Dict[str, Any]:
        return {"reclaimed_leases": int(self.reclaimed_leases), "timestamp": int(self.timestamp)}


def recover_runtime(state_db: StateDB, wal: Optional[JsonlWAL] = None) -> RecoverySummary:
    ts = now_unix()
    reclaimed = state_db.reclaim_expired_leases(now=ts, limit=500)
    summary = RecoverySummary(reclaimed_leases=int(reclaimed), timestamp=int(ts))
    if wal:
        wal.append("runtime_recovered", summary.to_dict())
    return summary

