from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import math
import threading

from base_types import (
    utc_now, EntropyLevel, EntropyCategory, EntropySample, EntropyThreshold,
    EntropyAlert, AlertSeverity, AttributionResult, AdaptiveThreshold
)


def exponential_decay(age_hours: float, half_life_hours: float = 24.0) -> float:
    if age_hours < 0:
        return 1.0
    return math.exp(-math.log(2) * age_hours / half_life_hours)


def weighted_entropy(values: List[Tuple[float, float]]) -> float:
    if not values:
        return 0.0
    total_weight = sum(w for _, w in values)
    if total_weight <= 0:
        return 0.0
    weighted_sum = sum(v * w for v, w in values)
    return weighted_sum / total_weight


@dataclass
class MetricDefinition:
    name: str
    category: EntropyCategory
    level: EntropyLevel
    weight: float = 1.0
    decay_half_life_hours: float = 24.0
    normalize_fn: Optional[str] = None


DEFAULT_THRESHOLDS: Dict[EntropyCategory, EntropyThreshold] = {
    EntropyCategory.INPUT: EntropyThreshold(
        category=EntropyCategory.INPUT,
        warning=0.3, critical=0.6, emergency=0.8, weight=1.0
    ),
    EntropyCategory.EVOLUTION: EntropyThreshold(
        category=EntropyCategory.EVOLUTION,
        warning=0.4, critical=0.7, emergency=0.9, weight=1.2
    ),
    EntropyCategory.OBSERVABILITY: EntropyThreshold(
        category=EntropyCategory.OBSERVABILITY,
        warning=0.35, critical=0.65, emergency=0.85, weight=0.8
    ),
    EntropyCategory.STRUCTURE: EntropyThreshold(
        category=EntropyCategory.STRUCTURE,
        warning=0.25, critical=0.5, emergency=0.75, weight=1.1
    ),
    EntropyCategory.BEHAVIOR: EntropyThreshold(
        category=EntropyCategory.BEHAVIOR,
        warning=0.3, critical=0.6, emergency=0.8, weight=1.0
    ),
    EntropyCategory.DATA: EntropyThreshold(
        category=EntropyCategory.DATA,
        warning=0.35, critical=0.65, emergency=0.85, weight=0.9
    ),
}


