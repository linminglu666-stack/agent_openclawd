"""
故障转移管理器
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import asyncio
import threading

from .health_checker import HealthChecker, HealthStatus
from .circuit_breaker import CircuitBreaker, CircuitState


@dataclass
class FailoverConfig:
    enabled: bool = True
    health_check_interval: int = 30
    health_check_timeout: int = 10
    failure_threshold: int = 3
    recovery_threshold: int = 2
    circuit_breaker_enabled: bool = True
    circuit_failure_threshold: int = 5
    circuit_timeout: int = 30
    max_retry_attempts: int = 3
    retry_delay_ms: int = 100


@dataclass
class FailoverEvent:
    instance_id: str
    event_type: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


class FailoverManager:
    
    def __init__(self, config: Optional[FailoverConfig] = None):
        self.config = config or FailoverConfig()
        
        self._health_checker = HealthChecker(
            check_interval=self.config.health_check_interval,
            timeout=self.config.health_check_timeout,
            failure_threshold=self.config.failure_threshold,
            recovery_threshold=self.config.recovery_threshold,
        )
        
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._instances: Dict[str, Dict[str, Any]] = {}
        self._fallback_order: Dict[str, List[str]] = {}
        
        self._event_listeners: List[Callable] = []
        self._event_history: List[FailoverEvent] = []
        self._lock = threading.Lock()
        
        self._health_checker.add_listener(self._on_health_change)
    
    def register_instance(
        self,
        instance_id: str,
        health_check_handler: Callable,
        metadata: Optional[Dict[str, Any]] = None,
        fallback_instances: Optional[List[str]] = None
    ):
        with self._lock:
            self._instances[instance_id] = {
                "metadata": metadata or {},
                "registered_at": datetime.now(),
            }
            
            self._health_checker.register(instance_id, health_check_handler)
            
            if self.config.circuit_breaker_enabled:
                self._circuit_breakers[instance_id] = CircuitBreaker(
                    failure_threshold=self.config.circuit_failure_threshold,
                    timeout=self.config.circuit_timeout,
                )
            
            if fallback_instances:
                self._fallback_order[instance_id] = fallback_instances
        
        self._record_event(instance_id, "registered", {"metadata": metadata})
    
    def unregister_instance(self, instance_id: str):
        with self._lock:
            self._health_checker.unregister(instance_id)
            
            if instance_id in self._circuit_breakers:
                del self._circuit_breakers[instance_id]
            
            if instance_id in self._instances:
                del self._instances[instance_id]
            
            if instance_id in self._fallback_order:
                del self._fallback_order[instance_id]
        
        self._record_event(instance_id, "unregistered", {})
    
    def is_available(self, instance_id: str) -> bool:
        if not self._health_checker.is_healthy(instance_id):
            return False
        
        if self.config.circuit_breaker_enabled:
            cb = self._circuit_breakers.get(instance_id)
            if cb and not cb.can_execute():
                return False
        
        return True
    
    def get_available_instances(self) -> List[str]:
        available = []
        for instance_id in self._instances.keys():
            if self.is_available(instance_id):
                available.append(instance_id)
        return available
    
    def get_fallback(self, instance_id: str) -> Optional[str]:
        fallback_list = self._fallback_order.get(instance_id, [])
        
        for fallback_id in fallback_list:
            if self.is_available(fallback_id):
                return fallback_id
        
        all_instances = list(self._instances.keys())
        for alt_id in all_instances:
            if alt_id != instance_id and self.is_available(alt_id):
                return alt_id
        
        return None
    
    def record_success(self, instance_id: str, latency_ms: int = 0):
        if self.config.circuit_breaker_enabled:
            cb = self._circuit_breakers.get(instance_id)
            if cb:
                cb.record_success()
    
    def record_failure(self, instance_id: str, error: Optional[str] = None):
        if self.config.circuit_breaker_enabled:
            cb = self._circuit_breakers.get(instance_id)
            if cb:
                cb.record_failure(error)
        
        self._record_event(instance_id, "failure", {"error": error})
    
    async def execute_with_failover(
        self,
        instance_id: str,
        operation: Callable,
        *args,
        **kwargs
    ) -> Any:
        instances_to_try = [instance_id]
        
        fallback = self.get_fallback(instance_id)
        if fallback:
            instances_to_try.append(fallback)
        
        last_error = None
        
        for attempt, current_instance in enumerate(instances_to_try):
            if not self.is_available(current_instance):
                continue
            
            cb = self._circuit_breakers.get(current_instance)
            
            for retry in range(self.config.max_retry_attempts):
                try:
                    if asyncio.iscoroutinefunction(operation):
                        result = await operation(*args, **kwargs)
                    else:
                        result = operation(*args, **kwargs)
                    
                    self.record_success(current_instance)
                    return result
                    
                except Exception as e:
                    last_error = str(e)
                    self.record_failure(current_instance, last_error)
                    
                    if retry < self.config.max_retry_attempts - 1:
                        await asyncio.sleep(self.config.retry_delay_ms / 1000)
            
            if cb and cb.state == CircuitState.OPEN:
                continue
        
        raise Exception(f"All instances failed. Last error: {last_error}")
    
    def get_health_status(self, instance_id: str) -> Optional[HealthStatus]:
        return self._health_checker.get_status(instance_id)
    
    def get_all_health_status(self) -> Dict[str, HealthStatus]:
        return self._health_checker.get_all_status()
    
    def get_circuit_breaker(self, instance_id: str) -> Optional[CircuitBreaker]:
        return self._circuit_breakers.get(instance_id)
    
    def force_open_circuit(self, instance_id: str):
        cb = self._circuit_breakers.get(instance_id)
        if cb:
            cb.force_open()
            self._record_event(instance_id, "circuit_forced_open", {})
    
    def force_close_circuit(self, instance_id: str):
        cb = self._circuit_breakers.get(instance_id)
        if cb:
            cb.force_close()
            self._record_event(instance_id, "circuit_forced_close", {})
    
    async def start(self):
        await self._health_checker.start()
    
    async def stop(self):
        await self._health_checker.stop()
    
    def add_event_listener(self, callback: Callable):
        self._event_listeners.append(callback)
    
    def remove_event_listener(self, callback: Callable):
        if callback in self._event_listeners:
            self._event_listeners.remove(callback)
    
    def get_event_history(self, limit: int = 100) -> List[FailoverEvent]:
        return self._event_history[-limit:]
    
    def _on_health_change(self, event: str, status: HealthStatus):
        self._record_event(
            status.instance_id,
            f"health_{event}",
            {
                "is_healthy": status.is_healthy,
                "consecutive_failures": status.consecutive_failures,
            }
        )
    
    def _record_event(self, instance_id: str, event_type: str, details: Dict[str, Any]):
        event = FailoverEvent(
            instance_id=instance_id,
            event_type=event_type,
            timestamp=datetime.now(),
            details=details,
        )
        
        self._event_history.append(event)
        if len(self._event_history) > 1000:
            self._event_history = self._event_history[-500:]
        
        for callback in self._event_listeners:
            try:
                callback(event)
            except Exception:
                pass
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "config": {
                "enabled": self.config.enabled,
                "health_check_interval": self.config.health_check_interval,
                "circuit_breaker_enabled": self.config.circuit_breaker_enabled,
            },
            "instances": {
                iid: {
                    "available": self.is_available(iid),
                    "health": self.get_health_status(iid).to_dict() if self.get_health_status(iid) else None,
                    "circuit_breaker": cb.to_dict() if (cb := self._circuit_breakers.get(iid)) else None,
                }
                for iid in self._instances.keys()
            },
            "event_count": len(self._event_history),
        }
