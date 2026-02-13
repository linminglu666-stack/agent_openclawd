from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import uuid
import asyncio

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocols.interfaces import ITracer
from utils.logger import get_logger


@dataclass
class Span:
    span_id: str
    operation_name: str
    trace_id: str
    parent_span_id: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    status: str = "ok"
    tags: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def duration_ms(self) -> Optional[float]:
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds() * 1000.0


class InMemoryTracer(ITracer):
    def __init__(self):
        self._traces: Dict[str, Dict[str, Span]] = {}
        self._span_index: Dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._logger = get_logger("observability.tracer")

    def start_span(self, operation_name: str, parent_span_id: Optional[str] = None) -> str:
        trace_id = self._span_index.get(parent_span_id) if parent_span_id else str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        span = Span(
            span_id=span_id,
            operation_name=operation_name,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        )
        if trace_id not in self._traces:
            self._traces[trace_id] = {}
        self._traces[trace_id][span_id] = span
        self._span_index[span_id] = trace_id
        return span_id

    def end_span(self, span_id: str, status: str = "ok") -> bool:
        trace_id = self._span_index.get(span_id)
        if not trace_id:
            return False
        span = self._traces.get(trace_id, {}).get(span_id)
        if not span:
            return False
        span.end_time = datetime.utcnow()
        span.status = status
        return True

    def add_event(self, span_id: str, event: Dict[str, Any]) -> bool:
        trace_id = self._span_index.get(span_id)
        if not trace_id:
            return False
        span = self._traces.get(trace_id, {}).get(span_id)
        if not span:
            return False
        span.events.append({"timestamp": datetime.utcnow().isoformat(), **(event or {})})
        return True

    def get_trace(self, trace_id: str) -> Dict[str, Any]:
        spans = self._traces.get(trace_id, {})
        return {
            "trace_id": trace_id,
            "spans": [
                {
                    "span_id": s.span_id,
                    "operation_name": s.operation_name,
                    "parent_span_id": s.parent_span_id,
                    "start_time": s.start_time.isoformat(),
                    "end_time": s.end_time.isoformat() if s.end_time else None,
                    "duration_ms": s.duration_ms(),
                    "status": s.status,
                    "tags": s.tags,
                    "events": s.events,
                }
                for s in spans.values()
            ],
        }

