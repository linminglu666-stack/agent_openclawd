from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.logger import get_logger


class ProblemType(Enum):
    FACTUAL_QA = "factual_qa"
    MULTI_STEP_REASONING = "multi_step_reasoning"
    CODE_GENERATION = "code_generation"
    OPEN_ANALYSIS = "open_analysis"
    CREATIVE_WRITING = "creative_writing"
    MATH_PROBLEM = "math_problem"
    PLANNING = "planning"
    UNKNOWN = "unknown"


@dataclass
class StrategyConfig:
    strategies: List[str] = field(default_factory=list)
    priority: int = 0
    min_confidence: float = 0.5


STRATEGY_MAP: Dict[ProblemType, StrategyConfig] = {
    ProblemType.FACTUAL_QA: StrategyConfig(strategies=["cot"], priority=1, min_confidence=0.6),
    ProblemType.MULTI_STEP_REASONING: StrategyConfig(strategies=["cot", "tot", "scratchpad"], priority=2, min_confidence=0.7),
    ProblemType.CODE_GENERATION: StrategyConfig(strategies=["cot", "code_interpreter"], priority=2, min_confidence=0.7),
    ProblemType.OPEN_ANALYSIS: StrategyConfig(strategies=["self_consistency", "reflexion"], priority=2, min_confidence=0.6),
    ProblemType.CREATIVE_WRITING: StrategyConfig(strategies=["tot", "diversity_sampling"], priority=1, min_confidence=0.5),
    ProblemType.MATH_PROBLEM: StrategyConfig(strategies=["cot", "tot", "self_consistency"], priority=3, min_confidence=0.8),
    ProblemType.PLANNING: StrategyConfig(strategies=["tot", "scratchpad"], priority=2, min_confidence=0.7),
    ProblemType.UNKNOWN: StrategyConfig(strategies=["cot"], priority=0, min_confidence=0.5),
}


class StrategyRouter:
    def __init__(self):
        self._logger = get_logger("reasoning.strategy_router")
        self._keywords: Dict[ProblemType, List[str]] = {
            ProblemType.FACTUAL_QA: ["what is", "who is", "when did", "where is", "define", "explain"],
            ProblemType.MULTI_STEP_REASONING: ["step by step", "first then", "sequence", "process", "how to"],
            ProblemType.CODE_GENERATION: ["write code", "implement", "function", "class", "program", "script"],
            ProblemType.OPEN_ANALYSIS: ["analyze", "compare", "evaluate", "pros and cons", "discuss"],
            ProblemType.CREATIVE_WRITING: ["write a story", "create", "imagine", "compose", "design"],
            ProblemType.MATH_PROBLEM: ["calculate", "solve", "equation", "formula", "math", "compute"],
            ProblemType.PLANNING: ["plan", "schedule", "organize", "arrange", "roadmap"],
        }

    def classify(self, query: str) -> ProblemType:
        query_lower = query.lower()
        scores: Dict[ProblemType, int] = {pt: 0 for pt in ProblemType}

        for problem_type, keywords in self._keywords.items():
            for kw in keywords:
                if kw in query_lower:
                    scores[problem_type] += 1

        max_score = max(scores.values())
        if max_score == 0:
            return ProblemType.UNKNOWN

        for pt, score in scores.items():
            if score == max_score:
                self._logger.debug("Classified query", query=query[:50], problem_type=pt.value)
                return pt

        return ProblemType.UNKNOWN

    def select_strategies(self, problem_type: ProblemType, complexity: str = "medium") -> List[str]:
        config = STRATEGY_MAP.get(problem_type, STRATEGY_MAP[ProblemType.UNKNOWN])
        strategies = list(config.strategies)

        if complexity == "high":
            if "reflexion" not in strategies:
                strategies.append("reflexion")
            if "truth_gate" not in strategies:
                strategies.append("truth_gate")
        elif complexity == "low" and len(strategies) > 1:
            strategies = strategies[:1]

        self._logger.info("Selected strategies", problem_type=problem_type.value, strategies=strategies)
        return strategies

    def get_config(self, problem_type: ProblemType) -> StrategyConfig:
        return STRATEGY_MAP.get(problem_type, STRATEGY_MAP[ProblemType.UNKNOWN])

    def estimate_complexity(self, query: str, context: Dict[str, Any]) -> str:
        word_count = len(query.split())
        has_constraints = bool(context.get("constraints"))
        has_dependencies = bool(context.get("dependencies"))

        if word_count > 100 or (has_constraints and has_dependencies):
            return "high"
        elif word_count > 30 or has_constraints or has_dependencies:
            return "medium"
        else:
            return "low"
