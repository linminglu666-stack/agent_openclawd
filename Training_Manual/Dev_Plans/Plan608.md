# Plan608 Flask BFF API

## 目标
建立统一 API 入口。

## 代码（`src/bff/app.py`）
```python
from __future__ import annotations

from flask import Flask, jsonify, request

from src.bff.security import require_role, write_audit
from src.bff.sse import Event, bus, sse_stream
from src.orchestrator.service import OrchestratorService
from src.scheduler.service import SchedulerService
from src.shared.config import settings
from src.shared.store import EventStore, StateDB

app = Flask(__name__)

event_store = EventStore(settings.event_dir)
state_db = StateDB(settings.db_path)
scheduler = SchedulerService(event_store=event_store, state_db=state_db)
orchestrator = OrchestratorService.with_default_worker(event_store=event_store, state_db=state_db)


@app.get("/health")
def health():
    return jsonify({"ok": True, "env": settings.env})


@app.get("/api/v1/runs")
def list_runs():
    return jsonify({"items": state_db.list_runs()})


@app.post("/api/v1/runs/trigger")
@require_role("editor")
def trigger_run():
    data = request.get_json(force=True, silent=True) or {}
    workflow_id = data.get("workflow_id", "default_workflow")
    version = data.get("version", "v1")

    run_id = scheduler.schedule_run(workflow_id=workflow_id, version=version)
    scheduler.mark_running(run_id, workflow_id=workflow_id, version=version)

    out = orchestrator.run_single_node(
        run_id=run_id,
        workflow_id=workflow_id,
        version=version,
        node_id="default_node",
        payload={"query": data.get("query", "")},
    )

    write_audit(settings.audit_dir, action="trigger_run", resource=run_id, status="ok", req=request)
    bus.publish(Event(type="run.finished", payload={"run_id": run_id, "ok": out["ok"]}))
    return jsonify({"run_id": run_id, "result": out})


@app.get("/api/v1/events")
def events():
    return sse_stream()


if __name__ == "__main__":
    app.run(host=settings.host, port=settings.port)
```

## 验收
- `/health` 返回 200
