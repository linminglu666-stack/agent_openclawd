"""
健康检查器
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


@dataclass
class HealthCheckResult:
    instance_id: str
    success: bool
    latency_ms: int = 0
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "success": self.success,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "details": self.details,
            "checked_at": self.checked_at.isoformat(),
        }


@dataclass
class HealthStatus:
    instance_id: str
    is_healthy: bool
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_check: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_error: Optional[str] = None
    total_checks: int = 0
    total_failures: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "is_healthy": self.is_healthy,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_error": self.last_error,
            "total_checks": self.total_checks,
            "total_failures": self.total_failures,
        }


class HealthChecker:
    
    def __init__(
        self,
        check_interval: int = 30,
        timeout: int = 10,
        failure_threshold: int = 3,
        recovery_threshold: int = 2
    ):
        self.check_interval = check_interval
        self.timeout = timeout
        self.failure_threshold = failure_threshold
        self.recovery_threshold = recovery_threshold
        
        self._health_status: Dict[str, HealthStatus] = {}
        self._check_handlers: Dict[str, Callable] = {}
        self._listeners: List[Callable] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    def register(self, instance_id: str, check_handler: Callable):
        self._check_handlers[instance_id] = check_handler
        if instance_id not in self._health_status:
            self._health_status[instance_id] = HealthStatus(
                instance_id=instance_id,
                is_healthy=True
            )
    
    def unregister(self, instance_id: str):
        if instance_id in self._check_handlers:
            del self._check_handlers[instance_id]
        if instance_id in self._health_status:
            del self._health_status[instance_id]
    
    async def check(self, instance_id: str) -> HealthCheckResult:
        handler = self._check_handlers.get(instance_id)
        if not handler:
            return HealthCheckResult(
                instance_id=instance_id,
                success=False,
                error="No check handler registered"
            )
        
        status = self._health_status.get(instance_id)
        if not status:
            status = HealthStatus(instance_id=instance_id, is_healthy=True)
            self._health_status[instance_id] = status
        
        try:
            import time
            start = time.time()
            
            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(
                    handler(),
                    timeout=self.timeout
                )
            else:
                result = handler()
            
            latency_ms = int((time.time() - start) * 1000)
            
            success = bool(result) if result is not None else True
            
            self._update_status(status, success, None)
            
            return HealthCheckResult(
                instance_id=instance_id,
                success=success,
                latency_ms=latency_ms,
                details={"result": str(result)} if result else {}
            )
            
        except asyncio.TimeoutError:
            error = f"Health check timeout after {self.timeout}s"
            self._update_status(status, False, error)
            return HealthCheckResult(
                instance_id=instance_id,
                success=False,
                latency_ms=self.timeout * 1000,
                error=error
            )
        except Exception as e:
            error = str(e)
            self._update_status(status, False, error)
            return HealthCheckResult(
                instance_id=instance_id,
                success=False,
                error=error
            )
    
    def _update_status(self, status: HealthStatus, success: bool, error: Optional[str]):
        now = datetime.now()
        status.last_check = now
        status.total_checks += 1
        
        if success:
            status.consecutive_failures = 0
            status.consecutive_successes += 1
            status.last_success = now
            
            if not status.is_healthy:
                if status.consecutive_successes >= self.recovery_threshold:
                    status.is_healthy = True
                    self._notify_listeners("recovered", status)
        else:
            status.consecutive_successes = 0
            status.consecutive_failures += 1
            status.total_failures += 1
            status.last_failure = now
            status.last_error = error
            
            if status.is_healthy:
                if status.consecutive_failures >= self.failure_threshold:
                    status.is_healthy = False
                    self._notify_listeners("failed", status)
    
    async def check_all(self) -> List[HealthCheckResult]:
        results = []
        for instance_id in list(self._check_handlers.keys()):
            result = await self.check(instance_id)
            results.append(result)
        return results
    
    def get_status(self, instance_id: str) -> Optional[HealthStatus]:
        return self._health_status.get(instance_id)
    
    def get_all_status(self) -> Dict[str, HealthStatus]:
        return self._health_status.copy()
    
    def is_healthy(self, instance_id: str) -> bool:
        status = self._health_status.get(instance_id)
        return status.is_healthy if status else True
    
    async def start(self):
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_periodic_checks())
    
    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
    
    async def _run_periodic_checks(self):
        while self._running:
            try:
                await self.check_all()
            except Exception:
                pass
            await asyncio.sleep(self.check_interval)
    
    def add_listener(self, callback: Callable):
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable):
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self, event: str, status: HealthStatus):
        for callback in self._listeners:
            try:
                callback(event, status)
            except Exception:
                pass
