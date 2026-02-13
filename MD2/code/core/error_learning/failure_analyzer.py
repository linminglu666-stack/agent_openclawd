"""
失败分析器
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import threading


class FailureType(Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    INTERMITTENT = "intermittent"
    CASCADING = "cascading"


@dataclass
class FailureEvent:
    event_id: str
    failure_type: FailureType
    
    component: str
    operation: str
    error_message: str
    
    timestamp: datetime = field(default_factory=datetime.now)
    
    trace_id: str = ""
    correlation_id: str = ""
    
    impact: str = "unknown"
    affected_users: int = 0
    
    context: Dict[str, Any] = field(default_factory=dict)
    
    root_cause: Optional[str] = None
    resolution: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "failure_type": self.failure_type.value,
            "component": self.component,
            "operation": self.operation,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "impact": self.impact,
            "affected_users": self.affected_users,
            "context": self.context,
            "root_cause": self.root_cause,
            "resolution": self.resolution,
        }


@dataclass
class FailureReport:
    report_id: str
    generated_at: datetime = field(default_factory=datetime.now)
    
    total_failures: int = 0
    unique_failures: int = 0
    
    by_component: Dict[str, int] = field(default_factory=dict)
    by_type: Dict[str, int] = field(default_factory=dict)
    by_hour: Dict[int, int] = field(default_factory=dict)
    
    top_failures: List[Dict[str, Any]] = field(default_factory=list)
    
    mttr_minutes: float = 0.0
    mtbf_minutes: float = 0.0
    
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "total_failures": self.total_failures,
            "unique_failures": self.unique_failures,
            "by_component": self.by_component,
            "by_type": self.by_type,
            "by_hour": self.by_hour,
            "top_failures": self.top_failures,
            "mttr_minutes": self.mttr_minutes,
            "mtbf_minutes": self.mtbf_minutes,
            "recommendations": self.recommendations,
        }


class FailureAnalyzer:
    
    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        
        self._events: Dict[str, FailureEvent] = {}
        self._component_index: Dict[str, List[str]] = {}
        self._lock = threading.Lock()
        self._listeners: List[Callable] = []
    
    def record(
        self,
        component: str,
        operation: str,
        error_message: str,
        failure_type: FailureType = FailureType.TRANSIENT,
        trace_id: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> FailureEvent:
        import uuid
        
        event = FailureEvent(
            event_id=f"fail-{uuid.uuid4().hex[:8]}",
            failure_type=failure_type,
            component=component,
            operation=operation,
            error_message=error_message,
            trace_id=trace_id,
            context=context or {},
        )
        
        with self._lock:
            self._events[event.event_id] = event
            
            if component not in self._component_index:
                self._component_index[component] = []
            self._component_index[component].append(event.event_id)
        
        self._notify_listeners("recorded", event)
        return event
    
    def get_event(self, event_id: str) -> Optional[FailureEvent]:
        return self._events.get(event_id)
    
    def get_events_by_component(self, component: str) -> List[FailureEvent]:
        event_ids = self._component_index.get(component, [])
        return [self._events[eid] for eid in event_ids if eid in self._events]
    
    def get_recent_events(
        self,
        hours: int = 1,
        component: Optional[str] = None
    ) -> List[FailureEvent]:
        cutoff = datetime.now() - timedelta(hours=hours)
        
        events = list(self._events.values())
        events = [e for e in events if e.timestamp >= cutoff]
        
        if component:
            events = [e for e in events if e.component == component]
        
        events.sort(key=lambda x: x.timestamp, reverse=True)
        return events
    
    def analyze(self, hours: int = 24) -> FailureReport:
        import uuid
        
        events = self.get_recent_events(hours)
        
        by_component: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        by_hour: Dict[int, int] = {}
        
        unique_errors: Dict[str, int] = {}
        
        for event in events:
            by_component[event.component] = by_component.get(event.component, 0) + 1
            by_type[event.failure_type.value] = by_type.get(event.failure_type.value, 0) + 1
            
            hour = event.timestamp.hour
            by_hour[hour] = by_hour.get(hour, 0) + 1
            
            error_key = f"{event.component}:{event.operation}:{event.error_message[:50]}"
            unique_errors[error_key] = unique_errors.get(error_key, 0) + 1
        
        top_failures = [
            {"key": k, "count": v}
            for k, v in sorted(unique_errors.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        recommendations = self._generate_recommendations(
            by_component, by_type, events
        )
        
        return FailureReport(
            report_id=f"report-{uuid.uuid4().hex[:8]}",
            total_failures=len(events),
            unique_failures=len(unique_errors),
            by_component=by_component,
            by_type=by_type,
            by_hour=by_hour,
            top_failures=top_failures,
            recommendations=recommendations,
        )
    
    def _generate_recommendations(
        self,
        by_component: Dict[str, int],
        by_type: Dict[str, int],
        events: List[FailureEvent]
    ) -> List[str]:
        recommendations = []
        
        if by_type.get(FailureType.CASCADING.value, 0) > 0:
            recommendations.append(
                "Cascading failures detected - implement circuit breakers"
            )
        
        if by_type.get(FailureType.TRANSIENT.value, 0) > len(events) * 0.5:
            recommendations.append(
                "High transient failure rate - review retry strategies"
            )
        
        top_component = max(by_component.items(), key=lambda x: x[1])[0] if by_component else None
        if top_component and by_component[top_component] > len(events) * 0.3:
            recommendations.append(
                f"Component '{top_component}' accounts for >30% of failures - prioritize investigation"
            )
        
        if len(events) > 100:
            recommendations.append(
                "High failure volume - consider implementing rate limiting or load shedding"
            )
        
        return recommendations
    
    def set_resolution(self, event_id: str, root_cause: str, resolution: str) -> bool:
        with self._lock:
            event = self._events.get(event_id)
            if not event:
                return False
            
            event.root_cause = root_cause
            event.resolution = resolution
            return True
    
    def cleanup_old_events(self) -> int:
        cutoff = datetime.now() - timedelta(hours=self.retention_hours)
        
        with self._lock:
            to_remove = [
                eid for eid, event in self._events.items()
                if event.timestamp < cutoff
            ]
            
            for eid in to_remove:
                del self._events[eid]
            
            for component in list(self._component_index.keys()):
                self._component_index[component] = [
                    eid for eid in self._component_index[component]
                    if eid in self._events
                ]
                if not self._component_index[component]:
                    del self._component_index[component]
            
            return len(to_remove)
    
    def get_stats(self) -> Dict[str, Any]:
        events = list(self._events.values())
        
        return {
            "total_events": len(events),
            "retention_hours": self.retention_hours,
            "components_tracked": len(self._component_index),
            "oldest_event": min(e.timestamp for e in events).isoformat() if events else None,
            "newest_event": max(e.timestamp for e in events).isoformat() if events else None,
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
