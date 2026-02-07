# Runbook: Scheduler + Orchestrator

## 1. 部署
1. 创建运行用户 `openclawd`。
2. 初始化目录 `/etc/openclawd` `/var/lib/openclawd` `/run/openclawd`。
3. 启动 systemd 服务（或 bootstrap）。
4. 配置 Windows Task Scheduler 拉起 WSL。

## 2. 例行检查
- 服务存活
- 最近 1h 成功率
- misfire 与 lost run
- 备份状态

## 3. 故障处置
- 调度停摆：检查 systemd/锁文件/DB 锁。
- run 卡死：标记 lost，按策略补跑。
- 索引损坏：触发重建。
- 高失败率：切换降级策略并告警。

## 4. 恢复演练
- 每周一次：备份恢复 + 事件重放 + 随机抽样验收。
