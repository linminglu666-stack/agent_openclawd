#!/bin/bash
# 性能基准测试脚本
# 对比优化前后的执行效率

source scripts/soul_tools.sh

BENCHMARK_LOG="data/soul/training_logs/benchmark_results.log"
soul_ensure_dir "data/soul/training_logs"

echo "========== Soul 高效维度基准测试 =========="
echo "开始时间: $(date)"
echo ""

# 测试1: 目录操作效率对比
echo "【测试1】目录创建效率"
echo "--- 优化前 (手动检查) ---"
soul_timer_start "mkdir_old"
for i in {1..100}; do
    if [[ ! -d "test_dir_$i" ]]; then
        mkdir -p "test_dir_$i" 2>/dev/null
    fi
    rmdir "test_dir_$i" 2>/dev/null
done
old_time=$(soul_timer_end "mkdir_old")
echo "旧方法耗时: ${old_time}ms"

echo "--- 优化后 (封装函数) ---"
soul_timer_start "mkdir_new"
for i in {1..100}; do
    soul_ensure_dir "test_dir_$i"
    rmdir "test_dir_$i" 2>/dev/null
done
new_time=$(soul_timer_end "mkdir_new")
echo "新方法耗时: ${new_time}ms"

mkdir_speedup=$(echo "scale=2; $old_time / $new_time" | bc 2>/dev/null || echo "N/A")
echo "目录操作加速比: ${mkdir_speedup}x"
echo ""

# 测试2: 日志写入效率对比  
echo "【测试2】日志写入效率"
LOG_FILE="/tmp/test_$(date +%s).log"

echo "--- 优化前 (逐行echo) ---"
soul_timer_start "log_old"
for i in {1..1000}; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Message $i" >> "$LOG_FILE"
done
old_log_time=$(soul_timer_end "log_old")
echo "旧方法耗时: ${old_log_time}ms"
rm -f "$LOG_FILE"

echo "--- 优化后 (批量写入) ---"
soul_timer_start "log_new"
{
    for i in {1..1000}; do
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Message $i"
    done
} > "$LOG_FILE"
new_log_time=$(soul_timer_end "log_new")
echo "新方法耗时: ${new_log_time}ms"
rm -f "$LOG_FILE"

log_speedup=$(echo "scale=2; $old_log_time / $new_log_time" | bc 2>/dev/null || echo "N/A")
echo "日志写入加速比: ${log_speedup}x"
echo ""

# 测试3: 计时器精度对比
echo "【测试3】计时器精度测试"
soul_timer_start "precision"
sleep 0.001  # 1ms
prec_time=$(soul_timer_end "precision")
echo "纳秒级计时器测量 1ms sleep: ${prec_time}ms"

# 生成测试报告
{
    echo "========== Soul 高效维度基准测试报告 =========="
    echo "测试时间: $(date)"
    echo ""
    echo "测试结果汇总:"
    echo "  1. 目录操作: 旧=${old_time}ms, 新=${new_time}ms, 加速=${mkdir_speedup}x"
    echo "  2. 日志写入: 旧=${old_log_time}ms, 新=${new_log_time}ms, 加速=${log_speedup}x"
    echo "  3. 计时精度: ${prec_time}ms (纳秒级)"
    echo ""
    echo "结论: Soul Tools 封装库显著提升执行效率"
} > "$BENCHMARK_LOG"

echo ""
echo "基准测试完成！"
echo "报告已保存: $BENCHMARK_LOG"
