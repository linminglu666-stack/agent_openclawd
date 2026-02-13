from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field, field_validator


class TimestampMixin(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: Optional[datetime] = None


class IDMixin(BaseModel):
    id: str = Field(..., min_length=1, max_length=128)


class TraceMixin(BaseModel):
    trace_id: Optional[str] = Field(None, max_length=128)
    parent_trace_id: Optional[str] = Field(None, max_length=128)


class VersionMixin(BaseModel):
    version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")


class BaseSchema(BaseModel):
    model_config = {
        "frozen": True,
        "extra": "forbid",
        "str_strip_whitespace": True,
    }


class TaskSchema(BaseSchema, IDMixin, TraceMixin, TimestampMixin):
    task_type: Literal["inference", "tool_call", "workflow", "learning", "evaluation"]
    priority: int = Field(default=0, ge=0, le=100)
    payload: Dict[str, Any] = Field(default_factory=dict)
    required_skill: Optional[str] = None
    timeout_ms: int = Field(default=300000, ge=1000, le=3600000)
    max_retries: int = Field(default=3, ge=0, le=10)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("payload")
    @classmethod
    def validate_payload(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(v, dict):
            raise ValueError("payload must be a dictionary")
        return v


class TaskResultSchema(BaseSchema, IDMixin, TraceMixin, TimestampMixin):
    task_id: str
    success: bool
    output: Optional[Any] = None
    error: Optional[str] = None
    latency_ms: int = Field(default=0, ge=0)
    reasoning_trace: List[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentSchema(BaseSchema, IDMixin, TimestampMixin):
    agent_id: str
    status: Literal["idle", "running", "failed", "blocked", "learning"]
    skills: List[str] = Field(default_factory=list)
    current_task: Optional[str] = None
    success_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    last_heartbeat: int = Field(default=0, ge=0)
    max_concurrent_tasks: int = Field(default=5, ge=1, le=100)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("skills")
    @classmethod
    def validate_skills(cls, v: List[str]) -> List[str]:
        return [s.strip() for s in v if s.strip()]


class AgentHeartbeatSchema(BaseSchema):
    agent_id: str
    status: Literal["idle", "running", "failed", "blocked", "learning"]
    cpu: float = Field(ge=0.0, le=1.0)
    mem: float = Field(ge=0.0, le=1.0)
    queue_depth: int = Field(ge=0)
    timestamp: int = Field(ge=0)
    version: str = Field(default="1.0.0")
    skills: List[str] = Field(default_factory=list)
    health: Dict[str, Any] = Field(default_factory=dict)
    resource_limits: Dict[str, Any] = Field(default_factory=dict)


class MemoryEntrySchema(BaseSchema, IDMixin, TraceMixin, TimestampMixin):
    entry_type: Literal["fact", "skill", "experience", "preference", "constraint"]
    content: str = Field(..., min_length=1)
    source: str = Field(default="system")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    access_count: int = Field(default=0, ge=0)
    last_accessed: Optional[int] = None
    expires_at: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReasoningStepSchema(BaseSchema, TraceMixin):
    step_id: str
    step_type: Literal["observation", "thought", "action", "reflection", "conclusion"]
    content: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    dependencies: List[str] = Field(default_factory=list)
    timestamp: int = Field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))


class ReasoningResultSchema(BaseSchema, TraceMixin, TimestampMixin):
    query: str
    answer: str
    reasoning_steps: List[ReasoningStepSchema] = Field(default_factory=list)
    strategy: Literal["cot", "tot", "reflexion", "self_consistency", "hybrid"]
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    consistency_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    alternatives: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EventSchema(BaseSchema, TraceMixin, TimestampMixin):
    event_id: str
    event_type: str
    source: str
    topic: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    severity: Literal["debug", "info", "warning", "error", "critical"] = "info"
    correlation_id: Optional[str] = None


class APIRequestSchema(BaseSchema, TraceMixin):
    request_id: str
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    path: str
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    roles: List[str] = Field(default_factory=list)


class APIResponseSchema(BaseSchema, TraceMixin, TimestampMixin):
    request_id: str
    status_code: int = Field(ge=100, le=599)
    body: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)
    latency_ms: int = Field(default=0, ge=0)


class QualityScoreSchema(BaseSchema, TraceMixin, TimestampMixin):
    overall: float = Field(ge=0.0, le=1.0)
    consistency: float = Field(ge=0.0, le=1.0)
    calibration: float = Field(ge=0.0, le=1.0)
    structure: float = Field(ge=0.0, le=1.0)
    semantics: float = Field(ge=0.0, le=1.0)
    risk_level: Literal["low", "medium", "high"]
    confidence_interval: Tuple[float, float] = Field(default=(0.0, 1.0))


class PredictionSchema(BaseSchema, TimestampMixin):
    prediction_id: str
    metric_name: str
    predicted_value: float
    confidence_interval: Tuple[float, float]
    confidence_level: float = Field(ge=0.0, le=1.0)
    target_time: int
    model_version: str
    features_used: List[str] = Field(default_factory=list)


class HealthStatusSchema(BaseSchema, TimestampMixin):
    component: str
    healthy: bool
    details: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: int = Field(default=0, ge=0)
    checks: Dict[str, bool] = Field(default_factory=dict)


SchemaType = (
    TaskSchema
    | TaskResultSchema
    | AgentSchema
    | AgentHeartbeatSchema
    | MemoryEntrySchema
    | ReasoningStepSchema
    | ReasoningResultSchema
    | EventSchema
    | APIRequestSchema
    | APIResponseSchema
    | QualityScoreSchema
    | PredictionSchema
    | HealthStatusSchema
)
