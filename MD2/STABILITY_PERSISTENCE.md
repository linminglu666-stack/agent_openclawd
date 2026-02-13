# 稳定性与持久化（系统级服务验收）

本文件将 [OPENCLAW_X_COMPLETE_ARCHITECTURE.md](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/OPENCLAW_X_COMPLETE_ARCHITECTURE.md) 中“系统级服务注册与持久化强化”的验收要求，落到可落盘的目录约定、数据落点、恢复闭环与 systemd 运行契约。

## 目标

- 服务注册一次成功，脚本可重复执行（幂等）
- 服务重启可恢复：关键状态不丢失，不重复执行，不出现“老化后异常飘移”
- 可观测可审计：trace_id 贯穿，证据链可追溯

## 必须持久化的最小集合

- **Scheduler**：计划表、next_fire_at、计划版本、最近 N 次触发记录
- **Runner**：租约（lease）、幂等键（idempotency key）、执行队列偏移/游标
- **Orchestrator**：DAG 执行状态（节点级）、断点续跑信息、审批闭环状态
- **Memory Indexer**：索引构建游标、批处理进度、冲突解决记录
- **Eval**：离线评估任务记录、阈值版本、报告摘要索引
- **BFF**：仅缓存态可丢，鉴权与审计必须持久化（审计可 jsonl）

## 持久化落点与格式

- WAL（追加写）：用于恢复任务执行、租约、幂等键、审计事件等“序列化事件”
- Snapshot（快照）：用于快速启动（避免全量重放），按保留策略清理
- 单机最小实现建议：SQLite（状态表+索引）+ jsonl WAL（人类可读与可追溯）

## 重启恢复闭环（验收要点）

1. 启动时：加载最新快照 → 重放 snapshot 之后的 WAL → 校验一致性
2. 发现未释放租约：按租约过期策略回收；按幂等键避免重复执行
3. 发现中断 DAG：按节点状态继续；必要时触发补偿动作并写入审计
4. 完成恢复：输出健康状态与恢复摘要（可审计）

## 服务老化防护（长期运行稳定性）

- 有界内存：队列、缓存、证据链、审计缓冲必须有保留策略（retention）
- 自愈触发：健康检查失败 → 记录审计/证据 → 进程退出让 systemd 拉起
- 可控再生：可选启用 RuntimeMaxSec（避免长时间运行导致的碎片/泄漏累积）

## systemd 运行契约（建议）

- 幂等安装脚本：只在 unit 变化时 reload/restart；否则不扰动
- 持久化目录：StateDirectory/LogsDirectory 统一约束，权限固定
- 安全加固：NoNewPrivileges、ProtectSystem、ProtectHome、PrivateTmp
- 资源护栏：MemoryMax/TasksMax/TimeoutStopSec
- 启动/停止：ExecStartPre 做目录/权限校验；StopSignal/Timeout 保障优雅退出

## 与代码骨架的对应关系（MD2/code）

- persistence：WAL/快照/SQLite 状态存储骨架
- recovery：重放与幂等恢复骨架
- health：health/readiness 契约与检查项
- services：每个 service 的入口与 ServiceBase

