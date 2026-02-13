from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RouteCandidate:
    name: str
    score: float
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RouteDecision:
    target: str
    confidence: float
    reasoning: str
    alternatives: List[RouteCandidate] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "alternatives": [
                {"name": a.name, "score": a.score, "reason": a.reason, "metadata": a.metadata} for a in self.alternatives
            ],
        }


class ModelRouter:
    def __init__(self):
        self._rules: List[Dict[str, Any]] = []

    def add_rule(self, rule: Dict[str, Any]) -> bool:
        self._rules.append(rule)
        return True

    def decide(self, task: Dict[str, Any]) -> RouteDecision:
        task_type = str(task.get("task_type", "unknown"))
        text = str(task.get("prompt") or task.get("task_data", {}).get("prompt") or "")

        candidates: List[RouteCandidate] = []
        if task_type in {"memory_query", "memory"}:
            candidates.append(RouteCandidate(name="memory_hub", score=0.9, reason="task_type_memory"))
        if task_type in {"reasoning", "analysis"} or len(text) > 200:
            candidates.append(RouteCandidate(name="reasoning", score=0.85, reason="complex_or_reasoning"))
        if task_type in {"agent_task", "tool"}:
            candidates.append(RouteCandidate(name="agent_pool", score=0.8, reason="agent_task"))

        if not candidates:
            candidates.append(RouteCandidate(name="kernel", score=0.6, reason="default"))

        candidates.sort(key=lambda c: c.score, reverse=True)
        best = candidates[0]
        return RouteDecision(target=best.name, confidence=best.score, reasoning=best.reason, alternatives=candidates[1:4])

