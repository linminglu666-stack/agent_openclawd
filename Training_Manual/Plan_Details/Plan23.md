# Plan23 详情（与主计划对齐）

- 对应主计划：Training_Manual/Plan23
- 主计划标题：Plan23 核心-指令型：模型路由与能耗治理

## 核心要点索引（来自主计划）
3:1. 目标
6:2. 核心机制

## 计划原文摘录
Plan23 核心-指令型：模型路由与能耗治理

1. 目标
- 在保证质量的前提下降低 token/CPU/延迟成本。

2. 核心机制
- 任务分层：L0(Light) / L1(Standard) / L2(Deep) / L3(Critical)。
- 模型路由：默认小模型，按风险/复杂度升级。
- 预算守门：超预算自动触发压缩上下文、降级工具、分步执行。

3. 路由规则
- `complexity <= 3 && risk=low -> Light`
- `conflict/high-stakes -> Deep/Critical`
- `history_fail_rate > 阈值 -> 升级模型`

4. 持久化
- `model_routing_logs`：路由决策与理由。
- `cost_ledger`：token/cpu/io 成本明细。

5. 验收
- 平均成本下降 >= 25%。
- 关键任务质量不下降。
