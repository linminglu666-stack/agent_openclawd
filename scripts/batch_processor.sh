#!/bin/bash
# 高效批量日志处理器 - 优化版本
# 对比：逐行处理 vs 批量处理

source scripts/soul_tools.sh

soul_ensure_dir "data/soul/training_logs"
OUTPUT_FILE="data/soul/training_logs/optimized_output.log"

soul_info "开始批量日志处理优化测试"

# 生成测试数据
soul_timer_start "data_gen"
TEST_DATA_FILE="/tmp/test_data_$$.txt"
for i in {1..5000}; do
    echo "log_entry_$i|$(date +%s)|INFO|Test message $i"
done > "$TEST_DATA_FILE"
data_gen_time=$(soul_timer_end "data_gen")
soul_info "测试数据生成完成: ${data_gen_time}ms (5000条记录)"

# 方法1: 逐行处理（低效）
soul_info "【方法1】逐行处理模式..."
soul_timer_start "method1"
while IFS= read -r line; do
    id=$(echo "$line" | cut -d'|' -f1)
    ts=$(echo "$line" | cut -d'|' -f2)
    level=$(echo "$line" | cut -d'|' -f3)
    msg=$(echo "$line" | cut -d'|' -f4)
    echo "[$ts] [$level] $id: $msg" >> "${OUTPUT_FILE}.method1"
done < "$TEST_DATA_FILE"
method1_time=$(soul_timer_end "method1")
soul_info "逐行处理耗时: ${method1_time}ms"

# 方法2: 批量awk处理（高效）
soul_info "【方法2】批量AWK处理模式..."
soul_timer_start "method2"
awk -F'|' '{
    printf "[%s] [%s] %s: %s\n", $2, $3, $1, $4
}' "$TEST_DATA_FILE" > "${OUTPUT_FILE}.method2"
method2_time=$(soul_timer_end "method2")
soul_info "批量AWK耗时: ${method2_time}ms"

# 方法3: 批量子shell处理（平衡）
soul_timer_start "method3"
{
    while IFS='|' read -r id ts level msg; do
        printf "[%s] [%s] %s: %s\n" "$ts" "$level" "$id" "$msg"
    done < "$TEST_DATA_FILE"
} > "${OUTPUT_FILE}.method3"
method3_time=$(soul_timer_end "method3")
soul_info "批量子shell耗时: ${method3_time}ms"

# 计算加速比
echo ""
echo "========== 性能对比结果 =========="
echo "逐行处理 (方法1): ${method1_time}ms"
echo "批量AWK (方法2): ${method2_time}ms"
echo "批量子shell (方法3): ${method3_time}ms"
echo ""

if command -v bc > /dev/null 2>&1; then
    speedup1=$(echo "scale=2; $method1_time / $method2_time" | bc)
    speedup2=$(echo "scale=2; $method1_time / $method3_time" | bc)
    echo "AWK加速比 vs 逐行: ${speedup1}x"
    echo "子shell加速比 vs 逐行: ${speedup2}x"
fi

# 验证输出一致性
line_count1=$(wc -l < "${OUTPUT_FILE}.method1")
line_count2=$(wc -l < "${OUTPUT_FILE}.method2")
line_count3=$(wc -l < "${OUTPUT_FILE}.method3")
echo ""
echo "输出一致性验证:"
echo "  方法1行数: $line_count1"
echo "  方法2行数: $line_count2"
echo "  方法3行数: $line_count3"

# 清理
rm -f "$TEST_DATA_FILE" "${OUTPUT_FILE}.method1" "${OUTPUT_FILE}.method2" "${OUTPUT_FILE}.method3"

soul_info "批量日志处理测试完成"
