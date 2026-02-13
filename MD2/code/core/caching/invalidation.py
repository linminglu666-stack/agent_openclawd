"""
缓存失效广播
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import asyncio
import threading


class InvalidationType(Enum):
    KEY = "key"
    TAG = "tag"
    PREFIX = "prefix"
    ALL = "all"


@dataclass
class InvalidationEvent:
    event_id: str
    invalidation_type: InvalidationType
    target: str
    source_node: str
    
    created_at: datetime = field(default_factory=datetime.now)
    processed: bool = False
    processed_at: Optional[datetime] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "invalidation_type": self.invalidation_type.value,
            "target": self.target,
            "source_node": self.source_node,
            "created_at": self.created_at.isoformat(),
            "processed": self.processed,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvalidationEvent":
        return cls(
            event_id=data["event_id"],
            invalidation_type=InvalidationType(data["invalidation_type"]),
            target=data["target"],
            source_node=data["source_node"],
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            processed=data.get("processed", False),
            processed_at=datetime.fromisoformat(data["processed_at"]) if data.get("processed_at") else None,
            metadata=data.get("metadata", {}),
        )


class InvalidationBroadcaster:
    
    def __init__(self, node_id: str = "node-1"):
        self.node_id = node_id
        self._handlers: List[Callable] = []
        self._pending_events: List[InvalidationEvent] = []
        self._processed_events: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        self._listeners: List[Callable] = []
    
    def broadcast_key_invalidation(self, key: str):
        event = self._create_event(InvalidationType.KEY, key)
        self._broadcast(event)
    
    def broadcast_tag_invalidation(self, tag: str):
        event = self._create_event(InvalidationType.TAG, tag)
        self._broadcast(event)
    
    def broadcast_prefix_invalidation(self, prefix: str):
        event = self._create_event(InvalidationType.PREFIX, prefix)
        self._broadcast(event)
    
    def broadcast_all_invalidation(self):
        event = self._create_event(InvalidationType.ALL, "*")
        self._broadcast(event)
    
    def _create_event(self, invalidation_type: InvalidationType, target: str) -> InvalidationEvent:
        import uuid
        return InvalidationEvent(
            event_id=f"inv-{uuid.uuid4().hex[:8]}",
            invalidation_type=invalidation_type,
            target=target,
            source_node=self.node_id,
        )
    
    def _broadcast(self, event: InvalidationEvent):
        with self._lock:
            self._pending_events.append(event)
        
        for callback in self._handlers:
            try:
                callback(event)
            except Exception:
                pass
        
        self._notify_listeners("broadcast", event)
    
    def register_handler(self, handler: Callable):
        self._handlers.append(handler)
    
    def unregister_handler(self, handler: Callable):
        if handler in self._handlers:
            self._handlers.remove(handler)
    
    def receive_event(self, event_data: Dict[str, Any]) -> bool:
        try:
            event = InvalidationEvent.from_dict(event_data)
            
            if event.source_node == self.node_id:
                return False
            
            with self._lock:
                if event.event_id in self._processed_events:
                    return False
                
                self._processed_events[event.event_id] = datetime.now()
                
                self._cleanup_old_events()
            
            event.processed = True
            event.processed_at = datetime.now()
            
            self._notify_listeners("receive", event)
            return True
            
        except Exception:
            return False
    
    def _cleanup_old_events(self):
        cutoff = datetime.now()
        self._processed_events = {
            k: v for k, v in self._processed_events.items()
        }
    
    def get_pending_events(self) -> List[InvalidationEvent]:
        with self._lock:
            return list(self._pending_events)
    
    def clear_pending_events(self):
        with self._lock:
            self._pending_events.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "node_id": self.node_id,
                "pending_events": len(self._pending_events),
                "processed_events": len(self._processed_events),
                "handlers_count": len(self._handlers),
            }
    
    def add_listener(self, callback: Callable):
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable):
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self, event_type: str, event: InvalidationEvent):
        for callback in self._listeners:
            try:
                callback(event_type, event)
            except Exception:
                pass
