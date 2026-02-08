#!/bin/bash
# 简化版批量日志处理器 - 快速验证
source scripts/soul_tools.sh

soul_info "开始简化版批量处理测试 (500条记录)..."

# 生成少量测试数据
TEST_DATA="/tmp/quick_test_$$.txt"
for i in {1..500}; do
    echo "log_$i|$(date +%s)|INFO|msg_$i"
done > "$TEST_DATA"

# 方法1: 逐行处理
soul_timer_start "m1"
while IFS= read -r line; do
    echo "$line" | cut -d'|' -f1 > /dev/null
done < "$TEST_DATA"
t1=$(soul_timer_end "m1")

# 方法2: 批量AWK
soul_timer_start "m2"
awk -F'|' '{print $1}' "$TEST_DATA" > /dev/null
t2=$(soul_timer_end "m2")

echo ""
echo "========== 快速性能对比 =========="
echo "逐行处理: ${t1}ms"
echo "批量AWK: ${t2}ms"

if command -v bc > /dev/null 2>&1; then
    speedup=$(echo "scale=2; $t1 / $t2" | bc)
    echo "AWK加速比: ${speedup}x"
    echo "批量处理效率提升: $(echo "scale=1; ($t1 - $t2) * 100 / $t1" | bc)%"
fi

rm -f "$TEST_DATA"
soul_info "快速测试完成"
