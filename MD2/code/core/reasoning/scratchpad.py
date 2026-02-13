from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.logger import get_logger


@dataclass
class ScratchpadEntry:
    entry_id: str
    key: str
    value: Any
    entry_type: str
    timestamp: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))
    ttl: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScratchpadSnapshot:
    snapshot_id: str
    entries: Dict[str, ScratchpadEntry] = field(default_factory=dict)
    created_at: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))
    trace_id: Optional[str] = None


class ScratchpadManager:
    def __init__(self, max_entries: int = 1000, default_ttl: int = 3600):
        self._max_entries = max_entries
        self._default_ttl = default_ttl
        self._entries: Dict[str, ScratchpadEntry] = {}
        self._entry_counter = 0
        self._logger = get_logger("reasoning.scratchpad")

    def store(self, key: str, value: Any, entry_type: str = "general", ttl: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None) -> ScratchpadEntry:
        self._entry_counter += 1
        entry_id = f"scratch_{self._entry_counter}"

        if len(self._entries) >= self._max_entries:
            self._evict_oldest()

        entry = ScratchpadEntry(
            entry_id=entry_id,
            key=key,
            value=value,
            entry_type=entry_type,
            ttl=ttl or self._default_ttl,
            metadata=metadata or {},
        )

        self._entries[key] = entry
        self._logger.debug("Stored scratchpad entry", key=key, entry_type=entry_type)

        return entry

    def retrieve(self, key: str) -> Optional[Any]:
        entry = self._entries.get(key)
        if not entry:
            return None

        if entry.ttl and (datetime.now(tz=timezone.utc).timestamp() - entry.timestamp) > entry.ttl:
            del self._entries[key]
            return None

        return entry.value

    def get_entry(self, key: str) -> Optional[ScratchpadEntry]:
        return self._entries.get(key)

    def update(self, key: str, value: Any) -> Optional[ScratchpadEntry]:
        if key not in self._entries:
            return None

        entry = self._entries[key]
        entry.value = value
        entry.timestamp = int(datetime.now(tz=timezone.utc).timestamp())

        self._logger.debug("Updated scratchpad entry", key=key)
        return entry

    def delete(self, key: str) -> bool:
        if key in self._entries:
            del self._entries[key]
            self._logger.debug("Deleted scratchpad entry", key=key)
            return True
        return False

    def list_entries(self, entry_type: Optional[str] = None) -> List[ScratchpadEntry]:
        entries = list(self._entries.values())
        if entry_type:
            entries = [e for e in entries if e.entry_type == entry_type]
        return sorted(entries, key=lambda x: x.timestamp, reverse=True)

    def clear(self) -> int:
        count = len(self._entries)
        self._entries.clear()
        self._logger.info("Cleared scratchpad", count=count)
        return count

    def snapshot(self, trace_id: Optional[str] = None) -> ScratchpadSnapshot:
        self._entry_counter += 1
        snapshot_id = f"snap_{self._entry_counter}"

        snapshot = ScratchpadSnapshot(
            snapshot_id=snapshot_id,
            entries=dict(self._entries),
            trace_id=trace_id,
        )

        self._logger.debug("Created snapshot", snapshot_id=snapshot_id, entries=len(self._entries))
        return snapshot

    def restore(self, snapshot: ScratchpadSnapshot) -> bool:
        self._entries = dict(snapshot.entries)
        self._logger.info("Restored from snapshot", snapshot_id=snapshot.snapshot_id, entries=len(self._entries))
        return True

    def _evict_oldest(self) -> None:
        if not self._entries:
            return

        oldest_key = min(self._entries.keys(), key=lambda k: self._entries[k].timestamp)
        del self._entries[oldest_key]
        self._logger.debug("Evicted oldest entry", key=oldest_key)

    def get_stats(self) -> Dict[str, Any]:
        types: Dict[str, int] = {}
        for entry in self._entries.values():
            types[entry.entry_type] = types.get(entry.entry_type, 0) + 1

        return {
            "total_entries": len(self._entries),
            "max_entries": self._max_entries,
            "entry_types": types,
            "default_ttl": self._default_ttl,
        }

    def store_intermediate_result(self, step: int, result: Any, metadata: Optional[Dict[str, Any]] = None) -> ScratchpadEntry:
        key = f"step_{step}_result"
        return self.store(key, result, entry_type="intermediate", metadata=metadata)

    def get_intermediate_result(self, step: int) -> Optional[Any]:
        return self.retrieve(f"step_{step}_result")

    def store_reasoning_chain(self, chain: List[str], metadata: Optional[Dict[str, Any]] = None) -> ScratchpadEntry:
        return self.store("reasoning_chain", chain, entry_type="chain", metadata=metadata)

    def get_reasoning_chain(self) -> List[str]:
        chain = self.retrieve("reasoning_chain")
        return chain if isinstance(chain, list) else []
