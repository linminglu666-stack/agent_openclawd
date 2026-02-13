from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class HealthState(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    name: str
    ok: bool
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthReport:
    component: str
    state: HealthState
    checks: List[HealthCheck] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "state": self.state.value,
            "timestamp": self.timestamp,
            "checks": [{"name": c.name, "ok": c.ok, "details": c.details} for c in self.checks],
        }