class EntropyCalculator:
    def __init__(
        self,
        thresholds: Optional[Dict[EntropyCategory, EntropyThreshold]] = None,
        max_samples: int = 10000,
        sample_retention_hours: float = 168.0,
    ):
        self._thresholds = thresholds or dict(DEFAULT_THRESHOLDS)
        self._max_samples = max_samples
        self._sample_retention_hours = sample_retention_hours
        self._samples: List[EntropySample] = []
        self._lock = threading.RLock()
        self._metric_registry: Dict[str, MetricDefinition] = {}
        self._register_default_metrics()

    def _register_default_metrics(self) -> None:
        defaults = [
            MetricDefinition("inbox_stale", EntropyCategory.INPUT, EntropyLevel.SYSTEM, 1.5, 12.0),
            MetricDefinition("unindexed_outputs", EntropyCategory.EVOLUTION, EntropyLevel.MODULE, 1.2, 24.0),
            MetricDefinition("duplicate_topics", EntropyCategory.DATA, EntropyLevel.MODULE, 1.0, 48.0),
            MetricDefinition("rework_rate", EntropyCategory.BEHAVIOR, EntropyLevel.SYSTEM, 2.0, 168.0),
            MetricDefinition("retrieval_time", EntropyCategory.OBSERVABILITY, EntropyLevel.COMPONENT, 0.8, 6.0),
            MetricDefinition("config_drift", EntropyCategory.STRUCTURE, EntropyLevel.SYSTEM, 1.3, 24.0),
            MetricDefinition("dependency_churn", EntropyCategory.STRUCTURE, EntropyLevel.MODULE, 1.1, 72.0),
            MetricDefinition("error_rate", EntropyCategory.BEHAVIOR, EntropyLevel.COMPONENT, 1.8, 1.0),
            MetricDefinition("latency_variance", EntropyCategory.BEHAVIOR, EntropyLevel.COMPONENT, 1.0, 6.0),
            MetricDefinition("cache_miss_rate", EntropyCategory.DATA, EntropyLevel.COMPONENT, 0.7, 1.0),
        ]
        for m in defaults:
            self._metric_registry[m.name] = m

    def register_metric(self, definition: MetricDefinition) -> None:
        with self._lock:
            self._metric_registry[definition.name] = definition

    def record_sample(
        self,
        metric_name: str,
        value: float,
        source: str,
        raw_metrics: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None,
    ) -> Optional[EntropySample]:
        with self._lock:
            if metric_name not in self._metric_registry:
                return None
            definition = self._metric_registry[metric_name]
            sample = EntropySample(
                timestamp=timestamp or utc_now(),
                category=definition.category,
                level=definition.level,
                source=source,
                value=value,
                raw_metrics=raw_metrics or {},
                tags=tags or {},
            )
            self._samples.append(sample)
            self._prune_samples()
            return sample

    def record_raw_sample(self, sample: EntropySample) -> None:
        with self._lock:
            self._samples.append(sample)
            self._prune_samples()

    def _prune_samples(self) -> None:
        if len(self._samples) <= self._max_samples:
            return
        cutoff = utc_now() - timedelta(hours=self._sample_retention_hours)
        self._samples = [s for s in self._samples if s.timestamp >= cutoff]
        if len(self._samples) > self._max_samples:
            self._samples = self._samples[-self._max_samples:]

    def compute_entropy(
        self,
        category: Optional[EntropyCategory] = None,
        level: Optional[EntropyLevel] = None,
        source: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> float:
        with self._lock:
            samples = self._filter_samples(category, level, source, since)
            if not samples:
                return 0.0
            weighted_values: List[Tuple[float, float]] = []
            now = utc_now()
            for sample in samples:
                metric_def = self._find_metric_for_sample(sample)
                if not metric_def:
                    continue
                age_hours = (now - sample.timestamp).total_seconds() / 3600
                decay = exponential_decay(age_hours, metric_def.decay_half_life_hours)
                threshold = self._thresholds.get(sample.category)
                threshold_weight = threshold.weight if threshold else 1.0
                total_weight = metric_def.weight * decay * threshold_weight
                weighted_values.append((sample.value, total_weight))
            return weighted_entropy(weighted_values)

    def compute_by_category(
        self, since: Optional[datetime] = None
    ) -> Dict[EntropyCategory, float]:
        result: Dict[EntropyCategory, float] = {}
        for cat in EntropyCategory:
            result[cat] = self.compute_entropy(category=cat, since=since)
        return result

    def compute_by_level(
        self, since: Optional[datetime] = None
    ) -> Dict[EntropyLevel, float]:
        result: Dict[EntropyLevel, float] = {}
        for lvl in EntropyLevel:
            result[lvl] = self.compute_entropy(level=lvl, since=since)
        return result

    def compute_total_entropy(self, since: Optional[datetime] = None) -> float:
        by_category = self.compute_by_category(since)
        if not by_category:
            return 0.0
        weighted_sum = 0.0
        total_weight = 0.0
        for cat, value in by_category.items():
            threshold = self._thresholds.get(cat)
            weight = threshold.weight if threshold else 1.0
            weighted_sum += value * weight
            total_weight += weight
        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def compute_health_score(self, since: Optional[datetime] = None) -> float:
        total = self.compute_total_entropy(since)
        return max(0.0, min(1.0, 1.0 - total))

    def _filter_samples(
        self,
        category: Optional[EntropyCategory],
        level: Optional[EntropyLevel],
        source: Optional[str],
        since: Optional[datetime],
    ) -> List[EntropySample]:
        result = self._samples
        if since:
            result = [s for s in result if s.timestamp >= since]
        if category:
            result = [s for s in result if s.category == category]
        if level:
            result = [s for s in result if s.level == level]
        if source:
            result = [s for s in result if s.source == source]
        return result

    def _find_metric_for_sample(self, sample: EntropySample) -> Optional[MetricDefinition]:
        for definition in self._metric_registry.values():
            if definition.category == sample.category and definition.level == sample.level:
                return definition
        return None

    def get_samples(
        self,
        category: Optional[EntropyCategory] = None,
        level: Optional[EntropyLevel] = None,
        source: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[EntropySample]:
        with self._lock:
            samples = self._filter_samples(category, level, source, since)
            return samples[-limit:]

    def get_threshold(self, category: EntropyCategory) -> EntropyThreshold:
        return self._thresholds.get(category, DEFAULT_THRESHOLDS[category])

    def set_threshold(self, threshold: EntropyThreshold) -> None:
        with self._lock:
            self._thresholds[threshold.category] = threshold

    def get_top_contributors(
        self, top_n: int = 5, since: Optional[datetime] = None
    ) -> List[AttributionResult]:
        with self._lock:
            source_values: Dict[str, List[EntropySample]] = defaultdict(list)
            for sample in self._filter_samples(None, None, None, since):
                source_values[sample.source].append(sample)
            contributions: List[AttributionResult] = []
            total_entropy = self.compute_total_entropy(since)
            for source, samples in source_values.items():
                if not samples:
                    continue
                source_entropy = sum(s.value for s in samples) / len(samples)
                contribution_ratio = source_entropy / total_entropy if total_entropy > 0 else 0.0
                contributions.append(AttributionResult(
                    source=source,
                    category=samples[0].category,
                    contribution_ratio=contribution_ratio,
                    absolute_value=source_entropy,
                    trend_impact=0.0,
                    related_sources=[],
                    root_cause_hypothesis="",
                ))
            contributions.sort(key=lambda x: x.absolute_value, reverse=True)
            return contributions[:top_n]
