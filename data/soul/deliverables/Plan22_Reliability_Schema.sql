-- Plan22 可靠性数据持久化 Schema (SQLite)

-- 故障事件表
CREATE TABLE IF NOT EXISTS reliability_incidents (
    incident_id TEXT PRIMARY KEY,
    level TEXT NOT NULL CHECK(level IN ('P0', 'P1', 'P2', 'P3')),
    service TEXT NOT NULL,
    fault_type TEXT NOT NULL,
    description TEXT,
    started_at TIMESTAMP NOT NULL,
    detected_at TIMESTAMP,
    resolved_at TIMESTAMP,
    mttr_seconds INTEGER,
    root_cause TEXT,
    recovery_action TEXT,
    prevention TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 混沌演练记录表
CREATE TABLE IF NOT EXISTS chaos_runs (
    run_id TEXT PRIMARY KEY,
    scenario_id TEXT NOT NULL,
    scenario_name TEXT,
    target TEXT NOT NULL,
    level TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    injected_faults TEXT, -- JSON array
    detected BOOLEAN DEFAULT FALSE,
    recovered BOOLEAN DEFAULT FALSE,
    detection_time_ms INTEGER,
    recovery_time_ms INTEGER,
    pass_rate REAL,
    logs TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 恢复动作审计表
CREATE TABLE IF NOT EXISTS recovery_actions (
    action_id TEXT PRIMARY KEY,
    incident_id TEXT REFERENCES reliability_incidents(incident_id),
    action_type TEXT NOT NULL CHECK(action_type IN ('restart', 'retry', 'fallback', 'rollback')),
    executed_at TIMESTAMP NOT NULL,
    executed_by TEXT, -- 'system' or 'operator'
    success BOOLEAN NOT NULL,
    side_effects TEXT, -- JSON array
    rollback_action_id TEXT, -- self-reference for rollback chain
    verification_result TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 稳态健康检查记录表
CREATE TABLE IF NOT EXISTS steady_state_checks (
    check_id TEXT PRIMARY KEY,
    checked_at TIMESTAMP NOT NULL,
    overall_status TEXT NOT NULL CHECK(overall_status IN ('healthy', 'degraded', 'unhealthy')),
    total_components INTEGER,
    healthy_count INTEGER,
    degraded_count INTEGER,
    unhealthy_count INTEGER,
    details TEXT, -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 组件健康状态历史表
CREATE TABLE IF NOT EXISTS component_health_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_id TEXT REFERENCES steady_state_checks(check_id),
    component TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('healthy', 'degraded', 'unhealthy')),
    latency_ms REAL,
    message TEXT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_incidents_level ON reliability_incidents(level);
CREATE INDEX IF NOT EXISTS idx_incidents_service ON reliability_incidents(service);
CREATE INDEX IF NOT EXISTS idx_incidents_started_at ON reliability_incidents(started_at);
CREATE INDEX IF NOT EXISTS idx_chaos_runs_scenario ON chaos_runs(scenario_id);
CREATE INDEX IF NOT EXISTS idx_chaos_runs_started_at ON chaos_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_recovery_incident ON recovery_actions(incident_id);
CREATE INDEX IF NOT EXISTS idx_steady_state_checked_at ON steady_state_checks(checked_at);

-- 视图：故障统计
CREATE VIEW IF NOT EXISTS incident_stats AS
SELECT 
    level,
    service,
    COUNT(*) as incident_count,
    AVG(mttr_seconds) as avg_mttr,
    MAX(mttr_seconds) as max_mttr,
    MIN(mttr_seconds) as min_mttr
FROM reliability_incidents
GROUP BY level, service;

-- 视图：混沌演练成功率
CREATE VIEW IF NOT EXISTS chaos_success_rate AS
SELECT 
    scenario_id,
    scenario_name,
    COUNT(*) as total_runs,
    SUM(CASE WHEN recovered THEN 1 ELSE 0 END) as successful_recoveries,
    ROUND(100.0 * SUM(CASE WHEN recovered THEN 1 ELSE 0 END) / COUNT(*), 2) as recovery_rate_percent
FROM chaos_runs
GROUP BY scenario_id, scenario_name;

-- 视图：MTTR趋势（按周）
CREATE VIEW IF NOT EXISTS mttr_trend_weekly AS
SELECT 
    strftime('%Y-W%W', started_at) as week,
    level,
    COUNT(*) as incident_count,
    ROUND(AVG(mttr_seconds), 2) as avg_mttr_seconds,
    ROUND(AVG(CASE WHEN recovered THEN recovery_time_ms ELSE NULL END) / 1000.0, 2) as avg_recovery_time_seconds
FROM reliability_incidents
WHERE resolved_at IS NOT NULL
GROUP BY week, level
ORDER BY week DESC;
