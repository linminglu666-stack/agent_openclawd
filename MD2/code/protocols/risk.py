from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class RiskFactor:
    name: str
    weight: float
    score: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskScore:
    total: float
    level: str
    disposition: str
    factors: List[RiskFactor] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

