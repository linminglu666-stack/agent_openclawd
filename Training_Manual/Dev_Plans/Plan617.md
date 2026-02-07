# Plan617 一键集成启动器

## 目标
降低部署和联调复杂度。

## 代码（`scripts/bootstrap.sh`）
```bash
#!/usr/bin/env bash
set -e
python -m src.bff.app &
# add scheduler/orchestrator start here
wait
```

## 验收
- 单命令可启动核心服务
