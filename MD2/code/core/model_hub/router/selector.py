"""
智能模型选择器
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..model_metadata import ModelMetadata, HealthStatus
from ..registry import ModelRegistry
from .complexity import ComplexityEstimator, ComplexityScore
from .scoring import ModelScorer, ScoringContext, ModelScore


@dataclass
class RoutingRequest:
    request_id: str = ""
    prompt: str = ""
    
    task_type: str = "general"
    complexity: Optional[float] = None
    priority: int = 5
    
    max_latency_ms: Optional[int] = None
    max_cost: Optional[float] = None
    required_capabilities: List[str] = field(default_factory=list)
    
    prefer_quality: bool = True
    prefer_provider: Optional[str] = None
    
    session_id: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.request_id:
            self.request_id = f"req-{uuid.uuid4().hex[:8]}"


@dataclass
class RoutingDecision:
    request_id: str
    selected_model: Optional[ModelMetadata]
    
    reason: str
    confidence: float
    
    estimated_latency_ms: int
    estimated_cost: float
    estimated_tokens: int
    
    alternatives: List[ModelMetadata] = field(default_factory=list)
    scores: List[Dict[str, Any]] = field(default_factory=list)
    
    complexity: Optional[ComplexityScore] = None
    decision_time_ms: int = 0
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "selected_model": self.selected_model.to_dict() if self.selected_model else None,
            "reason": self.reason,
            "confidence": self.confidence,
            "estimated_latency_ms": self.estimated_latency_ms,
            "estimated_cost": self.estimated_cost,
            "estimated_tokens": self.estimated_tokens,
            "alternatives": [m.to_dict() for m in self.alternatives],
            "scores": self.scores,
            "complexity": self.complexity.to_dict() if self.complexity else None,
            "decision_time_ms": self.decision_time_ms,
            "created_at": self.created_at.isoformat(),
        }


class ModelSelector:
    
    def __init__(self, registry: Optional[ModelRegistry] = None):
        self.registry = registry or ModelRegistry()
        self.complexity_estimator = ComplexityEstimator()
        self.scorer = ModelScorer()
        
        self._session_model_map: Dict[str, str] = {}
        self._decision_history: List[RoutingDecision] = []
    
    def select(self, request: RoutingRequest) -> RoutingDecision:
        start_time = time.time()
        
        complexity = self._estimate_complexity(request)
        
        candidates = self._get_candidates(request)
        
        if not candidates:
            return RoutingDecision(
                request_id=request.request_id,
                selected_model=None,
                reason="no_available_models",
                confidence=0.0,
                estimated_latency_ms=0,
                estimated_cost=0,
                estimated_tokens=0,
                complexity=complexity,
            )
        
        context = self._build_context(request, complexity)
        
        ranked = self.scorer.rank_models(candidates, context)
        
        if not ranked:
            return RoutingDecision(
                request_id=request.request_id,
                selected_model=None,
                reason="scoring_failed",
                confidence=0.0,
                estimated_latency_ms=0,
                estimated_cost=0,
                estimated_tokens=0,
                complexity=complexity,
            )
        
        best = ranked[0]
        selected_model = self.registry.get(best.model_id)
        
        alternatives = []
        for score in ranked[1:4]:
            model = self.registry.get(score.model_id)
            if model:
                alternatives.append(model)
        
        if request.session_id and selected_model:
            self._session_model_map[request.session_id] = selected_model.model_id
        
        decision_time_ms = int((time.time() - start_time) * 1000)
        
        estimated_tokens = self._estimate_tokens(request.prompt)
        
        decision = RoutingDecision(
            request_id=request.request_id,
            selected_model=selected_model,
            reason=self._build_reason(best, complexity),
            confidence=best.total_score,
            estimated_latency_ms=selected_model.performance.avg_latency_ms if selected_model else 0,
            estimated_cost=selected_model.pricing.estimate_cost(estimated_tokens, estimated_tokens // 2) if selected_model else 0,
            estimated_tokens=estimated_tokens,
            alternatives=alternatives,
            scores=[s.to_dict() for s in ranked[:5]],
            complexity=complexity,
            decision_time_ms=decision_time_ms,
        )
        
        self._decision_history.append(decision)
        if len(self._decision_history) > 1000:
            self._decision_history = self._decision_history[-500:]
        
        return decision
    
    def select_fast(self, prompt: str, task_type: str = "general") -> Optional[ModelMetadata]:
        request = RoutingRequest(
            prompt=prompt,
            task_type=task_type,
        )
        decision = self.select(request)
        return decision.selected_model
    
    def explain(self, request_id: str) -> Optional[Dict[str, Any]]:
        for decision in reversed(self._decision_history):
            if decision.request_id == request_id:
                return decision.to_dict()
        return None
    
    def set_strategy(self, strategy: str):
        if strategy == "quality_first":
            self.scorer.set_quality_first()
        elif strategy == "cost_first":
            self.scorer.set_cost_first()
        elif strategy == "latency_first":
            self.scorer.set_latency_first()
    
    def clear_session(self, session_id: str):
        if session_id in self._session_model_map:
            del self._session_model_map[session_id]
    
    def _estimate_complexity(self, request: RoutingRequest) -> ComplexityScore:
        if request.complexity is not None:
            return ComplexityScore(
                overall=request.complexity,
                confidence=0.9,
            )
        
        return self.complexity_estimator.estimate(
            request.prompt,
            request.conversation_history
        )
    
    def _get_candidates(self, request: RoutingRequest) -> List[ModelMetadata]:
        all_models = self.registry.get_available_models()
        
        candidates = []
        for model in all_models:
            if not self._meets_constraints(model, request):
                continue
            if not self._meets_capabilities(model, request):
                continue
            candidates.append(model)
        
        return candidates
    
    def _meets_constraints(self, model: ModelMetadata, request: RoutingRequest) -> bool:
        if request.max_latency_ms:
            if model.performance.p95_latency_ms > request.max_latency_ms:
                return False
        
        if request.max_cost:
            estimated_tokens = len(request.prompt) // 4 + 500
            estimated_cost = model.pricing.estimate_cost(estimated_tokens, estimated_tokens // 2)
            if estimated_cost > request.max_cost:
                return False
        
        if model.health.status == HealthStatus.UNHEALTHY:
            return False
        
        return True
    
    def _meets_capabilities(self, model: ModelMetadata, request: RoutingRequest) -> bool:
        for cap in request.required_capabilities:
            if not model.capabilities.supports_capability(cap):
                return False
        return True
    
    def _build_context(self, request: RoutingRequest, complexity: ComplexityScore) -> ScoringContext:
        session_model = None
        if request.session_id:
            session_model = self._session_model_map.get(request.session_id)
        
        return ScoringContext(
            prompt=request.prompt,
            task_type=request.task_type,
            complexity=complexity,
            max_latency_ms=request.max_latency_ms,
            max_cost=request.max_cost,
            required_capabilities=request.required_capabilities,
            prefer_quality=request.prefer_quality,
            prefer_provider=request.prefer_provider,
            session_model=session_model,
        )
    
    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4 + 100
    
    def _build_reason(self, score: ModelScore, complexity: ComplexityScore) -> str:
        reasons = []
        
        if score.quality_score > 0.8:
            reasons.append("high_quality_match")
        elif score.quality_score > 0.6:
            reasons.append("good_quality_match")
        
        if score.task_affinity > 0.85:
            reasons.append(f"strong_{complexity.level}_task_affinity")
        
        if score.cost_score > 0.9:
            reasons.append("cost_effective")
        
        if score.latency_score > 0.8:
            reasons.append("low_latency")
        
        if not reasons:
            reasons.append("best_available_option")
        
        return "; ".join(reasons)
