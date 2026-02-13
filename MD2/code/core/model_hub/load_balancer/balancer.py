"""
负载均衡器
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
import threading

from .strategies import (
    LoadBalancerStrategy,
    RoundRobinStrategy,
    WeightedRoundRobinStrategy,
    LeastConnectionsStrategy,
    LeastLatencyStrategy,
    RandomStrategy,
    InstanceMetrics,
)


@dataclass
class LoadBalancerConfig:
    strategy_name: str = "weighted_round_robin"
    session_affinity: bool = True
    health_check_enabled: bool = True
    retry_count: int = 3
    retry_delay_ms: int = 100


class LoadBalancer:
    
    STRATEGIES = {
        "round_robin": RoundRobinStrategy,
        "weighted_round_robin": WeightedRoundRobinStrategy,
        "least_connections": LeastConnectionsStrategy,
        "least_latency": LeastLatencyStrategy,
        "random": RandomStrategy,
    }
    
    def __init__(self, config: Optional[LoadBalancerConfig] = None):
        self.config = config or LoadBalancerConfig()
        self._strategy = self._create_strategy(self.config.strategy_name)
        self._metrics: Dict[str, InstanceMetrics] = {}
        self._instances: List[str] = []
        self._lock = threading.Lock()
    
    def _create_strategy(self, name: str) -> LoadBalancerStrategy:
        strategy_class = self.STRATEGIES.get(name, WeightedRoundRobinStrategy)
        return strategy_class()
    
    def set_strategy(self, name: str):
        with self._lock:
            self._strategy = self._create_strategy(name)
            self.config.strategy_name = name
    
    def register_instance(self, instance_id: str, weight: float = 1.0):
        with self._lock:
            if instance_id not in self._instances:
                self._instances.append(instance_id)
            
            if instance_id not in self._metrics:
                self._metrics[instance_id] = InstanceMetrics(
                    instance_id=instance_id,
                    weight=weight
                )
            else:
                self._metrics[instance_id].weight = weight
    
    def unregister_instance(self, instance_id: str):
        with self._lock:
            if instance_id in self._instances:
                self._instances.remove(instance_id)
            if instance_id in self._metrics:
                del self._metrics[instance_id]
    
    def update_weight(self, instance_id: str, weight: float):
        with self._lock:
            if instance_id in self._metrics:
                self._metrics[instance_id].weight = weight
    
    def select(self, session_id: Optional[str] = None) -> Optional[str]:
        with self._lock:
            if not self._instances:
                return None
            
            available = list(self._instances)
            return self._strategy.select(available, self._metrics)
    
    def record_request_start(self, instance_id: str):
        with self._lock:
            if instance_id in self._metrics:
                self._metrics[instance_id].increment_connections()
    
    def record_request_end(self, instance_id: str, latency_ms: int, success: bool):
        with self._lock:
            if instance_id in self._metrics:
                self._metrics[instance_id].decrement_connections()
                self._metrics[instance_id].record_request(latency_ms, success)
    
    def get_metrics(self, instance_id: str) -> Optional[InstanceMetrics]:
        return self._metrics.get(instance_id)
    
    def get_all_metrics(self) -> Dict[str, InstanceMetrics]:
        return self._metrics.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_requests = sum(m.total_requests for m in self._metrics.values())
            total_errors = sum(m.total_errors for m in self._metrics.values())
            
            return {
                "strategy": self._strategy.get_name(),
                "instance_count": len(self._instances),
                "total_requests": total_requests,
                "total_errors": total_errors,
                "error_rate": total_errors / total_requests if total_requests > 0 else 0,
                "instances": {
                    iid: {
                        "weight": m.weight,
                        "active_connections": m.active_connections,
                        "total_requests": m.total_requests,
                        "error_rate": m.error_rate,
                        "avg_latency_ms": m.avg_latency_ms,
                    }
                    for iid, m in self._metrics.items()
                }
            }
    
    def list_instances(self) -> List[str]:
        return list(self._instances)
    
    def clear(self):
        with self._lock:
            self._instances.clear()
            self._metrics.clear()
