# Observability Standard

## 1. Metrics
- 调度：trigger_lag_ms, misfire_count, queue_depth
- 执行：run_success_rate, node_retry_count, timeout_count
- 资源：cpu_pct, mem_mb, io_wait, token_cost
- 质量：gate_pass_rate, hallucination_flag_rate

## 2. Logging
- 结构化日志（JSON）。
- 级别：debug/info/warn/error/fatal。
- 每条日志带 `trace_id/run_id/node_run_id`。

## 3. Tracing
- 跨模块链路追踪：BFF -> scheduler -> orchestrator -> worker。

## 4. 告警
- run 失败率 > 阈值
- heartbeat 超时
- 资源超预算
- 索引落后 checkpoint
