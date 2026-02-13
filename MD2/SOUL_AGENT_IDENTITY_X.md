# OpenClaw-X（X 架构）SOUL 与 Agent 身份文档

## 适用范围

本文档基于 OpenClaw-X 架构与当前落盘实现，梳理 SOUL 身份与 Agent 身份模型，面向 MD2/X 架构版本的运行与对接场景。

## SOUL 定义（X 架构版本）

SOUL 在 X 架构中指系统级身份与信任底座，覆盖安全鉴权、权限裁决、策略约束、全链追踪与审计留存。SOUL 不等同于单一模块，而是由以下能力组合而成：

- 身份认证与会话凭证：Token/Refresh 机制与用户主体信息
- 访问授权：RBAC 权限与角色授予
- 策略决策：基于上下文的 allow/deny 规则
- 风险与审批：风险评分、审批阻断、人工裁决
- 追踪与审计：trace_id 贯穿、审计日志与证据链留存

对应落盘模块：

- 认证：InMemoryAuthProvider 生成 token 与 refresh token，并绑定 user_id 与 roles  
  Code Reference: [auth.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/governance/auth.py)
- RBAC：权限与角色模型、授权检查  
  Code Reference: [rbac.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/governance/rbac.py)
- 策略引擎：规则匹配与决策  
  Code Reference: [policy_engine.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/governance/policy_engine.py)
- 风险评分与审批：风险因子、审批请求与裁决  
  Code Reference: [scorer.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/risk/scorer.py), [approvals.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/approvals.py)
- 追踪与审计：traceparent 协议与审计落地  
  Code Reference: [trace.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/trace.py), [audit.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/governance/audit.py)
- API 网关守卫：BFF 请求统一验证、授权与风险阻断  
  Code Reference: [bff_service.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/services/bff_service.py)

## SOUL 身份对象与命名规则

SOUL 统一管理以下身份对象：

- user_id：人类用户或外部调用主体
- agent_id：执行 Agent 或 Runner 身份
- service_id：系统服务身份（scheduler/orchestrator/runner/bff 等）
- approval_id：审批身份与裁决链路节点
- trace_id：全链路追踪主键
- run_id / workflow_id / task_id：业务执行链路身份

落盘实现中常见命名：

- run_id：`run-<workflow_id>-<timestamp>` 或 `run-<uuid>`  
  Code Reference: [service.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/scheduler/service.py)
- approval_id：`apr-<uuid>`  
  Code Reference: [state_db.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/persistence/state_db.py#L561-L588)
- trace_id：`tr-<uuid>` 或 W3C traceparent 解包所得  
  Code Reference: [trace.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/trace.py)

## SOUL 决策链路（BFF 入口）

X 架构默认从 BFF 进入 SOUL 决策链路：

1. token 校验，解析 user_id / roles
2. RBAC 权限检查
3. 策略引擎决策
4. 风险评分（写操作）
5. 风险高时生成审批请求
6. 审批通过后继续执行

对应实现入口：

Code Reference: [bff_service.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/services/bff_service.py#L755-L812)

## Agent 身份模型（X 架构版本）

Agent 身份以 agent_id 为主键，强调“可执行主体 + 可观测运行态”。核心结构由 AgentConfig 与 AgentHeartbeat 描述：

- agent_id：唯一身份
- skills：能力集合
- state：运行态（idle/running/failed/blocked/learning）
- queue_depth / cpu / mem：运行资源与负载
- metrics：执行质量指标

对应实现：

Code Reference: [agent.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/agent_pool/agent.py), [state_db.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/persistence/state_db.py#L512-L543)

## Agent 与 SOUL 的协作关系

SOUL 提供身份与信任语义，Agent 负责执行与产出。主要交互点：

- Agent 心跳上报：写入 agent_id 状态与负载  
  Code Reference: [runner_service.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/services/runner_service.py#L67-L99)
- 任务领取与执行：work_items 绑定 agent_id 与状态迁移  
  Code Reference: [state_db.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/persistence/state_db.py#L470-L510)
- 审批与风险：Agent 运行受 SOUL 规则约束  
  Code Reference: [run_engine.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/orchestrator/run_engine.py)

## 追踪与审计关联规则

X 架构要求 trace_id 贯穿：

- 所有外部请求通过 BFF 保持 traceparent
- 审计与证据链记录携带 trace_id
- Agent 执行任务时从 work item 上下文提取 trace_id

对应实现：

Code Reference: [trace.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/trace.py), [runner_service.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/services/runner_service.py#L130-L137), [audit.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/governance/audit.py)

## 版本约束与后续扩展

当前文档适配 MD2/X 架构版本，特性约束：

- 认证与授权为 in-memory 实现
- SOUL 链路集中在 BFF 入口与编排器
- Agent 身份为单机运行态模型

扩展建议：

- 将 SOUL 统一输出为协议化 ApiResponse
- 引入外部身份提供方与多租户隔离
- 为 agent_id 与 service_id 引入证书身份与请求签名（timestamp/nonce/trace_id）
- 建立证书生命周期与轮换策略
