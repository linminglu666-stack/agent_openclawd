from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .layers import MemoryLayerName


@dataclass
class WritebackPlan:
    layer: MemoryLayerName
    ttl: Optional[int]
    confidence: float
    metadata: Dict[str, Any]


class WritebackPlanner:
    def __init__(self, high_confidence: float = 0.85):
        self._high_confidence = high_confidence

    def plan(self, key: str, value: Any, context: Dict[str, Any]) -> WritebackPlan:
        confidence = float(context.get("confidence", 0.5))
        ttl = context.get("ttl")
        layer = MemoryLayerName.L2_SESSION

        if confidence >= self._high_confidence:
            layer = MemoryLayerName.L3_PROFILE

        if context.get("is_knowledge") is True:
            layer = MemoryLayerName.L4_KNOWLEDGE

        if context.get("is_ephemeral") is True:
            layer = MemoryLayerName.L1_CONTEXT

        metadata = {
            "source": context.get("source", ""),
            "trace_id": context.get("trace_id"),
        }

        return WritebackPlan(layer=layer, ttl=ttl, confidence=confidence, metadata=metadata)

