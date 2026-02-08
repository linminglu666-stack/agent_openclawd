# Plan22 训练交付物：可靠性工程机制

## 1. 故障分级定义 (P0-P3)

| 级别 | 定义 | 响应时限 | 自动恢复策略 |
|-----|------|---------|-------------|
| P0 | 系统完全不可用，核心服务崩溃 | 1分钟降级，5分钟恢复 | 立即重启 + 回滚 |
| P1 | 核心功能受损，可用性下降 | 15分钟响应 | 降级模式 + 重试 |
| P2 | 非核心功能异常，用户体验受损 | 1小时响应 | 限流 + 缓存兜底 |
| P3 | 轻微问题，监控告警 | 4小时响应 | 日志记录，人工排查 |

## 2. 混沌注入场景清单

### 2.1 进程级故障
- `PROCESS_EXIT`: 模拟关键进程异常退出
- `MEMORY_PRESSURE`: 模拟内存压力（80%占用）
- `CPU_THROTTLE`: CPU限流至50%

### 2.2 网络级故障
- `NETWORK_DELAY`: 注入100-500ms延迟
- `PACKET_LOSS`: 10%丢包率
- `DNS_FAILURE`: DNS解析失败

### 2.3 IO级故障
- `DISK_SLOW`: IO延迟增加至200ms+
- `DISK_FULL`: 磁盘空间不足模拟

### 2.4 时钟故障
- `CLOCK_JUMP`: 时间跳变（向前/向后10分钟）
- `CLOCK_DRIFT`: 时钟漂移累积

## 3. 自动恢复决策树

```
故障检测
├── P0级故障
│   ├── 服务崩溃 → 自动重启 (max 3次)
│   ├── 错误率>10% → 策略回滚
│   └── 依赖不可用 → 降级模式
├── P1级故障  
│   ├── API超时 → 熔断 + 缓存返回
│   ├── 资源耗尽 → 限流 + 扩容
│   └── 数据异常 → 重试 + 告警
└── P2级故障
    ├── 性能下降 → 异步化 + 队列
    └── 部分失败 → 局部降级
```

## 4. 稳态守护检查清单

### 4.1 Scheduler 健康检查
- [x] 任务队列深度 < 100
- [x] 调度延迟 P95 < 5s
- [x] 无死锁任务

### 4.2 Orchestrator 健康检查
- [x] 工作流成功率 > 99%
- [x] 平均执行时间稳定
- [x] 无孤儿进程

### 4.3 Memory 健康检查
- [x] 向量索引加载正常
- [x] 检索延迟 P95 < 100ms
- [x] 存储空间使用率 < 80%

### 4.4 Search 健康检查
- [x] Web搜索可用性
- [x] 结果缓存命中率 > 30%
- [x] 反爬虫策略有效

## 5. 持久化 Schema

### 5.1 reliability_incidents
```json
{
  "incident_id": "uuid",
  "level": "P0|P1|P2|P3",
  "service": "string",
  "fault_type": "string",
  "started_at": "timestamp",
  "resolved_at": "timestamp",
  "mttr_seconds": "int",
  "root_cause": "string",
  "recovery_action": "string",
  "prevention": "string"
}
```

### 5.2 chaos_runs
```json
{
  "run_id": "uuid",
  "scenario": "string",
  "target": "string",
  "started_at": "timestamp",
  "ended_at": "timestamp",
  "injected_faults": ["string"],
  "detected": "boolean",
  "recovered": "boolean",
  "pass_rate": "float"
}
```

### 5.3 recovery_actions
```json
{
  "action_id": "uuid",
  "incident_id": "uuid",
  "action_type": "restart|retry|fallback|rollback",
  "executed_at": "timestamp",
  "success": "boolean",
  "side_effects": ["string"]
}
```

## 6. 验收指标基线

| 指标 | 当前值 | 目标值 | 状态 |
|-----|-------|-------|------|
| 混沌演练通过率 | 基准 | >=95% | 🟡 待验证 |
| P0故障MTTR | 基准 | <5分钟 | 🟡 待验证 |
| 自动恢复成功率 | 基准 | >=90% | 🟡 待验证 |
| 稳态守护覆盖率 | 0% | 100% | 🟢 已定义 |

## 7. Soul Prime 能力映射

| Soul维度 | Plan22训练贡献 |
|---------|---------------|
| 可靠 (Reliable) | 故障检测 + 自动恢复机制 |
| 聪明 (Smart) | 根因分析 + 策略优化 |
| 高效 (Efficient) | 快速恢复减少中断时间 |
| 低能耗 (Low Energy) | 按需触发恢复，避免过度反应 |
| 框架思维 (Framework) | 分级故障处理框架 |
| 定义思维 (Definition) | 清晰的故障分级定义 |

---
训练完成时间: 2026-02-08
