#!/usr/bin/env python3
"""
Git自动推送定时任务配置
使用OpenClawd Scheduler每12小时执行一次
"""

import sys
sys.path.insert(0, '/home/maco_six/.openclaw/workspace/agent_openclawd/10_src/scheduler')

from scheduler import get_scheduler, Schedule, MisfirePolicy, ConcurrencyMode

scheduler = get_scheduler()

# 创建Git自动推送任务 (每12小时)
git_push_schedule = Schedule(
    schedule_id='git-auto-push',
    name='Git自动推送任务',
    cron='0 */12 * * *',  # 每12小时执行一次 (00:00 和 12:00)
    timezone='Asia/Shanghai',
    command='bash /home/maco_six/.openclaw/workspace/scripts/git_auto_push.sh',
    enabled=True,
    misfire_policy=MisfirePolicy.RUN_ONCE,
    concurrency=ConcurrencyMode.FORBID,  # 禁止并发，避免推送冲突
    timeout_sec=300,  # 5分钟超时
    retries=3,  # 失败重试3次
    backoff_sec=[60, 300, 600]  # 重试间隔：1分钟, 5分钟, 10分钟
)

# 删除旧任务（如果存在）
try:
    scheduler.remove_schedule('git-auto-push')
    print('🗑️  旧任务已删除')
except:
    pass

# 添加新任务
scheduler.add_schedule(git_push_schedule)

print('=' * 70)
print('✅ Git自动推送任务已配置')
print('=' * 70)
print(f'任务ID: {git_push_schedule.schedule_id}')
print(f'执行频率: 每12小时 (00:00 和 12:00)')
print(f'下次执行: {git_push_schedule.next_fire_at}')
print(f'超时: {git_push_schedule.timeout_sec}秒')
print(f'重试: {git_push_schedule.retries}次')
print('=' * 70)

# 列出所有调度任务
print('\n📋 当前所有定时任务:')
for s in scheduler.list_schedules():
    status = '🟢' if s.enabled else '🔴'
    print(f'  {status} {s.schedule_id}: {s.cron} - {s.name}')
