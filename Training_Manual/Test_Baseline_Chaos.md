# Test Baseline and Chaos

## 1. 基线测试
- 单元：路由/状态机/校验器
- 集成：scheduler + orchestrator + sqlite
- e2e：从 schedule 到 summary 全链路

## 2. Golden 测试
- 关键任务固定输入，输出对比基线。
- 变更后必须通过回归对比。

## 3. 混沌测试
- kill scheduler 进程 -> 自动恢复
- kill worker 进程 -> run 标记 lost + 恢复
- 时钟跳变 -> misfire 策略正确
- IO 限速 -> 超时与退避生效

## 4. 验收门槛
- 关键链路通过率 >= 99%
- 故障恢复时间在 SLO 范围内
