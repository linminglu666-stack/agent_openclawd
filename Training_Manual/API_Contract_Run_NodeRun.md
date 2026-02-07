# API Contract: Run / NodeRun

## 1. Run 状态机
- `scheduled -> running -> success|failed|timeout|canceled`
- `running -> paused -> running`
- `running -> lost`

## 2. NodeRun 状态机
- `queued -> running -> success|failed|canceled|skipped`

## 3. 核心接口
- `POST /api/v1/workflows/{workflow_id}:runNow`
- `GET /api/v1/runs`
- `GET /api/v1/runs/{run_id}`
- `POST /api/v1/runs/{run_id}:cancel|pause|resume|retry`
- `GET /api/v1/runs/{run_id}/nodeRuns`
- `POST /api/v1/nodeRuns/{node_run_id}:retry|cancel|skip`
- `GET /api/v1/events` (SSE)

## 4. 错误码
- `400 invalid_request`
- `401 unauthorized`
- `403 forbidden`
- `404 not_found`
- `409 revision_conflict`
- `409 concurrency_conflict`
- `422 validation_failed`
- `429 rate_limited`
- `500 internal_error`
- `503 dependency_unavailable`

## 5. 幂等
- 触发类接口要求 `Idempotency-Key`。
- 同 key + 同 body 返回同一 `run_id`。

## 6. 审计
- 写操作必须记录：`who/when/action/resource/before/after/result`。
