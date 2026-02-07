# Plan615 混沌演练与自动回滚

## 目标
故障可注入、可恢复、可回滚。

## 代码（`scripts/chaos_kill_scheduler.sh`）
```bash
#!/usr/bin/env bash
pkill -f "src.scheduler.service" || true
```

## 代码（`scripts/auto_rollback.sh`）
```bash
#!/usr/bin/env bash
set -e
git checkout "$1"
```

## 验收
- 演练后能恢复到可用状态
