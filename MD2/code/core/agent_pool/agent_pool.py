from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from protocols.interfaces import IModule, IAgentPool
from utils.logger import get_logger
from .agent import Agent, AgentState, AgentConfig, AgentHeartbeat


@dataclass
class AgentPoolConfig:
    max_agents: int = 100
    heartbeat_timeout_sec: int = 30
    idle_timeout_sec: int = 60
    max_retries: int = 3
    enable_auto_learning: bool = True


@dataclass
class DispatchResult:
    task_id: str
    assigned_agent: Optional[str]
    reason: str
    alternatives: List[str] = field(default_factory=list)
    estimated_start_ms: int = 0


class AgentPool(IModule, IAgentPool):
    def __init__(self, config: Optional[AgentPoolConfig] = None):
        self._config = config or AgentPoolConfig()
        self._agents: Dict[str, Agent] = {}
        self._initialized = False
        self._logger = get_logger("agent_pool")
        self._agent_counter = 0

    @property
    def name(self) -> str:
        return "agent_pool"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self, config: Dict[str, Any]) -> bool:
        if config.get("max_agents"):
            self._config.max_agents = config["max_agents"]
        if config.get("heartbeat_timeout_sec"):
            self._config.heartbeat_timeout_sec = config["heartbeat_timeout_sec"]
        if config.get("idle_timeout_sec"):
            self._config.idle_timeout_sec = config["idle_timeout_sec"]

        self._initialized = True
        self._logger.info("Agent pool initialized", config=self._config.__dict__)
        return True

    async def shutdown(self) -> bool:
        self._initialized = False
        self._logger.info("Agent pool shutdown")
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {
            "component": self.name,
            "initialized": self._initialized,
            "total_agents": len(self._agents),
            "idle_agents": len([a for a in self._agents.values() if a.state == AgentState.IDLE]),
            "running_agents": len([a for a in self._agents.values() if a.state == AgentState.RUNNING]),
        }

    async def execute(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if command == "register":
            success = await self.register(
                args.get("agent_id", ""),
                args.get("skills", []),
                args.get("metadata", {}),
            )
            return {"success": success}
        elif command == "unregister":
            success = await self.unregister(args.get("agent_id", ""))
            return {"success": success}
        elif command == "status":
            status = await self.get_status(args.get("agent_id", ""))
            return status or {"error": "agent not found"}
        elif command == "dispatch":
            result = await self.dispatch(args.get("task", {}), args.get("hints", {}))
            return result.__dict__
        elif command == "list":
            agents = await self.list_available(args.get("required_skill"))
            return {"agents": agents}
        else:
            return {"error": f"Unknown command: {command}"}

    async def register(self, agent_id: str, skills: List[str], metadata: Dict[str, Any]) -> bool:
        if agent_id in self._agents:
            self._logger.warn("Agent already registered", agent_id=agent_id)
            return False

        if len(self._agents) >= self._config.max_agents:
            self._logger.error("Agent pool full", max_agents=self._config.max_agents)
            return False

        config = AgentConfig(
            agent_id=agent_id,
            skills=skills,
            max_concurrent_tasks=metadata.get("max_concurrent_tasks", 5),
            idle_timeout_sec=metadata.get("idle_timeout_sec", self._config.idle_timeout_sec),
            resource_limits=metadata.get("resource_limits", {}),
        )

        agent = Agent(config)
        self._agents[agent_id] = agent

        self._logger.info("Agent registered", agent_id=agent_id, skills=skills)
        return True

    async def unregister(self, agent_id: str) -> bool:
        if agent_id not in self._agents:
            return False

        agent = self._agents[agent_id]
        if agent.state == AgentState.RUNNING:
            self._logger.warn("Cannot unregister running agent", agent_id=agent_id)
            return False

        del self._agents[agent_id]
        self._logger.info("Agent unregistered", agent_id=agent_id)
        return True

    async def get_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        return agent.get_status()

    async def list_available(self, required_skill: Optional[str] = None) -> List[Dict[str, Any]]:
        available = []
        for agent in self._agents.values():
            if agent.state not in (AgentState.IDLE, AgentState.LEARNING):
                continue

            if required_skill and required_skill not in agent.skills:
                continue

            available.append(agent.get_status())

        return available

    async def dispatch(self, task: Dict[str, Any], hints: Dict[str, Any]) -> DispatchResult:
        task_id = task.get("task_id", "")
        required_skill = task.get("required_skill") or hints.get("required_skill")

        candidates = []
        for agent in self._agents.values():
            if agent.state not in (AgentState.IDLE, AgentState.LEARNING):
                continue

            if required_skill and required_skill not in agent.skills:
                continue

            score = self._score_agent(agent, task, hints)
            candidates.append((agent, score))

        if not candidates:
            self._logger.warn("No available agents for task", task_id=task_id)
            return DispatchResult(
                task_id=task_id,
                assigned_agent=None,
                reason="no_available_agents",
            )

        candidates.sort(key=lambda x: x[1], reverse=True)
        best_agent = candidates[0][0]

        success = best_agent.assign_task(task_id)
        if not success:
            return DispatchResult(
                task_id=task_id,
                assigned_agent=None,
                reason="assignment_failed",
            )

        alternatives = [a.agent_id for a, _ in candidates[1:4]]

        self._logger.info(
            "Task dispatched",
            task_id=task_id,
            agent=best_agent.agent_id,
            alternatives=len(alternatives),
        )

        return DispatchResult(
            task_id=task_id,
            assigned_agent=best_agent.agent_id,
            reason="best_match_by_skill_and_load",
            alternatives=alternatives,
            estimated_start_ms=1000,
        )

    def _score_agent(self, agent: Agent, task: Dict[str, Any], hints: Dict[str, Any]) -> float:
        score = 0.5

        if agent.state == AgentState.IDLE:
            score += 0.3
        elif agent.state == AgentState.LEARNING:
            score += 0.1

        metrics = agent.get_status().get("metrics", {})
        success_rate = metrics.get("success_rate", 0.9)
        score += success_rate * 0.2

        required_skill = task.get("required_skill")
        if required_skill and required_skill in agent.skills:
            score += 0.2

        return min(score, 1.0)

    def tick(self, now: Optional[int] = None) -> Dict[str, Any]:
        ts = now or int(datetime.now(tz=timezone.utc).timestamp())
        learning_started = 0
        timeouts_detected = 0

        for agent in self._agents.values():
            if self._config.enable_auto_learning and agent.should_start_learning(ts):
                if agent.start_learning():
                    learning_started += 1

            heartbeat = agent.heartbeat()
            if ts - heartbeat.timestamp > self._config.heartbeat_timeout_sec:
                agent.fail("heartbeat_timeout")
                timeouts_detected += 1

        if learning_started > 0 or timeouts_detected > 0:
            self._logger.info(
                "Pool tick complete",
                learning_started=learning_started,
                timeouts_detected=timeouts_detected,
            )

        return {
            "learning_started": learning_started,
            "timeouts_detected": timeouts_detected,
        }

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)

    def get_stats(self) -> Dict[str, Any]:
        state_counts: Dict[str, int] = {}
        for agent in self._agents.values():
            state = agent.state.value
            state_counts[state] = state_counts.get(state, 0) + 1

        return {
            "total_agents": len(self._agents),
            "state_distribution": state_counts,
            "config": self._config.__dict__,
        }
