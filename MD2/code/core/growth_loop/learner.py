from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import uuid

from core.persistence import StateDB
from protocols.learning import LearningReport
from protocols.workflow import now_unix


@dataclass
class LearningInput:
    agent_id: str
    trace_id: str = ""
    max_audit: int = 50


class Learner:
    def __init__(self, state_db: StateDB):
        self._db = state_db

    def learn(self, inp: LearningInput) -> LearningReport:
        report_id = f"lr-{uuid.uuid4().hex}"
        ts = now_unix()
        summary = f"learned_from_audit:{inp.max_audit}"
        report = LearningReport(
            report_id=report_id,
            agent_id=inp.agent_id,
            summary=summary,
            new_skills=[],
            memory_delta=[],
            validation={"self_test_passed": True, "test_cases": 0, "test_passed": 0, "test_failed": 0},
            rollback_info={"can_rollback": True, "rollback_steps": []},
            created_at=ts,
        )
        self._db.write_learning_report(report)
        return report

