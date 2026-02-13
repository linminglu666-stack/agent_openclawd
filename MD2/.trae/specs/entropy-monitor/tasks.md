# Tasks

- [ ] Task 1: 后端核心逻辑重构 - Entropy Governance V2
    - [ ] SubTask 1.1: 在 `EntropyControlCenter` 中定义 `EntropyCategory` 枚举及新的 `EntropyMetrics` 数据结构（包含 INPUT, EVOLUTION, OBSERVABILITY, STRUCTURE, BEHAVIOR, DATA 六大类）。
    - [ ] SubTask 1.2: 重构 `compute_metrics`，实现现有指标（如 inbox_stale）到新类别的映射，并补充 STRUCTURE/BEHAVIOR/DATA 的（模拟或基于日志的）计算逻辑。
    - [ ] SubTask 1.3: 实现历史数据存储 (`EntropyHistory`)，支持按类别记录时间序列。
    - [ ] SubTask 1.4: 实现阈值配置管理 (`EntropyConfig`)，支持按类别设置告警阈值。

- [ ] Task 2: 后端 API 接口升级
    - [ ] SubTask 2.1: 升级 `BFF Service` 的 `/v1/governance/entropy` 接口，支持返回 V2 格式的详细指标。
    - [ ] SubTask 2.2: 新增 `GET /v1/governance/entropy/history` 接口，返回历史趋势数据。
    - [ ] SubTask 2.3: 新增 `GET/POST /v1/governance/entropy/config` 接口，支持读写配置。
    - [ ] SubTask 2.4: 更新并运行验证脚本 (`verify_entropy_v2.py`)，确保 API 行为符合预期。

- [ ] Task 3: 前端数据层适配
    - [ ] SubTask 3.1: 更新 `web/js/api.js`，适配新的 V2 接口（mock 或真实调用）。
    - [ ] SubTask 3.2: 更新 `web/js/store.js`，新增 `entropy` 模块，管理六维指标、历史趋势及配置状态。

- [ ] Task 4: 前端可视化组件开发
    - [ ] SubTask 4.1: 创建 `web/js/components/modules/EntropyMonitor.js`，设计包含雷达图、趋势图和详情列表的布局。
    - [ ] SubTask 4.2: 使用 `charts.js` 实现六维雷达图（展示当前各类别熵值分布）。
    - [ ] SubTask 4.3: 使用 `charts.js` 实现历史趋势折线图。
    - [ ] SubTask 4.4: 实现配置面板，支持调整各类别阈值。
    - [ ] SubTask 4.5: 集成到 `web/js/components/modules/Governance.js`，新增 "Entropy V2" 标签页。

- [ ] Task 5: 验证与文档
    - [ ] SubTask 5.1: 运行全链路测试（API -> Frontend），验证数据流转及图表渲染。
    - [ ] SubTask 5.2: 编写 V2 算法说明文档及 API 文档。

# Task Dependencies
- Task 2 depends on Task 1
- Task 4 depends on Task 3
- Task 3 depends on Task 2
