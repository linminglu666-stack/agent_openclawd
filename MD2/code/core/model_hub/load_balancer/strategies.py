"""
负载均衡策略
"""

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class InstanceMetrics:
    instance_id: str
    weight: float = 1.0
    
    active_connections: int = 0
    total_requests: int = 0
    total_errors: int = 0
    
    avg_latency_ms: int = 0
    recent_latencies: List[int] = field(default_factory=list)
    
    last_request_time: Optional[datetime] = None
    
    def record_request(self, latency_ms: int, success: bool):
        self.total_requests += 1
        if not success:
            self.total_errors += 1
        
        self.recent_latencies.append(latency_ms)
        if len(self.recent_latencies) > 100:
            self.recent_latencies = self.recent_latencies[-100:]
        
        if self.recent_latencies:
            self.avg_latency_ms = sum(self.recent_latencies) // len(self.recent_latencies)
        
        self.last_request_time = datetime.now()
    
    def increment_connections(self):
        self.active_connections += 1
    
    def decrement_connections(self):
        if self.active_connections > 0:
            self.active_connections -= 1
    
    @property
    def error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_errors / self.total_requests


class LoadBalancerStrategy(ABC):
    
    @abstractmethod
    def select(self, instances: List[str], metrics: Dict[str, InstanceMetrics]) -> Optional[str]:
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        pass


class RoundRobinStrategy(LoadBalancerStrategy):
    
    def __init__(self):
        self._current_index = 0
    
    def select(self, instances: List[str], metrics: Dict[str, InstanceMetrics]) -> Optional[str]:
        if not instances:
            return None
        
        selected = instances[self._current_index % len(instances)]
        self._current_index += 1
        return selected
    
    def get_name(self) -> str:
        return "round_robin"


class WeightedRoundRobinStrategy(LoadBalancerStrategy):
    
    def __init__(self):
        self._current_index = 0
        self._current_weight = 0
    
    def select(self, instances: List[str], metrics: Dict[str, InstanceMetrics]) -> Optional[str]:
        if not instances:
            return None
        
        weighted_instances = []
        for instance_id in instances:
            m = metrics.get(instance_id)
            weight = int(m.weight * 10) if m else 10
            weighted_instances.extend([instance_id] * weight)
        
        if not weighted_instances:
            return None
        
        selected = weighted_instances[self._current_index % len(weighted_instances)]
        self._current_index += 1
        return selected
    
    def get_name(self) -> str:
        return "weighted_round_robin"


class LeastConnectionsStrategy(LoadBalancerStrategy):
    
    def select(self, instances: List[str], metrics: Dict[str, InstanceMetrics]) -> Optional[str]:
        if not instances:
            return None
        
        min_connections = float('inf')
        selected = instances[0]
        
        for instance_id in instances:
            m = metrics.get(instance_id)
            connections = m.active_connections if m else 0
            
            if connections < min_connections:
                min_connections = connections
                selected = instance_id
        
        return selected
    
    def get_name(self) -> str:
        return "least_connections"


class LeastLatencyStrategy(LoadBalancerStrategy):
    
    def select(self, instances: List[str], metrics: Dict[str, InstanceMetrics]) -> Optional[str]:
        if not instances:
            return None
        
        min_latency = float('inf')
        selected = instances[0]
        
        for instance_id in instances:
            m = metrics.get(instance_id)
            latency = m.avg_latency_ms if m and m.avg_latency_ms > 0 else 10000
            
            if latency < min_latency:
                min_latency = latency
                selected = instance_id
        
        return selected
    
    def get_name(self) -> str:
        return "least_latency"


class RandomStrategy(LoadBalancerStrategy):
    
    def select(self, instances: List[str], metrics: Dict[str, InstanceMetrics]) -> Optional[str]:
        if not instances:
            return None
        return random.choice(instances)
    
    def get_name(self) -> str:
        return "random"


class SessionAffinityStrategy(LoadBalancerStrategy):
    
    def __init__(self, fallback_strategy: LoadBalancerStrategy):
        self._fallback = fallback_strategy
        self._session_map: Dict[str, str] = {}
    
    def select(
        self,
        instances: List[str],
        metrics: Dict[str, InstanceMetrics],
        session_id: Optional[str] = None
    ) -> Optional[str]:
        if not instances:
            return None
        
        if session_id:
            if session_id in self._session_map:
                affinity_instance = self._session_map[session_id]
                if affinity_instance in instances:
                    return affinity_instance
            
            selected = self._fallback.select(instances, metrics)
            if selected:
                self._session_map[session_id] = selected
            return selected
        
        return self._fallback.select(instances, metrics)
    
    def get_name(self) -> str:
        return f"session_affinity({self._fallback.get_name()})"
    
    def clear_session(self, session_id: str):
        if session_id in self._session_map:
            del self._session_map[session_id]
