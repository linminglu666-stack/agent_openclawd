from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncio

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocols.interfaces import IMetricsCollector


@dataclass
class MetricPoint:
    name: str
    value: float
    metric_type: str
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type,
            "labels": self.labels,
            "timestamp": self.timestamp.isoformat(),
        }


class InMemoryMetricsCollector(IMetricsCollector):
    def __init__(self, max_points: int = 10000):
        self._max_points = max_points
        self._points: List[MetricPoint] = []
        self._lock = asyncio.Lock()

    def record_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> bool:
        return self._append(name=name, value=value, metric_type="counter", labels=labels)

    def record_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> bool:
        return self._append(name=name, value=value, metric_type="gauge", labels=labels)

    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> bool:
        return self._append(name=name, value=value, metric_type="histogram", labels=labels)

    def get_metrics(self, name: Optional[str] = None) -> Dict[str, Any]:
        points = [p for p in self._points if name is None or p.name == name]
        return {"count": len(points), "points": [p.to_dict() for p in points]}

    def _append(self, name: str, value: float, metric_type: str, labels: Optional[Dict[str, str]]) -> bool:
        point = MetricPoint(name=name, value=float(value), metric_type=metric_type, labels=labels or {})
        self._points.append(point)
        if len(self._points) > self._max_points:
            self._points = self._points[-self._max_points :]
        return True

