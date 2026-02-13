"""
限流器
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import threading
import time


class RateLimitStrategy(Enum):
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimitPolicy:
    name: str
    max_requests: int
    window_seconds: int
    
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    
    burst_size: Optional[int] = None
    refill_rate: Optional[float] = None
    
    retry_after_seconds: int = 60
    
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "strategy": self.strategy.value,
            "burst_size": self.burst_size,
            "refill_rate": self.refill_rate,
            "retry_after_seconds": self.retry_after_seconds,
            "enabled": self.enabled,
        }


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_at: datetime
    retry_after: int = 0
    
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "remaining": self.remaining,
            "reset_at": self.reset_at.isoformat(),
            "retry_after": self.retry_after,
            "reason": self.reason,
        }


class TokenBucket:
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def get_tokens(self) -> float:
        with self._lock:
            self._refill()
            return self.tokens


class SlidingWindowCounter:
    
    def __init__(self, window_seconds: int, max_requests: int):
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.requests: List[float] = []
        self._lock = threading.Lock()
    
    def record(self) -> bool:
        with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds
            
            self.requests = [t for t in self.requests if t > cutoff]
            
            if len(self.requests) >= self.max_requests:
                return False
            
            self.requests.append(now)
            return True
    
    def get_count(self) -> int:
        with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds
            self.requests = [t for t in self.requests if t > cutoff]
            return len(self.requests)
    
    def get_remaining(self) -> int:
        return max(0, self.max_requests - self.get_count())
    
    def get_reset_time(self) -> datetime:
        with self._lock:
            if not self.requests:
                return datetime.now()
            oldest = min(self.requests)
            return datetime.fromtimestamp(oldest + self.window_seconds)


class RateLimiter:
    
    DEFAULT_POLICIES = {
        "per_minute": RateLimitPolicy(
            name="per_minute",
            max_requests=60,
            window_seconds=60,
        ),
        "per_hour": RateLimitPolicy(
            name="per_hour",
            max_requests=1000,
            window_seconds=3600,
        ),
        "per_day": RateLimitPolicy(
            name="per_day",
            max_requests=10000,
            window_seconds=86400,
        ),
    }
    
    def __init__(self):
        self._policies: Dict[str, RateLimitPolicy] = dict(self.DEFAULT_POLICIES)
        self._counters: Dict[str, Dict[str, SlidingWindowCounter]] = {}
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = threading.Lock()
        self._listeners: List[Callable] = []
    
    def add_policy(self, policy: RateLimitPolicy):
        with self._lock:
            self._policies[policy.name] = policy
    
    def remove_policy(self, name: str):
        with self._lock:
            if name in self._policies:
                del self._policies[name]
    
    def get_policy(self, name: str) -> Optional[RateLimitPolicy]:
        return self._policies.get(name)
    
    def check(
        self,
        key: str,
        policy_name: str = "per_minute"
    ) -> RateLimitResult:
        policy = self._policies.get(policy_name)
        if not policy:
            return RateLimitResult(
                allowed=True,
                remaining=-1,
                reset_at=datetime.now() + timedelta(seconds=60),
                reason="Policy not found",
            )
        
        if not policy.enabled:
            return RateLimitResult(
                allowed=True,
                remaining=-1,
                reset_at=datetime.now() + timedelta(seconds=60),
            )
        
        with self._lock:
            if key not in self._counters:
                self._counters[key] = {}
            
            if policy_name not in self._counters[key]:
                self._counters[key][policy_name] = SlidingWindowCounter(
                    window_seconds=policy.window_seconds,
                    max_requests=policy.max_requests,
                )
            
            counter = self._counters[key][policy_name]
        
        allowed = counter.record()
        remaining = counter.get_remaining()
        reset_at = counter.get_reset_time()
        
        if not allowed:
            self._notify_listeners(key, policy_name, "rate_limited")
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=reset_at,
                retry_after=policy.retry_after_seconds,
                reason=f"Rate limit exceeded for policy '{policy_name}'",
            )
        
        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            reset_at=reset_at,
        )
    
    def check_tenant(
        self,
        tenant_id: str,
        policies: Optional[List[str]] = None
    ) -> Dict[str, RateLimitResult]:
        if policies is None:
            policies = ["per_minute", "per_hour", "per_day"]
        
        results = {}
        for policy_name in policies:
            key = f"tenant:{tenant_id}"
            results[policy_name] = self.check(key, policy_name)
        
        return results
    
    def reset(self, key: str, policy_name: Optional[str] = None):
        with self._lock:
            if key not in self._counters:
                return
            
            if policy_name:
                if policy_name in self._counters[key]:
                    del self._counters[key][policy_name]
            else:
                del self._counters[key]
    
    def get_usage(self, key: str, policy_name: str) -> Dict[str, Any]:
        with self._lock:
            if key not in self._counters:
                return {"count": 0, "remaining": 0, "limit": 0}
            
            if policy_name not in self._counters[key]:
                return {"count": 0, "remaining": 0, "limit": 0}
            
            counter = self._counters[key][policy_name]
            policy = self._policies.get(policy_name)
            
            return {
                "count": counter.get_count(),
                "remaining": counter.get_remaining(),
                "limit": policy.max_requests if policy else 0,
                "reset_at": counter.get_reset_time().isoformat(),
            }
    
    def add_listener(self, callback: Callable):
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable):
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self, key: str, policy: str, event: str):
        for callback in self._listeners:
            try:
                callback(key, policy, event)
            except Exception:
                pass
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_keys = len(self._counters)
            active_keys = sum(
                1 for counters in self._counters.values()
                if any(c.get_count() > 0 for c in counters.values())
            )
            
            return {
                "total_tracked_keys": total_keys,
                "active_keys": active_keys,
                "policies": list(self._policies.keys()),
            }
