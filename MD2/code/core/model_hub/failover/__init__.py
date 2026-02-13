"""
故障转移模块
"""

from .health_checker import HealthChecker, HealthCheckResult
from .circuit_breaker import CircuitBreaker, CircuitState
from .failover_manager import FailoverManager

__all__ = [
    "HealthChecker",
    "HealthCheckResult",
    "CircuitBreaker",
    "CircuitState",
    "FailoverManager",
]
