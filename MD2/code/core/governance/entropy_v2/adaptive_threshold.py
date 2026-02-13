from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import math
import threading

from base_types import (
    utc_now, EntropyCategory, EntropyThreshold, AdaptiveThreshold, EntropySample
)


@dataclass
class ThresholdAdjustment:
    category: EntropyCategory
    old_warning: float
    old_critical: float
    old_emergency: float
    new_warning: float
    new_critical: float
    new_emergency: float
    reason: str
    timestamp: datetime = field(default_factory=utc_now)
    confidence: float = 0.0


class AdaptiveThresholdManager:
    def __init__(
        self,
        calculator: "EntropyCalculator",
        adaptation_interval_hours: float = 24.0,
        min_samples: int = 50,
        max_adjustment_factor: float = 0.3,
        stability_window: int = 10,
    ):
        self._calculator = calculator
        self._adaptation_interval = timedelta(hours=adaptation_interval_hours)
        self._min_samples = min_samples
        self._max_adjustment_factor = max_adjustment_factor
        self._stability_window = stability_window
        self._adaptive_thresholds: Dict[EntropyCategory, AdaptiveThreshold] = {}
        self._adjustment_history: List[ThresholdAdjustment] = []
        self._baseline_history: Dict[EntropyCategory, deque] = {}
        self._last_adaptation: Dict[EntropyCategory, datetime] = {}
        self._lock = threading.RLock()
        self._initialize_adaptive_thresholds()

    def _initialize_adaptive_thresholds(self) -> None:
        base_thresholds = {
            EntropyCategory.INPUT: (0.3, 0.6, 0.8),
            EntropyCategory.EVOLUTION: (0.4, 0.7, 0.9),
            EntropyCategory.OBSERVABILITY: (0.35, 0.65, 0.85),
            EntropyCategory.STRUCTURE: (0.25, 0.5, 0.75),
            EntropyCategory.BEHAVIOR: (0.3, 0.6, 0.8),
            EntropyCategory.DATA: (0.35, 0.65, 0.85),
        }
        for category, (warning, critical, emergency) in base_thresholds.items():
            self._adaptive_thresholds[category] = AdaptiveThreshold(
                category=category,
                base_warning=warning,
                base_critical=critical,
                base_emergency=emergency,
            )
            self._baseline_history[category] = deque(maxlen=1000)
            self._last_adaptation[category] = utc_now() - timedelta(days=1)

    def record_baseline(self, category: EntropyCategory, value: float) -> None:
        with self._lock:
            self._baseline_history[category].append({
                "timestamp": utc_now(),
                "value": value,
            })

    def should_adapt(self, category: EntropyCategory) -> bool:
        with self._lock:
            last = self._last_adaptation.get(category)
            if not last:
                return True
            if utc_now() - last < self._adaptation_interval:
                return False
            history = self._baseline_history.get(category, deque())
            return len(history) >= self._min_samples

    def adapt_threshold(self, category: EntropyCategory) -> Optional[ThresholdAdjustment]:
        with self._lock:
            if not self.should_adapt(category):
                return None
            history = list(self._baseline_history.get(category, deque()))
            if len(history) < self._min_samples:
                return None
            values = [h["value"] for h in history]
            mean_val = sum(values) / len(values)
            variance = sum((v - mean_val) ** 2 for v in values) / len(values)
            std_dev = math.sqrt(variance)
            adaptive = self._adaptive_thresholds[category]
            old_threshold = self._calculator.get_threshold(category)
            new_warning = self._compute_adaptive_threshold(
                adaptive.base_warning, mean_val, std_dev, adaptive.learning_rate
            )
            new_critical = self._compute_adaptive_threshold(
                adaptive.base_critical, mean_val, std_dev, adaptive.learning_rate
            )
            new_emergency = self._compute_adaptive_threshold(
                adaptive.base_emergency, mean_val, std_dev, adaptive.learning_rate
            )
            max_change = self._max_adjustment_factor
            new_warning = self._clamp_change(old_threshold.warning, new_warning, max_change)
            new_critical = self._clamp_change(old_threshold.critical, new_critical, max_change)
            new_emergency = self._clamp_change(old_threshold.emergency, new_emergency, max_change)
            new_warning = min(new_warning, new_critical * 0.9)
            new_critical = min(new_critical, new_emergency * 0.95)
            new_threshold = EntropyThreshold(
                category=category,
                warning=new_warning,
                critical=new_critical,
                emergency=new_emergency,
                weight=old_threshold.weight,
            )
            self._calculator.set_threshold(new_threshold)
            adjustment = ThresholdAdjustment(
                category=category,
                old_warning=old_threshold.warning,
                old_critical=old_threshold.critical,
                old_emergency=old_threshold.emergency,
                new_warning=new_warning,
                new_critical=new_critical,
                new_emergency=new_emergency,
                reason=self._generate_reason(mean_val, std_dev),
                confidence=self._compute_confidence(len(values), std_dev, mean_val),
            )
            self._adjustment_history.append(adjustment)
            self._last_adaptation[category] = utc_now()
            return adjustment

    def _compute_adaptive_threshold(
        self,
        base: float,
        mean: float,
        std_dev: float,
        learning_rate: float,
    ) -> float:
        if mean < base:
            adjustment = (base - mean) * learning_rate
            return max(0.1, base - adjustment)
        elif mean > base:
            adjustment = (mean - base) * learning_rate * 0.5
            return min(1.0, base + adjustment + std_dev * 0.1)
        return base

    def _clamp_change(
        self,
        old_value: float,
        new_value: float,
        max_change: float,
    ) -> float:
        change = new_value - old_value
        max_absolute_change = old_value * max_change
        if abs(change) > max_absolute_change:
            change = max_absolute_change if change > 0 else -max_absolute_change
        return old_value + change

    def _generate_reason(self, mean: float, std_dev: float) -> str:
        if std_dev < 0.05:
            return f"Stable baseline (mean={mean:.3f}, low variance)"
        elif std_dev < 0.15:
            return f"Moderate variance (mean={mean:.3f}, std={std_dev:.3f})"
        else:
            return f"High variance detected (mean={mean:.3f}, std={std_dev:.3f})"

    def _compute_confidence(
        self,
        sample_count: int,
        std_dev: float,
        mean: float,
    ) -> float:
        count_factor = min(1.0, sample_count / 100.0)
        stability_factor = 1.0 - min(1.0, std_dev / (mean + 0.01))
        return count_factor * stability_factor * 0.8 + 0.2

    def adapt_all(self) -> List[ThresholdAdjustment]:
        adjustments: List[ThresholdAdjustment] = []
        for category in EntropyCategory:
            adjustment = self.adapt_threshold(category)
            if adjustment:
                adjustments.append(adjustment)
        return adjustments

    def get_current_threshold(self, category: EntropyCategory) -> EntropyThreshold:
        return self._calculator.get_threshold(category)

    def get_adjustment_history(
        self,
        category: Optional[EntropyCategory] = None,
        limit: int = 100,
    ) -> List[ThresholdAdjustment]:
        with self._lock:
            history = self._adjustment_history.copy()
        if category:
            history = [a for a in history if a.category == category]
        return history[-limit:]

    def reset_to_baseline(self, category: EntropyCategory) -> EntropyThreshold:
        adaptive = self._adaptive_thresholds[category]
        threshold = EntropyThreshold(
            category=category,
            warning=adaptive.base_warning,
            critical=adaptive.base_critical,
            emergency=adaptive.base_emergency,
        )
        self._calculator.set_threshold(threshold)
        return threshold

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            stats: Dict[str, Any] = {
                "categories": {},
                "total_adjustments": len(self._adjustment_history),
            }
            for category in EntropyCategory:
                history = list(self._baseline_history.get(category, deque()))
                threshold = self._calculator.get_threshold(category)
                adaptive = self._adaptive_thresholds[category]
                stats["categories"][category.value] = {
                    "current_warning": threshold.warning,
                    "current_critical": threshold.critical,
                    "current_emergency": threshold.emergency,
                    "baseline_warning": adaptive.base_warning,
                    "baseline_critical": adaptive.base_critical,
                    "baseline_emergency": adaptive.base_emergency,
                    "sample_count": len(history),
                    "last_adaptation": self._last_adaptation.get(category, None).isoformat() if self._last_adaptation.get(category, None) else None,
                }
        return stats
