from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from .layers import LayeredMemoryItem


class ConflictPolicy(Enum):
    PREFER_NEWER = "prefer_newer"
    PREFER_HIGHER_CONFIDENCE = "prefer_higher_confidence"
    PREFER_EXISTING = "prefer_existing"


@dataclass
class ConflictResolutionResult:
    chosen: LayeredMemoryItem
    policy: ConflictPolicy
    merged: bool
    details: Dict[str, Any]


class ConflictResolver:
    def __init__(self, policy: ConflictPolicy = ConflictPolicy.PREFER_HIGHER_CONFIDENCE):
        self._policy = policy

    def resolve(self, existing: Optional[LayeredMemoryItem], incoming: LayeredMemoryItem) -> ConflictResolutionResult:
        if existing is None:
            return ConflictResolutionResult(
                chosen=incoming,
                policy=self._policy,
                merged=False,
                details={"reason": "no_existing"},
            )

        if self._policy == ConflictPolicy.PREFER_EXISTING:
            return ConflictResolutionResult(
                chosen=existing,
                policy=self._policy,
                merged=False,
                details={"reason": "prefer_existing"},
            )

        if self._policy == ConflictPolicy.PREFER_NEWER:
            chosen = incoming if incoming.updated_at >= existing.updated_at else existing
            return ConflictResolutionResult(
                chosen=chosen,
                policy=self._policy,
                merged=False,
                details={"existing_updated_at": existing.updated_at.isoformat(), "incoming_updated_at": incoming.updated_at.isoformat()},
            )

        if incoming.confidence > existing.confidence:
            return ConflictResolutionResult(
                chosen=incoming,
                policy=self._policy,
                merged=False,
                details={"existing_confidence": existing.confidence, "incoming_confidence": incoming.confidence},
            )

        return ConflictResolutionResult(
            chosen=existing,
            policy=self._policy,
            merged=False,
            details={"existing_confidence": existing.confidence, "incoming_confidence": incoming.confidence},
        )

