from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.persistence import StateDB
from protocols.workflow import now_unix


@dataclass
class IdleSignal:
    agent_id: str
    last_seen: int
    queue_depth: int
    metrics: Dict[str, Any]


class IdleDetector:
    def __init__(self, state_db: StateDB, idle_timeout_sec: int = 60, max_queue_depth: int = 0):
        self._db = state_db
        self._idle_timeout = int(idle_timeout_sec)
        self._max_queue_depth = int(max_queue_depth)

    def detect(self, now: Optional[int] = None, limit: int = 50) -> List[IdleSignal]:
        ts = int(now if now is not None else now_unix())
        idle_before = ts - self._idle_timeout
        agents = self._db.list_idle_agents(idle_before=idle_before, max_queue_depth=self._max_queue_depth, limit=limit)
        out: List[IdleSignal] = []
        for a in agents:
            out.append(
                IdleSignal(
                    agent_id=str(a.get("agent_id")),
                    last_seen=int(a.get("last_seen") or 0),
                    queue_depth=int(a.get("queue_depth") or 0),
                    metrics=dict(a.get("metrics") or {}),
                )
            )
        return out

