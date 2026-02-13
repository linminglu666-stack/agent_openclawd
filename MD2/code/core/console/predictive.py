from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import statistics
import math


class MetricType(Enum):
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    AGENT_UTILIZATION = "agent_utilization"
    QUEUE_DEPTH = "queue_depth"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    TASK_SUCCESS_RATE = "task_success_rate"
    REASONING_QUALITY = "reasoning_quality"
    # Entropy Metrics
    RETRIEVAL_TIME = "retrieval_time"
    INBOX_STALE_COUNT = "inbox_stale_count"
    UNINDEXED_OUTPUTS = "unindexed_outputs"
    DUPLICATE_TOPICS = "duplicate_topics"
    REWORK_EVENTS = "rework_events"


class AnomalyType(Enum):
    SPIKE = "spike"
    DROP = "drop"
    TREND_CHANGE = "trend_change"
    OUTLIER = "outlier"
    THRESHOLD_BREACH = "threshold_breach"


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class MetricPoint:
    timestamp: int
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Prediction:
    prediction_id: str
    metric_type: MetricType
    predicted_value: float
    confidence_interval: Tuple[float, float]
    confidence_level: float
    target_time: int
    model_version: str
    features_used: List[str] = field(default_factory=list)
    created_at: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))


@dataclass(frozen=True)
class Anomaly:
    anomaly_id: str
    anomaly_type: AnomalyType
    metric_type: MetricType
    severity: Severity
    detected_at: int
    value: float
    expected_range: Tuple[float, float]
    description: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionRecommendation:
    recommendation_id: str
    title: str
    description: str
    priority: int
    actions: List[str]
    estimated_impact: str
    risk_level: Severity
    created_at: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))


class PredictionModel(ABC):
    @abstractmethod
    def predict(self, history: List[MetricPoint], horizon: int) -> Prediction:
        pass
    
    @abstractmethod
    def get_model_version(self) -> str:
        pass


class MovingAverageModel(PredictionModel):
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self._version = "ma_v1.0"
    
    def predict(self, history: List[MetricPoint], horizon: int) -> Prediction:
        if not history:
            return Prediction(
                prediction_id=f"pred_{int(datetime.now(tz=timezone.utc).timestamp())}",
                metric_type=MetricType.LATENCY,
                predicted_value=0.0,
                confidence_interval=(0.0, 0.0),
                confidence_level=0.0,
                target_time=horizon,
                model_version=self._version,
            )
        
        values = [p.value for p in history[-self.window_size:]]
        mean = statistics.mean(values)
        
        if len(values) > 1:
            stdev = statistics.stdev(values)
            ci_lower = mean - 1.96 * stdev
            ci_upper = mean + 1.96 * stdev
            confidence = 0.95
        else:
            ci_lower = mean * 0.9
            ci_upper = mean * 1.1
            confidence = 0.5
        
        return Prediction(
            prediction_id=f"pred_{int(datetime.now(tz=timezone.utc).timestamp())}",
            metric_type=MetricType.LATENCY,
            predicted_value=mean,
            confidence_interval=(ci_lower, ci_upper),
            confidence_level=confidence,
            target_time=horizon,
            model_version=self._version,
            features_used=["moving_average"],
        )
    
    def get_model_version(self) -> str:
        return self._version


class ExponentialSmoothingModel(PredictionModel):
    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        self._version = "exp_smooth_v1.0"
    
    def predict(self, history: List[MetricPoint], horizon: int) -> Prediction:
        if not history:
            return Prediction(
                prediction_id=f"pred_{int(datetime.now(tz=timezone.utc).timestamp())}",
                metric_type=MetricType.LATENCY,
                predicted_value=0.0,
                confidence_interval=(0.0, 0.0),
                confidence_level=0.0,
                target_time=horizon,
                model_version=self._version,
            )
        
        values = [p.value for p in history]
        smoothed = values[0]
        for v in values[1:]:
            smoothed = self.alpha * v + (1 - self.alpha) * smoothed
        
        variance = sum((v - smoothed) ** 2 for v in values) / len(values) if len(values) > 1 else 0
        stdev = math.sqrt(variance)
        
        ci_lower = smoothed - 1.96 * stdev
        ci_upper = smoothed + 1.96 * stdev
        
        return Prediction(
            prediction_id=f"pred_{int(datetime.now(tz=timezone.utc).timestamp())}",
            metric_type=MetricType.LATENCY,
            predicted_value=smoothed,
            confidence_interval=(ci_lower, ci_upper),
            confidence_level=0.95,
            target_time=horizon,
            model_version=self._version,
            features_used=["exponential_smoothing"],
        )
    
    def get_model_version(self) -> str:
        return self._version


class AnomalyDetector:
    def __init__(
        self,
        spike_threshold: float = 3.0,
        drop_threshold: float = 0.5,
        trend_window: int = 10,
    ):
        self.spike_threshold = spike_threshold
        self.drop_threshold = drop_threshold
        self.trend_window = trend_window
    
    def detect(self, history: List[MetricPoint], current: MetricPoint) -> Optional[Anomaly]:
        if len(history) < 3:
            return None
        
        values = [p.value for p in history]
        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0
        
        if stdev > 0:
            z_score = abs(current.value - mean) / stdev
            if z_score > self.spike_threshold:
                return Anomaly(
                    anomaly_id=f"anom_{int(datetime.now(tz=timezone.utc).timestamp())}",
                    anomaly_type=AnomalyType.SPIKE if current.value > mean else AnomalyType.DROP,
                    metric_type=MetricType.LATENCY,
                    severity=Severity.HIGH if z_score > 4 else Severity.MEDIUM,
                    detected_at=current.timestamp,
                    value=current.value,
                    expected_range=(mean - 2 * stdev, mean + 2 * stdev),
                    description=f"Value {current.value:.2f} is {z_score:.1f} std from mean {mean:.2f}",
                )
        
        if current.value < mean * self.drop_threshold:
            return Anomaly(
                anomaly_id=f"anom_{int(datetime.now(tz=timezone.utc).timestamp())}",
                anomaly_type=AnomalyType.DROP,
                metric_type=MetricType.LATENCY,
                severity=Severity.MEDIUM,
                detected_at=current.timestamp,
                value=current.value,
                expected_range=(mean * self.drop_threshold, float('inf')),
                description=f"Value dropped below {self.drop_threshold * 100}% of mean",
            )
        
        if len(history) >= self.trend_window:
            recent = [p.value for p in history[-self.trend_window:]]
            older = [p.value for p in history[-2*self.trend_window:-self.trend_window]] if len(history) >= 2 * self.trend_window else []
            
            if older:
                recent_mean = statistics.mean(recent)
                older_mean = statistics.mean(older)
                change_ratio = (recent_mean - older_mean) / older_mean if older_mean != 0 else 0
                
                if abs(change_ratio) > 0.3:
                    return Anomaly(
                        anomaly_id=f"anom_{int(datetime.now(tz=timezone.utc).timestamp())}",
                        anomaly_type=AnomalyType.TREND_CHANGE,
                        metric_type=MetricType.LATENCY,
                        severity=Severity.LOW,
                        detected_at=current.timestamp,
                        value=current.value,
                        expected_range=(older_mean * 0.9, older_mean * 1.1),
                        description=f"Trend changed by {change_ratio * 100:.1f}%",
                    )
        
        return None


class WhatIfSimulator:
    def __init__(self):
        self._scenarios: Dict[str, Dict[str, Any]] = {}
    
    def register_scenario(self, name: str, parameters: Dict[str, Any]) -> None:
        self._scenarios[name] = parameters
    
    def simulate(
        self,
        scenario_name: str,
        baseline: List[MetricPoint],
        duration_steps: int = 10,
    ) -> List[MetricPoint]:
        if scenario_name not in self._scenarios:
            return baseline
        
        params = self._scenarios[scenario_name]
        result = []
        
        for i, point in enumerate(baseline):
            new_value = point.value
            
            if "traffic_increase" in params:
                factor = 1 + params["traffic_increase"] * (i / len(baseline))
                new_value *= factor
            
            if "latency_addition" in params:
                new_value += params["latency_addition"]
            
            if "error_rate_change" in params:
                new_value = max(0, min(1, new_value + params["error_rate_change"]))
            
            result.append(MetricPoint(
                timestamp=point.timestamp,
                value=new_value,
                labels=point.labels,
            ))
        
        return result
    
    def compare_scenarios(
        self,
        baseline: List[MetricPoint],
        scenarios: List[str],
    ) -> Dict[str, List[MetricPoint]]:
        results = {}
        for scenario in scenarios:
            results[scenario] = self.simulate(scenario, baseline)
        return results


