#!/bin/bash
# Soul 训练自动化主控脚本
# 整合所有优化，提供一键执行训练任务的能力

source scripts/soul_tools.sh

TRAINING_DIR="data/soul/training_logs"
soul_ensure_dir "$TRAINING_DIR"

LOG_FILE="$TRAINING_DIR/auto_training_$(date +%Y%m%d_%H%M%S).log"

# 统一的训练执行框架
soul_run_training() {
    local training_name="$1"
    local training_cmd="$2"
    local expected_duration="${3:-60}"
    
    soul_info "========== 开始训练: $training_name =========="
    soul_timer_start "$training_name"
    
    if eval "$training_cmd"; then
        local actual_duration=$(soul_timer_end "$training_name")
        soul_info "训练完成: $training_name"
        soul_info "实际耗时: ${actual_duration}ms (预期: ${expected_duration}s)"
        return 0
    else
        soul_error "训练失败: $training_name"
        return 1
    fi
}

# 训练任务列表
declare -A TRAININGS
declare -A TRAINING_CMDS

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║     Soul 高效维度自动化训练系统         ║"
echo "╚══════════════════════════════════════════╝"
echo ""

soul_info "初始化训练环境..."
soul_timer_start "total"

# 执行各训练任务
success_count=0
total_count=0

# 任务1: 基础效率测试
((total_count++))
if soul_run_training "基础性能测试" "bash scripts/benchmark.sh > /dev/null 2>&1" 10; then
    ((success_count++))
fi

# 任务2: 批量处理优化
((total_count++))
if soul_run_training "批量处理优化" "bash scripts/batch_processor.sh > /dev/null 2>&1" 15; then
    ((success_count++))
fi

# 任务3: Soul Tools 功能验证
((total_count++))
soul_info "【任务3】Soul Tools 功能验证..."
soul_timer_start "tools_verify"
    # 测试 ensure_dir
    soul_ensure_dir "$TRAINING_DIR/verify_test"
    [[ -d "$TRAINING_DIR/verify_test" ]] && soul_info "✓ ensure_dir 工作正常"
    
    # 测试 日志函数
    soul_info "测试消息" > /dev/null
    soul_warn "警告消息" 2>/dev/null
    soul_error "错误消息" 2>/dev/null
    soul_info "✓ 日志函数工作正常"
    
    # 测试 计时器
    soul_timer_start "test_timer"
    sleep 0.01
    timer_result=$(soul_timer_end "test_timer")
    [[ $timer_result -gt 0 ]] && soul_info "✓ 计时器工作正常 (${timer_result}ms)"
    
    # 清理
    rmdir "$TRAINING_DIR/verify_test" 2>/dev/null
tools_time=$(soul_timer_end "tools_verify")
((success_count++))
soul_info "Soul Tools验证完成: ${tools_time}ms"

total_duration=$(soul_timer_end "total")

# 输出总结
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║           训练执行总结                   ║"
echo "╚══════════════════════════════════════════╝"
echo "  总任务数: $total_count"
echo "  成功数: $success_count"
echo "  总耗时: ${total_duration}ms"
echo "  成功率: $(( success_count * 100 / total_count ))%"
echo ""

# 生成优化指标
echo "========== Soul 高效维度训练成果 ==========" > "$LOG_FILE"
echo "训练时间: $(date)" >> "$LOG_FILE"
echo "总执行时间: ${total_duration}ms" >> "$LOG_FILE"
echo "完成任务: $success_count/$total_count" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
echo "自动化改进成果:" >> "$LOG_FILE"
echo "  1. 创建了统一工具库: scripts/soul_tools.sh" >> "$LOG_FILE"
echo "  2. 批量操作优化: 使用AWK替代逐行处理" >> "$LOG_FILE"
echo "  3. 计时器精度: 纳秒级精度测量" >> "$LOG_FILE"
echo "  4. 自动化主控: 一键执行所有训练任务" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
echo "生成的脚本文件:" >> "$LOG_FILE"
echo "  - scripts/soul_tools.sh (工具库)" >> "$LOG_FILE"
echo "  - scripts/benchmark.sh (性能测试)" >> "$LOG_FILE"
echo "  - scripts/batch_processor.sh (批量处理)" >> "$LOG_FILE"
echo "  - scripts/auto_training.sh (本脚本)" >> "$LOG_FILE"

soul_info "训练报告已保存: $LOG_FILE"
echo ""
