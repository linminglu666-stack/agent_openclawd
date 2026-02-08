#!/bin/bash
# Soul Tools - 高效自动化脚本库
# 功能: 提供常用操作的统一封装，减少重复代码

SOUL_LOG_DIR="${SOUL_LOG_DIR:-./logs}"
SOUL_TIMESTAMP_FORMAT="${SOUL_TIMESTAMP_FORMAT:-%Y-%m-%d %H:%M:%S.%3N}"

# 确保目录存在
soul_ensure_dir() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir" 2>/dev/null
        return $?
    fi
    return 0
}

# 统一日志输出
soul_log() {
    local level="$1"
    local msg="$2"
    local timestamp
    timestamp=$(date +"$SOUL_TIMESTAMP_FORMAT")
    echo "[$timestamp] [$level] $msg"
}

soul_info() { soul_log "INFO" "$1"; }
soul_warn() { soul_log "WARN" "$1" >&2; }
soul_error() { soul_log "ERROR" "$1" >&2; }

# 性能计时器
soul_timer_start() {
    local name="${1:-default}"
    eval "SOUL_TIMER_${name}=$(date +%s%N)"
}

soul_timer_end() {
    local name="${1:-default}"
    local start_var="SOUL_TIMER_${name}"
    local start_time=${!start_var}
    local end_time=$(date +%s%N)
    local duration_ms=$(( (end_time - start_time) / 1000000 ))
    echo "$duration_ms"
}

soul_timer_log() {
    local name="$1"
    local operation="$2"
    local duration=$(soul_timer_end "$name")
    soul_info "[$operation] 耗时: ${duration}ms"
}

# 文件写入（原子操作）
soul_write_file() {
    local file="$1"
    local content="$2"
    local tmp_file="${file}.tmp.$$"
    
    soul_ensure_dir "$(dirname "$file")" || return 1
    echo -e "$content" > "$tmp_file" && mv "$tmp_file" "$file"
    return $?
}

# 安全清理临时文件
soul_cleanup() {
    local pattern="${1:-*.tmp.*}"
    find . -name "$pattern" -type f -mmin +60 -delete 2>/dev/null
}

# 批量命令执行（带重试）
soul_exec_with_retry() {
    local cmd="$1"
    local max_retries="${2:-3}"
    local delay="${3:-1}"
    local attempt=0
    
    while (( attempt < max_retries )); do
        eval "$cmd" && return 0
        attempt=$((attempt + 1))
        [[ $attempt -lt $max_retries ]] && sleep "$delay"
    done
    return 1
}

echo "Soul Tools 库已加载"
