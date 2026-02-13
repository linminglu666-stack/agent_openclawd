# 运行目录约定（systemd StateDirectory/LogsDirectory）

本文件定义系统级服务在 Linux 上的默认落盘路径、权限与保留策略，用于保证“重启可恢复 + 运维一致性”。
## 默认路径
- 状态目录：`/var/lib/openclaw-x/`
  - `wal/`：追加写事件日志
  - `wal/`：追加写事件日志
  - `snapshots/`：快照目录
  - `db/`：SQLite（或其他本地状态库）
  - `leases/`：租约与幂等键（如按文件分片存放）
  - `skills/`：技能 registry 与缓存索引
- 日志目录：`/var/log/openclaw-x/`
  - `audit/`：审计 jsonl
  - `services/`：服务自身日志（如需额外落盘）
- 运行时目录：`/run/openclaw-x/`
  - `pid/`：PID/锁
  - `sockets/`：unix socket（如 BFF/本地 RPC）
## 权限建议
\n
- 目录权限：
  - `/var/lib/openclaw-x`：`openclaw:openclaw` 0750
- 目录权限：
  - `/var/lib/openclaw-x`：`openclaw:openclaw` 0750
  - `/var/log/openclaw-x`：`openclaw:openclaw` 0750
  - `/run/openclaw-x`：由 systemd RuntimeDirectory 创建
## 保留策略（建议默认值）
\n
- Snapshots：保留最近 20 份（或 7 天）
- Audit：保留最近 30 天（或归档到对象存储）
- Snapshots：保留最近 20 份（或 7 天）
- Audit：保留最近 30 天（或归档到对象存储）
- Evidence：按 trace_id 维度保留最近 N 条/最近 7 天
## 与 systemd 的映射
\n
- `StateDirectory=openclaw-x`（对应 /var/lib/openclaw-x）
- `LogsDirectory=openclaw-x`（对应 /var/log/openclaw-x）
- `StateDirectory=openclaw-x`（对应 /var/lib/openclaw-x）
- `LogsDirectory=openclaw-x`（对应 /var/log/openclaw-x）
- `RuntimeDirectory=openclaw-x`（对应 /run/openclaw-x）
服务入口读取这些路径时，优先使用环境变量：
- `OPENCLAW_STATE_DIR`（默认 /var/lib/openclaw-x）
- `OPENCLAW_STATE_DIR`（默认 /var/lib/openclaw-x）
- `OPENCLAW_LOG_DIR`（默认 /var/log/openclaw-x）
- `OPENCLAW_RUNTIME_DIR`（默认 /run/openclaw-x）
