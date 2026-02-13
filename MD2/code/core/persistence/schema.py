from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class SchemaMigration:
    version: int
    ddl: List[str]


SCHEMA_V1 = SchemaMigration(
    version=1,
    ddl=[
        "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at INTEGER NOT NULL)",
        "CREATE TABLE IF NOT EXISTS schedules (id TEXT PRIMARY KEY, workflow_id TEXT NOT NULL, version TEXT NOT NULL, enabled INTEGER NOT NULL, policy_json TEXT NOT NULL, next_fire_at INTEGER NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_schedules_workflow ON schedules(workflow_id)",
        "CREATE INDEX IF NOT EXISTS idx_schedules_next_fire ON schedules(next_fire_at)",
        "CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, trace_id TEXT NOT NULL, workflow_id TEXT NOT NULL, status TEXT NOT NULL, config_snapshot TEXT NOT NULL, started_at INTEGER NOT NULL, ended_at INTEGER NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_runs_workflow_started ON runs(workflow_id, started_at)",
        "CREATE INDEX IF NOT EXISTS idx_runs_trace ON runs(trace_id)",
        "CREATE TABLE IF NOT EXISTS node_runs (run_id TEXT NOT NULL, node_id TEXT NOT NULL, status TEXT NOT NULL, snapshot TEXT NOT NULL, started_at INTEGER NOT NULL, ended_at INTEGER NOT NULL, PRIMARY KEY(run_id, node_id))",
        "CREATE INDEX IF NOT EXISTS idx_node_runs_run ON node_runs(run_id)",
        "CREATE TABLE IF NOT EXISTS work_items (task_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, priority INTEGER NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, lease_owner TEXT NOT NULL, lease_expires_at INTEGER NOT NULL, idempotency_key TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_work_items_idem ON work_items(idempotency_key)",
        "CREATE INDEX IF NOT EXISTS idx_work_items_status_prio ON work_items(status, priority)",
        "CREATE INDEX IF NOT EXISTS idx_work_items_lease ON work_items(lease_expires_at)",
        "CREATE TABLE IF NOT EXISTS evidence (evidence_id TEXT PRIMARY KEY, trace_id TEXT NOT NULL, type TEXT NOT NULL, content TEXT NOT NULL, hash TEXT NOT NULL, created_at INTEGER NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_evidence_trace ON evidence(trace_id)",
        "CREATE TABLE IF NOT EXISTS audit_logs (audit_id TEXT PRIMARY KEY, trace_id TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, resource TEXT NOT NULL, result TEXT NOT NULL, timestamp INTEGER NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_audit_trace_ts ON audit_logs(trace_id, timestamp)",
        "CREATE TABLE IF NOT EXISTS memory_units (memory_id TEXT PRIMARY KEY, content TEXT NOT NULL, keywords TEXT NOT NULL, category TEXT NOT NULL, scope TEXT NOT NULL, confidence REAL NOT NULL, updated_at INTEGER NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_memory_category_scope ON memory_units(category, scope)",
    ],
)

SCHEMA_V2 = SchemaMigration(
    version=2,
    ddl=[
        "CREATE TABLE IF NOT EXISTS workflows (workflow_id TEXT NOT NULL, version TEXT NOT NULL, dag_json TEXT NOT NULL, metadata_json TEXT NOT NULL, created_at INTEGER NOT NULL, PRIMARY KEY(workflow_id, version))",
        "CREATE INDEX IF NOT EXISTS idx_workflows_workflow ON workflows(workflow_id)",
        "CREATE TABLE IF NOT EXISTS approvals (approval_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, status TEXT NOT NULL, risk_score REAL NOT NULL, risk_factors_json TEXT NOT NULL, requester_json TEXT NOT NULL, expires_at INTEGER NOT NULL, decision_json TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_approvals_status_expires ON approvals(status, expires_at)",
        "CREATE INDEX IF NOT EXISTS idx_approvals_task ON approvals(task_id)",
        "CREATE TABLE IF NOT EXISTS schedule_triggers (id INTEGER PRIMARY KEY AUTOINCREMENT, schedule_id TEXT NOT NULL, fire_at INTEGER NOT NULL, run_id TEXT NOT NULL, status TEXT NOT NULL, created_at INTEGER NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_schedule_triggers_schedule ON schedule_triggers(schedule_id, fire_at)",
        "CREATE TABLE IF NOT EXISTS agent_heartbeats (agent_id TEXT PRIMARY KEY, status TEXT NOT NULL, cpu REAL NOT NULL, mem REAL NOT NULL, queue_depth INTEGER NOT NULL, skills_json TEXT NOT NULL, metrics_json TEXT NOT NULL, last_seen INTEGER NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_agent_heartbeats_last_seen ON agent_heartbeats(last_seen)",
        "CREATE TABLE IF NOT EXISTS learning_reports (report_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, content_json TEXT NOT NULL, created_at INTEGER NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_learning_reports_agent ON learning_reports(agent_id, created_at)",
        "CREATE TABLE IF NOT EXISTS event_offsets (subscriber_id TEXT NOT NULL, topic TEXT NOT NULL, offset INTEGER NOT NULL, updated_at INTEGER NOT NULL, PRIMARY KEY(subscriber_id, topic))",
    ],
)


ALL_MIGRATIONS = [SCHEMA_V1, SCHEMA_V2]
