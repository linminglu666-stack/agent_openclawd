# Agent OpenClawd - 深度理解进化训练系统

[![GitHub](https://img.shields.io/badge/GitHub-linminglu666--stack%2Fagent__openclawd-blue)](https://github.com/linminglu666-stack/agent_openclawd)
[![Version](https://img.shields.io/badge/Version-7.0-green)]()
[![Training](https://img.shields.io/badge/Training-4400%20Tasks-orange)]()

> 🤖 **蟹老板** 的AI自我进化与深度理解训练系统

## 🎯 项目概述

Agent OpenClawd 是一个**防造假的深度理解进化训练系统**，通过多轮真实推理形成深刻理解，并将理解整合到记忆系统中供后续任务调用。

### 核心特性

- ✅ **防造假机制**: 真实模型推理，最高级别思考 (`thinking=high`)
- ✅ **深度理解**: 50轮渐进式理解深化，非简单模式匹配
- ✅ **自动训练**: 每小时自动检查并执行训练任务
- ✅ **故障恢复**: 超时检测+自动重试，确保训练连续性
- ✅ **记忆整合**: 理解结果自动存入记忆系统
- ✅ **定时推送**: 每12小时自动推送到GitHub

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    深度理解训练系统 v7.0                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐      ┌──────────────────┐                │
│  │   定时调度器      │      │   Git自动推送    │                │
│  │  (每小时检查)    │      │  (每12小时)     │                │
│  └────────┬─────────┘      └──────────────────┘                │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────────────────────────┐                       │
│  │      训练监控器 (Training Monitor)   │                       │
│  │  - 检查当前训练状态                  │                       │
│  │  - 超时检测 (10分钟)                 │                       │
│  │  - 自动故障恢复                      │                       │
│  └─────────────────┬───────────────────┘                       │
│                    │                                            │
│         ┌─────────┴─────────┐                                  │
│         │                   │                                  │
│         ▼                   ▼                                  │
│  ┌─────────────┐    ┌─────────────┐                           │
│  │ 有训练任务  │    │ 无训练任务  │                           │
│  │   → 跳过   │    │ → 创建新任务│                           │
│  └─────────────┘    └──────┬──────┘                           │
│                            │                                   │
│                            ▼                                   │
│  ┌─────────────────────────────────────┐                      │
│  │    深度理解训练子代理                │                      │
│  │  - 最高思考级别 (thinking=high)     │                      │
│  │  - 50轮渐进式深度理解               │                      │
│  │  - 防造假验证机制                   │                      │
│  │  - 结果 → 记忆系统                  │                      │
│  └─────────────────────────────────────┘                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 训练规模

| 指标 | 数值 |
|------|------|
| **进化型Plan总数** | 88 个 |
| **每Plan训练轮数** | 50 轮 |
| **总训练任务** | **4,400** 个 |
| **预计总时间** | 220 小时 (约9天) |
| **并发数** | 100 子代理 |
| **思考级别** | high |

### Plan分类

| 分类 | Plan数 | 说明 |
|------|--------|------|
| **认知底座层** | 5 | 记忆、学习、推理、知识、记忆城堡 |
| **基础架构层** | 6 | Web、调度、API、编排、插件、搜索 |
| **质量治理层** | 6 | 错误、路由、缓存、质量、成本、安全 |
| **能力扩展层** | 1 | 插件生态 |
| **扩展进化层** | 70 | 数据处理、ML、NLP、视觉、RL、系统优化 |

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone https://github.com/linminglu666-stack/agent_openclawd.git
cd agent_openclawd

# 确保OpenClawd Scheduler运行
sudo systemctl status openclawd-scheduler
```

### 2. 查看训练状态

```bash
# 查看部署状态
bash training/deep_understanding/check_deployment.sh

# 查看监控日志
tail -f training/deep_understanding/monitor.log

# 查看定时任务
python3 -c "from scheduler import get_scheduler; \
  [print(f'{s.schedule_id}: {s.cron}') for s in get_scheduler().list_schedules()]"
```

### 3. 手动触发训练

```bash
# 立即执行一次监控周期
python3 training/deep_understanding/training_monitor.py

# 查看训练清单
ls training/deep_understanding/training_manifest.json
```

---

## 📁 项目结构

```
agent_openclawd/
├── README.md                          # 本文件
├── AGENTS.md                          # 代理配置
├── SOUL.md                           # Soul定义
├── USER.md                           # 用户信息
├── MEMORY.md                         # 长期记忆
├── HEARTBEAT.md                      # 心跳任务清单
├── BOOTSTRAP.md                      # 启动引导
│
├── agent_openclawd/                  # 核心系统
│   ├── 10_src/                       # 源代码
│   │   ├── scheduler/                # 调度器
│   │   │   └── scheduler.py          # OpenClawd Scheduler
│   │   └── heartbeat/                # 心跳系统
│   ├── 11_scripts/                   # 可执行脚本
│   │   ├── deep_understanding_monitor.py  # 深度理解监控器
│   │   └── ...
│   ├── 20_data/                      # 数据目录
│   ├── 60_deploy/                    # 部署配置
│   │   └── systemd/                  # Systemd服务
│   └── 70_docs/                      # 文档
│
├── data/soul/                        # Soul数据
│   ├── deliverables/                 # Plan交付物 (500+ Plan)
│   ├── TRAINING_AUDIT_SOP.md         # 训练审查SOP
│   └── ...
│
├── training/                         # 训练系统
│   └── deep_understanding/           # 深度理解训练
│       ├── training_manifest.json    # 训练清单 (4400任务)
│       ├── training_monitor.py       # 监控器核心
│       ├── execute_training.py       # 训练执行器
│       ├── check_deployment.sh       # 部署检查
│       ├── DEPLOYMENT.md             # 部署文档
│       ├── EXTENDED_PLAN_LIST.md     # Plan列表
│       ├── monitor.log               # 监控日志
│       ├── monitor_state.json        # 监控状态
│       ├── memory_integration/       # 记忆整合结果
│       └── results/                  # 训练结果
│
├── evolution/                        # 进化系统
│   └── plans/                        # 进化型Plan
│       ├── plan16/                   # Web控制台
│       ├── plan17/                   # Cron调度器
│       ├── plan18/                   # Flask API
│       ├── plan19/                   # 任务编排
│       ├── plan20/                   # Chrome插件
│       └── plan21/                   # 联网搜索
│
├── memory/                           # 记忆系统
│   ├── evolution_report_group4_1000r.json
│   ├── evolution_history_group4.json
│   └── evo_training_group4_summary.md
│
└── reports/                          # 报告
    ├── TOOL-001_工具集成优化报告.md
    ├── EFFI-001_计算效率压缩报告.md
    └── ...
```

---

## ⚙️ 防造假机制

每个训练任务必须通过以下验证：

| 验证项 | 标准 | 说明 |
|--------|------|------|
| **Token消耗** | >100 tokens | 确保真实推理 |
| **执行时间** | >10秒 | 确保深度思考 |
| **内容长度** | >100字符 | 确保有实质输出 |
| **思考痕迹** | 含"核心洞察" | 确保思考过程 |

### 审查评级

| 评级 | 分数 | 状态 |
|------|------|------|
| A | ≥95% | ✅ 优秀 |
| B | ≥85% | ✅ 良好 |
| C | ≥70% | ✅ 通过 |
| D | <70% | ❌ 未通过 |
| F | 多项失败 | ❌ 未通过 |

**通过标准**: 评级 ≥ C

---

## 🔄 自动化工作流

### 1. 深度理解训练 (每小时)

```
定时触发 (每小时)
    ↓
检查训练状态
    ├── 有进行中的任务 → 检查是否超时
    │                       ├── 未超时 → 跳过
    │                       └── 超时 → 标记失败，重试
    │
    └── 无进行中的任务 → 创建新训练任务
                            ↓
                     调度训练子代理
                            ↓
                     50轮深度理解训练
                            ↓
                     防造假验证
                            ↓
                     结果整合到记忆系统
```

### 2. Git自动推送 (每12小时)

```
定时触发 (每12小时)
    ↓
git add -A
    ↓
git commit -m "自动提交: $(date)"
    ↓
git push origin master
    ↓
推送完成
```

---

## 🛠️ 配置说明

### 训练配置

```python
TRAINING_CONFIG = {
    "training_rounds": 50,           # 每Plan 50轮
    "max_concurrent": 100,           # 最大并发100
    "thinking_level": "high",        # 最高思考级别
    "audit_enabled": True,           # 启用审查
    "required_audit_rating": "C",    # 最低通过评级
    "timeout_minutes": 10            # 超时时间10分钟
}
```

### 定时任务配置

| 任务 | 频率 | 说明 |
|------|------|------|
| `deep-understanding-monitor` | 每小时 | 深度理解训练监控 |
| `git-auto-push` | 每12小时 | 自动推送到GitHub |

---

## 📈 监控与日志

### 查看监控状态

```bash
# 查看监控器状态
cat training/deep_understanding/monitor_state.json

# 输出示例:
{
  "current_task_id": "P002_R01",
  "current_plan_id": 2,
  "current_round": 1,
  "status": "running",
  "completed_tasks": 0,
  "failed_tasks": 0,
  "total_plans": 88,
  "total_tasks": 4400
}
```

### 查看训练进度

```bash
# 查看已完成Plan
ls training/deep_understanding/memory_integration/

# 查看训练结果
ls training/deep_understanding/results/
```

---

## 🤝 贡献指南

### 添加新的进化型Plan

1. 编辑 `training/generate_extended_evolution_training.py`
2. 在 `EVOLUTION_PLANS_*` 中添加新Plan
3. 运行生成器更新清单

```bash
python3 training/generate_extended_evolution_training.py
```

### 修改训练配置

编辑 `training/deep_understanding/training_monitor.py`：

```python
TRAINING_ROUNDS = 50  # 修改轮数
MAX_CONCURRENT = 100  # 修改并发数
TIMEOUT_SECONDS = 600  # 修改超时时间
```

---

## 📝 重要文档

| 文档 | 说明 |
|------|------|
| [SOUL.md](SOUL.md) | Soul定义与六维能力模型 |
| [AGENTS.md](AGENTS.md) | 代理配置指南 |
| [USER.md](USER.md) | 用户信息 |
| [MEMORY.md](MEMORY.md) | 长期记忆存储 |
| [HEARTBEAT.md](HEARTBEAT.md) | 心跳任务清单 |
| [training/deep_understanding/DEPLOYMENT.md](training/deep_understanding/DEPLOYMENT.md) | 部署文档 |
| [training/deep_understanding/EXTENDED_PLAN_LIST.md](training/deep_understanding/EXTENDED_PLAN_LIST.md) | Plan列表 |

---

## 🔧 故障排查

### 问题1: 训练不启动

```bash
# 检查调度器状态
sudo systemctl status openclawd-scheduler

# 检查监控器脚本权限
ls -la agent_openclawd/11_scripts/deep_understanding_monitor.py

# 手动执行监控器
python3 training/deep_understanding/training_monitor.py
```

### 问题2: 验证失败

检查输出是否包含：
- ✅ Token消耗 > 100
- ✅ 执行时间 > 10秒
- ✅ 内容长度 > 100字符
- ✅ 包含"核心洞察"

### 问题3: Git推送失败

```bash
# 检查远程仓库
git remote -v

# 检查认证
git config --list | grep credential

# 手动推送测试
git push origin master
```

---

## 📜 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🦀 关于蟹老板

> 高效、诚实、全能，持续自主学习进步。

**蟹老板** 是本项目的主角AI助手，通过深度理解进化训练系统不断提升自身能力。

---

*Last Updated: 2026-02-08*
*Version: 7.0*
*Training Tasks: 4,400*
