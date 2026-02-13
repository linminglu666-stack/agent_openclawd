# OpenClaw-X 自研内核与模块化方案索引

## 目标

在保留 OpenClaw 最小可用内核的前提下，全面替换上层机制，形成可自主演进的 OpenClaw-X。

## 核心文档

### 完整架构文档

- [OPENCLAW_X_COMPLETE_ARCHITECTURE.md](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/OPENCLAW_X_COMPLETE_ARCHITECTURE.md)
  - **唯一完整文档**，包含所有设计思路、流程图、实现细节、模块间数据接口与通信协议
  - 整合了所有原分散文档的核心内容

### 补充设计文档

基于训练总结深度分析补充的专项设计文档：

- [SELF_SUPERVISED_QUALITY_ASSESSMENT.md](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/SELF_SUPERVISED_QUALITY_ASSESSMENT.md)
  - 自监督质量评估与自动反馈循环设计
  - 不确定性量化、置信度校准、多时间尺度反馈

- [PREDICTIVE_CONSOLE_DESIGN.md](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/PREDICTIVE_CONSOLE_DESIGN.md)
  - 预测性控制台与认知驱动运维设计
  - 主动推理回路、预测误差分层呈现

- [METACOGNITION_SELF_IMPROVEMENT.md](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/METACOGNITION_SELF_IMPROVEMENT.md)
  - 元认知与自改进机制设计
  - 双层认知架构、预测误差驱动学习、探索-利用平衡

- [HIERARCHICAL_TASK_DECOMPOSITION.md](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/HIERARCHICAL_TASK_DECOMPOSITION.md)
  - 层次化任务分解与依赖DAG执行
  - 状态机设计、调度算法、错误处理机制

- [DISTRIBUTED_TRACING_DESIGN.md](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/DISTRIBUTED_TRACING_DESIGN.md)
  - 分布式追踪与可观测性深度设计
  - Trace/Span/Context、采样策略、OpenTelemetry集成

- [INTELLIGENT_MODEL_ROUTING.md](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/INTELLIGENT_MODEL_ROUTING.md)
  - 智能模型路由与错误模式演化
  - 自适应路由器、错误模式库、元模式机制

- [NEURO_SYMBOLIC_KG_REASONING.md](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/NEURO_SYMBOLIC_KG_REASONING.md)
  - 神经符号知识图谱推理与自适应缓存策略
  - 推理路由机制、渐进式表征转换、局部性强度度量

### 运行与验收补充

- [STABILITY_PERSISTENCE.md](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/STABILITY_PERSISTENCE.md)
  - 系统级服务注册与持久化验收要点（重启可恢复、无服务老化）
- [RUNTIME_LAYOUT.md](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/RUNTIME_LAYOUT.md)
  - systemd StateDirectory/LogsDirectory 的默认落盘目录约定
- [systemd/](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/systemd)
  - systemd unit 模板（Type=notify + Watchdog + StateDirectory）
- [scripts/](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/scripts)
  - install_systemd/rollback/skills_register 等运维脚本骨架

## 可视化追踪系统

### 设计文档

- [VISUAL_TRACING_DESIGN.md](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/VISUAL_TRACING_DESIGN.md)
  - 完整设计文档：数据模型、API设计、前端架构、实现要点
  - 支持决策树、时间线、推理链、ToT探索四种可视化模式

### 后端代码

- [code/visual_tracing_core.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/visual_tracing_core.py)
  - 核心数据结构：VisualTrace、VisualSpan、VisualDecisionTree、ReasoningChain
  - TraceCollector 单例采集器，支持 WebSocket 广播
  - 完整的序列化和数据转换方法

- [code/visual_tracing_api.py](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/code/visual_tracing_api.py)
  - FastAPI 后端服务
  - RESTful API：追踪CRUD、瀑布图、决策树、推理链
  - WebSocket 实时推送 `/api/v1/traces/{trace_id}/stream`
  - 内置演示数据生成

### 前端代码

#### 主视图组件
- [web/js/components/modules/Tracing.js](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/web/js/components/modules/Tracing.js)
  - 追踪探索主视图
  - 视图切换：Timeline / Decision Tree / Reasoning Chain / ToT Explorer
  - 支持导出、刷新、新窗口打开

#### 子组件
- [web/js/components/modules/tracing/DecisionTree.js](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/web/js/components/modules/tracing/DecisionTree.js)
  - D3.js 决策树可视化
  - 支持缩放、拖拽、节点点击

