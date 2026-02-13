"""
反馈闭环
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import threading


class FeedbackType(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    CORRECTION = "correction"
    SUGGESTION = "suggestion"


class FeedbackSource(Enum):
    USER = "user"
    SYSTEM = "system"
    EVALUATOR = "evaluator"
    AUDIT = "audit"
    EXTERNAL = "external"


@dataclass
class FeedbackEntry:
    feedback_id: str
    feedback_type: FeedbackType
    source: FeedbackSource
    
    component: str
    operation: str
    
    rating: Optional[float] = None
    comment: Optional[str] = None
    
    expected_output: Optional[Any] = None
    actual_output: Optional[Any] = None
    
    trace_id: str = ""
    session_id: str = ""
    tenant_id: str = ""
    
    created_at: datetime = field(default_factory=datetime.now)
    
    processed: bool = False
    processed_at: Optional[datetime] = None
    
    action_taken: Optional[str] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "feedback_type": self.feedback_type.value,
            "source": self.source.value,
            "component": self.component,
            "operation": self.operation,
            "rating": self.rating,
            "comment": self.comment,
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat(),
            "processed": self.processed,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "action_taken": self.action_taken,
            "metadata": self.metadata,
        }


@dataclass
class FeedbackAggregation:
    component: str
    operation: str
    
    total_feedback: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    
    avg_rating: float = 0.0
    rating_distribution: Dict[str, int] = field(default_factory=dict)
    
    top_issues: List[str] = field(default_factory=list)
    top_suggestions: List[str] = field(default_factory=list)
    
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "operation": self.operation,
            "total_feedback": self.total_feedback,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "avg_rating": self.avg_rating,
            "rating_distribution": self.rating_distribution,
            "top_issues": self.top_issues,
            "top_suggestions": self.top_suggestions,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
        }
    
    @property
    def satisfaction_rate(self) -> float:
        if self.total_feedback == 0:
            return 0.0
        return self.positive_count / self.total_feedback


class FeedbackLoop:
    
    def __init__(self):
        self._entries: Dict[str, FeedbackEntry] = {}
        self._component_index: Dict[str, List[str]] = {}
        self._handlers: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self._listeners: List[Callable] = []
    
    def submit(
        self,
        feedback_type: FeedbackType,
        source: FeedbackSource,
        component: str,
        operation: str,
        rating: Optional[float] = None,
        comment: Optional[str] = None,
        expected_output: Optional[Any] = None,
        actual_output: Optional[Any] = None,
        trace_id: str = "",
        session_id: str = "",
        tenant_id: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> FeedbackEntry:
        import uuid
        
        entry = FeedbackEntry(
            feedback_id=f"fb-{uuid.uuid4().hex[:8]}",
            feedback_type=feedback_type,
            source=source,
            component=component,
            operation=operation,
            rating=rating,
            comment=comment,
            expected_output=expected_output,
            actual_output=actual_output,
            trace_id=trace_id,
            session_id=session_id,
            tenant_id=tenant_id,
            metadata=metadata or {},
        )
        
        with self._lock:
            self._entries[entry.feedback_id] = entry
            
            key = f"{component}:{operation}"
            if key not in self._component_index:
                self._component_index[key] = []
            self._component_index[key].append(entry.feedback_id)
        
        self._process_feedback(entry)
        self._notify_listeners("submitted", entry)
        
        return entry
    
    def submit_user_feedback(
        self,
        component: str,
        operation: str,
        rating: float,
        comment: Optional[str] = None,
        trace_id: str = ""
    ) -> FeedbackEntry:
        if rating >= 4:
            feedback_type = FeedbackType.POSITIVE
        elif rating >= 3:
            feedback_type = FeedbackType.NEUTRAL
        else:
            feedback_type = FeedbackType.NEGATIVE
        
        return self.submit(
            feedback_type=feedback_type,
            source=FeedbackSource.USER,
            component=component,
            operation=operation,
            rating=rating,
            comment=comment,
            trace_id=trace_id,
        )
    
    def submit_correction(
        self,
        component: str,
        operation: str,
        expected_output: Any,
        actual_output: Any,
        trace_id: str = ""
    ) -> FeedbackEntry:
        return self.submit(
            feedback_type=FeedbackType.CORRECTION,
            source=FeedbackSource.USER,
            component=component,
            operation=operation,
            expected_output=expected_output,
            actual_output=actual_output,
            trace_id=trace_id,
        )
    
    def register_handler(self, component: str, handler: Callable):
        self._handlers[component] = handler
    
    def _process_feedback(self, entry: FeedbackEntry):
        handler = self._handlers.get(entry.component)
        if handler:
            try:
                action = handler(entry)
                entry.action_taken = action
                entry.processed = True
                entry.processed_at = datetime.now()
            except Exception:
                pass
    
    def get_entry(self, feedback_id: str) -> Optional[FeedbackEntry]:
        return self._entries.get(feedback_id)
    
    def get_entries_by_component(
        self,
        component: str,
        operation: Optional[str] = None,
        limit: int = 100
    ) -> List[FeedbackEntry]:
        with self._lock:
            if operation:
                key = f"{component}:{operation}"
                entry_ids = self._component_index.get(key, [])
            else:
                entry_ids = []
                for k, ids in self._component_index.items():
                    if k.startswith(f"{component}:"):
                        entry_ids.extend(ids)
        
        entries = [self._entries[eid] for eid in entry_ids if eid in self._entries]
        entries.sort(key=lambda x: x.created_at, reverse=True)
        return entries[:limit]
    
    def aggregate(
        self,
        component: str,
        operation: Optional[str] = None,
        days: int = 7
    ) -> FeedbackAggregation:
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        
        entries = self.get_entries_by_component(component, operation)
        entries = [e for e in entries if e.created_at >= cutoff]
        
        if not entries:
            return FeedbackAggregation(
                component=component,
                operation=operation or "*",
                period_start=cutoff,
                period_end=datetime.now(),
            )
        
        positive = sum(1 for e in entries if e.feedback_type == FeedbackType.POSITIVE)
        negative = sum(1 for e in entries if e.feedback_type == FeedbackType.NEGATIVE)
        neutral = sum(1 for e in entries if e.feedback_type == FeedbackType.NEUTRAL)
        
        ratings = [e.rating for e in entries if e.rating is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
        
        rating_dist: Dict[str, int] = {}
        for r in ratings:
            bucket = str(int(r))
            rating_dist[bucket] = rating_dist.get(bucket, 0) + 1
        
        issues = []
        suggestions = []
        for e in entries:
            if e.feedback_type == FeedbackType.NEGATIVE and e.comment:
                issues.append(e.comment)
            elif e.feedback_type == FeedbackType.SUGGESTION and e.comment:
                suggestions.append(e.comment)
        
        return FeedbackAggregation(
            component=component,
            operation=operation or "*",
            total_feedback=len(entries),
            positive_count=positive,
            negative_count=negative,
            neutral_count=neutral,
            avg_rating=avg_rating,
            rating_distribution=rating_dist,
            top_issues=issues[:5],
            top_suggestions=suggestions[:5],
            period_start=cutoff,
            period_end=datetime.now(),
        )
    
    def get_unprocessed(self, limit: int = 100) -> List[FeedbackEntry]:
        entries = [e for e in self._entries.values() if not e.processed]
        entries.sort(key=lambda x: x.created_at)
        return entries[:limit]
    
    def mark_processed(self, feedback_id: str, action_taken: str) -> bool:
        with self._lock:
            entry = self._entries.get(feedback_id)
            if not entry:
                return False
            
            entry.processed = True
            entry.processed_at = datetime.now()
            entry.action_taken = action_taken
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        entries = list(self._entries.values())
        
        by_type: Dict[str, int] = {}
        for e in entries:
            key = e.feedback_type.value
            by_type[key] = by_type.get(key, 0) + 1
        
        return {
            "total_feedback": len(entries),
            "processed": sum(1 for e in entries if e.processed),
            "unprocessed": sum(1 for e in entries if not e.processed),
            "by_type": by_type,
            "components_with_feedback": len(self._component_index),
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
