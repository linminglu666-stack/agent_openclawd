from __future__ import annotations

import asyncio
import os
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.runtime import get_runtime_paths, build_runtime_container
from core.scheduler import ScheduleOnlyScheduler
from core.orchestrator import RunEngine
from protocols.workflows import WorkflowDefinition
from services.runner_service import RunnerService
from protocols.workflow import now_unix


async def _run_runner_once() -> None:
    svc = RunnerService()
    await svc.initialize()
    await svc.tick()
    await svc.shutdown()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="md2-e2e-") as td:
        state_dir = os.path.join(td, "state")
        log_dir = os.path.join(td, "log")
        runtime_dir = os.path.join(td, "run")
        os.environ["OPENCLAW_STATE_DIR"] = state_dir
        os.environ["OPENCLAW_LOG_DIR"] = log_dir
        os.environ["OPENCLAW_RUNTIME_DIR"] = runtime_dir

        rt = build_runtime_container(paths=get_runtime_paths(state_dir=state_dir, log_dir=log_dir, runtime_dir=runtime_dir))

        wf = WorkflowDefinition(
            workflow_id="wf-demo",
            version="v1",
            dag={
                "dag_id": "wf-demo",
                "nodes": [
                    {"node_id": "n1", "type": "task", "task_type": "default", "task_data": {"input": {"hello": "world"}}, "priority": 1},
                ],
                "edges": [],
            },
            metadata={},
        )
        rt.state_db.upsert_workflow(wf)

        sch = rt.state_db.create_schedule(workflow_id="wf-demo", version="v1", enabled=True, policy={"type": "interval", "every_sec": 60})
        now = now_unix()
        rt.state_db.set_schedule_next_fire_at(sch.id, now)

        ScheduleOnlyScheduler(state_db=rt.state_db, wal=rt.wal).tick(now=now)
        RunEngine(state_db=rt.state_db, wal=rt.wal).tick(now=now)
        asyncio.run(_run_runner_once())
        RunEngine(state_db=rt.state_db, wal=rt.wal).tick(now=now_unix())

        runs, _ = rt.state_db.list_runs(workflow_id="wf-demo", limit=10, cursor="")
        if not runs:
            raise SystemExit("no_runs")
        run = runs[0]
        ev = rt.state_db.list_evidence(trace_id=run.trace_id, limit=50)
        au = rt.state_db.list_audit_logs(trace_id=run.trace_id, limit=50)
        if not ev:
            raise SystemExit("no_evidence")
        if not au:
            raise SystemExit("no_audit")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
