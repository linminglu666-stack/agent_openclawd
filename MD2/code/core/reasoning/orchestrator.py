from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from protocols.interfaces import IModule
from utils.logger import get_logger

from .strategy_router import StrategyRouter, ProblemType
from .cot_injector import CoTInjector, CoTTemplate, CoTResult
from .tot_engine import TreeOfThoughtEngine, ToTResult
from .reflexion_engine import ReflexionEngine, ReflexionResult, ReflexionConfig
from .self_consistency import SelfConsistencySampler, ConsensusResult, SamplerConfig
from .scratchpad import ScratchpadManager, ScratchpadSnapshot


@dataclass
class ReasoningConfig:
    enable_cot: bool = True
    enable_tot: bool = True
    enable_reflexion: bool = True
    enable_self_consistency: bool = True
    default_strategy: str = "cot"
    max_iterations: int = 3
    min_confidence: float = 0.6


@dataclass
class ReasoningResult:
    query: str
    problem_type: ProblemType
    strategies_used: List[str]
    answer: str
    confidence: float
    reasoning_trace: List[str]
    intermediate_results: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None
    latency_ms: int = 0


class ReasoningOrchestrator(IModule):
    def __init__(self, config: Optional[ReasoningConfig] = None):
        self._config = config or ReasoningConfig()
        self._strategy_router = StrategyRouter()
        self._cot_injector = CoTInjector()
        self._tot_engine = TreeOfThoughtEngine()
        self._reflexion_engine = ReflexionEngine(ReflexionConfig(max_iterations=self._config.max_iterations))
        self._self_consistency = SelfConsistencySampler(SamplerConfig(num_samples=5))
        self._scratchpad = ScratchpadManager()
        self._initialized = False
        self._logger = get_logger("reasoning.orchestrator")

    @property
    def name(self) -> str:
        return "reasoning_orchestrator"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self, config: Dict[str, Any]) -> bool:
        if config.get("enable_cot") is not None:
            self._config.enable_cot = config["enable_cot"]
        if config.get("enable_tot") is not None:
            self._config.enable_tot = config["enable_tot"]
        if config.get("enable_reflexion") is not None:
            self._config.enable_reflexion = config["enable_reflexion"]
        if config.get("enable_self_consistency") is not None:
            self._config.enable_self_consistency = config["enable_self_consistency"]

        self._initialized = True
        self._logger.info("Reasoning orchestrator initialized", config=self._config.__dict__)
        return True

    async def shutdown(self) -> bool:
        self._initialized = False
        self._logger.info("Reasoning orchestrator shutdown")
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {
            "component": self.name,
            "initialized": self._initialized,
            "config": self._config.__dict__,
            "scratchpad_stats": self._scratchpad.get_stats(),
        }

    async def execute(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if command == "reason":
            result = await self.reason(args.get("query", ""), args.get("context", {}))
            return result.__dict__
        elif command == "classify":
            problem_type = self._strategy_router.classify(args.get("query", ""))
            return {"problem_type": problem_type.value}
        elif command == "snapshot":
            snapshot = self._scratchpad.snapshot(args.get("trace_id"))
            return {"snapshot_id": snapshot.snapshot_id, "entries": len(snapshot.entries)}
        else:
            return {"error": f"Unknown command: {command}"}

    async def reason(self, query: str, context: Optional[Dict[str, Any]] = None) -> ReasoningResult:
        import time
        start = time.time()

        ctx = context or {}
        trace_id = ctx.get("trace_id")

        problem_type = self._strategy_router.classify(query)
        complexity = self._strategy_router.estimate_complexity(query, ctx)
        strategies = self._strategy_router.select_strategies(problem_type, complexity)

        self._logger.info(
            "Starting reasoning",
            query=query[:50],
            problem_type=problem_type.value,
            strategies=strategies,
        )

        reasoning_trace: List[str] = []
        intermediate_results: Dict[str, Any] = {}
        current_answer = ""
        confidence = 0.5

        if "cot" in strategies and self._config.enable_cot:
            cot_result = self._cot_injector.inject(query, context=ctx)
            reasoning_trace.append(f"CoT Template: {cot_result.template.value}")
            intermediate_results["cot_prompt"] = cot_result.prompt

            simulated_answer = f"经过思考分析，关于'{query[:30]}...'的答案是..."
            cot_parsed = self._cot_injector.parse_response(simulated_answer)
            current_answer = cot_parsed.final_answer or simulated_answer
            confidence = cot_parsed.confidence
            intermediate_results["cot_result"] = cot_parsed.__dict__

        if "tot" in strategies and self._config.enable_tot:
            tot_result = self._tot_engine.expand(query, ctx)
            reasoning_trace.append(f"ToT: {tot_result.total_nodes} nodes explored")
            intermediate_results["tot_result"] = {
                "total_nodes": tot_result.total_nodes,
                "best_path_length": len(tot_result.best_path),
            }

            if tot_result.best_answer and tot_result.confidence > confidence:
                current_answer = tot_result.best_answer
                confidence = tot_result.confidence

        if "self_consistency" in strategies and self._config.enable_self_consistency:
            consensus = await self._self_consistency.sample(query, context=ctx)
            reasoning_trace.append(f"Self-Consistency: {consensus.total_samples} samples, agreement={consensus.agreement_ratio:.2f}")
            intermediate_results["consensus"] = {
                "vote_distribution": consensus.vote_distribution,
                "agreement_ratio": consensus.agreement_ratio,
            }

            if consensus.confidence > confidence:
                current_answer = consensus.final_answer
                confidence = consensus.confidence

        if "reflexion" in strategies and self._config.enable_reflexion:
            if current_answer:
                reflexion_result = await self._reflexion_engine.reflect(query, current_answer, ctx)
                reasoning_trace.append(f"Reflexion: {reflexion_result.iteration} iterations")
                intermediate_results["reflexion"] = {
                    "iterations": reflexion_result.iteration,
                    "original_score": reflexion_result.trace[0].get("score", 0) if reflexion_result.trace else 0,
                    "final_score": reflexion_result.score,
                }

                if reflexion_result.score > confidence:
                    current_answer = reflexion_result.improved_answer
                    confidence = reflexion_result.score

        if not current_answer:
            current_answer = f"无法确定答案，建议使用更多策略分析"
            confidence = 0.3

        latency_ms = int((time.time() - start) * 1000)

        self._logger.info(
            "Reasoning complete",
            strategies_used=strategies,
            confidence=confidence,
            latency_ms=latency_ms,
        )

        return ReasoningResult(
            query=query,
            problem_type=problem_type,
            strategies_used=strategies,
            answer=current_answer,
            confidence=confidence,
            reasoning_trace=reasoning_trace,
            intermediate_results=intermediate_results,
            trace_id=trace_id,
            latency_ms=latency_ms,
        )

    def get_strategy_router(self) -> StrategyRouter:
        return self._strategy_router

    def get_cot_injector(self) -> CoTInjector:
        return self._cot_injector

    def get_tot_engine(self) -> TreeOfThoughtEngine:
        return self._tot_engine

    def get_reflexion_engine(self) -> ReflexionEngine:
        return self._reflexion_engine

    def get_self_consistency(self) -> SelfConsistencySampler:
        return self._self_consistency

    def get_scratchpad(self) -> ScratchpadManager:
        return self._scratchpad
