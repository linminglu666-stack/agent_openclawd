# 代码索引（MD2/code）

本索引按模块边界列出当前已落盘的代码文件，并提供“职责说明 / 关键依赖 / 与架构章节的对应关系”。

## protocols（协议层）

- [interfaces.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/interfaces.py)：模块接口协议（IModule、IKernel、IAgent、IRouter、IScheduler、IReasoner、IMemory 等）
- [messages.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/messages.py)：模块间消息协议（MessageHeader、TaskRequest/Response、TraceEvent 等）
- [states.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/states.py)：状态枚举与状态机（Task/Scheduler/Reasoning/Health 等）
- [config.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/config.py)：配置快照与 FeatureFlags 数据契约
- [risk.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/risk.py)：风险评分数据契约
- [persistence.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/persistence.py)：WAL/快照/租约等持久化数据契约
- [health.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/health.py)：健康检查数据契约
- [skills.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/skills.py)：技能注册表数据契约
- [workflow.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/workflow.py)：调度/运行/工作项状态机与数据模型（runs/node_runs/work_items）
- [api.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/api.py)：对外 API 通用契约（错误码、分页、元信息）
- [bff.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/bff.py)：BFF 对外 API 合同（Schedule/Run/WorkItem）
- [trace.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/trace.py)：W3C Trace Context（traceparent/tracestate）契约与解析
- [topics.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/topics.py)：事件总线 topic 常量清单
- [events.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/events.py)：事件信封（版本/trace/payload/meta）
- [approvals.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/approvals.py)：审批数据契约（审批队列）
- [workflows.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/workflows.py)：工作流定义数据契约（DAG）
- [learning.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/protocols/learning.py)：学习报告数据契约（Growth Loop）

## utils（通用工具）

- [logger.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/utils/logger.py)：结构化日志与 trace/span 上下文日志器
- [serializer.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/utils/serializer.py)：对象序列化/反序列化工具
- [validators.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/utils/validators.py)：输入校验与约束工具

## core/kernel（内核层）

- [kernel.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/kernel/kernel.py)：内核执行与查询入口（IKernel 的骨架实现）
- [adapter.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/kernel/adapter.py)：适配层（IAdapter 的骨架实现）

## core/central_brain（中央机）

- [coordinator.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/central_brain/coordinator.py)：模块注册、任务执行流编排、广播事件
- [scheduler.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/central_brain/scheduler.py)：异步任务调度（优先级队列、超时、重试、依赖）
- [router.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/central_brain/router.py)：任务路由（Agent/推理/记忆/内核的分流入口）
- [model_router.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/central_brain/model_router.py)：智能路由（按任务特征选择模块/模型通道）
- [error_patterns.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/central_brain/error_patterns.py)：错误模式库（匹配与建议动作）
- [route_module.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/central_brain/route_module.py)：路由模块骨架（供 Coordinator 执行流使用）

## core/orchestrator（DAG 编排）

- [dag.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/orchestrator/dag.py)：DAG 规范（节点/边/元数据）
- [executor.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/orchestrator/executor.py)：DAG 执行记录与持久化骨架（SQLite + WAL）
- [run_engine.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/orchestrator/run_engine.py)：运行驱动引擎（runs/node_runs/work_items + 审批阻断/续跑）

## core/agent_pool（多 Agent 协作）

- [agent.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/agent_pool/agent.py)：Agent 抽象与示例实现
- [pool.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/agent_pool/pool.py)：Agent 池（并发调度与负载管理骨架）
- [registry.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/agent_pool/registry.py)：Agent 注册与能力查询

## core/reasoning（推理增强层）

- [orchestrator.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/reasoning/orchestrator.py)：CoT/ToT/Reflexion/Self-Consistency 等推理策略骨架
- [strategy_router.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/reasoning/strategy_router.py)：推理策略选择与路由
- [scratchpad.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/reasoning/scratchpad.py)：Scratchpad 结构与记录
- [kg_reasoner.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/reasoning/kg_reasoner.py)：神经符号 KG 推理（最小图结构与查询/推断骨架）

## core/runtime（运行时装配）

- [paths.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/runtime/paths.py)：运行目录解析与统一创建
- [container.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/runtime/container.py)：RuntimeContainer（持久化/审计/追踪/租约/幂等统一装配）

## core/scheduler（schedule-only 调度）

- [engine.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/scheduler/engine.py)：调度策略求值（policy_json → fire/next_fire_at）
- [service.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/scheduler/service.py)：ScheduleOnlyScheduler（扫描 due schedules → 触发 runs）

## core/memory_hub（记忆入口）

- [hub.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/memory_hub/hub.py)：记忆枢纽入口（IMemory/IKnowledgeBase 等的组合骨架）
- [layered_hub.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/memory_hub/layered_hub.py)：分层记忆 Hub（L1-L4 的组合骨架）
- [layers.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/memory_hub/layers.py)：记忆分层数据结构与 InMemoryLayer
- [conflict_resolver.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/memory_hub/conflict_resolver.py)：冲突版本控制与合并策略
- [drift.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/memory_hub/drift.py)：上下文漂移检测
- [writeback.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/memory_hub/writeback.py)：回写策略规划

