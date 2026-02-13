from __future__ import annotations

from dataclasses import dataclass, field
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
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "level": self.level,
            "disposition": self.disposition,
            "reasons": self.reasons,
            "factors": [{"name": f.name, "weight": f.weight, "score": f.score, "details": f.details} for f in self.factors],
        }


class RiskScorer:
    def __init__(self, low: float = 0.3, medium: float = 0.6, high: float = 0.8):
        self._low = float(low)
        self._medium = float(medium)
        self._high = float(high)

    def score(self, command: str, context: Optional[Dict[str, Any]] = None) -> RiskScore:
        ctx = context or {}
        factors: List[RiskFactor] = []

        cmd = (command or "").lower()
        if any(x in cmd for x in ["rm -rf", "mkfs", ":(){", "dd if=", "shutdown", "reboot"]):
            factors.append(RiskFactor(name="dangerous_shell", weight=1.0, score=1.0, details={"command": command}))

        if "curl" in cmd or "wget" in cmd:
            factors.append(RiskFactor(name="network_fetch", weight=0.4, score=0.7, details={"command": command}))

        if ctx.get("requires_write") is True:
            factors.append(RiskFactor(name="write_operation", weight=0.5, score=0.6, details={}))

        if ctx.get("contains_secrets") is True:
            factors.append(RiskFactor(name="secrets_risk", weight=0.8, score=0.9, details={}))

        total = 0.0
        denom = 0.0
        for f in factors:
            w = max(0.0, float(f.weight))
            s = max(0.0, min(1.0, float(f.score)))
            total += w * s
            denom += w
        total = total / denom if denom > 0 else 0.0

        level = "low"
        disposition = "allow"
        if total >= self._high:
            level = "high"
            disposition = "deny"
        elif total >= self._medium:
            level = "medium"
            disposition = "approve"
        elif total >= self._low:
            level = "guarded"
            disposition = "allow_with_constraints"

        reasons = [f.name for f in factors]
        return RiskScore(total=total, level=level, disposition=disposition, factors=factors, reasons=reasons)

