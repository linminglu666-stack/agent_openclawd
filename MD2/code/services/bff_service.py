from __future__ import annotations

from typing import Any, Dict

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import asyncio
import collections
import json
import mimetypes
import os
import subprocess
import sys
import threading
import time
import uuid

from core.runtime import build_runtime_container
from core.skills.registry import SkillsRegistry
from protocols.workflow import RunRecord, RunStatus, now_unix
from protocols.trace import TraceContext
from core.governance.auth import InMemoryAuthProvider
from core.governance.rbac import InMemoryAuthorizer
from core.governance.policy_engine import SimplePolicyEngine, PolicyRule
from core.governance.redaction import SimpleRedactor
from core.risk.scorer import RiskScorer
from protocols.approvals import ApprovalDecision, ApprovalStatus
from protocols.workflows import WorkflowDefinition
from services.service_base import ServiceBase, ServiceConfig
from utils import (
    validate_workflow_create,
    validate_schedule_create,
    validate_schedule_update,
    validate_run_trigger,
    validate_work_item_enqueue,
    validate_work_item_claim,
    validate_work_item_ack,
    validate_approval_decision,
    validate_system_control,
)


class _ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


@dataclass
class _BffConfig:
    host: str
    port: int


@dataclass
class _Deps:
    auth: InMemoryAuthProvider
    authorizer: InMemoryAuthorizer
    policy: SimplePolicyEngine
    redactor: SimpleRedactor
    risk: RiskScorer
    system: SystemManager


class SystemManager:
    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._logs = collections.deque(maxlen=2000)
        self._lock = threading.Lock()
        self._monitoring = False
    
    def start(self):
        with self._lock:
            if self._proc and self._proc.poll() is None:
                return False # Already running
            
            # Assume running from workspace root
            cmd = [sys.executable, "code/openclawd.py"]
            env = os.environ.copy()
            cwd = os.getcwd()
            if "PYTHONPATH" not in env:
                env["PYTHONPATH"] = cwd
            
            try:
                self._proc = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT,
                    cwd=cwd,
                    env=env,
                    text=True,
                    bufsize=1
                )
                self._monitoring = True
                threading.Thread(target=self._monitor_logs, daemon=True).start()
                self._log_internal("System started.")
                return True
            except Exception as e:
                self._log_internal(f"Failed to start: {e}")
                return False

    def stop(self):
        with self._lock:
            if self._proc:
                self._log_internal("Stopping system...")
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                self._proc = None
                self._log_internal("System stopped.")
            self._monitoring = False
            return True

    def restart(self):
        self.stop()
        return self.start()
        
    def status(self) -> str:
        if self._proc and self._proc.poll() is None:
            return "running"
        return "stopped"

    def get_logs(self) -> list[str]:
        return list(self._logs)

    def _monitor_logs(self):
        proc = self._proc
        if not proc or not proc.stdout:
            return
        
        try:
            for line in proc.stdout:
                self._logs.append(line)
        except Exception:
            pass
        finally:
            if proc.poll() is not None:
                self._log_internal(f"System exited with code {proc.returncode}")

    def _log_internal(self, msg: str):
        self._logs.append(f"[BFF] {msg}\n")


def _run_async(coro):
    return asyncio.run(coro)


