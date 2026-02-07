# Plan596 仓库脚手架与基础目录

## 目标
建立可扩展目录骨架。

## 代码
```bash
mkdir -p src/{scheduler,orchestrator,workers,memory,kg,search,bff,plugins,shared}
mkdir -p config scripts tests migrations data/{state,events,index,archive}
touch src/__init__.py
```

## 验收
- 目录创建完成
- `rg --files src` 可见模块
