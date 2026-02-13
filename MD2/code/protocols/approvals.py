from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELED = "canceled"


@dataclass
class ApprovalRequest:
    approval_id: str
    task_id: str
    risk_score: float
    risk_factors: List[Dict[str, Any]] = field(default_factory=list)
    requester: Dict[str, Any] = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    expires_at: int = 0
    created_at: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))


@dataclass
class ApprovalDecision:
    approval_id: str
    decision: str
    approver: str
    reason: str = ""
    conditions: List[str] = field(default_factory=list)
    signed_at: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))

