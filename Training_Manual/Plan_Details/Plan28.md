# Plan28 详情（与主计划对齐）

- 对应主计划：Training_Manual/Plan28
- 主计划标题：Plan28 核心-指令型：安全强化机制

## 核心要点索引（来自主计划）
3:1. 目标
6:2. 机制

## 计划原文摘录
Plan28 核心-指令型：安全强化机制

1. 目标
- 降低越权操作、供应链风险、注入风险。

2. 机制
- Policy Sandbox：按操作类型白名单授权。
- 双人审批：高风险操作（skip/force/路径合同变更）。
- 供应链校验：插件/依赖签名校验。
- Prompt Injection 防护：不可信上下文隔离。

3. 持久化
- `security_policies`、`approval_records`、`security_events`。

4. 验收
- 高风险操作全部可追溯。
- 安全演练通过率持续提升。
