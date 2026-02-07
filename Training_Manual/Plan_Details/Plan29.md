# Plan29 详情（与主计划对齐）

- 对应主计划：Training_Manual/Plan29
- 主计划标题：Plan29 核心-指令型：能力插件生态机制

## 核心要点索引（来自主计划）
3:1. 目标
6:2. 插件契约

## 计划原文摘录
Plan29 核心-指令型：能力插件生态机制

1. 目标
- 建立标准化插件框架，扩展能力且可控。

2. 插件契约
- manifest：name/version/capabilities/permissions。
- I/O Contract：输入输出 schema。
- 生命周期：install/enable/disable/upgrade/rollback。

3. 运行机制
- 沙箱执行。
- 超时与资源配额。
- 插件健康检查与熔断。

4. 持久化
- `plugins`、`plugin_versions`、`plugin_runs`、`plugin_audit`。

5. 验收
- 新插件接入不改核心代码。
- 插件故障不拖垮主系统。
