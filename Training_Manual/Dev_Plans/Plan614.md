# Plan614 备份恢复工具链

## 目标
状态和事件可备份可恢复。

## 代码（`scripts/backup.sh`）
```bash
#!/usr/bin/env bash
set -e
mkdir -p backup
cp -r data/state backup/state_$(date +%F_%H%M%S)
cp -r data/events backup/events_$(date +%F_%H%M%S)
```

## 代码（`scripts/restore.sh`）
```bash
#!/usr/bin/env bash
set -e
src="$1"
cp -r "$src"/* data/
```

## 验收
- 可完成备份并恢复
