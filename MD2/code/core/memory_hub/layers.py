from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import asyncio
import uuid

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocols.interfaces import IMemoryLayer
from utils.logger import get_logger


class MemoryLayerName(Enum):
    L1_CONTEXT = "l1_context"
    L2_SESSION = "l2_session"
    L3_PROFILE = "l3_profile"
    L4_KNOWLEDGE = "l4_knowledge"


@dataclass
class MemoryVersion:
    version_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_version_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    source: str = ""
    trace_id: Optional[str] = None


@dataclass
class LayeredMemoryItem:
    key: str
    value: Any
    layer: MemoryLayerName
    confidence: float = 0.5
    version: MemoryVersion = field(default_factory=MemoryVersion)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    ttl: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "layer": self.layer.value,
            "confidence": self.confidence,
            "version": {
                "version_id": self.version.version_id,
                "parent_version_id": self.version.parent_version_id,
                "created_at": self.version.created_at.isoformat(),
                "source": self.version.source,
                "trace_id": self.version.trace_id,
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "ttl": self.ttl,
            "metadata": self.metadata,
        }


class InMemoryLayer(IMemoryLayer):
    def __init__(self, layer: MemoryLayerName):
        self._layer = layer
        self._items: Dict[str, LayeredMemoryItem] = {}
        self._lock = asyncio.Lock()
        self._logger = get_logger(f"memory.layer.{layer.value}")

    @property
    def layer_name(self) -> str:
        return self._layer.value

    async def store(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        async with self._lock:
            existing = self._items.get(key)
            version = MemoryVersion(parent_version_id=existing.version.version_id if existing else None)
            item = LayeredMemoryItem(
                key=key,
                value=value,
                layer=self._layer,
                confidence=existing.confidence if existing else 0.5,
                version=version,
                ttl=ttl,
                metadata=existing.metadata.copy() if existing else {},
            )
            self._items[key] = item
            return True

    async def retrieve(self, key: str) -> Optional[Any]:
        async with self._lock:
            item = self._items.get(key)
            return item.value if item else None

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key not in self._items:
                return False
            del self._items[key]
            return True

    async def query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        async with self._lock:
            prefix = query.get("prefix")
            min_conf = query.get("min_confidence")

            results: List[Dict[str, Any]] = []
            for key, item in self._items.items():
                if prefix and not str(key).startswith(str(prefix)):
                    continue
                if min_conf is not None and item.confidence < float(min_conf):
                    continue
                results.append(item.to_dict())
            return results

    async def clear(self) -> bool:
        async with self._lock:
            self._items.clear()
            return True

    async def get_confidence(self, key: str) -> Optional[float]:
        async with self._lock:
            item = self._items.get(key)
            return item.confidence if item else None

    async def set_confidence(self, key: str, confidence: float) -> bool:
        async with self._lock:
            item = self._items.get(key)
            if not item:
                return False
            item.confidence = max(0.0, min(1.0, float(confidence)))
            item.updated_at = datetime.utcnow()
            return True

    async def get_item(self, key: str) -> Optional[LayeredMemoryItem]:
        async with self._lock:
            return self._items.get(key)

