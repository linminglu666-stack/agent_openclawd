from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.persistence import StateDB
from core.persistence import JsonlWAL
from protocols.workflow import now_unix

from .idle_detector import IdleDetector
from .learner import Learner, LearningInput


@dataclass
class GrowthLoopHealth:
    state: str
    idle_agents: int
    reports_written: int


class GrowthLoop:
    def __init__(self, state_db: StateDB, wal: JsonlWAL):
        self._db = state_db
        self._wal = wal
        self._idle = IdleDetector(state_db=state_db)
        self._learner = Learner(state_db=state_db)

    def tick(self, now: Optional[int] = None) -> GrowthLoopHealth:
        ts = int(now if now is not None else now_unix())
        idle = self._idle.detect(now=ts)
        written = 0
        for sig in idle:
            report = self._learner.learn(LearningInput(agent_id=sig.agent_id))
            self._wal.append("learning.report", {"report_id": report.report_id, "agent_id": report.agent_id})
            written += 1
        return GrowthLoopHealth(state="running", idle_agents=len(idle), reports_written=written)

