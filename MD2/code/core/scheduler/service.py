from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import uuid

from core.persistence import StateDB
from core.persistence import JsonlWAL

from protocols.workflow import RunRecord, RunStatus, now_unix

from .engine import ScheduleEngine


@dataclass
class SchedulerHealth:
    state: str
    due_checked: int
    triggered: int


class ScheduleOnlyScheduler:
    def __init__(self, state_db: StateDB, wal: JsonlWAL, engine: Optional[ScheduleEngine] = None):
        self._db = state_db
        self._wal = wal
        self._engine = engine or ScheduleEngine()

    def tick(self, now: Optional[int] = None, max_due: int = 100) -> SchedulerHealth:
        ts = int(now if now is not None else now_unix())
        schedules = self._db.list_due_schedules(now=ts, limit=max_due)
        triggered = 0
        for sch in schedules:
            decision = self._engine.compute(sch["policy_json"], ts, int(sch["next_fire_at"]))
            if sch["next_fire_at"] <= 0 and decision.next_fire_at > 0:
                self._db.set_schedule_next_fire_at(sch["id"], decision.next_fire_at)
                continue
            if not decision.due:
                continue
            run_id = f"run-{sch['id']}-{decision.fire_at}"
            trace_id = f"tr-{uuid.uuid4().hex}"
            run = RunRecord(
                run_id=run_id,
                trace_id=trace_id,
                workflow_id=str(sch["workflow_id"]),
                status=RunStatus.QUEUED,
                config_snapshot={},
                started_at=ts,
                ended_at=0,
            )
            self._db.upsert_run(run)
            self._db.add_schedule_trigger(schedule_id=str(sch["id"]), fire_at=int(decision.fire_at), run_id=run_id, status="triggered")
            self._db.set_schedule_next_fire_at(str(sch["id"]), int(decision.next_fire_at))
            self._wal.append("schedule_triggered", {"schedule_id": sch["id"], "run_id": run_id, "fire_at": int(decision.fire_at)})
            triggered += 1
        return SchedulerHealth(state="running", due_checked=len(schedules), triggered=triggered)

