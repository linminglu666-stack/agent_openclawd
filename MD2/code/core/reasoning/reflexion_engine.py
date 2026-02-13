from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.logger import get_logger


@dataclass
class ReflexionResult:
    iteration: int
    original_answer: str
    reflection: str
    improved_answer: str
    score: float
    should_continue: bool
    trace: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ReflexionConfig:
    max_iterations: int = 3
    improvement_threshold: float = 0.1
    min_score: float = 0.7


class ReflexionEngine:
    def __init__(self, config: Optional[ReflexionConfig] = None):
        self._config = config or ReflexionConfig()
        self._logger = get_logger("reasoning.reflexion")
        self._iteration_count = 0

    async def reflect(
        self,
        problem: str,
        initial_answer: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ReflexionResult:
        self._iteration_count = 0
        ctx = context or {}
        current_answer = initial_answer
        current_score = self._evaluate_answer(initial_answer, problem, ctx)
        trace = []

        trace.append({
            "iteration": 0,
            "answer": initial_answer,
            "score": current_score,
            "timestamp": int(datetime.now(tz=timezone.utc).timestamp()),
        })

        while self._iteration_count < self._config.max_iterations:
            self._iteration_count += 1

            reflection = self._generate_reflection(problem, current_answer, ctx)
            improved = self._improve_answer(problem, current_answer, reflection, ctx)
            new_score = self._evaluate_answer(improved, problem, ctx)

            improvement = new_score - current_score
            should_continue = (
                improvement >= self._config.improvement_threshold
                and new_score < self._config.min_score
                and self._iteration_count < self._config.max_iterations
            )

            trace.append({
                "iteration": self._iteration_count,
                "reflection": reflection,
                "improved_answer": improved,
                "score": new_score,
                "improvement": improvement,
                "timestamp": int(datetime.now(tz=timezone.utc).timestamp()),
            })

            self._logger.debug(
                "Reflexion iteration",
                iteration=self._iteration_count,
                score=new_score,
                improvement=improvement,
            )

            if new_score > current_score:
                current_answer = improved
                current_score = new_score

            if not should_continue:
                break

        return ReflexionResult(
            iteration=self._iteration_count,
            original_answer=initial_answer,
            reflection=trace[-1].get("reflection", "") if len(trace) > 1 else "",
            improved_answer=current_answer,
            score=current_score,
            should_continue=False,
            trace=trace,
        )

    def _generate_reflection(self, problem: str, answer: str, context: Dict[str, Any]) -> str:
        reflections = []

        if len(answer) < 20:
            reflections.append("答案过于简短，需要更详细的解释")

        if "可能" in answer or "也许" in answer or "maybe" in answer.lower():
            reflections.append("答案存在不确定性，需要更明确的结论")

        if not any(c in answer for c in "0123456789") and any(c in problem for c in "0123456789"):
            reflections.append("问题包含数字但答案缺少具体数值")

        if "因为" not in answer and "所以" not in answer and "because" not in answer.lower():
            reflections.append("答案缺少推理过程，建议添加因果解释")

        if not reflections:
            reflections.append("答案基本合理，可以进一步优化表达和完整性")

        return "; ".join(reflections)

    def _improve_answer(self, problem: str, answer: str, reflection: str, context: Dict[str, Any]) -> str:
        improvements = []

        if "过于简短" in reflection:
            improvements.append("详细解释：")

        if "不确定性" in reflection:
            improvements.append("基于分析，我们可以得出更明确的结论：")

        if "缺少具体数值" in reflection:
            improvements.append("经过计算，")

        if "缺少推理过程" in reflection:
            improvements.append("推理过程如下：")

        if improvements:
            prefix = " ".join(improvements)
            return f"{prefix}{answer}"
        else:
            return f"经过进一步思考，{answer}"

    def _evaluate_answer(self, answer: str, problem: str, context: Dict[str, Any]) -> float:
        score = 0.5

        if len(answer) >= 50:
            score += 0.1
        if len(answer) >= 100:
            score += 0.05

        if any(w in answer for w in ["因为", "所以", "因此", "由于", "because", "therefore"]):
            score += 0.1

        if any(w in answer for w in ["首先", "然后", "最后", "first", "then", "finally"]):
            score += 0.1

        if context.get("expected_keywords"):
            for kw in context["expected_keywords"]:
                if kw in answer:
                    score += 0.05

        return min(score, 1.0)

    def reset(self) -> None:
        self._iteration_count = 0
        self._logger.debug("Reflexion engine reset")
