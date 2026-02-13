from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class InstanceStatus(Enum):
    CREATING = "creating"
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    IDLE = "idle"
    ERROR = "error"
    TERMINATING = "terminating"
    TERMINATED = "terminated"


@dataclass(frozen=True)
class ResourceQuota:
    cpu_cores: float = 1.0
    memory_mb: int = 2048
    storage_gb: int = 10
    max_concurrent_tasks: int = 3
    api_rate_limit: int = 200
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_cores": self.cpu_cores,
            "memory_mb": self.memory_mb,
            "storage_gb": self.storage_gb,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "api_rate_limit": self.api_rate_limit,
        }


@dataclass(frozen=True)
class InstanceConfig:
    model: str = "gpt-4"
    quality_threshold: float = 0.85
    timeout_multiplier: float = 1.0
    custom_skills: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InstanceEndpoints:
    api: str
    websocket: str
    health: str


@dataclass
class Instance:
    instance_id: str
    name: str
    profession_id: str
    status: InstanceStatus
    config: InstanceConfig
    resources: ResourceQuota
    endpoints: Optional[InstanceEndpoints] = None
    created_at: int = 0
    updated_at: int = 0
    current_tasks: List[str] = field(default_factory=list)
    completed_tasks: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.created_at == 0:
            now = int(datetime.now(tz=timezone.utc).timestamp())
            object.__setattr__(self, "created_at", now)
            object.__setattr__(self, "updated_at", now)
    
    def is_available(self) -> bool:
        return self.status in (InstanceStatus.READY, InstanceStatus.IDLE) and \
               len(self.current_tasks) < self.resources.max_concurrent_tasks
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "name": self.name,
            "profession_id": self.profession_id,
            "status": self.status.value,
            "config": {
                "model": self.config.model,
                "quality_threshold": self.config.quality_threshold,
                "timeout_multiplier": self.config.timeout_multiplier,
            },
            "resources": self.resources.to_dict(),
            "endpoints": {
                "api": self.endpoints.api,
                "websocket": self.endpoints.websocket,
                "health": self.endpoints.health,
            } if self.endpoints else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "current_tasks": self.current_tasks,
            "completed_tasks": self.completed_tasks,
            "error_count": self.error_count,
        }


@dataclass(frozen=True)
class InstanceCreateRequest:
    profession_id: str
    name: str
    config: Optional[InstanceConfig] = None
    resource_quota: Optional[ResourceQuota] = None
    workspace_id: Optional[str] = None
    team_id: Optional[str] = None


@dataclass(frozen=True)
class InstanceCreateResponse:
    instance_id: str
    status: InstanceStatus
    endpoints: Optional[InstanceEndpoints]
    created_at: int