## core/eval_gate（评估与真值门）

- [gate.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/eval_gate/gate.py)：评估门模块（评分、决策、与真值门联动）
- [truth_gate.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/eval_gate/truth_gate.py)：真值门（claim/evidence 的最小检查骨架）

## core/observability（可观测与证据链）

- [event_bus.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/observability/event_bus.py)：事件总线（in-memory pub/sub）
- [persistent_bus.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/observability/persistent_bus.py)：可选持久化事件总线（WAL + offset 回放）
- [tracing.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/observability/tracing.py)：追踪（trace/span 的最小实现）
- [metrics.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/observability/metrics.py)：指标收集（in-memory）
- [evidence.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/observability/evidence.py)：证据链记录（digest 与 trace 索引）

## core/governance（鉴权、RBAC、策略与审计）

- [auth.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/governance/auth.py)：鉴权（token/refresh 的 in-memory 骨架）
- [rbac.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/governance/rbac.py)：RBAC（角色/权限与授权检查）
- [policy_engine.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/governance/policy_engine.py)：策略引擎（allow/deny 规则匹配）
- [audit.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/governance/audit.py)：审计落地（in-memory，可选 jsonl）
- [redaction.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/governance/redaction.py)：脱敏（递归屏蔽敏感字段）

## core/metacognition（元认知与自改进）

- [failure_library.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/metacognition/failure_library.py)：失败模式库（匹配与修复建议）
- [cognitive_debt.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/metacognition/cognitive_debt.py)：认知债务台账（聚合与统计）
- [loop.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/metacognition/loop.py)：元认知循环（observe/propose/apply）

## core/config（配置与回滚）

- [store.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/config/store.py)：版本化配置存取（current/versions/snapshot）
- [feature_flags.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/config/feature_flags.py)：Feature Flag 规则求值（最小安全解析）
- [rollback.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/config/rollback.py)：回滚入口（快照→切换→健康验证→审计）

## core/risk（风险评分）

- [scorer.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/risk/scorer.py)：风险因子与处置建议（allow/approve/deny）

## core/skills（技能生态）

- [registry.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/skills/registry.py)：从 skills/*.skills.json 生成 registry.json
- [loader.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/skills/loader.py)：按 registry.json 加载启用的技能版本
- [batch_ops.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/skills/batch_ops.py)：技能启停/切换的批量操作

## core/persistence（持久化）

- [jsonl_wal.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/persistence/jsonl_wal.py)：追加写 WAL（fsync）
- [snapshot_store.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/persistence/snapshot_store.py)：快照存取与枚举
- [sqlite_store.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/persistence/sqlite_store.py)：单机最小状态库（CAS/版本）
- [schema.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/persistence/schema.py)：统一核心数据表 Schema（迁移 + DDL）
- [state_db.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/persistence/state_db.py)：StateDB 访问层（schedules/runs/node_runs/work_items/证据/审计/记忆）

## core/recovery（恢复与幂等）

- [startup.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/recovery/startup.py)：启动恢复（回收 lease/写恢复摘要）

## core/growth_loop（成长循环）

- [idle_detector.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/growth_loop/idle_detector.py)：空闲检测（基于 heartbeats）
- [learner.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/growth_loop/learner.py)：学习产物生成（LearningReport）
- [loop.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/growth_loop/loop.py)：成长循环（detect→learn→write→broadcast）

## core/health（健康契约）

- [contract.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/health/contract.py)：HealthReport/HealthCheck 与分级

## core/recovery（恢复与幂等）

- [replay.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/recovery/replay.py)：WAL 重放骨架（按类型 handler）
- [idempotency.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/core/recovery/idempotency.py)：租约与幂等键落盘骨架

## services（系统服务入口）

- [service_base.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/services/service_base.py)：ServiceBase（sd_notify/Watchdog/优雅退出/目录约定）
- [scheduler_service.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/services/scheduler_service.py)：openclawd-scheduler 入口
- [orchestrator_service.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/services/orchestrator_service.py)：openclawd-orchestrator 入口
- [runner_service.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/services/runner_service.py)：openclawd-runner 入口
- [memory_indexer_service.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/services/memory_indexer_service.py)：openclawd-memory-indexer 入口
- [eval_service.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/services/eval_service.py)：openclawd-eval 入口
- [bff_service.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/services/bff_service.py)：openclawd-bff 入口
- [growth_loop_service.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/services/growth_loop_service.py)：openclawd-growth-loop 入口

## examples（串联示例）

- [pipeline_demo.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/examples/pipeline_demo.py)：治理→路由→KG 推理→评估门→证据链→记忆回写→元认知 的参考流程
- [e2e_smoke.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/examples/e2e_smoke.py)：schedule→run→node_runs→work_items→runner→audit/evidence 的端到端冒烟验证
