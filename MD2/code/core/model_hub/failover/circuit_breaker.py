"""
熔断器
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import threading
import time


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitStats:
    total_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_state_change: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "last_state_change": self.last_state_change.isoformat() if self.last_state_change else None,
        }


class CircuitBreaker:
    
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout: int = 30,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._lock = threading.Lock()
        self._half_open_calls = 0
        self._listeners: List[Callable] = []
    
    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state
    
    @property
    def stats(self) -> CircuitStats:
        with self._lock:
            return self._stats
    
    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        return self.state == CircuitState.HALF_OPEN
    
    def can_execute(self) -> bool:
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to(CircuitState.HALF_OPEN)
                    return True
                return False
            
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
            
            return False
    
    def record_success(self):
        with self._lock:
            self._stats.total_requests += 1
            self._stats.total_successes += 1
            self._stats.consecutive_failures = 0
            self._stats.consecutive_successes += 1
            self._stats.last_success_time = datetime.now()
            
            if self._state == CircuitState.HALF_OPEN:
                if self._stats.consecutive_successes >= self.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
    
    def record_failure(self, error: Optional[str] = None):
        with self._lock:
            self._stats.total_requests += 1
            self._stats.total_failures += 1
            self._stats.consecutive_successes = 0
            self._stats.consecutive_failures += 1
            self._stats.last_failure_time = datetime.now()
            
            if self._state == CircuitState.CLOSED:
                if self._stats.consecutive_failures >= self.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
            
            elif self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.OPEN)
    
    def _should_attempt_reset(self) -> bool:
        if not self._stats.last_failure_time:
            return True
        
        elapsed = datetime.now() - self._stats.last_failure_time
        return elapsed >= timedelta(seconds=self.timeout)
    
    def _transition_to(self, new_state: CircuitState):
        old_state = self._state
        self._state = new_state
        self._stats.last_state_change = datetime.now()
        
        if new_state == CircuitState.CLOSED:
            self._stats.consecutive_failures = 0
            self._stats.consecutive_successes = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
        
        self._notify_listeners(old_state, new_state)
    
    def force_open(self):
        with self._lock:
            self._transition_to(CircuitState.OPEN)
    
    def force_close(self):
        with self._lock:
            self._transition_to(CircuitState.CLOSED)
    
    def reset(self):
        with self._lock:
            self._state = CircuitState.CLOSED
            self._stats = CircuitStats()
            self._half_open_calls = 0
    
    def add_listener(self, callback: Callable):
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable):
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self, old_state: CircuitState, new_state: CircuitState):
        for callback in self._listeners:
            try:
                callback(old_state, new_state, self._stats)
            except Exception:
                pass
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "stats": self._stats.to_dict(),
            "config": {
                "failure_threshold": self.failure_threshold,
                "success_threshold": self.success_threshold,
                "timeout": self.timeout,
                "half_open_max_calls": self.half_open_max_calls,
            }
        }
