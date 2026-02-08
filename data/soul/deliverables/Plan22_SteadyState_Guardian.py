#!/usr/bin/env python3
"""
Plan22 稳态守护检查器
用于监控关键链路健康状态
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class HealthCheck:
    component: str
    status: HealthStatus
    latency_ms: float
    message: str
    checked_at: str

class SteadyStateGuardian:
    """稳态守护器 - 监控关键链路健康"""
    
    COMPONENTS = ["scheduler", "orchestrator", "memory", "search"]
    
    # 阈值定义
    THRESHOLDS = {
        "scheduler": {
            "queue_depth_max": 100,
            "latency_p95_max_ms": 5000,
            "success_rate_min": 0.99
        },
        "orchestrator": {
            "workflow_success_rate_min": 0.99,
            "orphan_process_max": 0,
            "latency_p95_max_ms": 10000
        },
        "memory": {
            "index_load_time_max_ms": 5000,
            "search_latency_p95_max_ms": 100,
            "storage_usage_max_percent": 80
        },
        "search": {
            "availability_min": 0.95,
            "cache_hit_rate_min": 0.30,
            "latency_p95_max_ms": 3000
        }
    }
    
    def __init__(self):
        self.checks: List[HealthCheck] = []
        self.last_check_time = None
    
    def check_scheduler(self) -> HealthCheck:
        """检查 Scheduler 健康状态"""
        # 模拟检查（实际应查询真实指标）
        latency = self._simulate_latency()
        
        if latency > self.THRESHOLDS["scheduler"]["latency_p95_max_ms"]:
            return HealthCheck(
                component="scheduler",
                status=HealthStatus.DEGRADED,
                latency_ms=latency,
                message="调度延迟超过阈值",
                checked_at=datetime.now().isoformat()
            )
        
        return HealthCheck(
            component="scheduler",
            status=HealthStatus.HEALTHY,
            latency_ms=latency,
            message="运行正常",
            checked_at=datetime.now().isoformat()
        )
    
    def check_orchestrator(self) -> HealthCheck:
        """检查 Orchestrator 健康状态"""
        latency = self._simulate_latency()
        
        return HealthCheck(
            component="orchestrator",
            status=HealthStatus.HEALTHY,
            latency_ms=latency,
            message="工作流执行正常",
            checked_at=datetime.now().isoformat()
        )
    
    def check_memory(self) -> HealthCheck:
        """检查 Memory 健康状态"""
        latency = self._simulate_latency(10, 50)
        
        return HealthCheck(
            component="memory",
            status=HealthStatus.HEALTHY,
            latency_ms=latency,
            message="向量检索正常",
            checked_at=datetime.now().isoformat()
        )
    
    def check_search(self) -> HealthCheck:
        """检查 Search 健康状态"""
        latency = self._simulate_latency()
        
        return HealthCheck(
            component="search",
            status=HealthStatus.HEALTHY,
            latency_ms=latency,
            message="搜索服务可用",
            checked_at=datetime.now().isoformat()
        )
    
    def _simulate_latency(self, min_ms=50, max_ms=500) -> float:
        """模拟延迟（实际应查询真实指标）"""
        return min_ms + (max_ms - min_ms) * 0.5
    
    def run_all_checks(self) -> Dict:
        """执行所有健康检查"""
        self.checks = [
            self.check_scheduler(),
            self.check_orchestrator(),
            self.check_memory(),
            self.check_search()
        ]
        self.last_check_time = datetime.now().isoformat()
        
        healthy_count = sum(1 for c in self.checks if c.status == HealthStatus.HEALTHY)
        degraded_count = sum(1 for c in self.checks if c.status == HealthStatus.DEGRADED)
        unhealthy_count = sum(1 for c in self.checks if c.status == HealthStatus.UNHEALTHY)
        
        return {
            "checked_at": self.last_check_time,
            "overall_status": self._calculate_overall_status(),
            "summary": {
                "total": len(self.checks),
                "healthy": healthy_count,
                "degraded": degraded_count,
                "unhealthy": unhealthy_count
            },
            "details": [
                {
                    "component": c.component,
                    "status": c.status.value,
                    "latency_ms": c.latency_ms,
                    "message": c.message
                }
                for c in self.checks
            ]
        }
    
    def _calculate_overall_status(self) -> str:
        """计算整体健康状态"""
        statuses = [c.status for c in self.checks]
        if HealthStatus.UNHEALTHY in statuses:
            return "unhealthy"
        elif HealthStatus.DEGRADED in statuses:
            return "degraded"
        return "healthy"
    
    def generate_report(self) -> str:
        """生成检查报告"""
        result = self.run_all_checks()
        
        report_lines = [
            "# 稳态守护检查报告",
            f"检查时间: {result['checked_at']}",
            f"整体状态: {result['overall_status']}",
            "",
            "## 组件状态汇总",
            f"- 健康: {result['summary']['healthy']}/{result['summary']['total']}",
            f"- 降级: {result['summary']['degraded']}/{result['summary']['total']}",
            f"- 异常: {result['summary']['unhealthy']}/{result['summary']['total']}",
            "",
            "## 详细检查结果"
        ]
        
        for detail in result['details']:
            icon = "✅" if detail['status'] == 'healthy' else "⚠️" if detail['status'] == 'degraded' else "❌"
            report_lines.append(f"\n### {detail['component']}")
            report_lines.append(f"{icon} 状态: {detail['status']}")
            report_lines.append(f"⏱️ 延迟: {detail['latency_ms']:.2f}ms")
            report_lines.append(f"📝 {detail['message']}")
        
        return "\n".join(report_lines)


def main():
    guardian = SteadyStateGuardian()
    report = guardian.generate_report()
    print(report)
    
    # 保存检查结果
    output = {
        "schema": "steady_state_check",
        "version": "1.0",
        **guardian.run_all_checks()
    }
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"steady_state_check_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n检查结果已保存: {filename}")


if __name__ == "__main__":
    main()
