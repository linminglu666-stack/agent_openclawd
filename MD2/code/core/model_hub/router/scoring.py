"""
模型评分算法
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..model_metadata import ModelMetadata, HealthStatus
from .complexity import ComplexityScore


@dataclass
class ScoringContext:
    prompt: str
    task_type: str
    complexity: ComplexityScore
    
    max_latency_ms: Optional[int] = None
    max_cost: Optional[float] = None
    required_capabilities: List[str] = field(default_factory=list)
    
    prefer_quality: bool = True
    prefer_provider: Optional[str] = None
    
    current_loads: Dict[str, float] = field(default_factory=dict)
    
    session_model: Optional[str] = None


@dataclass
class ModelScore:
    model_id: str
    total_score: float
    
    quality_score: float
    cost_score: float
    latency_score: float
    load_score: float
    task_affinity: float
    
    breakdown: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "total_score": self.total_score,
            "quality_score": self.quality_score,
            "cost_score": self.cost_score,
            "latency_score": self.latency_score,
            "load_score": self.load_score,
            "task_affinity": self.task_affinity,
            "breakdown": self.breakdown,
        }


class ModelScorer:
    
    DEFAULT_WEIGHTS = {
        "quality": 0.35,
        "cost": 0.20,
        "latency": 0.20,
        "load": 0.10,
        "task_affinity": 0.15,
    }
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._normalize_weights()
    
    def _normalize_weights(self):
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}
    
    def set_weights(self, weights: Dict[str, float]):
        self.weights = weights.copy()
        self._normalize_weights()
    
    def set_quality_first(self):
        self.weights = {
            "quality": 0.50,
            "cost": 0.10,
            "latency": 0.15,
            "load": 0.10,
            "task_affinity": 0.15,
        }
    
    def set_cost_first(self):
        self.weights = {
            "quality": 0.20,
            "cost": 0.45,
            "latency": 0.15,
            "load": 0.10,
            "task_affinity": 0.10,
        }
    
    def set_latency_first(self):
        self.weights = {
            "quality": 0.25,
            "cost": 0.15,
            "latency": 0.40,
            "load": 0.10,
            "task_affinity": 0.10,
        }
    
    def score(self, model: ModelMetadata, context: ScoringContext) -> ModelScore:
        quality_score = self._calc_quality_score(model, context)
        cost_score = self._calc_cost_score(model, context)
        latency_score = self._calc_latency_score(model, context)
        load_score = self._calc_load_score(model, context)
        task_affinity = self._calc_task_affinity(model, context)
        
        total = (
            quality_score * self.weights["quality"] +
            cost_score * self.weights["cost"] +
            latency_score * self.weights["latency"] +
            load_score * self.weights["load"] +
            task_affinity * self.weights["task_affinity"]
        )
        
        if context.prefer_provider and model.provider == context.prefer_provider:
            total = min(total * 1.1, 1.0)
        
        if context.session_model and model.model_id == context.session_model:
            total = min(total * 1.15, 1.0)
        
        return ModelScore(
            model_id=model.model_id,
            total_score=total,
            quality_score=quality_score,
            cost_score=cost_score,
            latency_score=latency_score,
            load_score=load_score,
            task_affinity=task_affinity,
            breakdown={
                "quality": quality_score * self.weights["quality"],
                "cost": cost_score * self.weights["cost"],
                "latency": latency_score * self.weights["latency"],
                "load": load_score * self.weights["load"],
                "task_affinity": task_affinity * self.weights["task_affinity"],
            },
        )
    
    def _calc_quality_score(self, model: ModelMetadata, context: ScoringContext) -> float:
        caps = model.capabilities
        
        task_score = caps.get_task_score(context.task_type)
        
        complexity_factor = context.complexity.overall
        
        if complexity_factor > 0.7:
            quality_base = (caps.reasoning_score + caps.coding_score) / 2
        elif complexity_factor > 0.4:
            quality_base = (caps.reasoning_score + caps.analysis_score) / 2
        else:
            quality_base = 0.8
        
        final_score = task_score * 0.6 + quality_base * 0.4
        
        if model.health.status == HealthStatus.DEGRADED:
            final_score *= 0.85
        
        return min(final_score, 1.0)
    
    def _calc_cost_score(self, model: ModelMetadata, context: ScoringContext) -> float:
        pricing = model.pricing
        
        if pricing.input_price_per_1k == 0 and pricing.output_price_per_1k == 0:
            return 1.0
        
        estimated_tokens = len(context.prompt) // 4 + 500
        estimated_cost = pricing.estimate_cost(estimated_tokens, 500)
        
        if context.max_cost and estimated_cost > context.max_cost:
            return 0.0
        
        max_reasonable_cost = 0.10
        min_cost = 0.0
        
        if estimated_cost >= max_reasonable_cost:
            return 0.1
        
        cost_score = 1.0 - (estimated_cost - min_cost) / (max_reasonable_cost - min_cost)
        
        return max(cost_score, 0.1)
    
    def _calc_latency_score(self, model: ModelMetadata, context: ScoringContext) -> float:
        perf = model.performance
        
        if context.max_latency_ms and perf.p95_latency_ms > context.max_latency_ms:
            return 0.0
        
        max_latency = 10000
        min_latency = 100
        
        avg_latency = perf.avg_latency_ms
        
        if avg_latency <= min_latency:
            return 1.0
        elif avg_latency >= max_latency:
            return 0.1
        
        latency_score = 1.0 - (avg_latency - min_latency) / (max_latency - min_latency)
        
        return max(latency_score, 0.1)
    
    def _calc_load_score(self, model: ModelMetadata, context: ScoringContext) -> float:
        current_load = context.current_loads.get(model.model_id, 0.0)
        
        if current_load >= 1.0:
            return 0.0
        elif current_load >= 0.9:
            return 0.2
        elif current_load >= 0.7:
            return 0.5
        elif current_load >= 0.5:
            return 0.7
        else:
            return 1.0 - current_load * 0.5
    
    def _calc_task_affinity(self, model: ModelMetadata, context: ScoringContext) -> float:
        caps = model.capabilities
        
        task_scores = {
            "coding": caps.coding_score,
            "reasoning": caps.reasoning_score,
            "creative": caps.creative_score,
            "analysis": caps.analysis_score,
            "general": 0.75,
            "math": caps.reasoning_score,
        }
        
        base_score = task_scores.get(context.task_type, 0.7)
        
        complexity = context.complexity.overall
        
        if complexity > 0.7:
            if base_score < 0.85:
                base_score *= 0.8
        
        return min(base_score, 1.0)
    
    def rank_models(
        self,
        models: List[ModelMetadata],
        context: ScoringContext
    ) -> List[ModelScore]:
        scores = [self.score(m, context) for m in models]
        scores.sort(key=lambda s: s.total_score, reverse=True)
        return scores
