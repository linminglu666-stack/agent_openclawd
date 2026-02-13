from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Set
import math
import threading
import uuid

from base_types import (
    utc_now, EntropyCategory, EntropyLevel, EntropySample, EntropyThreshold,
    EntropyAlert, AlertSeverity, TrendAnalysis, EntropyReport, AttributionResult
)
from calculator import EntropyCalculator


@dataclass
class AlertRule:
    rule_id: str
    name: str
    category: EntropyCategory
    condition: Callable[[float, EntropyThreshold], bool]
    severity_factory: Callable[[float, EntropyThreshold], AlertSeverity]
    message_template: str
    suggested_actions: List[str]
    cooldown_minutes: float = 5.0
    enabled: bool = True


@dataclass
class AlertState:
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    last_severity: Optional[AlertSeverity] = None


class EntropyMonitor:
    def __init__(
        self,
        calculator: EntropyCalculator,
        max_alerts: int = 1000,
        alert_retention_hours: float = 168.0,
        trend_window_hours: float = 24.0,
        min_trend_samples: int = 10,
    ):
        self._calculator = calculator
        self._max_alerts = max_alerts
        self._alert_retention_hours = alert_retention_hours
        self._trend_window_hours = trend_window_hours
        self._min_trend_samples = min_trend_samples
        self._alerts: List[EntropyAlert] = []
        self._alert_states: Dict[str, AlertState] = {}
        self._rules: Dict[str, AlertRule] = {}
        self._subscribers: List[Callable[[EntropyAlert], None]] = []
        self._lock = threading.RLock()
        self._trend_cache: Dict[str, TrendAnalysis] = {}
        self._trend_cache_time: Dict[str, datetime] = {}
        self._trend_cache_ttl = timedelta(minutes=5)
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        default_rules = [
            AlertRule(
                rule_id="entropy_warning",
                name="Entropy Warning Level",
                category=EntropyCategory.EVOLUTION,
                condition=lambda v, t: v >= t.warning,
                severity_factory=lambda v, t: t.classify(v),
                message_template="Entropy for {category} has reached warning level: {value:.2f}",
                suggested_actions=["Review recent changes", "Schedule entropy sweep"],
                cooldown_minutes=30.0,
            ),
            AlertRule(
                rule_id="entropy_critical",
                name="Entropy Critical Level",
                category=EntropyCategory.EVOLUTION,
                condition=lambda v, t: v >= t.critical,
                severity_factory=lambda v, t: t.classify(v),
                message_template="CRITICAL: Entropy for {category} is {value:.2f}",
                suggested_actions=["Immediate entropy sweep required", "Review root cause"],
                cooldown_minutes=10.0,
            ),
            AlertRule(
                rule_id="rapid_entropy_increase",
                name="Rapid Entropy Increase",
                category=EntropyCategory.EVOLUTION,
                condition=lambda v, t: False,
                severity_factory=lambda v, t: AlertSeverity.WARNING,
                message_template="Rapid entropy increase detected: slope {slope:.4f}/hour",
                suggested_actions=["Investigate recent changes", "Consider rollback"],
                cooldown_minutes=60.0,
            ),
        ]
        for rule in default_rules:
            self._rules[rule.rule_id] = rule

    def add_rule(self, rule: AlertRule) -> None:
        with self._lock:
            self._rules[rule.rule_id] = rule

    def subscribe(self, callback: Callable[[EntropyAlert], None]) -> None:
        with self._lock:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[EntropyAlert], None]) -> None:
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def check_and_alert(
        self,
        category: Optional[EntropyCategory] = None,
        source: Optional[str] = None,
    ) -> List[EntropyAlert]:
        now = utc_now()
        generated_alerts: List[EntropyAlert] = []
        with self._lock:
            categories_to_check = [category] if category else list(EntropyCategory)
            for cat in categories_to_check:
                threshold = self._calculator.get_threshold(cat)
                entropy_value = self._calculator.compute_entropy(category=cat)
                for rule in self._rules.values():
                    if not rule.enabled or rule.category != cat:
                        continue
                    state = self._alert_states.get(rule.rule_id, AlertState())
                    if state.last_triggered:
                        cooldown = timedelta(minutes=rule.cooldown_minutes)
                        if now - state.last_triggered < cooldown:
                            continue
                    if rule.condition(entropy_value, threshold):
                        severity = rule.severity_factory(entropy_value, threshold)
                        alert = self._create_alert(
                            rule, cat, source or "system", entropy_value, threshold, now
                        )
                        self._alerts.append(alert)
                        state.last_triggered = now
                        state.trigger_count += 1
                        state.last_severity = severity
                        self._alert_states[rule.rule_id] = state
                        generated_alerts.append(alert)
                        self._notify_subscribers(alert)
            self._prune_alerts()
        return generated_alerts

    def _create_alert(
        self,
        rule: AlertRule,
        category: EntropyCategory,
        source: str,
        value: float,
        threshold: EntropyThreshold,
        timestamp: datetime,
    ) -> EntropyAlert:
        severity = rule.severity_factory(value, threshold)
        threshold_value = {
            AlertSeverity.INFO: 0.0,
            AlertSeverity.WARNING: threshold.warning,
            AlertSeverity.CRITICAL: threshold.critical,
            AlertSeverity.EMERGENCY: threshold.emergency,
        }.get(severity, threshold.warning)
        return EntropyAlert(
            alert_id=str(uuid.uuid4()),
            timestamp=timestamp,
            severity=severity,
            category=category,
            source=source,
            current_value=value,
            threshold=threshold_value,
            message=rule.message_template.format(
                category=category.value, value=value, source=source
            ),
            suggested_actions=rule.suggested_actions.copy(),
        )

    def _notify_subscribers(self, alert: EntropyAlert) -> None:
        for callback in self._subscribers:
            try:
                callback(alert)
            except Exception:
                pass

    def _prune_alerts(self) -> None:
        if len(self._alerts) <= self._max_alerts:
            return
        cutoff = utc_now() - timedelta(hours=self._alert_retention_hours)
        self._alerts = [a for a in self._alerts if a.timestamp >= cutoff]
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[-self._max_alerts:]

    def acknowledge_alert(
        self, alert_id: str, acknowledged_by: str
    ) -> Optional[EntropyAlert]:
        with self._lock:
            for alert in self._alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    alert.acknowledged_by = acknowledged_by
                    alert.acknowledged_at = utc_now()
                    return alert
        return None

    def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        category: Optional[EntropyCategory] = None,
        limit: int = 100,
    ) -> List[EntropyAlert]:
        with self._lock:
            result = [a for a in self._alerts if not a.acknowledged]
            if severity:
                result = [a for a in result if a.severity == severity]
            if category:
                result = [a for a in result if a.category == category]
            result.sort(key=lambda x: (x.severity.value, -x.timestamp.timestamp()))
            return result[:limit]

    def analyze_trend(
        self,
        category: EntropyCategory,
        source: Optional[str] = None,
        window_hours: Optional[float] = None,
    ) -> Optional[TrendAnalysis]:
        cache_key = f"{category.value}:{source or 'all'}"
        now = utc_now()
        with self._lock:
            if cache_key in self._trend_cache_time:
                if now - self._trend_cache_time[cache_key] < self._trend_cache_ttl:
                    return self._trend_cache.get(cache_key)
        window_hours = window_hours or self._trend_window_hours
        since = now - timedelta(hours=window_hours)
        samples = self._calculator.get_samples(
            category=category, source=source, since=since
        )
        if len(samples) < self._min_trend_samples:
            return None
        values = [(s.timestamp.timestamp(), s.value) for s in samples]
        values.sort(key=lambda x: x[0])
        timestamps = [t for t, _ in values]
        vals = [v for _, v in values]
        n = len(vals)
        mean_val = sum(vals) / n
        variance = sum((v - mean_val) ** 2 for v in vals) / n
        std_dev = math.sqrt(variance)
        min_val = min(vals)
        max_val = max(vals)
        sum_t = sum(timestamps)
        sum_v = sum(vals)
        sum_tt = sum(t * t for t in timestamps)
        sum_tv = sum(t * v for t, v in values)
        denom = n * sum_tt - sum_t * sum_t
        if abs(denom) < 1e-10:
            slope = 0.0
        else:
            slope = (n * sum_tv - sum_t * sum_v) / denom
        slope_per_hour = slope * 3600
        if slope_per_hour > 0.01:
            trend_direction = "increasing"
        elif slope_per_hour < -0.01:
            trend_direction = "decreasing"
        else:
            trend_direction = "stable"
        time_span_hours = (timestamps[-1] - timestamps[0]) / 3600
        prediction_1h = mean_val + slope_per_hour
        prediction_24h = mean_val + slope_per_hour * 24
        confidence = min(1.0, n / 30.0) * (1.0 - std_dev / (mean_val + 0.001))
        analysis = TrendAnalysis(
            category=category,
            source=source or "all",
            samples_count=n,
            time_range_hours=time_span_hours,
            mean=mean_val,
            std_dev=std_dev,
            min_val=min_val,
            max_val=max_val,
            slope=slope_per_hour,
            trend_direction=trend_direction,
            prediction_1h=max(0.0, prediction_1h),
            prediction_24h=max(0.0, prediction_24h),
            confidence=confidence,
        )
        with self._lock:
            self._trend_cache[cache_key] = analysis
            self._trend_cache_time[cache_key] = now
        return analysis

    def detect_rapid_changes(
        self,
        threshold_slope: float = 0.05,
        window_hours: float = 1.0,
    ) -> List[TrendAnalysis]:
        rapid_changes: List[TrendAnalysis] = []
        for category in EntropyCategory:
            trend = self.analyze_trend(category, window_hours=window_hours)
            if trend and abs(trend.slope) > threshold_slope:
                rapid_changes.append(trend)
        return rapid_changes

    def generate_report(
        self,
        include_trends: bool = True,
        include_recommendations: bool = True,
    ) -> EntropyReport:
        now = utc_now()
        total_entropy = self._calculator.compute_total_entropy()
        by_category = self._calculator.compute_by_category()
        by_level = self._calculator.compute_by_level()
        top_contributors = self._calculator.get_top_contributors()
        active_alerts = self.get_active_alerts(limit=50)
        trends: List[TrendAnalysis] = []
        if include_trends:
            for category in EntropyCategory:
                trend = self.analyze_trend(category)
                if trend:
                    trends.append(trend)
        recommendations: List[str] = []
        if include_recommendations:
            recommendations = self._generate_recommendations(
                total_entropy, by_category, active_alerts, trends
            )
        return EntropyReport(
            timestamp=now,
            total_entropy=total_entropy,
            by_category=by_category,
            by_level=by_level,
            top_contributors=top_contributors,
            active_alerts=active_alerts,
            pending_sweeps=[],
            trends=trends,
            health_score=self._calculator.compute_health_score(),
            recommendations=recommendations,
        )

    def _generate_recommendations(
        self,
        total_entropy: float,
        by_category: Dict[EntropyCategory, float],
        alerts: List[EntropyAlert],
        trends: List[TrendAnalysis],
    ) -> List[str]:
        recommendations: List[str] = []
        critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        if critical_alerts:
            recommendations.append("URGENT: Address critical alerts immediately")
        for category, value in by_category.items():
            threshold = self._calculator.get_threshold(category)
            if value >= threshold.critical:
                recommendations.append(
                    f"Critical entropy in {category.value}: Consider immediate sweep"
                )
            elif value >= threshold.warning:
                recommendations.append(
                    f"High entropy in {category.value}: Schedule cleanup"
                )
        for trend in trends:
            if trend.trend_direction == "increasing" and trend.slope > 0.03:
                recommendations.append(
                    f"Rising entropy trend in {trend.category.value}: Investigate root cause"
                )
        if total_entropy > 0.7:
            recommendations.append("System-wide entropy is high: Consider comprehensive review")
        elif total_entropy > 0.5:
            recommendations.append("Moderate system entropy: Monitor closely")
        return recommendations
