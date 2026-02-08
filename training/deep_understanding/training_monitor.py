#!/usr/bin/env python3
"""
深度理解训练监控器 - 11_scripts 包装器
"""

import sys
import os

# 添加训练目录到路径
training_dir = "/home/maco_six/.openclaw/workspace/training/deep_understanding"
sys.path.insert(0, training_dir)

# 导入并执行监控器
from training_monitor import main, log_message

if __name__ == "__main__":
    log_message("=" * 70)
    log_message("🤖 深度理解训练监控器 (由调度器触发)")
    log_message("=" * 70)
    main()
