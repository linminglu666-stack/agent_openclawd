from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.logger import get_logger


@dataclass
class RoutingResult:
    task_id: str
    target_agent: str
    reason: str
    confidence: float
    alternatives: List[str] = field(default_factory=list)
    estimated_start_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "target_agent": self.target_agent,
            "reason": self.reason,
            "confidence": self.confidence,
            "alternatives": self.alternatives,
            "estimated_start_ms": self.estimated_start_ms,
        }


@dataclass
class AgentInfo:
    agent_id: str
    skills: List[str]
    status: str = "idle"
    load: float = 0.0
    success_rate: float = 0.9
    avg_latency_ms: int = 1000
    queue_depth: int = 0
    last_heartbeat: int = 0


class TaskRouter:
    def __init__(self):
        self._agents: Dict[str, AgentInfo] = {}
        self._logger = get_logger("central_brain.router")
        self._routing_rules: List[Dict[str, Any]] = []

    def register_agent(self, agent_id: str, skills: List[str], metadata: Optional[Dict[str, Any]] = None) -> bool:
        info = AgentInfo(
            agent_id=agent_id,
            skills=skills,
            status=metadata.get("status", "idle") if metadata else "idle",
            load=metadata.get("load", 0.0) if metadata else 0.0,
            success_rate=metadata.get("success_rate", 0.9) if metadata else 0.9,
            avg_latency_ms=metadata.get("avg_latency_ms", 1000) if metadata else 1000,
            queue_depth=metadata.get("queue_depth", 0) if metadata else 0,
        )
        self._agents[agent_id] = info
        self._logger.info("Agent registered", agent_id=agent_id, skills=skills)
        return True

    def unregister_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            self._logger.info("Agent unregistered", agent_id=agent_id)
            return True
        return False

    def update_agent_status(self, agent_id: str, status: Dict[str, Any]) -> bool:
        if agent_id not in self._agents:
            return False

        info = self._agents[agent_id]
        if "status" in status:
            info.status = status["status"]
        if "load" in status:
            info.load = status["load"]
        if "queue_depth" in status:
            info.queue_depth = status["queue_depth"]
        if "success_rate" in status:
            info.success_rate = status["success_rate"]

        return True

    def route(self, task: Dict[str, Any]) -> RoutingResult:
        task_id = task.get("task_id", "")
        required_skill = task.get("required_skill")
        task_type = task.get("task_type", "general")

        candidates = self._find_candidates(required_skill, task_type)

        if not candidates:
            self._logger.warn("No available agents for task", task_id=task_id, required_skill=required_skill)
            return RoutingResult(
                task_id=task_id,
                target_agent="",
                reason="no_available_agents",
                confidence=0.0,
            )

        scored = [(agent_id, self._score_agent(agent_id, task)) for agent_id in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)

        best_agent = scored[0][0]
        best_score = scored[0][1]
        alternatives = [a for a, s in scored[1:4]]

        estimated_start = self._estimate_start_time(best_agent)

        self._logger.info(
            "Task routed",
            task_id=task_id,
            target=best_agent,
            score=best_score,
            alternatives=len(alternatives),
        )

        return RoutingResult(
            task_id=task_id,
            target_agent=best_agent,
            reason="best_match_by_skill_and_load",
            confidence=best_score,
            alternatives=alternatives,
            estimated_start_ms=estimated_start,
        )

    def _find_candidates(self, required_skill: Optional[str], task_type: str) -> List[str]:
        candidates = []

        for agent_id, info in self._agents.items():
            if info.status not in ("idle", "running"):
                continue

            if required_skill and required_skill not in info.skills:
                continue

            candidates.append(agent_id)

        return candidates

    def _score_agent(self, agent_id: str, task: Dict[str, Any]) -> float:
        info = self._agents[agent_id]

        skill_score = 1.0
        required_skill = task.get("required_skill")
        if required_skill and required_skill in info.skills:
            skill_score = 1.0
        elif required_skill:
            skill_score = 0.5

        load_score = 1.0 - min(info.load, 1.0)
        queue_score = 1.0 / (1.0 + info.queue_depth * 0.1)
        reliability_score = info.success_rate

        latency_score = 1.0
        if info.avg_latency_ms > 5000:
            latency_score = 0.5
        elif info.avg_latency_ms > 2000:
            latency_score = 0.7

        total = (
            skill_score * 0.3 +
            load_score * 0.25 +
            queue_score * 0.15 +
            reliability_score * 0.2 +
            latency_score * 0.1
        )

        return total

    def _estimate_start_time(self, agent_id: str) -> int:
        info = self._agents[agent_id]
        base_latency = info.avg_latency_ms
        queue_delay = info.queue_depth * base_latency
        return base_latency + queue_delay

    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        info = self._agents.get(agent_id)
        if not info:
            return None
        return {
            "agent_id": info.agent_id,
            "skills": info.skills,
            "status": info.status,
            "load": info.load,
            "success_rate": info.success_rate,
            "avg_latency_ms": info.avg_latency_ms,
            "queue_depth": info.queue_depth,
        }

    def list_agents(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        agents = []
        for info in self._agents.values():
            if status and info.status != status:
                continue
            agents.append({
                "agent_id": info.agent_id,
                "skills": info.skills,
                "status": info.status,
                "load": info.load,
            })
        return agents

    def add_routing_rule(self, rule: Dict[str, Any]) -> bool:
        self._routing_rules.append(rule)
        self._logger.info("Routing rule added", rule=rule)
        return True
