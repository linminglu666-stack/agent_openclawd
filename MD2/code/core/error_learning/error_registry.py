"""
错误模式注册中心
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import hashlib
import json
import threading


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    VALIDATION = "validation"
    DEPENDENCY = "dependency"
    LOGIC = "logic"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    PERMISSION = "permission"
    DATA = "data"
    UNKNOWN = "unknown"


@dataclass
class ErrorInstance:
    instance_id: str
    pattern_id: str
    
    error_message: str
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    occurred_at: datetime = field(default_factory=datetime.now)
    component: str = ""
    operation: str = ""
    
    trace_id: str = ""
    span_id: str = ""
    tenant_id: str = ""
    
    resolved: bool = False
    resolution: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "pattern_id": self.pattern_id,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "context": self.context,
            "occurred_at": self.occurred_at.isoformat(),
            "component": self.component,
            "operation": self.operation,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "tenant_id": self.tenant_id,
            "resolved": self.resolved,
            "resolution": self.resolution,
        }


@dataclass
class ErrorPattern:
    pattern_id: str
    name: str
    category: ErrorCategory
    severity: ErrorSeverity
    
    description: str = ""
    
    signature_patterns: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    occurrences: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    
    components_affected: List[str] = field(default_factory=list)
    
    root_cause_hypothesis: str = ""
    suggested_fix: str = ""
    
    auto_recoverable: bool = False
    recovery_strategy: str = ""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "signature_patterns": self.signature_patterns,
            "keywords": self.keywords,
            "occurrences": self.occurrences,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "components_affected": self.components_affected,
            "root_cause_hypothesis": self.root_cause_hypothesis,
            "suggested_fix": self.suggested_fix,
            "auto_recoverable": self.auto_recoverable,
            "recovery_strategy": self.recovery_strategy,
            "metadata": self.metadata,
        }
    
    def matches(self, error_message: str, context: Optional[Dict] = None) -> bool:
        error_lower = error_message.lower()
        
        for keyword in self.keywords:
            if keyword.lower() in error_lower:
                return True
        
        import re
        for pattern in self.signature_patterns:
            try:
                if re.search(pattern, error_message, re.IGNORECASE):
                    return True
            except re.error:
                continue
        
        return False


class ErrorPatternRegistry:
    
    def __init__(self):
        self._patterns: Dict[str, ErrorPattern] = {}
        self._instances: Dict[str, ErrorInstance] = {}
        self._category_index: Dict[ErrorCategory, List[str]] = {}
        self._lock = threading.Lock()
        self._listeners: List[Callable] = []
        
        self._initialize_common_patterns()
    
    def _initialize_common_patterns(self):
        common_patterns = [
            ErrorPattern(
                pattern_id="timeout_generic",
                name="Generic Timeout",
                category=ErrorCategory.TIMEOUT,
                severity=ErrorSeverity.MEDIUM,
                keywords=["timeout", "timed out", "deadline exceeded"],
                suggested_fix="Increase timeout or optimize operation",
            ),
            ErrorPattern(
                pattern_id="rate_limit_exceeded",
                name="Rate Limit Exceeded",
                category=ErrorCategory.RATE_LIMIT,
                severity=ErrorSeverity.HIGH,
                keywords=["rate limit", "too many requests", "429"],
                suggested_fix="Implement exponential backoff and retry",
            ),
            ErrorPattern(
                pattern_id="connection_refused",
                name="Connection Refused",
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.HIGH,
                keywords=["connection refused", "econnrefused", "network unreachable"],
                suggested_fix="Check service availability and network configuration",
            ),
            ErrorPattern(
                pattern_id="out_of_memory",
                name="Out of Memory",
                category=ErrorCategory.RESOURCE_EXHAUSTED,
                severity=ErrorSeverity.CRITICAL,
                keywords=["out of memory", "oom", "memory allocation failed"],
                suggested_fix="Reduce memory usage or increase available memory",
            ),
            ErrorPattern(
                pattern_id="validation_failed",
                name="Validation Failed",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.LOW,
                keywords=["validation failed", "invalid", "malformed"],
                suggested_fix="Check input data format and constraints",
            ),
        ]
        
        for pattern in common_patterns:
            self._patterns[pattern.pattern_id] = pattern
    
    def register_pattern(self, pattern: ErrorPattern) -> bool:
        with self._lock:
            if pattern.pattern_id in self._patterns:
                return False
            
            self._patterns[pattern.pattern_id] = pattern
            
            if pattern.category not in self._category_index:
                self._category_index[pattern.category] = []
            self._category_index[pattern.category].append(pattern.pattern_id)
            
            self._notify_listeners("pattern_registered", pattern)
            return True
    
    def record_error(
        self,
        error_message: str,
        stack_trace: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        component: str = "",
        operation: str = "",
        trace_id: str = "",
        tenant_id: str = ""
    ) -> ErrorInstance:
        import uuid
        
        pattern = self._find_matching_pattern(error_message, context)
        
        instance = ErrorInstance(
            instance_id=f"err-{uuid.uuid4().hex[:8]}",
            pattern_id=pattern.pattern_id if pattern else "unknown",
            error_message=error_message,
            stack_trace=stack_trace,
            context=context or {},
            component=component,
            operation=operation,
            trace_id=trace_id,
            tenant_id=tenant_id,
        )
        
        with self._lock:
            self._instances[instance.instance_id] = instance
            
            if pattern:
                pattern.occurrences += 1
                pattern.last_seen = datetime.now()
                if pattern.first_seen is None:
                    pattern.first_seen = datetime.now()
                
                if component and component not in pattern.components_affected:
                    pattern.components_affected.append(component)
        
        self._notify_listeners("error_recorded", instance)
        return instance
    
    def _find_matching_pattern(
        self,
        error_message: str,
        context: Optional[Dict] = None
    ) -> Optional[ErrorPattern]:
        for pattern in self._patterns.values():
            if pattern.matches(error_message, context):
                return pattern
        return None
    
    def get_pattern(self, pattern_id: str) -> Optional[ErrorPattern]:
        return self._patterns.get(pattern_id)
    
    def get_patterns_by_category(self, category: ErrorCategory) -> List[ErrorPattern]:
        pattern_ids = self._category_index.get(category, [])
        return [self._patterns[pid] for pid in pattern_ids if pid in self._patterns]
    
    def get_instance(self, instance_id: str) -> Optional[ErrorInstance]:
        return self._instances.get(instance_id)
    
    def get_recent_instances(
        self,
        limit: int = 100,
        pattern_id: Optional[str] = None,
        component: Optional[str] = None
    ) -> List[ErrorInstance]:
        instances = list(self._instances.values())
        
        if pattern_id:
            instances = [i for i in instances if i.pattern_id == pattern_id]
        if component:
            instances = [i for i in instances if i.component == component]
        
        instances.sort(key=lambda x: x.occurred_at, reverse=True)
        return instances[:limit]
    
    def resolve_instance(self, instance_id: str, resolution: str) -> bool:
        with self._lock:
            instance = self._instances.get(instance_id)
            if not instance:
                return False
            
            instance.resolved = True
            instance.resolution = resolution
            return True
    
    def get_top_patterns(self, limit: int = 10) -> List[ErrorPattern]:
        patterns = list(self._patterns.values())
        patterns.sort(key=lambda x: x.occurrences, reverse=True)
        return patterns[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        total_instances = len(self._instances)
        resolved_instances = sum(1 for i in self._instances.values() if i.resolved)
        
        by_category = {}
        for category in ErrorCategory:
            patterns = self.get_patterns_by_category(category)
            by_category[category.value] = {
                "pattern_count": len(patterns),
                "total_occurrences": sum(p.occurrences for p in patterns),
            }
        
        return {
            "total_patterns": len(self._patterns),
            "total_instances": total_instances,
            "resolved_instances": resolved_instances,
            "unresolved_instances": total_instances - resolved_instances,
            "by_category": by_category,
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