class _Handler(BaseHTTPRequestHandler):
    container = None
    deps: _Deps | None = None

    def do_GET(self):
        if self.path == "/healthz":
            self._json(200, self._health())
            return
        if self.path == "/readyz":
            self._json(200, self._ready())
            return
        if self.path == "/skills":
            self._json(200, self._skills())
            return
        if self.path == "/config/current":
            self._json(200, self._config_current())
            return
        if self.path.startswith("/v1/schedules"):
            deny = self._guard(action="read", resource="schedule")
            if deny:
                self._json(*deny)
                return
            self._json(*self._schedules_get())
            return
        if self.path.startswith("/v1/runs"):
            deny = self._guard(action="read", resource="run")
            if deny:
                self._json(*deny)
                return
            self._json(*self._runs_get())
            return
        if self.path.startswith("/v1/approvals"):
            deny = self._guard(action="read", resource="approval")
            if deny:
                self._json(*deny)
                return
            self._json(*self._approvals_get())
            return
        if self.path.startswith("/v1/workflows"):
            deny = self._guard(action="read", resource="workflow")
            if deny:
                self._json(*deny)
                return
            self._json(*self._workflows_get())
            return
        if self.path.startswith("/v1/evidence"):
            deny = self._guard(action="read", resource="evidence")
            if deny:
                self._json(*deny)
                return
            self._json(*self._evidence_get())
            return
        if self.path.startswith("/v1/audit"):
            deny = self._guard(action="read", resource="audit")
            if deny:
                self._json(*deny)
                return
            self._json(*self._audit_get())
            return
        if self.path.startswith("/v1/agents"):
            deny = self._guard(action="read", resource="infrastructure")
            if deny:
                self._json(*deny)
                return
            self._json(*self._agents_get())
            return
        if self.path.startswith("/v1/work-items"):
            # Check for GET (List) vs POST/ACK (Write) - actually do_POST handles writes.
            # This is do_GET.
            deny = self._guard(action="read", resource="work_item")
            if deny:
                self._json(*deny)
                return
            self._json(*self._work_items_get())
            return
        if self.path.startswith("/v1/learning/reports"):
            deny = self._guard(action="read", resource="learning")
            if deny:
                self._json(*deny)
                return
            self._json(*self._learning_reports_get())
            return
        if self.path == "/v1/events/stream":
            # Public/Token check inside stream or loose for now?
            # Let's do basic check but not strictly RBAC for stream simplicity in this MVP
            self._events_stream()
            return
        
        if self.path.startswith("/v1/governance/entropy"):
            deny = self._guard(action="read", resource="governance")
            if deny:
                self._json(*deny)
                return
            
            if self.path.endswith("/history"):
                self._json(*self._entropy_history_get())
                return
            if self.path.endswith("/config"):
                self._json(*self._entropy_config_get())
                return
            
            # Default to metrics
            self._json(*self._entropy_metrics_get())
            return

        if self.path == "/v1/system/status":
            # Guard?
            self._json(200, {"ok": True, "status": self.deps.system.status()})
            return
        if self.path == "/v1/system/logs":
            self._json(200, {"ok": True, "logs": self.deps.system.get_logs()})
            return

        # Fallback to static files
        self._static_file(self.path)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()


    def do_POST(self):
        if self.path == "/v1/auth/login":
            self._json(*self._auth_login())
            return
        if self.path == "/v1/schedules":
            deny = self._guard(action="write", resource="schedule", risk_ctx={"requires_write": True})
            if deny:
                self._json(*deny)
                return
            self._json(*self._schedules_post())
            return
        if self.path == "/v1/runs":
            deny = self._guard(action="write", resource="run", risk_ctx={"requires_write": True})
            if deny:
                self._json(*deny)
                return
            self._json(*self._runs_post())
            return
        if self.path == "/v1/work-items":
            deny = self._guard(action="write", resource="work_item", risk_ctx={"requires_write": True})
            if deny:
                self._json(*deny)
                return
            self._json(*self._work_items_post())
            return
        if self.path == "/v1/work-items/claim":
            deny = self._guard(action="write", resource="work_item", risk_ctx={"requires_write": True})
            if deny:
                self._json(*deny)
                return
            self._json(*self._work_items_claim())
            return
        if self.path == "/v1/work-items/ack":
            deny = self._guard(action="write", resource="work_item", risk_ctx={"requires_write": True})
            if deny:
                self._json(*deny)
                return
            self._json(*self._work_items_ack())
            return
        if self.path == "/v1/workflows":
            deny = self._guard(action="write", resource="workflow", risk_ctx={"requires_write": True})
            if deny:
                self._json(*deny)
                return
            self._json(*self._workflows_post())
            return
        if self.path.startswith("/v1/approvals/") and self.path.endswith("/decision"):
            deny = self._guard(action="write", resource="approval", risk_ctx={"requires_write": True})
            if deny:
                self._json(*deny)
                return
            self._json(*self._approvals_decide())
            return

        if self.path == "/v1/system/control":
            deny = self._guard(action="write", resource="system")
            if deny:
                self._json(*deny)
                return
            
            body = self._read_json()
            invalid = self._validate_body(body, validate_system_control)
            if invalid:
                self._json(*invalid)
                return
            action = body.get("action")
            if action == "start":
                ok = self.deps.system.start()
            elif action == "stop":
                ok = self.deps.system.stop()
            elif action == "restart":
                ok = self.deps.system.restart()
            else:
                self._json(400, {"ok": False, "error": "invalid_action"})
                return
            
            self._json(200, {"ok": ok, "status": self.deps.system.status()})
            return

        self._json(404, {"error": "not_found"})

    def do_PATCH(self):
        if self.path.startswith("/v1/schedules/"):
            deny = self._guard(action="write", resource="schedule", risk_ctx={"requires_write": True})
            if deny:
                self._json(*deny)
                return
            self._json(*self._schedules_patch())
            return
        self._json(404, {"error": "not_found"})

    def _agents_get(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        limit = int(self._query().get("limit", "100") or 100)
        agents = rt.state_db.list_all_agents(limit=limit)
        return 200, {"ok": True, "agents": agents}

    def _work_items_get(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        status = str(self._query().get("status", "")).strip()
        limit = int(self._query().get("limit", "50") or 50)
        items = rt.state_db.list_work_items(status=status, limit=limit)
        return 200, {"ok": True, "work_items": items}

    def _learning_reports_get(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        agent_id = str(self._query().get("agent_id", "")).strip()
        limit = int(self._query().get("limit", "50") or 50)
        reports = rt.state_db.list_learning_reports(agent_id=agent_id, limit=limit)
        return 200, {"ok": True, "reports": reports}

    def _events_stream(self):
        # SSE Handler
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        rt = self.container
        
        # Tracking State
        last_runs_ts = 0
        last_approval_id = ""
        last_queue_ts = 0

        try:
            while True:
                now = now_unix()
                
                # 1. Heartbeat
                self.wfile.write(f"event: heartbeat\ndata: {now}\n\n".encode("utf-8"))
                
                try:
                    # 2. Runs Update Check (by checking count or max updated_at if DB supported it)
                    # For MVP, we check count of active runs or just trigger update periodically?
                    # Let's check if any run was updated recently?
                    # SQLite doesn't give us "max updated_at" easily without index/scan.
                    # We'll rely on "polling signals" - checking counts or specific triggers.
                    
                    # Approvals
                    pending_approvals = rt.state_db.list_approvals(status="pending", limit=1)
                    latest_approval_id = str(pending_approvals[0]["approval_id"]) if pending_approvals else ""
                    if latest_approval_id != last_approval_id:
                        self.wfile.write(f"event: update:approvals\ndata: {now}\n\n".encode("utf-8"))
                        last_approval_id = latest_approval_id

                    # Infrastructure (Agents)
                    # Check if any agent heartbeat is recent?
                    # Let's just send a generic "refresh" signal every 5 seconds for all views
                    # This is "Short Polling via SSE" but efficient enough for <50 clients.
                    
                    # Actually, we can check DB.
                    # list_runs(limit=1) returns latest.
                    runs, _ = rt.state_db.list_runs(limit=1)
                    if runs:
                        latest_run = runs[0]
                        if latest_run.started_at > last_runs_ts:
                            self.wfile.write(f"event: update:runs\ndata: {now}\n\n".encode("utf-8"))
                            last_runs_ts = latest_run.started_at

                    # Queue (Work Items)
                    # Check latest work item
                    latest_wi = rt.state_db.list_work_items(limit=1)
                    if latest_wi:
                        ts = int(latest_wi[0].get("updated_at", 0))
                        if ts > last_queue_ts:
                            self.wfile.write(f"event: update:queue\ndata: {now}\n\n".encode("utf-8"))
                            last_queue_ts = ts

                    # Dashboard Stats
                    n_approvals = len(rt.state_db.list_approvals(status="pending", limit=100))
                    data = json.dumps({"pending_approvals": n_approvals, "server_time": now})
                    self.wfile.write(f"event: stats\ndata: {data}\n\n".encode("utf-8"))
                    
                    # Force refresh signals for other views periodically (every 5s)
                    if int(now) % 5 == 0:
                        self.wfile.write(f"event: update:agents\ndata: {now}\n\n".encode("utf-8"))
                        self.wfile.write(f"event: update:approvals\ndata: {now}\n\n".encode("utf-8"))
                        self.wfile.write(f"event: update:system\ndata: {now}\n\n".encode("utf-8"))
                        self.wfile.write(f"event: update:runs\ndata: {now}\n\n".encode("utf-8"))
                        self.wfile.write(f"event: update:queue\ndata: {now}\n\n".encode("utf-8"))
                        self.wfile.write(f"event: update:dashboard\ndata: {now}\n\n".encode("utf-8"))
                        self.wfile.write(f"event: update:schedules\ndata: {now}\n\n".encode("utf-8"))
                        self.wfile.write(f"event: update:workflows\ndata: {now}\n\n".encode("utf-8"))
                        self.wfile.write(f"event: update:skills\ndata: {now}\n\n".encode("utf-8"))
                        self.wfile.write(f"event: update:learning\ndata: {now}\n\n".encode("utf-8"))
                        self.wfile.write(f"event: update:evidence\ndata: {now}\n\n".encode("utf-8"))
                        self.wfile.write(f"event: update:audit\ndata: {now}\n\n".encode("utf-8"))

                except Exception:
                    pass

                self.wfile.flush()
                time.sleep(2)
        except (BrokenPipeError, ConnectionResetError):
            pass # Client disconnected

    def _static_file(self, path: str):
        # Determine web root
        rt = self.container
        md2_dir = os.environ.get("OPENCLAW_MD2_DIR") or str(rt.paths.state_dir.parent)
        web_root = os.path.join(md2_dir, "web")
        
        # Clean path
        if path == "/":
            path = "/index.html"
        path = path.lstrip("/")
        
        # Security check: prevent directory traversal
        full_path = os.path.abspath(os.path.join(web_root, path))
        if not full_path.startswith(os.path.abspath(web_root)):
            self._json(403, {"error": "forbidden"})
            return

        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            self._json(404, {"error": "not_found", "path": path})
            return

        # Serve file
        mime_type, _ = mimetypes.guess_type(full_path)
        if not mime_type:
            mime_type = "application/octet-stream"
            
        try:
            with open(full_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            # Add CORS headers for static files too if needed
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._json(500, {"error": "internal_error", "details": str(e)})

    def log_message(self, format, *args):
        return

    def _health(self) -> Dict[str, Any]:
        rt = self.container
        sched = rt.state_store.get("scheduler/health") or {}
        return {"ok": True, "scheduler": sched.get("value")}

    def _ready(self) -> Dict[str, Any]:
        rt = self.container
        current = rt.config_store.load_current()
        return {"ok": True, "has_config": current is not None}

    def _skills(self) -> Dict[str, Any]:
        rt = self.container
        md2_dir = os.environ.get("OPENCLAW_MD2_DIR") or str(rt.paths.state_dir.parent)
        reg_path = os.path.join(md2_dir, "skills", "registry.json")
        if not os.path.exists(reg_path):
            return {"ok": False, "error": "registry_not_found", "path": reg_path}
        reg = SkillsRegistry.load(reg_path)
        data = reg.to_dict()
        data["ok"] = True
        return data

    def _config_current(self) -> Dict[str, Any]:
        rt = self.container
        current = rt.config_store.load_current()
        return {"ok": True, "current": current.__dict__ if current else None}

    def _auth_login(self) -> tuple[int, Dict[str, Any]]:
        deps = self.deps
        if not deps:
            return 500, {"ok": False, "error": "deps_not_ready"}
        body = self._read_json()
        user_id = str(body.get("user_id", "")).strip()
        roles = list(body.get("roles") or [])
        if not user_id:
            return 400, {"ok": False, "error": "missing_user_id"}
        auth = deps.auth
        token = _run_async(auth.authenticate({"user_id": user_id, "roles": roles}))
        if not token:
            return 401, {"ok": False, "error": "auth_failed"}
        for r in roles:
            _run_async(deps.authorizer.assign_role(user_id, str(r)))
        return 200, {"ok": True, "token": token}

    def _approvals_get(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        if self.path == "/v1/approvals":
            status = str(self._query().get("status", "")).strip()
            items = rt.state_db.list_approvals(status=status, limit=int(self._query().get("limit", "50") or 50))
            return 200, {"ok": True, "approvals": items}
        if self.path.startswith("/v1/approvals/"):
            approval_id = self.path.split("/", 3)[3]
            obj = rt.state_db.get_approval(approval_id)
            return 200, {"ok": True, "approval": obj}
        return 404, {"ok": False, "error": "not_found"}

    def _approvals_decide(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        parts = self.path.split("/")
        approval_id = parts[3] if len(parts) > 3 else ""
        body = self._read_json()
        invalid = self._validate_body(body, validate_approval_decision)
        if invalid:
            return invalid
        decision = str(body.get("decision", "")).strip()
        approver = str(body.get("approver", "")).strip() or "human"
        if decision not in {"approved", "rejected"}:
            return 400, {"ok": False, "error": "invalid_decision"}
        new_status = ApprovalStatus.APPROVED if decision == "approved" else ApprovalStatus.REJECTED
        dec = ApprovalDecision(approval_id=approval_id, decision=decision, approver=approver, reason=str(body.get("reason", "")), conditions=list(body.get("conditions") or []))
        ok = rt.state_db.decide_approval(approval_id=approval_id, decision=dec, new_status=new_status)
        if not ok:
            return 409, {"ok": False, "error": "approval_not_pending"}
        return 200, {"ok": True, "updated": True}

    def _workflows_post(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        body = self._read_json()
        invalid = self._validate_body(body, validate_workflow_create)
        if invalid:
            return invalid
        workflow_id = str(body.get("workflow_id", "")).strip()
        version = str(body.get("version", "")).strip() or "v1"
        dag = dict(body.get("dag") or {})
        metadata = dict(body.get("metadata") or {})
        if not workflow_id:
            return 400, {"ok": False, "error": "missing_workflow_id"}
        wf = WorkflowDefinition(workflow_id=workflow_id, version=version, dag=dag, metadata=metadata)
        rt.state_db.upsert_workflow(wf)
        return 200, {"ok": True, "workflow": {"workflow_id": wf.workflow_id, "version": wf.version, "created_at": wf.created_at}}

    def _workflows_get(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        if self.path == "/v1/workflows":
            items = rt.state_db.list_workflows(limit=int(self._query().get("limit", "50") or 50))
            return 200, {"ok": True, "workflows": items}
        if self.path.startswith("/v1/workflows/"):
            workflow_id = self.path.split("/", 3)[3]
            version = str(self._query().get("version", "")).strip()
            wf = rt.state_db.get_workflow(workflow_id, version) if version else None
            if not wf:
                wf2 = rt.state_db.get_latest_workflow(workflow_id)
                return 200, {"ok": True, "workflow": wf2}
            return 200, {"ok": True, "workflow": {"workflow_id": wf.workflow_id, "version": wf.version, "dag": wf.dag, "metadata": wf.metadata, "created_at": wf.created_at}}
        return 404, {"ok": False, "error": "not_found"}

    def _evidence_get(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        trace_id = str(self._query().get("trace_id", "")).strip()
        if not trace_id:
            return 400, {"ok": False, "error": "missing_trace_id"}
        items = rt.state_db.list_evidence(trace_id=trace_id, limit=int(self._query().get("limit", "100") or 100))
        return 200, {"ok": True, "evidence": items}

    def _audit_get(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        trace_id = str(self._query().get("trace_id", "")).strip()
        items = rt.state_db.list_audit_logs(trace_id=trace_id, limit=int(self._query().get("limit", "200") or 200))
        return 200, {"ok": True, "audit": items}

    def _entropy_metrics_get(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        metrics = rt.entropy.compute_metrics()
        return 200, {"ok": True, "metrics": self._serialize_metrics(metrics)}

    def _entropy_history_get(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        # Trigger a snapshot if history is empty for demo purposes? 
        # Or just return what is there.
        # Let's ensure at least one snapshot exists if empty
        if not rt.entropy.history:
            rt.entropy.snapshot_metrics()
            
        history = rt.entropy.history
        data = [
            {
                "timestamp": h.timestamp.isoformat(),
                "metrics": self._serialize_metrics(h.metrics)
            }
            for h in history
        ]
        return 200, {"ok": True, "history": data}

    def _entropy_config_get(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        config = rt.entropy.config
        return 200, {"ok": True, "config": config.__dict__}

    def _serialize_metrics(self, metrics) -> Dict[str, Any]:
        d = dict(metrics.__dict__)
        if "by_category" in d:
            # Convert Enum keys to strings
            d["by_category"] = {k.value if hasattr(k, "value") else str(k): v for k, v in d["by_category"].items()}
        return d

    def _schedule_view(self, sch) -> Dict[str, Any] | None:
        if not sch:
            return None
        data = dict(sch.__dict__)
        data["schedule_id"] = sch.id
        data["policy"] = data.get("policy_json")
        return data

    def _schedules_post(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        body = self._read_json()
        invalid = self._validate_body(body, validate_schedule_create)
        if invalid:
            return invalid
        workflow_id = str(body.get("workflow_id", "")).strip()
        version = str(body.get("version", "")).strip() or "v1"
        enabled = bool(body.get("enabled", True))
        policy = dict(body.get("policy") or {})
        if not workflow_id:
            return 400, {"ok": False, "error": "missing_workflow_id"}
        try:
            sch = rt.state_db.create_schedule(workflow_id=workflow_id, version=version, enabled=enabled, policy=policy)
            return 200, {"ok": True, "schedule": self._schedule_view(sch)}
        except Exception as e:
            return 400, {"ok": False, "error": str(e)}

    def _schedules_get(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        if self.path == "/v1/schedules":
            workflow_id = str(self._query().get("workflow_id", "")).strip()
            limit = int(self._query().get("limit", "50") or 50)
            cursor = str(self._query().get("cursor", "")).strip()
            items, next_cursor = rt.state_db.list_schedules(workflow_id=workflow_id, limit=limit, cursor=cursor)
            return 200, {"ok": True, "schedules": [self._schedule_view(s) for s in items], "next_cursor": next_cursor}
        if self.path.startswith("/v1/schedules/"):
            schedule_id = self.path.split("/", 3)[3]
            sch = rt.state_db.get_schedule(schedule_id)
            return 200, {"ok": True, "schedule": self._schedule_view(sch)}
        return 404, {"ok": False, "error": "not_found"}

    def _schedules_patch(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        schedule_id = self.path.split("/", 3)[3]
        body = self._read_json()
        invalid = self._validate_body(body, validate_schedule_update)
        if invalid:
            return invalid
        enabled = body.get("enabled")
        policy = body.get("policy")
        if enabled is None and policy is None:
            return 400, {"ok": False, "error": "missing_update_fields"}
        try:
            sch = rt.state_db.update_schedule(schedule_id=schedule_id, enabled=enabled, policy=policy)
        except Exception as e:
            return 400, {"ok": False, "error": str(e)}
        if not sch:
            return 404, {"ok": False, "error": "not_found"}
        return 200, {"ok": True, "schedule": self._schedule_view(sch)}

    def _runs_post(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        body = self._read_json()
        invalid = self._validate_body(body, validate_run_trigger)
        if invalid:
            return invalid
        workflow_id = str(body.get("workflow_id", "")).strip()
        if not workflow_id:
            return 400, {"ok": False, "error": "missing_workflow_id"}
        run_id = str(body.get("run_id", "")).strip() or f"run-{uuid.uuid4().hex}"
        trace_id = str(body.get("trace_id", "")).strip() or f"tr-{uuid.uuid4().hex}"
        snapshot = dict(body.get("config_snapshot") or {})
        now = now_unix()
        run = RunRecord(run_id=run_id, trace_id=trace_id, workflow_id=workflow_id, status=RunStatus.PENDING, config_snapshot=snapshot, started_at=now, ended_at=0)
        rt.state_db.upsert_run(run)
        return 200, {"ok": True, "run": {"run_id": run.run_id, "trace_id": run.trace_id, "workflow_id": run.workflow_id, "status": run.status.value, "config_snapshot": run.config_snapshot, "started_at": run.started_at, "ended_at": run.ended_at}}

    def _runs_get(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        if self.path == "/v1/runs":
            workflow_id = str(self._query().get("workflow_id", "")).strip()
            limit = int(self._query().get("limit", "50") or 50)
            cursor = str(self._query().get("cursor", "")).strip()
            runs, next_cursor = rt.state_db.list_runs(workflow_id=workflow_id, limit=limit, cursor=cursor)
            return 200, {"ok": True, "runs": [r.__dict__ | {"status": r.status.value} for r in runs], "next_cursor": next_cursor}
        if self.path.startswith("/v1/runs/"):
            run_id = self.path.split("/", 3)[3]
            run = rt.state_db.get_run(run_id)
            nodes = rt.state_db.list_node_runs(run_id) if run else []
            return 200, {"ok": True, "run": (run.__dict__ | {"status": run.status.value}) if run else None, "nodes": [n.__dict__ | {"status": n.status.value} for n in nodes]}
        return 404, {"ok": False, "error": "not_found"}

    def _work_items_post(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        body = self._read_json()
        invalid = self._validate_body(body, validate_work_item_enqueue)
        if invalid:
            return invalid
        task_id = str(body.get("task_id", "")).strip()
        if not task_id:
            return 400, {"ok": False, "error": "missing_task_id"}
        priority = int(body.get("priority", 0) or 0)
        payload = dict(body.get("payload") or {})
        idem = str(body.get("idempotency_key", "")).strip()
        try:
            wi = rt.state_db.enqueue_work_item(task_id=task_id, priority=priority, payload=payload, idempotency_key=idem)
            return 200, {"ok": True, "work_item": wi.__dict__ | {"status": wi.status.value}}
        except Exception as e:
            return 409, {"ok": False, "error": str(e)}

    def _work_items_claim(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        body = self._read_json()
        invalid = self._validate_body(body, validate_work_item_claim)
        if invalid:
            return invalid
        agent_id = str(body.get("agent_id", "")).strip()
        if not agent_id:
            return 400, {"ok": False, "error": "missing_agent_id"}
        max_priority = int(body.get("max_priority", 10) or 10)
        lease_ttl_sec = int(body.get("lease_ttl_sec", 60) or 60)
        wi = rt.state_db.claim_work_item(agent_id=agent_id, max_priority=max_priority, lease_ttl_sec=lease_ttl_sec)
        return 200, {"ok": True, "work_item": (wi.__dict__ | {"status": wi.status.value}) if wi else None}

    def _work_items_ack(self) -> tuple[int, Dict[str, Any]]:
        rt = self.container
        body = self._read_json()
        invalid = self._validate_body(body, validate_work_item_ack)
        if invalid:
            return invalid
        task_id = str(body.get("task_id", "")).strip()
        agent_id = str(body.get("agent_id", "")).strip()
        ok = bool(body.get("ok", False))
        if not task_id or not agent_id:
            return 400, {"ok": False, "error": "missing_task_or_agent"}
        updated = rt.state_db.ack_work_item(task_id=task_id, agent_id=agent_id, ok=ok)
        if not updated:
            return 409, {"ok": False, "error": "work_item_not_updatable"}
        return 200, {"ok": True, "updated": True}

    def _guard(self, action: str, resource: str, risk_ctx: Dict[str, Any] | None = None) -> tuple[int, Dict[str, Any]] | None:
        deps = self.deps
        rt = self.container
        if not deps or not rt:
            return 500, {"ok": False, "error": "deps_not_ready"}
        trace = self._trace()
        if self.path.startswith("/v1/") and self.path != "/v1/auth/login":
            token = self._bearer_token()
            if not token:
                return 401, {"ok": False, "error": "missing_token", "trace_id": trace.trace_id}
            info = _run_async(deps.auth.validate_token(token))
            if not info:
                return 401, {"ok": False, "error": "invalid_token", "trace_id": trace.trace_id}
            user = dict(info.get("user") or {})
            user_id = str(user.get("user_id") or "")
            allowed = _run_async(deps.authorizer.check_permission(user_id=user_id, resource=resource, action=action))
            if not allowed:
                rt.state_db.add_audit_log(trace_id=trace.trace_id, actor=user_id, action=action, resource=resource, result={"ok": False, "reason": "rbac"})
                return 403, {"ok": False, "error": "permission_denied", "trace_id": trace.trace_id}
            pol = _run_async(deps.policy.decide(subject=user, action=action, resource={"type": resource}, context={"path": self.path}))
            if not pol.get("allowed", False):
                rt.state_db.add_audit_log(trace_id=trace.trace_id, actor=user_id, action=action, resource=resource, result={"ok": False, "reason": pol.get("reason")})
                return 403, {"ok": False, "error": "policy_denied", "trace_id": trace.trace_id}

            if action == "write":
                rs = deps.risk.score(command=f"bff:{resource}:{action}", context=risk_ctx or {})
                if rs.disposition == "deny":
                    rt.state_db.add_audit_log(trace_id=trace.trace_id, actor=user_id, action=action, resource=resource, result={"ok": False, "risk": rs.to_dict()})
                    return 403, {"ok": False, "error": "risk_denied", "risk": rs.to_dict(), "trace_id": trace.trace_id}
                if rs.disposition == "approve":
                    appr = rt.state_db.create_approval(
                        task_id=f"bff:{resource}:{uuid.uuid4().hex}",
                        risk_score=float(rs.total),
                        risk_factors=[{"factor": f.name, "score": f.score, "weight": f.weight} for f in rs.factors],
                        requester={"user_id": user_id, "trace_id": trace.trace_id},
                        expires_at=int(now_unix() + 3600),
                    )
                    rt.state_db.add_audit_log(trace_id=trace.trace_id, actor=user_id, action=action, resource=resource, result={"ok": False, "approval_id": appr.approval_id, "risk": rs.to_dict()})
                    return 409, {"ok": False, "error": "approval_required", "approval_id": appr.approval_id, "risk": rs.to_dict(), "trace_id": trace.trace_id}

            rt.state_db.add_audit_log(trace_id=trace.trace_id, actor=user_id, action=action, resource=resource, result={"ok": True})
        return None

    def _bearer_token(self) -> str:
        auth = str(self.headers.get("Authorization", "") or "")
        if not auth.lower().startswith("bearer "):
            return ""
        return auth.split(" ", 1)[1].strip()

    def _trace(self) -> TraceContext:
        headers = {k: str(v) for k, v in self.headers.items()}
        ctx = TraceContext.from_headers(headers)
        if ctx:
            return ctx
        trace_id = uuid.uuid4().hex.ljust(32, "0")[:32]
        span_id = uuid.uuid4().hex.ljust(16, "0")[:16]
        return TraceContext.build(trace_id=trace_id, span_id=span_id, sampled=True)

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            obj = json.loads(raw.decode("utf-8"))
        except Exception:
            obj = {}
        if isinstance(obj, dict):
            return obj
        return {}

    def _validate_body(self, body: Dict[str, Any], validator):
        res = validator(body)
        if res.is_valid:
            return None
        return 400, {"ok": False, "error": "invalid_request", "details": res.to_dict()}

    def _query(self) -> Dict[str, str]:
        path, _, q = self.path.partition("?")
        self.path = path
        out: Dict[str, str] = {}
        if not q:
            return out
        for part in q.split("&"):
            k, _, v = part.partition("=")
            if k:
                out[k] = v
        return out

    def _json(self, status: int, obj: Dict[str, Any]):
        deps = self.deps
        if deps:
            obj = deps.redactor.redact(obj)
        trace = self._trace()
        if "ok" not in obj:
            obj["ok"] = status < 400
        if "error" in obj and "error_code" not in obj:
            obj["error_code"] = obj.get("error")
        if obj.get("ok") is True and "result" not in obj:
            obj["result"] = obj.get("data")
            if obj["result"] is None:
                for key in [
                    "run",
                    "runs",
                    "workflow",
                    "workflows",
                    "schedule",
                    "schedules",
                    "work_item",
                    "work_items",
                    "approval",
                    "approvals",
                    "reports",
                    "agents",
                    "audit",
                    "evidence",
                    "nodes",
                    "logs",
                    "status",
                    "scheduler",
                    "has_config",
                ]:
                    if key in obj:
                        obj["result"] = obj[key]
                        break
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("traceparent", trace.traceparent)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class BffService(ServiceBase):
    def __init__(self):
        super().__init__(ServiceConfig(name="bff", tick_interval_sec=2.0))
        self._rt = build_runtime_container()
        self._server: _ThreadedHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._cfg = _BffConfig(
            host=os.environ.get("OPENCLAW_BFF_HOST", "127.0.0.1"),
            port=int(os.environ.get("OPENCLAW_BFF_PORT", "8080")),
        )

    async def initialize(self) -> bool:
        ok = await super().initialize()
        if not ok:
            return False
        self._rt.paths.ensure()
        _Handler.container = self._rt
        deps = _Deps(
            auth=InMemoryAuthProvider(),
            authorizer=InMemoryAuthorizer(),
            policy=SimplePolicyEngine(default_allow=True),
            redactor=SimpleRedactor(),
            risk=RiskScorer(),
            system=SystemManager(),
        )
        await deps.authorizer.add_role("admin", [{"resource": "*", "action": "*"}])
        await deps.authorizer.add_role("reader", [{"resource": "*", "action": "read"}])
        _Handler.deps = deps
        self._server = _ThreadedHTTPServer((self._cfg.host, self._cfg.port), _Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return True

    async def shutdown(self) -> bool:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        return await super().shutdown()

    async def tick(self) -> None:
        return None


def main() -> int:
    return BffService.main(BffService())


if __name__ == "__main__":
    raise SystemExit(main())
