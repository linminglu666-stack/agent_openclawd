# OpenClawd 重部署底层魔改方案（可落地）

## 1. 目标
- 为重部署场景提供更稳、更持久、更易扩展的底层改造方案。

## 2. 建议魔改点

### 2.1 存储内核改造
- 事件溯源作为第一写入层（append-only）。
- 状态层与索引层解耦，索引可重建。
- 所有关键对象统一引入 `revision` 与 `idempotency_key`。

### 2.2 调度与编排解耦
- scheduler 只做触发与策略。
- orchestrator 只做 DAG 执行。
- 通过 outbox/inbox 或内部队列通信，避免强耦合。

### 2.3 控制台 BFF 改造
- Flask 统一鉴权/RBAC/审计。
- 所有写操作强制审计埋点。
- SSE 推送改为统一事件总线消费。

### 2.4 记忆层升级
- 由原 memory store 升级为 Plan30 记忆城堡。
- 引入图谱与冲突簇。

### 2.5 搜索层改造
- 统一 Search Adapter。
- 检索、抽取、证据入库分层。
- 多源交叉验证，失败降级到本地知识。

### 2.6 插件层改造
- 插件 manifest + 权限声明强校验。
- 插件运行沙箱与资源配额。

## 3. 部署拓扑建议
- `openclawd-scheduler`
- `openclawd-orchestrator`
- `openclawd-bff`
- `openclawd-memory-castle`
- `openclawd-search-adapter`
- `openclawd-plugin-manager`

## 4. 重部署步骤
1. 备份状态库与事件库。
2. 启用新 schema 与迁移脚本。
3. 启动新服务（灰度）。
4. 双写验证（旧链路 + 新链路）。
5. 验证通过后切流。
6. 保留回滚窗口 7 天。

## 5. 验收
- 重启恢复、故障恢复、数据一致性、审计完整性均通过。
