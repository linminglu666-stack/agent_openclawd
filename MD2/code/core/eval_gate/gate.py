from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocols.interfaces import IEvalGate, IModule
from utils.logger import get_logger
from .truth_gate import TruthGate, TruthGateConfig


@dataclass
class EvalGateConfig:
    min_score: float = 0.7
    require_truth_gate: bool = True
    default_decision_on_error: str = "reject"


class EvalGateModule(IEvalGate, IModule):
    def __init__(
        self,
        config: Optional[EvalGateConfig] = None,
        truth_gate: Optional[TruthGate] = None,
        truth_gate_config: Optional[TruthGateConfig] = None,
    ):
        self._config = config or EvalGateConfig()
        self._truth_gate = truth_gate or TruthGate(truth_gate_config)
        self._initialized = False
        self._logger = get_logger("eval.gate")

    @property
    def name(self) -> str:
        return "eval_gate"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self, config: Dict[str, Any]) -> bool:
        self._initialized = True
        return True

    async def shutdown(self) -> bool:
        self._initialized = False
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {"component": self.name, "initialized": self._initialized}

    async def execute(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if command != "evaluate":
            return {"error": "unknown_command", "command": command}

        task = args.get("task", {}) or {}
        result = args.get("result", {}) or args.get("task_data", {}) or {}
        context = args.get("context", {}) or {}
        return await self.evaluate(task=task, result=result, context=context)

    async def evaluate(self, task: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        task_id = task.get("task_id") or context.get("task_id")
        trace_id = context.get("trace_id")

        try:
            base_score = float(result.get("confidence", result.get("score", 0.0)) or 0.0)
            reasons: List[str] = []

            truth = None
            if self._config.require_truth_gate:
                claim = {"text": result.get("conclusion") or result.get("answer") or result.get("output") or ""}
                evidence = result.get("evidence", []) or context.get("evidence", []) or []
                truth = await self._truth_gate.check(claim=claim, evidence=evidence, context=context)
                if not truth.get("ok", False):
                    reasons.extend(truth.get("reasons", []) or ["truth_gate_failed"])

            score = base_score
            if truth is not None and truth.get("score") is not None:
                score = min(score, float(truth["score"]))

            decision = "accept" if score >= self._config.min_score and not reasons else "reject"

            return {
                "task_id": task_id,
                "decision": decision,
                "score": score,
                "reasons": reasons,
                "truth": truth,
            }

        except Exception as e:
            self._logger.error("EvalGate evaluate error", trace_id=trace_id, task_id=task_id, error=str(e))
            return {
                "task_id": task_id,
                "decision": self._config.default_decision_on_error,
                "score": 0.0,
                "reasons": ["eval_gate_error"],
                "error": str(e),
            }