- [web/js/components/modules/tracing/Timeline.js](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/web/js/components/modules/tracing/Timeline.js)
  - 时间线瀑布图组件
  - Span 嵌套关系展示

- [web/js/components/modules/tracing/ReasoningChain.js](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/web/js/components/modules/tracing/ReasoningChain.js)
  - 推理链可视化
  - Thought-Action-Observation 迭代展示

- [web/js/components/modules/tracing/ToTExplorer.js](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/web/js/components/modules/tracing/ToTExplorer.js)
  - Tree of Thought 思维树探索视图
  - 多路径推理过程可视化
  - 支持展开/收起、仅显示选中路径

#### 样式文件
- [web/css/tracing.css](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/web/css/tracing.css)
  - 可视化追踪专用样式
  - 决策树、时间线、推理链、ToT Explorer 样式
  - 暗色主题适配、响应式布局

### API文档

- [docs/API_INTERFACE.md](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/docs/API_INTERFACE.md)
  - API 接口参考
  - 认证、Mock配置、Web架构说明

## Web管理后台

### 设计文档

- [MD2_X_ARCH_WEB_CONSOLE_SCHEME.md](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/MD2_X_ARCH_WEB_CONSOLE_SCHEME.md)
  - Web控制台整体方案设计
  - 模块划分、技术栈选型

### 前端架构

```
web/
├── index.html                 # 入口页面
├── js/
│   ├── app.js                 # Vue 3 应用入口
│   ├── store.js               # 响应式状态管理
│   ├── router.js              # 路由配置
│   └── components/
│       ├── layout/
│       │   ├── Sidebar.js     # 侧边栏导航
│       │   └── Header.js      # 顶部导航
│       └── modules/
│           ├── Dashboard.js   # 仪表盘
│           ├── Agents.js      # Agent管理
│           ├── Tracing.js     # 追踪探索
│           ├── Config.js      # 配置管理
│           ├── Copilot.js     # AI助手
│           └── tracing/       # 追踪子组件
├── css/
│   ├── main.css               # 全局样式
│   └── tracing.css            # 追踪专用样式
└── assets/                    # 静态资源
```

### 技术栈

| 层级 | 技术选型 |
|------|----------|
| 框架 | Vue 3 (ES Modules) |
| 状态管理 | Reactive Store |
| 可视化 | D3.js + ECharts |
| 样式 | Tailwind CSS |
| HTTP | Fetch API |
| 实时通信 | WebSocket |

## 技能文件（skills/）

保留的技能JSON文件，用于注册到 registry.json：

- [Kernel.skills.json](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/skills/Kernel.skills.json)
- [Scheduler_Orchestrator.skills.json](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/skills/Scheduler_Orchestrator.skills.json)
- [Observability_Trace.skills.json](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/skills/Observability_Trace.skills.json)
- [Auth_RBAC.skills.json](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/skills/Auth_RBAC.skills.json)
- [Config_Rollback.skills.json](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/skills/Config_Rollback.skills.json)
- [Risk_Scorer.skills.json](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/skills/Risk_Scorer.skills.json)
- [Eval_Gate.skills.json](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/skills/Eval_Gate.skills.json)
- [Memory_Knowledge.skills.json](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/skills/Memory_Knowledge.skills.json)
- [Skills_Plugins.skills.json](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/skills/Skills_Plugins.skills.json)
- [Web_Admin_Backoffice.skills.json](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/skills/Web_Admin_Backoffice.skills.json)

## 推理增强模块

- [REASONING_DESIGN.md](file:///home/maco_six/.openclaw/workspace/agent_openclawd/src/reasoning/REASONING_DESIGN.md) - 推理深度增强技术设计

已实现模块：
- StrategyRouter: 问题分类与策略选择
- CoTInjector: 思维链注入
- SelfConsistencySampler: 多次采样与投票
- TreeOfThoughtEngine: 树状思维展开
- ReflexionEngine: 自我反思与迭代
- ScratchpadManager: 工作记忆管理
- ReasoningOrchestrator: 统一编排入口
- CodeInterpreterSandbox: 代码执行沙箱

## 验收标准

详见 [OPENCLAW_X_COMPLETE_ARCHITECTURE.md](file:///home/maco_six/.openclaw/workspace/Training_Manual/MD2/OPENCLAW_X_COMPLETE_ARCHITECTURE.md) 第六部分。

---

**文档版本**: v1.1.0  
**最后更新**: 2026-02-13  
**维护者**: OpenClaw-X Team
