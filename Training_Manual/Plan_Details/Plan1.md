# Plan1 详情（与主计划对齐）

- 对应主计划：Training_Manual/Plan1
- 主计划标题：Agent Autonomous Heartbeat - 底层架构

## 核心要点索引（来自主计划）
31:1. 自主唤醒（自我唤醒）
41:2. 双层心跳

## 计划原文摘录
Agent Autonomous Heartbeat - 底层架构
架构层级对比
┌─────────────────────────────────────────────────────────────────┐
│                        应用层 (User)                             │
│                      人类与Agent交互                             │
├─────────────────────────────────────────────────────────────────┤
│                        Skill层                                   │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│   │  heartbeat  │  │   weather   │  │    git      │            │
│   │  -engine    │  │             │  │             │            │
│   └─────────────┘  └─────────────┘  └─────────────┘            │
│   【被动调用】被Agent调用才执行                                   │
├─────────────────────────────────────────────────────────────────┤
│                        Agent核心层 ⭐                            │
│   ┌───────────────────────────────────────────────────────┐    │
│   │              Autonomous Heartbeat                      │    │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │    │
│   │  │ Self     │  │ Growth   │  │ Decision │            │    │
│   │  │ Reflection│  │ Engine   │  │ Engine   │            │    │
│   │  └──────────┘  └──────────┘  └──────────┘            │    │
│   │  【自主运行】自己唤醒自己，不需要外部触发                   │    │
│   └───────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                        Gateway层                                 │
│   Cron调度 → agentTurn/isolated session → Heartbeat Agent      │
├─────────────────────────────────────────────────────────────────┤
│                        基础设施层                                │
│   文件系统 (agent-self/*.json) / 日志 / 配置                     │
└─────────────────────────────────────────────────────────────────┘
核心设计原则
1. 自主唤醒（自我唤醒）
不是： 人类发消息 → Agent响应 → 检查心跳 而是： 定时器触发 → Agent自己醒来 → 自我反思 → 自主决策

Cron (每15分钟)
    ↓
Gateway创建 isolated session
    ↓
AgentTurn: "执行心跳"
    ↓
Heartbeat Agent自己驱动
2. 双层心跳
第一层：底层心跳（核心心跳）

每15分钟执行一次
在isolated session中运行
纯自我反思，不打扰用户
更新成长数据、学习模式
第二层：汇报层（通知层）

基于Layer 1的决策
只在有价值时向main session发送消息
遵循静默规则、去重机制
3. 三问钩子集成
每次心跳自动执行：

def autonomous_heartbeat():
    # 1. 身份检查：我是谁？
    identity = load_identity()
    logger.info(f"我是 {identity.name}, Lv.{identity.level} {identity.title}")
    
    # 2. 动机检查：我想做什么？
    motivation = load_motivation()
    pending = scan_pending_tasks()
    patterns = analyze_patterns()
    
    # 3. 代价检查：值得做吗？
    cost = estimate_cost()
    benefit = estimate_benefit(pending, patterns)
    roi = calculate_roi(cost, benefit)
    
    # 决策
    if should_notify(roi, context):
        notify_main_session(format_message(pending, identity))
    else:
        log_silent_heartbeat()
    
    # 成长
    update_growth_experience()
数据流
单次心跳流程
Cron触发 (15分钟间隔)
    ↓
┌──────────────────────────────────┐
│ Gateway                          │
│  - 创建 isolated session         │
│  - 注入 heartbeat context        │
└──────────────┬───────────────────┘
               ↓
┌──────────────────────────────────┐
│ Heartbeat Agent (isolated)       │
│                                  │
│  1. 读取 agent-self/identity.json│
│  2. 读取 agent-self/motivation.json
│  3. 读取 agent-self/cost-tracker.json
│  4. 读取 HEARTBEAT.md            │
│                                  │
│  【自我反思】                     │
│  - 检查等级进度                  │
│  - 分析待办任务                  │
│  - 评估代价收益                  │
│                                  │
│  【自主决策】                     │
│  - 静默时段? → 跳过              │
│  - 内容重复? → 跳过              │
│  - 有价值?   → 继续              │
│                                  │
│  【执行】                         │
│  IF 汇报:                        │
│    - 生成消息                    │
│    - sessions_send → main        │
│    - 记录消息哈希                │
│    - 更新经验 (+30)              │
│  ELSE:                           │
│    - 记录静默                    │
│    - 更新经验 (+5)               │
│                                  │
│  【保存】                         │
│  - 写回 identity.json            │
│  - 写回 motivation.json          │
│  - 写回 cost-tracker.json        │
└──────────────┬───────────────────┘
               ↓
        Session结束
        (心跳不保活)
心跳与主会话的关系
┌──────────────┐         ┌─────────────────┐
│  Main Session │         │ Heartbeat Agent │
│   (人类交互)  │◄────────│  (isolated)     │
└──────────────┘ 汇报     └─────────────────┘
       ↑                           │
       │                           │ 自我反思
       │                    ┌──────┴──────┐
       │                    │ agent-self/ │
       └────────────────────┤ identity    │
                            │ motivation  │
                            │ cost        │
                            └─────────────┘
Cron Job配置
当前配置
{
  "name": "agent-autonomous-heartbeat",
  "schedule": {
    "kind": "every",
    "everyMs": 900000  // 15分钟
  },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "执行自我反思...",
    "model": "kimi-coding/k2p5",
    "thinking": "low"
  }
}
优势
Isolated Session： 不污染main session的历史记录
agentTurn： 真正的Agent自主行为，不是system命令
低思考：节省资源，快速执行
自主决策： Agent自己决定是否汇报
静默与汇报策略
静默条件（Agent自主判断）
silent_conditions = [
    is_night_time(23, 8),           # 深夜时段
    time_since_last_check() < 30min, # 过于频繁
    no_new_information(),            # 无新信息
    user_busy(),                     # 用户忙碌
    content_duplicate_24h(),         # 24h内重复
]

if any(silent_conditions):
    return SILENT
汇报条件
notify_conditions = [
    urgent_task_detected(),          # 发现紧急事项
    deadline_approaching(),          # 截止日期临近
    important_update(),              # 重要更新
    user_away_too_long(),            # 用户长时间未交互
    interesting_discovery(),         # 有趣发现
]

if any(notify_conditions) and roi > 1.5:
