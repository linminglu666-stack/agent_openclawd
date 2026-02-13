"""
质量评估器
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import threading


class MetricType(Enum):
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    USER_SATISFACTION = "user_satisfaction"
    COST_EFFICIENCY = "cost_efficiency"
    COMPLETENESS = "completeness"
    RELEVANCE = "relevance"
    COHERENCE = "coherence"


@dataclass
class EvaluationMetric:
    name: str
    metric_type: MetricType
    value: float
    
    threshold: float = 0.0
    weight: float = 1.0
    unit: str = ""
    
    passed: bool = True
    deviation: float = 0.0
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.passed = self.value >= self.threshold
        self.deviation = self.value - self.threshold
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "threshold": self.threshold,
            "weight": self.weight,
            "unit": self.unit,
            "passed": self.passed,
            "deviation": self.deviation,
            "metadata": self.metadata,
        }


@dataclass
class EvaluationResult:
    evaluation_id: str
    component: str
    version: str
    
    metrics: List[EvaluationMetric] = field(default_factory=list)
    
    overall_score: float = 0.0
    passed: bool = True
    
    evaluated_at: datetime = field(default_factory=datetime.now)
    duration_ms: int = 0
    
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "component": self.component,
            "version": self.version,
            "metrics": [m.to_dict() for m in self.metrics],
            "overall_score": self.overall_score,
            "passed": self.passed,
            "evaluated_at": self.evaluated_at.isoformat(),
            "duration_ms": self.duration_ms,
            "context": self.context,
        }
    
    def get_metric(self, name: str) -> Optional[EvaluationMetric]:
        for m in self.metrics:
            if m.name == name:
                return m
        return None
    
    def calculate_overall_score(self) -> float:
        if not self.metrics:
            return 0.0
        
        total_weight = sum(m.weight for m in self.metrics)
        if total_weight == 0:
            return 0.0
        
        weighted_sum = sum(m.value * m.weight for m in self.metrics)
        self.overall_score = weighted_sum / total_weight
        
        self.passed = all(m.passed for m in self.metrics)
        
        return self.overall_score


class QualityEvaluator:
    
    def __init__(self):
        self._evaluators: Dict[str, Callable] = {}
        self._thresholds: Dict[str, float] = {}
        self._results: Dict[str, EvaluationResult] = {}
        self._lock = threading.Lock()
        self._listeners: List[Callable] = []
        
        self._initialize_default_evaluators()
    
    def _initialize_default_evaluators(self):
        self._thresholds.update({
            "accuracy": 0.8,
            "precision": 0.75,
            "recall": 0.75,
            "f1_score": 0.75,
            "latency_p50_ms": 1000,
            "latency_p95_ms": 3000,
            "latency_p99_ms": 5000,
            "error_rate": 0.01,
            "throughput_rps": 100,
            "user_satisfaction": 0.7,
            "completeness": 0.8,
            "relevance": 0.8,
            "coherence": 0.75,
        })
    
    def register_evaluator(
        self,
        metric_name: str,
        evaluator_func: Callable,
        threshold: Optional[float] = None
    ):
        self._evaluators[metric_name] = evaluator_func
        if threshold is not None:
            self._thresholds[metric_name] = threshold
    
    def set_threshold(self, metric_name: str, threshold: float):
        self._thresholds[metric_name] = threshold
    
    def evaluate(
        self,
        component: str,
        version: str,
        test_cases: List[Dict[str, Any]],
        metrics_to_evaluate: Optional[List[str]] = None
    ) -> EvaluationResult:
        import uuid
        import time
        
        start_time = time.time()
        
        result = EvaluationResult(
            evaluation_id=f"eval-{uuid.uuid4().hex[:8]}",
            component=component,
            version=version,
        )
        
        metrics_names = metrics_to_evaluate or list(self._evaluators.keys())
        
        for metric_name in metrics_names:
            evaluator = self._evaluators.get(metric_name)
            if not evaluator:
                continue
            
            try:
                value = evaluator(test_cases)
                
                metric_type = self._get_metric_type(metric_name)
                threshold = self._thresholds.get(metric_name, 0.0)
                
                if metric_name.startswith("latency") or metric_name == "error_rate":
                    passed = value <= threshold
                else:
                    passed = value >= threshold
                
                metric = EvaluationMetric(
                    name=metric_name,
                    metric_type=metric_type,
                    value=value,
                    threshold=threshold,
                    passed=passed,
                )
                
                result.metrics.append(metric)
                
            except Exception as e:
                metric = EvaluationMetric(
                    name=metric_name,
                    metric_type=MetricType.ACCURACY,
                    value=0.0,
                    threshold=self._thresholds.get(metric_name, 0.0),
                    passed=False,
                    metadata={"error": str(e)},
                )
                result.metrics.append(metric)
        
        result.calculate_overall_score()
        result.duration_ms = int((time.time() - start_time) * 1000)
        
        with self._lock:
            self._results[result.evaluation_id] = result
        
        self._notify_listeners("evaluated", result)
        return result
    
    def _get_metric_type(self, metric_name: str) -> MetricType:
        type_mapping = {
            "accuracy": MetricType.ACCURACY,
            "precision": MetricType.PRECISION,
            "recall": MetricType.RECALL,
            "f1_score": MetricType.F1_SCORE,
            "latency": MetricType.LATENCY,
            "throughput": MetricType.THROUGHPUT,
            "error_rate": MetricType.ERROR_RATE,
            "user_satisfaction": MetricType.USER_SATISFACTION,
            "cost_efficiency": MetricType.COST_EFFICIENCY,
            "completeness": MetricType.COMPLETENESS,
            "relevance": MetricType.RELEVANCE,
            "coherence": MetricType.COHERENCE,
        }
        
        for key, metric_type in type_mapping.items():
            if key in metric_name.lower():
                return metric_type
        
        return MetricType.ACCURACY
    
    def get_result(self, evaluation_id: str) -> Optional[EvaluationResult]:
        return self._results.get(evaluation_id)
    
    def get_results_by_component(
        self,
        component: str,
        limit: int = 100
    ) -> List[EvaluationResult]:
        results = [
            r for r in self._results.values()
            if r.component == component
        ]
        results.sort(key=lambda x: x.evaluated_at, reverse=True)
        return results[:limit]
    
    def get_latest_result(self, component: str) -> Optional[EvaluationResult]:
        results = self.get_results_by_component(component, limit=1)
        return results[0] if results else None
    
    def compare_results(
        self,
        evaluation_id_1: str,
        evaluation_id_2: str
    ) -> Dict[str, Any]:
        result1 = self._results.get(evaluation_id_1)
        result2 = self._results.get(evaluation_id_2)
        
        if not result1 or not result2:
            return {"error": "One or both evaluations not found"}
        
        comparison = {
            "evaluation_1": evaluation_id_1,
            "evaluation_2": evaluation_id_2,
            "overall_score_diff": result2.overall_score - result1.overall_score,
            "metrics_diff": {},
        }
        
        metrics1 = {m.name: m for m in result1.metrics}
        metrics2 = {m.name: m for m in result2.metrics}
        
        for name in set(metrics1.keys()) | set(metrics2.keys()):
            m1 = metrics1.get(name)
            m2 = metrics2.get(name)
            
            if m1 and m2:
                comparison["metrics_diff"][name] = {
                    "before": m1.value,
                    "after": m2.value,
                    "change": m2.value - m1.value,
                    "improved": m2.value > m1.value if name not in ["error_rate", "latency"] else m2.value < m1.value,
                }
        
        return comparison
    
    def get_trend(
        self,
        component: str,
        metric_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        results = self.get_results_by_component(component, limit)
        
        trend = []
        for r in reversed(results):
            metric = r.get_metric(metric_name)
            if metric:
                trend.append({
                    "evaluated_at": r.evaluated_at.isoformat(),
                    "version": r.version,
                    "value": metric.value,
                    "passed": metric.passed,
                })
        
        return trend
    
    def get_stats(self) -> Dict[str, Any]:
        results = list(self._results.values())
        
        return {
            "total_evaluations": len(results),
            "passed_evaluations": sum(1 for r in results if r.passed),
            "failed_evaluations": sum(1 for r in results if not r.passed),
            "avg_overall_score": sum(r.overall_score for r in results) / len(results) if results else 0,
            "components_evaluated": len(set(r.component for r in results)),
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
