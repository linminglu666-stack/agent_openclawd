# Plan18 详情（与主计划对齐）

- 对应主计划：Training_Manual/Plan18
- 主计划标题：1. 术语与对象模型

## 核心要点索引（来自主计划）
1:1. 术语与对象模型
13:2. 总体架构（与你的 Flask 控制台后端打通）
14:2.1 组件职责
38:2.2 推荐通信方式

## 计划原文摘录
1. 术语与对象模型

为支持“Cron 调度 + DAG 执行 + 可视化控制”，建议把对象拆成 4 层（前端也更好做）：

层级	对象	说明
定义层	Workflow(DAG)	DAG 定义本体（节点、边、参数 schema、版本）
调度层	Schedule	Cron 绑定到某个 Workflow 版本/别名，定义触发策略与执行策略
执行层	Run	一次 Workflow 的执行实例（由 Schedule 触发或手动触发）
子执行层	NodeRun	Run 内每个节点的实例状态、日志、重试等

这意味着：你原来“job”概念在可视化里应更像 Schedule；Workflow（DAG）由 OpenClawd 内部已有体系提供或扩展一个注册表。

2. 总体架构（与你的 Flask 控制台后端打通）
2.1 组件职责

openclawd-scheduler（WSL 内系统服务）

维护 Schedule

计算 cron 下一次触发、处理 misfire、并发策略

触发时创建 Run，并投递给 orchestrator（DAG 执行引擎）

提供本机管理 API（建议 Unix socket）

openclawd-orchestrator/executor（DAG 执行引擎）

根据 Run 执行 DAG，生成 NodeRun 状态、日志、心跳、总结

你的 Flask 后端（控制台 BFF，推荐做法）

对前端提供统一 API（鉴权、RBAC、审计、聚合）

向 scheduler/orchestrator 的本机 API 发请求（或读同一数据库）

对前端提供 SSE/WS 事件流（可代理/聚合）

2.2 推荐通信方式

Flask → scheduler：unix:// /run/openclawd/scheduler.sock（安全，不暴露端口）

Flask → orchestrator：同样走 unix socket 或 loopback TCP（127.0.0.1）

前端 → Flask：HTTP/JSON + SSE（优先 SSE，足够好用）

你已有 Flask 后端，因此可以不单独做 scheduler-gateway 服务：由 Flask 直接充当 gateway/BFF，减少一个进程与一套鉴权。

3. 核心交互流程（控制台视角）
3.1 创建/编辑 Schedule（可视化配置）

前端编辑 cron/时区/策略/绑定的 workflow

调用：POST/PUT /api/v1/schedules

保存后列表直接展示：next_fire_at、last_run_status

3.2 定时触发执行（无需控制台参与）

scheduler 到点触发

scheduler 创建 Run（status=scheduled），写入存储

scheduler 投递 Run 给 orchestrator（队列/DB outbox/IPC）

orchestrator 执行，产生 NodeRun、日志与进度事件

完成后写 summary，并发出 run.finished

3.3 控制台实时观察（Run 详情）

前端打开 Run 页面，订阅 GET /api/v1/events?run_id=...（SSE）

实时更新：Run 状态、节点状态、进度心跳、日志尾部、失败原因

3.4 控制台控制（取消/暂停/恢复/重试）

POST /api/v1/runs/{run_id}:cancel

POST /api/v1/runs/{run_id}:pause（语义见后文）

POST /api/v1/runs/{run_id}:resume

POST /api/v1/nodeRuns/{node_run_id}:retry 等

4. API 规范（给 Flask 控制台直接对接的“外部 API”）

下文的 /api/v1/... 以“Flask 对前端暴露的 API”为准。Flask 内部如何转发到 scheduler/orchestrator，可按你的实现选择（转发/直连 DB/混合）。

4.1 认证与幂等

Header：Authorization: Bearer <JWT>

幂等（强烈建议用于“手动触发 Run”）：

Idempotency-Key: <uuid>

同 Key + 同用户 + 同请求体 → 返回同一 run_id

5. Workflow（DAG）相关接口（用于可视化选择、展示 DAG 图）
5.1 列表
GET /api/v1/workflows?search=&limit=&cursor=

返回（示例）：

{
  "items": [
    {
      "workflow_id": "build_pipeline",
      "name": "Build Pipeline",
      "latest_version": "v12",
      "tags": ["ci"],
      "updated_at": "..."
    }
  ],
  "next_cursor": null
}

5.2 详情（含参数 schema）
GET /api/v1/workflows/{workflow_id}
{
  "workflow_id": "build_pipeline",
  "name": "Build Pipeline",
  "versions": ["v10","v11","v12"],
  "default_version": "v12",
  "params_schema": {
    "type": "object",
    "properties": {
      "branch": {"type":"string","default":"main"},
      "fast": {"type":"boolean","default":false}
    }
  }
}

5.3 DAG 图（用于前端画拓扑）
GET /api/v1/workflows/{workflow_id}/graph?version=v12
{
  "nodes": [
    {"node_id":"checkout","name":"Checkout","type":"task"},
    {"node_id":"build","name":"Build","type":"task"}
  ],
  "edges": [
    {"from":"checkout","to":"build"}
  ]
}

6. Schedule（Cron 可视化配置）接口 —— 替代“内置 Cron”
6.1 Schedule 数据结构（建议）
{
  "schedule_id": "daily_build_3am",
  "name": "Daily Build 3AM",
  "enabled": true,

  "workflow_ref": {
    "workflow_id": "build_pipeline",
    "version": "v12"  
  },

  "schedule": {
    "cron": "0 3 * * *",
    "timezone": "Asia/Shanghai"
  },

  "trigger_policy": {
    "misfire": "run_once",
    "jitter_sec": 60
  },

  "run_policy": {
    "concurrency": {
      "mode": "forbid",
      "key": "build_pipeline_daily"
    },
    "timeout_sec": 1800,
    "retry": {"times": 2, "backoff_sec": [10, 30]},
    "queue": {"mode": "coalesce"} 
  },

  "params_template": {
    "branch": "main",
    "fast": false
