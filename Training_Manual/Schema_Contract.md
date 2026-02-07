# Schema Contract

## 1. 核心表
- `workflows(id, name, version, params_schema, created_at)`
- `schedules(id, workflow_id, version, cron, timezone, enabled, policy_json, revision, next_fire_at, updated_at)`
- `runs(id, schedule_id, workflow_id, version, status, trigger_source, scheduled_at, started_at, finished_at, heartbeat_at, summary_json)`
- `node_runs(id, run_id, node_id, status, attempt, started_at, finished_at, error_json)`
- `work_items(id, run_id, task_id, assigned_to, lease_until, status, artifacts_json)`
- `evidence(id, run_id, node_run_id, type, uri, hash, supports_claim)`
- `memory_units(id, type, scope, content, confidence, priority, version, created_at)`
- `audit_logs(id, actor, action, resource, before_json, after_json, result, ts)`

## 2. 索引
- `runs(status, scheduled_at)`
- `runs(workflow_id, scheduled_at)`
- `node_runs(run_id, status)`
- `audit_logs(ts)`

## 3. 迁移
- 迁移脚本必须幂等。
- 每次迁移包含 up/down。
- 大版本迁移先影子表回填再切换。
