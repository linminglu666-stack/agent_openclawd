# OpenClawd 开发搬运说明书（完整版）

## 1. 目标
- 让 OpenClawd 作为“代码搬运工”执行开发，不自由发挥核心实现。
- 通过标准顺序与固定文档输入，降低 Bug 与返工概率。

## 2. 文档角色关系（最关键）

### 2.1 根目录 Plan（`Training_Manual/Plan*`）
- 作用：定义“做什么、为什么做、做到什么标准”。
- 特点：偏战略和机制，不是直接代码文件。
- 用途：确定功能边界、质量门槛和持久化要求。

### 2.2 Plan 细节层（`Training_Manual/Plan_Details/Plan*.md`）
- 作用：对每个 Plan 做执行细化与对齐说明。
- 特点：和主 Plan 一一对应，用于执行前核对。
- 用途：避免误解主计划，确保实现不跑偏。

### 2.3 开发执行层（`Training_Manual/Dev_Plans/Plan595~620.md`）
- 作用：给出可复制代码、路径、验收命令。
- 特点：直接“照着做”即可。
- 用途：把架构方案落地成稳定代码。

### 2.4 三层关系
1. 根目录 Plan 决定目标与约束。
2. Plan_Details 解释与对齐目标。
3. Dev_Plans 给出实际代码与落地步骤。

执行时必须按 1 -> 2 -> 3 顺序，不允许跳层。

## 3. Training_Manual 文件用途总览（按类别）

### A. 全局主控
- `Training_Manual/Architecture_Integrated_v1.md`：全局架构、阶段路线。
- `Training_Manual/Executable_List`：全局执行顺序。
- `Training_Manual/CATALOG.md`：目录索引与关系图。

### B. 计划体系
- `Training_Manual/Plan0`：Soul 上位约束。
- `Training_Manual/Plan1`~`Training_Manual/Plan594`：能力计划主文档。
- `Training_Manual/Plan_Details/`：每个 Plan 的细节对齐文档。

### C. 开发搬运体系
- `Training_Manual/DEV_PLAN_INDEX.md`：开发计划唯一索引。
- `Training_Manual/Dev_Plans/Plan595.md`~`Plan620.md`：可复制代码开发计划。
- `Training_Manual/OpenClawd_Development_Handbook.md`：本手册。

### D. 合同与运维
- `Training_Manual/API_Contract_Run_NodeRun.md`：API/状态机。
- `Training_Manual/Schema_Contract.md`：数据契约。
- `Training_Manual/Security_RBAC_Audit.md`：安全与审计。
- `Training_Manual/Observability_Standard.md`：可观测规范。
- `Training_Manual/Test_Baseline_Chaos.md`：测试与混沌基线。
- `Training_Manual/Persistence_Final_Solution.md`：持久化方案。
- `Training_Manual/Runbook_Scheduler_Orchestrator.md`：运维手册。
- `Training_Manual/ReDeploy_Deep_Mod_Solution.md`：重部署改造方案。

## 4. 代码实现目录用途（本次已提供完整参考代码）

### 4.1 核心源码
- `src/shared/config.py`：统一配置加载。
- `src/shared/models.py`：对象模型契约。
- `src/shared/store.py`：事件存储 + 状态仓储。
- `src/shared/obs.py`：日志与指标。
- `src/scheduler/service.py`：调度服务。
- `src/orchestrator/service.py`：编排执行服务。
- `src/workers/base.py`：Worker 接口与默认实现。
- `src/memory/service.py`：记忆城堡写入。
- `src/kg/service.py`：知识图谱写入。
- `src/search/adapter.py`：搜索适配层。
- `src/plugins/extension_manager.py`：扩展管理。
- `src/plugins/sandbox.py`：插件沙箱策略。
- `src/bff/app.py`：Flask API 与事件接入。
- `src/bff/security.py`：RBAC + 审计。
- `src/bff/sse.py`：SSE 事件流。

### 4.2 脚本与质量
- `scripts/bootstrap.sh`：一键启动。
- `scripts/quality_gate.sh`：质量门命令。
- `scripts/backup.sh`：备份。
- `scripts/restore.sh`：恢复。
- `tests/test_smoke.py`：最小冒烟测试。
- `docs/bug_triage.md`：缺陷分级。
- `docs/release_checklist.md`：发布检查项。
- `docs/runbook.md`：运维操作手册。

## 5. 搬运执行流程（强制）
1. 读取 `Architecture_Integrated_v1.md` 确认当前 Stage。
2. 读取 `Executable_List` 确认执行顺序。
3. 读取对应 `Plan` 与 `Plan_Details`，锁定边界。
4. 执行对应 `Dev_Plans` 代码搬运。
5. 运行验收与质量门。
6. 失败则停止并回滚，不进入下个计划。

## 6. 质量与防 Bug规则
- 不改写 Dev_Plans 提供的代码语义。
- 每个变更必须有日志与审计。
- 每个阶段必须可回滚。
- 不通过测试，不允许推进。
- 原则（新增）：如非存在明确 BUG，或致命高风险错误代码，不要大改代码思路与架构路径。

## 7. 最小验收命令
```bash
python3 -m pytest -q
python3 -m src.bff.app
curl http://127.0.0.1:8080/health
```

## 8. 变更同步规则
新增或修改开发计划时，必须同步更新：
1. `Training_Manual/DEV_PLAN_INDEX.md`
2. `Training_Manual/OpenClawd_Development_Handbook.md`
3. `Training_Manual/Architecture_Integrated_v1.md`
4. `Training_Manual/Executable_List`
5. 对应 `Training_Manual/Plan_Details/Plan*.md`
