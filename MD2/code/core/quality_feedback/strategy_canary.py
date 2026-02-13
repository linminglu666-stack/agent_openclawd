"""
策略灰度发布
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import threading
import time


class CanaryStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    ABORTED = "aborted"


class RollbackReason(Enum):
    ERROR_RATE = "error_rate"
    LATENCY = "latency"
    USER_FEEDBACK = "user_feedback"
    MANUAL = "manual"
    METRICS_THRESHOLD = "metrics_threshold"


@dataclass
class CanaryMetrics:
    request_count: int = 0
    error_count: int = 0
    error_rate: float = 0.0
    
    latency_p50_ms: int = 0
    latency_p95_ms: int = 0
    latency_p99_ms: int = 0
    avg_latency_ms: float = 0.0
    
    user_satisfaction: float = 0.0
    feedback_count: int = 0
    negative_feedback_count: int = 0
    
    throughput_rps: float = 0.0
    
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_rate,
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p95_ms": self.latency_p95_ms,
            "latency_p99_ms": self.latency_p99_ms,
            "avg_latency_ms": self.avg_latency_ms,
            "user_satisfaction": self.user_satisfaction,
            "feedback_count": self.feedback_count,
            "negative_feedback_count": self.negative_feedback_count,
            "throughput_rps": self.throughput_rps,
            "custom_metrics": self.custom_metrics,
        }
    
    def update_from_request(self, latency_ms: int, success: bool):
        self.request_count += 1
        if not success:
            self.error_count += 1
        
        if self.request_count > 0:
            self.error_rate = self.error_count / self.request_count
        
        if self.avg_latency_ms == 0:
            self.avg_latency_ms = latency_ms
        else:
            self.avg_latency_ms = (
                self.avg_latency_ms * (self.request_count - 1) + latency_ms
            ) / self.request_count


@dataclass
class CanaryConfig:
    initial_percentage: float = 1.0
    increment_percentage: float = 5.0
    increment_interval_minutes: int = 30
    
    max_percentage: float = 100.0
    min_sample_size: int = 100
    
    error_rate_threshold: float = 0.05
    latency_p95_threshold_ms: int = 5000
    satisfaction_threshold: float = 0.7
    
    auto_rollback: bool = True
    auto_promote: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_percentage": self.initial_percentage,
            "increment_percentage": self.increment_percentage,
            "increment_interval_minutes": self.increment_interval_minutes,
            "max_percentage": self.max_percentage,
            "min_sample_size": self.min_sample_size,
            "error_rate_threshold": self.error_rate_threshold,
            "latency_p95_threshold_ms": self.latency_p95_threshold_ms,
            "satisfaction_threshold": self.satisfaction_threshold,
            "auto_rollback": self.auto_rollback,
            "auto_promote": self.auto_promote,
        }


@dataclass
class CanaryRelease:
    canary_id: str
    strategy_name: str
    
    baseline_version: str
    canary_version: str
    
    config: CanaryConfig
    
    current_percentage: float = 0.0
    
    status: CanaryStatus = CanaryStatus.PENDING
    
    baseline_metrics: CanaryMetrics = field(default_factory=CanaryMetrics)
    canary_metrics: CanaryMetrics = field(default_factory=CanaryMetrics)
    
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_increment_at: Optional[datetime] = None
    
    rollback_reason: Optional[RollbackReason] = None
    rollback_details: Optional[str] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "canary_id": self.canary_id,
            "strategy_name": self.strategy_name,
            "baseline_version": self.baseline_version,
            "canary_version": self.canary_version,
            "config": self.config.to_dict(),
            "current_percentage": self.current_percentage,
            "status": self.status.value,
            "baseline_metrics": self.baseline_metrics.to_dict(),
            "canary_metrics": self.canary_metrics.to_dict(),
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "last_increment_at": self.last_increment_at.isoformat() if self.last_increment_at else None,
            "rollback_reason": self.rollback_reason.value if self.rollback_reason else None,
            "rollback_details": self.rollback_details,
            "metadata": self.metadata,
        }
    
    def should_route_to_canary(self) -> bool:
        import random
        return random.random() * 100 < self.current_percentage
    
    def can_increment(self) -> bool:
        if self.current_percentage >= self.config.max_percentage:
            return False
        
        if self.status != CanaryStatus.RUNNING:
            return False
        
        if not self.last_increment_at:
            return True
        
        from datetime import timedelta
        elapsed = datetime.now() - self.last_increment_at
        return elapsed >= timedelta(minutes=self.config.increment_interval_minutes)


@dataclass
class CanaryResult:
    canary_id: str
    success: bool
    
    final_percentage: float = 0.0
    promoted: bool = False
    
    total_requests: int = 0
    total_errors: int = 0
    
    duration_minutes: float = 0.0
    
    completed_at: datetime = field(default_factory=datetime.now)
    
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "canary_id": self.canary_id,
            "success": self.success,
            "final_percentage": self.final_percentage,
            "promoted": self.promoted,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "duration_minutes": self.duration_minutes,
            "completed_at": self.completed_at.isoformat(),
            "summary": self.summary,
        }


class StrategyCanary:
    
    def __init__(self):
        self._canaries: Dict[str, CanaryRelease] = {}
        self._active_canaries: Dict[str, CanaryRelease] = {}
        self._lock = threading.Lock()
        self._listeners: List[Callable] = []
        
        self._check_thread: Optional[threading.Thread] = None
        self._running = False
    
    def create_canary(
        self,
        strategy_name: str,
        baseline_version: str,
        canary_version: str,
        config: Optional[CanaryConfig] = None
    ) -> CanaryRelease:
        import uuid
        
        canary = CanaryRelease(
            canary_id=f"canary-{uuid.uuid4().hex[:8]}",
            strategy_name=strategy_name,
            baseline_version=baseline_version,
            canary_version=canary_version,
            config=config or CanaryConfig(),
            current_percentage=0.0,
        )
        
        with self._lock:
            self._canaries[canary.canary_id] = canary
        
        return canary
    
    def start_canary(self, canary_id: str) -> bool:
        with self._lock:
            canary = self._canaries.get(canary_id)
            if not canary or canary.status != CanaryStatus.PENDING:
                return False
            
            canary.status = CanaryStatus.RUNNING
            canary.started_at = datetime.now()
            canary.current_percentage = canary.config.initial_percentage
            canary.last_increment_at = datetime.now()
            
            self._active_canaries[canary.strategy_name] = canary
        
        self._notify_listeners("started", canary)
        return True
    
    def route_request(
        self,
        strategy_name: str
    ) -> tuple[str, str]:
        with self._lock:
            canary = self._active_canaries.get(strategy_name)
            
            if not canary or canary.status != CanaryStatus.RUNNING:
                return "baseline", ""
            
            if canary.should_route_to_canary():
                return "canary", canary.canary_version
            else:
                return "baseline", canary.baseline_version
    
    def record_metrics(
        self,
        strategy_name: str,
        target: str,
        latency_ms: int,
        success: bool,
        user_satisfaction: Optional[float] = None
    ):
        with self._lock:
            canary = self._active_canaries.get(strategy_name)
            if not canary:
                return
            
            if target == "canary":
                canary.canary_metrics.update_from_request(latency_ms, success)
                if user_satisfaction is not None:
                    canary.canary_metrics.feedback_count += 1
                    if user_satisfaction < 0.5:
                        canary.canary_metrics.negative_feedback_count += 1
                    canary.canary_metrics.user_satisfaction = (
                        (canary.canary_metrics.user_satisfaction * (canary.canary_metrics.feedback_count - 1) + user_satisfaction)
                        / canary.canary_metrics.feedback_count
                    )
            else:
                canary.baseline_metrics.update_from_request(latency_ms, success)
    
    def check_canary(self, canary_id: str) -> Dict[str, Any]:
        with self._lock:
            canary = self._canaries.get(canary_id)
            if not canary:
                return {"error": "Canary not found"}
            
            result = self._evaluate_canary(canary)
            
            if result.get("should_rollback") and canary.config.auto_rollback:
                self._rollback_canary(canary, result.get("rollback_reason"), result.get("details"))
            elif result.get("can_increment") and canary.can_increment():
                self._increment_canary(canary)
            elif result.get("can_promote") and canary.config.auto_promote:
                self._promote_canary(canary)
            
            return result
    
    def _evaluate_canary(self, canary: CanaryRelease) -> Dict[str, Any]:
        result = {
            "canary_id": canary.canary_id,
            "current_percentage": canary.current_percentage,
            "canary_metrics": canary.canary_metrics.to_dict(),
            "baseline_metrics": canary.baseline_metrics.to_dict(),
            "should_rollback": False,
            "can_increment": False,
            "can_promote": False,
        }
        
        if canary.canary_metrics.request_count < canary.config.min_sample_size:
            result["status"] = "collecting_samples"
            return result
        
        if canary.canary_metrics.error_rate > canary.config.error_rate_threshold:
            result["should_rollback"] = True
            result["rollback_reason"] = RollbackReason.ERROR_RATE.value
            result["details"] = f"Error rate {canary.canary_metrics.error_rate:.2%} exceeds threshold {canary.config.error_rate_threshold:.2%}"
            return result
        
        if canary.canary_metrics.latency_p95_ms > canary.config.latency_p95_threshold_ms:
            result["should_rollback"] = True
            result["rollback_reason"] = RollbackReason.LATENCY.value
            result["details"] = f"P95 latency {canary.canary_metrics.latency_p95_ms}ms exceeds threshold {canary.config.latency_p95_threshold_ms}ms"
            return result
        
        if (canary.canary_metrics.feedback_count >= 10 and
            canary.canary_metrics.user_satisfaction < canary.config.satisfaction_threshold):
            result["should_rollback"] = True
            result["rollback_reason"] = RollbackReason.USER_FEEDBACK.value
            result["details"] = f"User satisfaction {canary.canary_metrics.user_satisfaction:.2f} below threshold {canary.config.satisfaction_threshold:.2f}"
            return result
        
        if canary.current_percentage >= canary.config.max_percentage:
            result["can_promote"] = True
        else:
            result["can_increment"] = True
        
        result["status"] = "healthy"
        return result
    
    def _increment_canary(self, canary: CanaryRelease):
        new_percentage = min(
            canary.current_percentage + canary.config.increment_percentage,
            canary.config.max_percentage
        )
        
        canary.current_percentage = new_percentage
        canary.last_increment_at = datetime.now()
        
        self._notify_listeners("incremented", canary)
    
    def _promote_canary(self, canary: CanaryRelease):
        canary.status = CanaryStatus.SUCCEEDED
        canary.completed_at = datetime.now()
        
        if canary.strategy_name in self._active_canaries:
            del self._active_canaries[canary.strategy_name]
        
        self._notify_listeners("promoted", canary)
    
    def _rollback_canary(
        self,
        canary: CanaryRelease,
        reason: Optional[str],
        details: Optional[str]
    ):
        canary.status = CanaryStatus.ROLLED_BACK
        canary.completed_at = datetime.now()
        canary.rollback_reason = RollbackReason(reason) if reason else RollbackReason.MANUAL
        canary.rollback_details = details
        
        if canary.strategy_name in self._active_canaries:
            del self._active_canaries[canary.strategy_name]
        
        self._notify_listeners("rolled_back", canary)
    
    def abort_canary(self, canary_id: str, reason: str = "") -> bool:
        with self._lock:
            canary = self._canaries.get(canary_id)
            if not canary or canary.status not in [CanaryStatus.PENDING, CanaryStatus.RUNNING]:
                return False
            
            canary.status = CanaryStatus.ABORTED
            canary.completed_at = datetime.now()
            canary.rollback_reason = RollbackReason.MANUAL
            canary.rollback_details = reason
            
            if canary.strategy_name in self._active_canaries:
                del self._active_canaries[canary.strategy_name]
            
            self._notify_listeners("aborted", canary)
            return True
    
    def get_canary(self, canary_id: str) -> Optional[CanaryRelease]:
        return self._canaries.get(canary_id)
    
    def get_active_canary(self, strategy_name: str) -> Optional[CanaryRelease]:
        return self._active_canaries.get(strategy_name)
    
    def get_canaries_by_strategy(
        self,
        strategy_name: str,
        limit: int = 100
    ) -> List[CanaryRelease]:
        canaries = [
            c for c in self._canaries.values()
            if c.strategy_name == strategy_name
        ]
        canaries.sort(key=lambda x: x.created_at, reverse=True)
        return canaries[:limit]
    
    def start_monitoring(self, check_interval_seconds: int = 60):
        if self._running:
            return
        
        self._running = True
        self._check_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(check_interval_seconds,),
            daemon=True
        )
        self._check_thread.start()
    
    def stop_monitoring(self):
        self._running = False
        if self._check_thread:
            self._check_thread.join(timeout=5)
            self._check_thread = None
    
    def _monitoring_loop(self, interval: int):
        while self._running:
            try:
                for canary_id in list(self._active_canaries.keys()):
                    canary = self._active_canaries.get(canary_id)
                    if canary:
                        self.check_canary(canary.canary_id)
            except Exception:
                pass
            
            time.sleep(interval)
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_canaries": len(self._canaries),
            "active_canaries": len(self._active_canaries),
            "by_status": {
                status.value: sum(1 for c in self._canaries.values() if c.status == status)
                for status in CanaryStatus
            },
        }
    
    def add_listener(self, callback: Callable):
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable):
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self, event: str, data: Any):
        for callback in self._listeners:
            try:
                callback(event, data)
            except Exception:
                pass
