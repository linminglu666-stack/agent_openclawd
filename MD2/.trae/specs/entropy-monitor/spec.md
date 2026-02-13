# 熵值监控与可视化模块设计文档 (Entropy Monitor Spec - V2 Architecture)

## Why
当前系统的熵值监控仅基于简单的计数指标（如收件箱积压、重复主题等），未能完全对齐《OpenClaw X 架构文档》中定义的 "Entropy Governance V2" 标准。为了实现更精细化的治理，需要基于 V2 架构的六大熵类别（Input, Evolution, Observability, Structure, Behavior, Data）重构后端计算逻辑，并提供配套的前端可视化监控。

## What Changes

### Backend (Python)
- **核心逻辑重构 (`EntropyControlCenter`)**:
    - 引入 `EntropyCategory` 枚举：INPUT, EVOLUTION, OBSERVABILITY, STRUCTURE, BEHAVIOR, DATA。
    - 扩展 `EntropyMetrics` 数据结构，增加六大类别的评分字段。
    - 升级 `compute_metrics` 方法，将现有指标映射到新类别，并补充缺失维度的计算逻辑（如基于日志的 Behavior 熵）。
    - 增加历史数据存储 (`EntropyHistory`) 和阈值配置 (`EntropyConfig`)。
- **API 扩展 (`BFF Service`)**:
    - `GET /v1/governance/entropy/metrics`: 返回包含六大类别详情的当前熵值。
    - `GET /v1/governance/entropy/history`: 返回时间序列数据（支持按类别筛选）。
    - `GET/POST /v1/governance/entropy/config`: 管理各类别及总熵值的报警阈值。

### Frontend (Vue.js)
- **Store (`store.js`)**:
    - 新增 `entropy` 模块，存储 V2 格式的指标数据、历史记录和配置。
- **UI 组件 (`EntropyMonitor.js`)**:
    - **多维雷达图**: 展示六大熵类别的分布情况（对齐架构文档中的可视化要求）。
    - **趋势折线图**: 展示总熵值及各分项随时间的变化。
    - **详情列表**: 列出导致高熵的具体 "熵源"（如具体的重复文件、积压任务）。
    - **配置面板**: 允许按类别设置阈值。
- **集成 (`Governance.js`)**:
    - 在 Governance 页面新增 "Entropy V2" 标签页。

## Impact
- **Affected Specs**: Governance V2, Observability
- **Affected Code**:
    - `code/core/governance/entropy_control.py` (Major Refactor)
    - `code/services/bff_service.py`
    - `web/js/components/modules/Governance.js`
    - `web/js/store.js`
    - `web/js/api.js`

## ADDED Requirements
### Requirement: V2 熵值计算
系统应基于架构文档定义的六大类别计算熵值。
- **Mapping**:
    - **INPUT**: Inbox 积压数, 命名规范性
    - **EVOLUTION**: 重复 Topic, 废弃输出未归档
    - **OBSERVABILITY**: 任务缺少 Deliverable/ADR
    - **STRUCTURE**: 依赖变更频率 (Mock)
    - **BEHAVIOR**: 错误率, 延迟波动 (Mock/Log-based)
    - **DATA**: 未索引输出, 缓存命中率 (Mock)

### Requirement: 多维可视化
前端应提供雷达图和趋势图。
- **Scenario**: 监控分析
    - **WHEN** 用户访问 Entropy 面板
    - **THEN** 展示六维雷达图，直观定位熵增主要来源（如 Input 过高表示需求输入混乱）。

## MODIFIED Requirements
### Requirement: 现有指标迁移
原有的 `retrieval_time`, `inbox_stale_count` 等指标需作为底层数据源，聚合到新的 V2 类别中，不再单独作为顶层指标展示。
