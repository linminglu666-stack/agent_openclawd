# OpenClawd 持久化最终方案

## 1. 目标
- 重启恢复：支持 WSL 停止、Windows 重启后的自动恢复。
- 数据可靠：事件不丢、状态可追溯、索引可重建。
- 成本可控：冷热分层、TTL 缓存、周期归档。

## 2. 存储架构

### 2.1 事件真相源（不可覆盖）
- 介质：JSONL append-only。
- 路径：`/var/lib/openclawd/events/`。
- 内容：schedule 变更、run/nodeRun 生命周期、审计、记忆 delta、搜索证据。

### 2.2 运行状态库（可覆盖）
- 介质：SQLite + WAL。
- 路径：`/var/lib/openclawd/state/openclawd.db`。
- 内容：schedules/runs/node_runs/work_items/locks/heartbeats。

### 2.3 检索索引库（可重建）
- 介质：SQLite FTS/倒排索引。
- 路径：`/var/lib/openclawd/index/`。
- 内容：全文检索索引、标签索引、时间索引、证据索引。

### 2.4 归档层（冷存）
- 介质：压缩包（zstd）。
- 路径：`/var/lib/openclawd/archive/YYYY-MM/`。
- 策略：月归档，保留 180 天。

## 3. 一致性与事务
- 写路径顺序：`event_log -> state_db -> index_db`。
- 失败策略：
  - event_log 失败：整事务失败（必须 fail-loud）。
  - state_db 失败：回滚并告警。
  - index_db 失败：标记 `index_dirty`，后台重建。

## 4. 恢复流程
1. 读取 checkpoint。
2. 重放 checkpoint 后事件。
3. 修复未完成 run/nodeRun。
4. 标记失联 `lost` 并按策略补跑。
5. 校验索引 freshness，不新鲜则重建。

## 5. WSL 双层恢复
- Linux 层：systemd/守护进程常驻。
- Windows 层：Task Scheduler 拉起 `wsl.exe`。
- 必要性：两层必须同时存在，缺一会导致跨系统重启恢复不完整。

## 6. 备份与演练
- 每 6 小时在线备份状态库。
- 每日全量备份事件与索引。
- 每周执行恢复演练（restore + replay + 抽检）。

## 7. 保留与清理
- 热数据（状态与近期索引）：30 天。
- 冷数据归档：180 天。
- 搜索缓存：热查询 1h，普通 24h。

## 8. 验收标准
- 重启后 5 分钟内恢复调度能力。
- 最近 7 天事件重放一致率 100%。
- 备份恢复演练连续 4 周通过。
