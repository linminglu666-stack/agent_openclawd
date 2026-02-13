from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple
import math
import threading
from abc import ABC, abstractmethod


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class EntropyLevel(int, Enum):
    SYSTEM = 0
    MODULE = 1
    COMPONENT = 2
    FUNCTION = 3


class EntropyCategory(str, Enum):
    INPUT = "input"
    EVOLUTION = "evolution"
    OBSERVABILITY = "observability"
    STRUCTURE = "structure"
    BEHAVIOR = "behavior"
    DATA = "data"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class SweepPriority(int, Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    DEFERRED = 4


class SweepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class EntropyThreshold:
    category: EntropyCategory
    warning: float
    critical: float
    emergency: float
    weight: float = 1.0
    
    def classify(self, value: float) -> AlertSeverity:
        if value >= self.emergency:
            return AlertSeverity.EMERGENCY
        if value >= self.critical:
            return AlertSeverity.CRITICAL
        if value >= self.warning:
            return AlertSeverity.WARNING
        return AlertSeverity.INFO


@dataclass
class EntropySample:
    timestamp: datetime
    category: EntropyCategory
    level: EntropyLevel
    source: str
    value: float
    raw_metrics: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class EntropyAlert:
    alert_id: str
    timestamp: datetime
    severity: AlertSeverity
    category: EntropyCategory
    source: str
    current_value: float
    threshold: float
    message: str
    suggested_actions: List[str] = field(default_factory=list)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


@dataclass
class SweepAction:
    action_id: str
    name: str
    description: str
    priority: SweepPriority
    category: EntropyCategory
    source: str
    estimated_impact: float
    executor: Optional[str] = None
    status: SweepStatus = SweepStatus.PENDING
    created_at: datetime = field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    actual_impact: Optional[float] = None


@dataclass
class TrendAnalysis:
    category: EntropyCategory
    source: str
    samples_count: int
    time_range_hours: float
    mean: float
    std_dev: float
    min_val: float
    max_val: float
    slope: float
    trend_direction: str
    prediction_1h: Optional[float] = None
    prediction_24h: Optional[float] = None
    confidence: float = 0.0


@dataclass
class AttributionResult:
    source: str
    category: EntropyCategory
    contribution_ratio: float
    absolute_value: float
    trend_impact: float
    related_sources: List[str] = field(default_factory=list)
    root_cause_hypothesis: str = ""


@dataclass
class EntropyReport:
    timestamp: datetime
    total_entropy: float
    by_category: Dict[EntropyCategory, float]
    by_level: Dict[EntropyLevel, float]
    top_contributors: List[AttributionResult]
    active_alerts: List[EntropyAlert]
    pending_sweeps: List[SweepAction]
    trends: List[TrendAnalysis]
    health_score: float
    recommendations: List[str]


@dataclass
class AdaptiveThreshold:
    category: EntropyCategory
    base_warning: float
    base_critical: float
    base_emergency: float
    adaptive_factor: float = 1.0
    learning_rate: float = 0.1
    history_window: int = 100
    min_samples_for_adaptation: int = 20