class ActionRecommender:
    def __init__(self):
        self._rules: List[Dict[str, Any]] = [
            {
                "condition": lambda a: a.anomaly_type == AnomalyType.SPIKE and a.severity == Severity.HIGH,
                "recommendation": ActionRecommendation(
                    recommendation_id="rec_spike_high",
                    title="High Latency Spike Detected",
                    description="Immediate action required for latency spike",
                    priority=1,
                    actions=[
                        "Scale up agent pool by 50%",
                        "Enable request throttling",
                        "Check for resource contention",
                        "Review recent deployments",
                    ],
                    estimated_impact="Reduce latency by 30-50%",
                    risk_level=Severity.LOW,
                ),
            },
            {
                "condition": lambda a: a.anomaly_type == AnomalyType.DROP and a.metric_type == MetricType.THROUGHPUT,
                "recommendation": ActionRecommendation(
                    recommendation_id="rec_throughput_drop",
                    title="Throughput Drop Detected",
                    description="System throughput has dropped significantly",
                    priority=2,
                    actions=[
                        "Check agent health status",
                        "Review queue depths",
                        "Verify network connectivity",
                        "Check for blocked tasks",
                    ],
                    estimated_impact="Restore throughput to baseline",
                    risk_level=Severity.MEDIUM,
                ),
            },
            {
                "condition": lambda a: a.anomaly_type == AnomalyType.TREND_CHANGE,
                "recommendation": ActionRecommendation(
                    recommendation_id="rec_trend_change",
                    title="Trend Change Detected",
                    description="Metric trend has changed significantly",
                    priority=3,
                    actions=[
                        "Analyze root cause",
                        "Review capacity planning",
                        "Consider proactive scaling",
                        "Update prediction models",
                    ],
                    estimated_impact="Prevent future issues",
                    risk_level=Severity.LOW,
                ),
            },
        ]
    
    def recommend(self, anomaly: Anomaly) -> Optional[ActionRecommendation]:
        for rule in self._rules:
            if rule["condition"](anomaly):
                return rule["recommendation"]
        return None
    
    def add_rule(self, condition, recommendation: ActionRecommendation) -> None:
        self._rules.append({
            "condition": condition,
            "recommendation": recommendation,
        })


class PredictiveConsole:
    def __init__(
        self,
        prediction_model: Optional[PredictionModel] = None,
        anomaly_detector: Optional[AnomalyDetector] = None,
    ):
        self._model = prediction_model or ExponentialSmoothingModel()
        self._detector = anomaly_detector or AnomalyDetector()
        self._simulator = WhatIfSimulator()
        self._recommender = ActionRecommender()
        self._metrics_history: Dict[MetricType, List[MetricPoint]] = {}
        self._predictions: List[Prediction] = []
        self._anomalies: List[Anomaly] = []
    
    def record_metric(self, metric_type: MetricType, point: MetricPoint) -> Optional[Anomaly]:
        if metric_type not in self._metrics_history:
            self._metrics_history[metric_type] = []
        
        history = self._metrics_history[metric_type]
        anomaly = self._detector.detect(history, point)
        
        if anomaly:
            self._anomalies.append(anomaly)
        
        self._metrics_history[metric_type].append(point)
        
        if len(self._metrics_history[metric_type]) > 1000:
            self._metrics_history[metric_type] = self._metrics_history[metric_type][-500:]
        
        return anomaly
    
    def predict(self, metric_type: MetricType, horizon: int = 300) -> Optional[Prediction]:
        history = self._metrics_history.get(metric_type, [])
        if not history:
            return None
        
        prediction = self._model.predict(history, horizon)
        self._predictions.append(prediction)
        return prediction
    
    def get_anomalies(self, since: Optional[int] = None) -> List[Anomaly]:
        if since is None:
            return self._anomalies.copy()
        return [a for a in self._anomalies if a.detected_at >= since]
    
    def get_recommendations(self) -> List[ActionRecommendation]:
        recommendations = []
        for anomaly in self._anomalies[-10:]:
            rec = self._recommender.recommend(anomaly)
            if rec:
                recommendations.append(rec)
        return recommendations
    
    def simulate_scenario(self, scenario_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        self._simulator.register_scenario(scenario_name, parameters)
        
        baseline = self._metrics_history.get(MetricType.LATENCY, [])
        if not baseline:
            return {"error": "No baseline data available"}
        
        simulated = self._simulator.simulate(scenario_name, baseline)
        
        baseline_mean = statistics.mean([p.value for p in baseline]) if baseline else 0
        simulated_mean = statistics.mean([p.value for p in simulated]) if simulated else 0
        
        return {
            "scenario": scenario_name,
            "baseline_mean": baseline_mean,
            "simulated_mean": simulated_mean,
            "change_percent": ((simulated_mean - baseline_mean) / baseline_mean * 100) if baseline_mean else 0,
            "data_points": len(simulated),
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        return {
            "metrics_tracked": list(self._metrics_history.keys()),
            "total_predictions": len(self._predictions),
            "total_anomalies": len(self._anomalies),
            "recent_anomalies": [
                {
                    "type": a.anomaly_type.value,
                    "severity": a.severity.value,
                    "description": a.description,
                }
                for a in self._anomalies[-5:]
            ],
            "recommendations": [
                {
                    "title": r.title,
                    "priority": r.priority,
                    "actions": r.actions,
                }
                for r in self.get_recommendations()
            ],
        }
