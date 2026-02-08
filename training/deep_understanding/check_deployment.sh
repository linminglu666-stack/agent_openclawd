#!/bin/bash
# 深度理解训练系统部署状态检查脚本

echo "================================================================================"
echo "🧠 深度理解训练系统 v6.0 - 部署状态检查"
echo "================================================================================"
echo ""

# 检查调度器状态
echo "📊 调度器状态:"
systemctl is-active openclawd-scheduler.service > /dev/null 2>&1 && echo "  ✅ OpenClawd Scheduler: 运行中" || echo "  ❌ OpenClawd Scheduler: 未运行"

# 检查定时任务
echo ""
echo "📋 定时任务:"
python3 -c "
import sys
sys.path.insert(0, '/home/maco_six/.openclaw/workspace/agent_openclawd/10_src/scheduler')
from scheduler import get_scheduler
scheduler = get_scheduler()
for s in scheduler.list_schedules():
    if s.schedule_id == 'deep-understanding-monitor':
        status = '🟢' if s.enabled else '🔴'
        print(f'  {status} {s.schedule_id}: {s.cron} (下次: {s.next_fire_at})')
"

# 检查监控状态
echo ""
echo "🔍 监控状态:"
MONITOR_STATE="/home/maco_six/.openclaw/workspace/training/deep_understanding/monitor_state.json"
if [ -f "$MONITOR_STATE" ]; then
    echo "  状态文件存在"
    python3 -c "
import json
with open('$MONITOR_STATE', 'r') as f:
    state = json.load(f)
print(f\"  当前状态: {state.get('status', 'unknown')}\")
print(f\"  完成任务: {state.get('completed_tasks', 0)}\")
print(f\"  失败任务: {state.get('failed_tasks', 0)}\")
if state.get('current_task_id'):
    print(f\"  当前任务: {state['current_task_id']}\")
"
else
    echo "  ⚠️ 状态文件不存在 (首次运行)"
fi

# 检查训练清单
echo ""
echo "📚 训练清单:"
MANIFEST="/home/maco_six/.openclaw/workspace/training/deep_understanding/training_manifest.json"
if [ -f "$MANIFEST" ]; then
    python3 -c "
import json
with open('$MANIFEST', 'r') as f:
    m = json.load(f)
print(f\"  Plan数量: {m['metadata']['total_plans']}\")
print(f\"  总任务数: {m['metadata']['total_tasks']}\")
print(f\"  训练轮数: 50轮/Plan\")
print(f\"  思考级别: high\")
"
else
    echo "  ❌ 训练清单不存在"
fi

# 检查日志
echo ""
echo "📝 最近日志:"
LOG_FILE="/home/maco_six/.openclaw/workspace/training/deep_understanding/monitor.log"
if [ -f "$LOG_FILE" ]; then
    echo "  最后10行:"
    tail -10 "$LOG_FILE" | sed 's/^/    /'
else
    echo "  ⚠️ 日志文件不存在"
fi

echo ""
echo "================================================================================"
echo "✅ 部署状态检查完成"
echo "================================================================================"
