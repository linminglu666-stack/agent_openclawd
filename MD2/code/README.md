# OpenClaw-X（MD2）代码骨架

本目录是基于 [OPENCLAW_X_COMPLETE_ARCHITECTURE.md](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/OPENCLAW_X_COMPLETE_ARCHITECTURE.md) 输出的“可读代码骨架”，用于沉淀模块边界、协议与最小实现示例。

- 目标：把架构文档中的模块拆成可落盘的代码结构与接口，方便后续替换为真实实现
- 非目标：本目录不启动服务、不提供生产可运行系统；示例文件也不会被自动执行

## 目录概览

- core/：核心运行时模块（中央机、调度、推理、记忆、评估门、治理、可观测、元认知等）
- protocols/：模块间协议（接口、消息、状态机与状态枚举）
- utils/：通用工具（日志、序列化、校验等）
- services/：系统级服务入口（配合 MD2/systemd 的 unit 模板）
- examples/：端到端串联示例（仅用于阅读与集成参考）

## 使用方式（阅读/集成）

建议从索引开始：

- [INDEX.md](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/INDEX.md)

如果要把该骨架接入真实系统，一般按以下路径替换：

1. 替换适配器：将 core/kernel/adapter.py 中的输入输出适配替换为真实协议/业务适配
2. 替换模型调用：将 core/reasoning/ 与 core/central_brain/router.py 中的策略路由连接到真实模型/工具
3. 替换存储：将 core/memory_hub/ 下的 in-memory 实现替换为向量库/关系库/对象存储
4. 打通治理与审计：将 core/governance/ 与 core/observability/ 的审计、证据链、追踪接到真实平台

## 系统级服务（落盘骨架）

- systemd 模板：见 [MD2/systemd](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/systemd)
- 安装/回滚脚本：见 [MD2/scripts](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/scripts)

## 约定

- 默认仅使用 Python 标准库（typing/dataclasses/asyncio 等），避免引入外部依赖
- 协议优先：先定 protocols，再在 core 中提供最小实现，以便真实系统替换
- trace_id/span_id 贯穿：消息头与日志字段尽量携带 trace_id/span_id，便于全链路追溯
