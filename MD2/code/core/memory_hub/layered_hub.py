from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocols.interfaces import IModule
from utils.logger import get_logger

from .layers import InMemoryLayer, MemoryLayerName, LayeredMemoryItem, MemoryVersion
from .conflict_resolver import ConflictResolver, ConflictPolicy
from .writeback import WritebackPlanner, WritebackPlan


@dataclass
class LayeredMemoryHubConfig:
    conflict_policy: ConflictPolicy = ConflictPolicy.PREFER_HIGHER_CONFIDENCE


class LayeredMemoryHub(IModule):
    def __init__(self, config: Optional[LayeredMemoryHubConfig] = None):
        self._config = config or LayeredMemoryHubConfig()
        self._layers: Dict[MemoryLayerName, InMemoryLayer] = {
            MemoryLayerName.L1_CONTEXT: InMemoryLayer(MemoryLayerName.L1_CONTEXT),
            MemoryLayerName.L2_SESSION: InMemoryLayer(MemoryLayerName.L2_SESSION),
            MemoryLayerName.L3_PROFILE: InMemoryLayer(MemoryLayerName.L3_PROFILE),
            MemoryLayerName.L4_KNOWLEDGE: InMemoryLayer(MemoryLayerName.L4_KNOWLEDGE),
        }
        self._conflict_resolver = ConflictResolver(self._config.conflict_policy)
        self._writeback_planner = WritebackPlanner()
        self._initialized = False
        self._logger = get_logger("memory.layered_hub")

    @property
    def name(self) -> str:
        return "layered_memory_hub"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self, config: Dict[str, Any]) -> bool:
        self._initialized = True
        return True

    async def shutdown(self) -> bool:
        for layer in self._layers.values():
            await layer.clear()
        self._initialized = False
        return True

    async def health_check(self) -> Dict[str, Any]:
        stats = {"component": self.name, "initialized": self._initialized, "layers": {}}
        for name, layer in self._layers.items():
            stats["layers"][name.value] = {"keys": len(await layer.query({}))}
        return stats

    def get_layer(self, layer: MemoryLayerName) -> InMemoryLayer:
        return self._layers[layer]

    async def upsert(
        self,
        key: str,
        value: Any,
        layer: MemoryLayerName,
        confidence: float = 0.5,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        source: str = "",
    ) -> Dict[str, Any]:
        target = self._layers[layer]
        existing = await target.get_item(key)

        version = MemoryVersion(parent_version_id=existing.version.version_id if existing else None, source=source, trace_id=trace_id)
        incoming = LayeredMemoryItem(
            key=key,
            value=value,
            layer=layer,
            confidence=float(confidence),
            version=version,
            ttl=ttl,
            metadata=metadata or {},
        )

        resolved = self._conflict_resolver.resolve(existing=existing, incoming=incoming)
        await target.store(key, resolved.chosen.value, ttl=ttl)
        await target.set_confidence(key, resolved.chosen.confidence)

        return {
            "ok": True,
            "layer": layer.value,
            "key": key,
            "chosen_version_id": resolved.chosen.version.version_id,
            "policy": resolved.policy.value,
            "details": resolved.details,
        }

    async def retrieve(self, key: str, preferred_layer: Optional[MemoryLayerName] = None) -> Optional[Any]:
        if preferred_layer is not None:
            return await self._layers[preferred_layer].retrieve(key)

        order = [
            MemoryLayerName.L1_CONTEXT,
            MemoryLayerName.L2_SESSION,
            MemoryLayerName.L3_PROFILE,
            MemoryLayerName.L4_KNOWLEDGE,
        ]
        for layer in order:
            value = await self._layers[layer].retrieve(key)
            if value is not None:
                return value
        return None

    async def query(self, query: Dict[str, Any], layer: Optional[MemoryLayerName] = None) -> List[Dict[str, Any]]:
        if layer is not None:
            return await self._layers[layer].query(query)

        results: List[Dict[str, Any]] = []
        for lyr in self._layers.values():
            results.extend(await lyr.query(query))
        return results

    async def writeback(self, key: str, value: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        plan: WritebackPlan = self._writeback_planner.plan(key=key, value=value, context=context)
        return await self.upsert(
            key=key,
            value=value,
            layer=plan.layer,
            ttl=plan.ttl,
            confidence=plan.confidence,
            metadata=plan.metadata,
            trace_id=plan.metadata.get("trace_id"),
            source=str(plan.metadata.get("source", "")),
        )

