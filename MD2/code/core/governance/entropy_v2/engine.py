from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional
import threading

from base_types import (
    utc_now, EntropyCategory, EntropyLevel, EntropySample, EntropyThreshold,
    EntropyAlert, AlertSeverity, SweepAction, SweepPriority, SweepStatus,
    TrendAnalysis, AttributionResult, EntropyReport
)
from calculator import EntropyCalculator
from monitor import EntropyMonitor
from sweeper import EntropySweeper
from attribution import EntropyAttributor
from adaptive_threshold import AdaptiveThresholdManager
from persistence import EntropyPersistence


@dataclass
class EntropyEngineConfig:
    max_samples: int = 10000
    sample_retention_hours: float = 168.0
    max_alerts: int = 1000
    alert_retention_hours: float = 168.0
    trend_window_hours: float = 24.0
    min_trend_samples: int = 10
    max_history: int = 1000
    execution_timeout_seconds: float = 300.0
    adaptation_interval_hours: float = 24.0
    db_path: Optional[str] = None
    auto_persist: bool = True


class EntropyEngine:
    _instance: Optional["EntropyEngine"] = None
    _lock = threading.RLock()

    def __init__(self, config: Optional[EntropyEngineConfig] = None):
        self._config = config or EntropyEngineConfig()
        self._calculator = EntropyCalculator(
            max_samples=self._config.max_samples,
            sample_retention_hours=self._config.sample_retention_hours,
        )
        self._monitor = EntropyMonitor(
            calculator=self._calculator,
            max_alerts=self._config.max_alerts,
            alert_retention_hours=self._config.alert_retention_hours,
            trend_window_hours=self._config.trend_window_hours,
            min_trend_samples=self._config.min_trend_samples,
        )
        self._sweeper = EntropySweeper(
            calculator=self._calculator,
            monitor=self._monitor,
            max_history=self._config.max_history,
            execution_timeout_seconds=self._config.execution_timeout_seconds,
        )
        self._attributor = EntropyAttributor(
            calculator=self._calculator,
        )
        self._adaptive = AdaptiveThresholdManager(
            calculator=self._calculator,
            adaptation_interval_hours=self._config.adaptation_interval_hours,
        )
        self._persistence: Optional[EntropyPersistence] = None
        if self._config.auto_persist:
            self._persistence = EntropyPersistence(
                db_path=self._config.db_path,
            )
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._scheduler_interval = 60.0
        self._scheduler_callbacks: List[Callable[[], None]] = []

    @classmethod
    def get_instance(cls, config: Optional[EntropyEngineConfig] = None) -> "EntropyEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config)
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            if cls._instance:
                cls._instance.stop()
                cls._instance = None

    @property
    def calculator(self) -> EntropyCalculator:
        return self._calculator

    @property
    def monitor(self) -> EntropyMonitor:
        return self._monitor

    @property
    def sweeper(self) -> EntropySweeper:
        return self._sweeper

    @property
    def attributor(self) -> EntropyAttributor:
        return self._attributor

    @property
    def adaptive(self) -> AdaptiveThresholdManager:
        return self._adaptive

    def record(
        self,
        metric_name: str,
        value: float,
        source: str,
        raw_metrics: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Optional[EntropySample]:
        sample = self._calculator.record_sample(
            metric_name=metric_name,
            value=value,
            source=source,
            raw_metrics=raw_metrics,
            tags=tags,
        )
        if sample and self._persistence:
            self._persistence.save_sample(sample)
        return sample

    def record_sample(self, sample: EntropySample) -> None:
        self._calculator.record_raw_sample(sample)
        if self._persistence:
            self._persistence.save_sample(sample)

    def check_alerts(
        self,
        category: Optional[EntropyCategory] = None,
    ) -> List[EntropyAlert]:
        alerts = self._monitor.check_and_alert(category=category)
        if self._persistence:
            for alert in alerts:
                self._persistence.save_alert(alert)
        return alerts

    def get_entropy(
        self,
        category: Optional[EntropyCategory] = None,
        level: Optional[EntropyLevel] = None,
        source: Optional[str] = None,
    ) -> float:
        return self._calculator.compute_entropy(
            category=category,
            level=level,
            source=source,
        )

    def get_health_score(self) -> float:
        return self._calculator.compute_health_score()

    def get_report(
        self,
        include_trends: bool = True,
        include_recommendations: bool = True,
    ) -> EntropyReport:
        report = self._monitor.generate_report(
            include_trends=include_trends,
            include_recommendations=include_recommendations,
        )
        report.pending_sweeps = self._sweeper.get_pending_actions(limit=20)
        report.top_contributors = self._attributor.analyze(top_n=5)
        if self._persistence:
            self._persistence.save_report(report)
        return report

    def plan_sweep(
        self,
        categories: Optional[List[EntropyCategory]] = None,
        auto_only: bool = False,
    ) -> List[SweepAction]:
        return self._sweeper.plan_sweep(
            categories=categories,
            auto_only=auto_only,
        )

    def execute_sweep(
        self,
        actions: Optional[List[SweepAction]] = None,
        max_actions: int = 10,
        dry_run: bool = False,
    ) -> List:
        if actions is None:
            actions = self._sweeper.plan_sweep(auto_only=True)
            actions = self._sweeper.prioritize_actions(actions, max_actions=max_actions)
        results = self._sweeper.execute_batch(actions, dry_run=dry_run)
        if self._persistence:
            for action in actions:
                self._persistence.save_sweep_action(action)
        return results

    def auto_sweep(self, max_actions: int = 5) -> List:
        results = self._sweeper.auto_sweep(max_actions=max_actions)
        return results

    def analyze_trend(
        self,
        category: EntropyCategory,
        source: Optional[str] = None,
    ) -> Optional[TrendAnalysis]:
        return self._monitor.analyze_trend(category=category, source=source)

    def analyze_attribution(
        self,
        top_n: int = 10,
    ) -> List[AttributionResult]:
        return self._attributor.analyze(top_n=top_n)

    def adapt_thresholds(self) -> List:
        return self._adaptive.adapt_all()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
        )
        self._scheduler_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5.0)
            self._scheduler_thread = None
        if self._persistence:
            self._persistence.close()

    def add_scheduler_callback(self, callback: Callable[[], None]) -> None:
        self._scheduler_callbacks.append(callback)

    def remove_scheduler_callback(self, callback: Callable[[], None]) -> None:
        if callback in self._scheduler_callbacks:
            self._scheduler_callbacks.remove(callback)

    def _scheduler_loop(self) -> None:
        import time
        while self._running:
            try:
                self._run_scheduled_tasks()
            except Exception:
                pass
            time.sleep(self._scheduler_interval)

    def _run_scheduled_tasks(self) -> None:
        self.check_alerts()
        for callback in self._scheduler_callbacks:
            try:
                callback()
            except Exception:
                pass

    def load_state(self) -> None:
        if not self._persistence:
            return
        thresholds = self._persistence.load_thresholds()
        for cat, threshold in thresholds.items():
            self._calculator.set_threshold(threshold)
        samples = self._persistence.load_samples(limit=10000)
        for sample in samples:
            self._calculator.record_raw_sample(sample)

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "calculator": {
                "sample_count": len(self._calculator.get_samples(limit=100000)),
            },
            "monitor": {
                "alert_count": len(self._monitor.get_active_alerts(limit=10000)),
            },
            "sweeper": self._sweeper.get_statistics(),
            "attributor": self._attributor.get_statistics(),
            "adaptive": self._adaptive.get_statistics(),
        }
