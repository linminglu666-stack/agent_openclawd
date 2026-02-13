from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class HealthCheck:
    name: str
    ok: bool
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthReport:
    component: str
    state: str
    checks: List[HealthCheck] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

