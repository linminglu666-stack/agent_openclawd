# Plan6 详情（与主计划对齐）

- 对应主计划：Training_Manual/Plan6
- 主计划标题：Plan6 核心-指令型：任务管理 + 子代理 + 指令解析（完整方案）

## 核心要点索引（来自主计划）
3:1. 目标
8:2. 子核心6-1：任务管理机制

## 计划原文摘录
Plan6 核心-指令型：任务管理 + 子代理 + 指令解析（完整方案）

1. 目标
- 把输入指令转成可执行 DAG。
- 按依赖与优先级调度多个子代理执行。
- 全流程可监控、可回放、可审计。

2. 子核心6-1：任务管理机制
- 输入：Task Card（目标、约束、DoD、时限）。
- 输出：Task DAG、调度计划、验收清单。
- 状态：queued/running/blocked/failed/done。
- 控制：超时、重试、退避、熔断、人工接管。

3. 子核心6-2：子代理机制
- 角色：planner/researcher/implementer/tester/reviewer/publisher。
- 原则：高风险任务必须 reviewer 二次门禁。
- 路由：按 `task.type + risk_level + tool_requirements` 自动分派。
- 汇报：每个子代理完成模块必须输出证据编号与下一步。

4. 子核心6-3：指令解析机制
- 解析字段：目标、约束、输入、输出、依赖、风险、优先级。
- 解析产物：`Interpretation` + `PlanOutline` + `Unknowns`。
- 冲突：高优先级约束覆盖低优先级，冲突必须显式记录。

5. 持久化
- 事件源：`events/task_*.jsonl` append-only。
- 状态库：SQLite `tasks/work_items/dependencies`。
- 恢复：checkpoint + 事件重放。

6. 验收
- 任一任务可追溯到：来源指令 -> 子任务 -> 证据 -> 结果。
- 支持崩溃恢复与失败显式报告。
