from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ModuleInfo:
    name: str
    version: str
    initialized: bool = False


@dataclass
class HealthStatus:
    component: str
    healthy: bool
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))


@dataclass
class ExecutionResult:
    success: bool
    output: Any = None
    error: Optional[str] = None
    trace_id: Optional[str] = None
    latency_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class IModule(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def shutdown(self) -> bool:
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def execute(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        pass


class IToolAdapter(ABC):
    @abstractmethod
    async def exec_command(self, command: str, opts: Dict[str, Any]) -> ExecutionResult:
        pass

    @abstractmethod
    async def read_file(self, path: str) -> ExecutionResult:
        pass

    @abstractmethod
    async def write_file(self, path: str, content: str) -> ExecutionResult:
        pass

    @abstractmethod
    async def list_dir(self, path: str) -> ExecutionResult:
        pass


class IMemoryAdapter(ABC):
    @abstractmethod
    async def store(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        pass

    @abstractmethod
    async def retrieve(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def query(self, pattern: str) -> List[Dict[str, Any]]:
        pass


class IMemoryLayer(IMemoryAdapter):
    @property
    @abstractmethod
    def layer_name(self) -> str:
        pass

    @abstractmethod
    async def get_item(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def set_confidence(self, key: str, confidence: float) -> bool:
        pass

    @abstractmethod
    async def clear(self) -> bool:
        pass


class IContextBus(ABC):
    @abstractmethod
    async def push(self, key: str, value: Any, trace_id: Optional[str] = None) -> bool:
        pass


class IEventBus(ABC):
    @abstractmethod
    async def publish(self, topic: str, event: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> str:
        pass

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        pass


class ITracer(ABC):
    @abstractmethod
    def start_span(self, operation_name: str, parent_span_id: Optional[str] = None) -> str:
        pass

    @abstractmethod
    def end_span(self, span_id: str, status: str = "ok") -> bool:
        pass

    @abstractmethod
    def add_event(self, span_id: str, event: Dict[str, Any]) -> bool:
        pass


class IMetricsCollector(ABC):
    @abstractmethod
    def record_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> bool:
        pass

    @abstractmethod
    def record_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> bool:
        pass

    @abstractmethod
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> bool:
        pass

    @abstractmethod
    def get_metrics(self, name: Optional[str] = None) -> Dict[str, Any]:
        pass


class IAuthorizer(ABC):
    @abstractmethod
    async def check_permission(self, user_id: str, resource: str, action: str) -> bool:
        pass

    @abstractmethod
    async def get_permissions(self, user_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def grant_permission(self, user_id: str, resource: str, action: str) -> bool:
        pass

    @abstractmethod
    async def revoke_permission(self, user_id: str, resource: str, action: str) -> bool:
        pass


class IAuditSink(ABC):
    @abstractmethod
    async def emit(self, event: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def list(self, limit: int = 100) -> List[Dict[str, Any]]:
        pass


class IRedactor(ABC):
    @abstractmethod
    def redact(self, data: Any, policy: Optional[Dict[str, Any]] = None) -> Any:
        pass


class IAuthProvider(ABC):
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        pass


class IPolicyEngine(ABC):
    @abstractmethod
    async def decide(
        self,
        subject: Dict[str, Any],
        action: str,
        resource: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def add_rule(self, rule: Any) -> bool:
        pass

    @abstractmethod
    async def pop(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any) -> bool:
        pass

    @abstractmethod
    async def snapshot(self) -> Dict[str, Any]:
        pass


class IReasoner(ABC):
    @property
    @abstractmethod
    def strategy(self) -> str:
        pass

    @abstractmethod
    async def reason(self, problem: str, context: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def evaluate(self, result: Dict[str, Any]) -> float:
        pass


class IEvalGate(ABC):
    @abstractmethod
    async def evaluate(self, task: Dict[str, Any], result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        pass


class IRiskScorer(ABC):
    @abstractmethod
    def score(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        pass


class IAgentPool(ABC):
    @abstractmethod
    async def register(self, agent_id: str, skills: List[str], metadata: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def unregister(self, agent_id: str) -> bool:
        pass

    @abstractmethod
    async def get_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def list_available(self, required_skill: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def dispatch(self, task: Dict[str, Any], hints: Dict[str, Any]) -> Dict[str, Any]:
        pass


class IMessageBus(ABC):
    @abstractmethod
    async def publish(self, topic: str, payload: Dict[str, Any], trace_id: Optional[str] = None) -> bool:
        pass

    @abstractmethod
    async def subscribe(self, topic: str, handler: Any) -> str:
        pass

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        pass


class IScheduler(ABC):
    @abstractmethod
    async def schedule(self, task: Dict[str, Any], policy: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    async def cancel(self, schedule_id: str) -> bool:
        pass

    @abstractmethod
    async def get_next(self) -> Optional[Dict[str, Any]]:
        pass


class IOrchestrator(ABC):
    @abstractmethod
    async def execute_dag(self, dag: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def resume(self, run_id: str, from_node: Optional[str] = None) -> Dict[str, Any]:
        pass


class IAuthProvider(ABC):
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def authorize(self, user_id: str, resource: str, action: str) -> bool:
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        pass


class IConfigStore(ABC):
    @abstractmethod
    async def get(self, key: str, default: Any = None) -> Any:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, version: Optional[str] = None) -> bool:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def list_versions(self, key: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def rollback(self, key: str, version: str) -> bool:
        pass


class ISkillRegistry(ABC):
    @abstractmethod
    async def register(self, skill: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def unregister(self, skill_id: str) -> bool:
        pass

    @abstractmethod
    async def get(self, skill_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def list_all(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def match(self, task_type: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        pass


class ITruthGate(ABC):
    @abstractmethod
    async def check(self, claim: Dict[str, Any], evidence: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        pass


class IGrowthLoop(ABC):
    @abstractmethod
    async def detect_idle(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def learn(self, agent_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def register_skill(self, skill: Dict[str, Any]) -> bool:
        pass
