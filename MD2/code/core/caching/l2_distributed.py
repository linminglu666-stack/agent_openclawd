"""
L2分布式缓存
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
import asyncio
import json
import threading


@dataclass
class DistributedCacheEntry:
    key: str
    value: Any
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    node_id: str = ""
    checksum: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "node_id": self.node_id,
            "checksum": self.checksum,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DistributedCacheEntry":
        return cls(
            key=data["key"],
            value=data["value"],
            version=data.get("version", 1),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            node_id=data.get("node_id", ""),
            checksum=data.get("checksum", ""),
        )


@dataclass
class L2Stats:
    hits: int = 0
    misses: int = 0
    writes: int = 0
    deletes: int = 0
    invalidations: int = 0
    
    sync_errors: int = 0
    last_sync: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "writes": self.writes,
            "deletes": self.deletes,
            "invalidations": self.invalidations,
            "sync_errors": self.sync_errors,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
        }


class L2DistributedCache:
    
    def __init__(
        self,
        node_id: str = "node-1",
        default_ttl_seconds: int = 3600,
        max_key_size: int = 1024,
        max_value_size: int = 10 * 1024 * 1024,
    ):
        self.node_id = node_id
        self.default_ttl_seconds = default_ttl_seconds
        self.max_key_size = max_key_size
        self.max_value_size = max_value_size
        
        self._store: Dict[str, DistributedCacheEntry] = {}
        self._version_counter = 0
        self._stats = L2Stats()
        self._lock = threading.RLock()
        self._listeners: List[Callable] = []
        
        self._sync_handlers: Dict[str, Callable] = {}
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            
            if entry is None:
                self._stats.misses += 1
                return None
            
            if entry.expires_at and datetime.now() > entry.expires_at:
                del self._store[key]
                self._stats.misses += 1
                return None
            
            self._stats.hits += 1
            return entry.value
    
    async def get_async(self, key: str) -> Optional[Any]:
        return self.get(key)
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        broadcast: bool = True
    ) -> bool:
        with self._lock:
            if len(key) > self.max_key_size:
                return False
            
            ttl = ttl_seconds or self.default_ttl_seconds
            expires_at = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None
            
            self._version_counter += 1
            
            entry = DistributedCacheEntry(
                key=key,
                value=value,
                version=self._version_counter,
                expires_at=expires_at,
                node_id=self.node_id,
                checksum=self._compute_checksum(value),
            )
            
            self._store[key] = entry
            self._stats.writes += 1
            
            if broadcast:
                self._notify_listeners("write", entry.to_dict())
            
            return True
    
    async def set_async(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        return self.set(key, value, ttl_seconds)
    
    def delete(self, key: str, broadcast: bool = True) -> bool:
        with self._lock:
            if key not in self._store:
                return False
            
            del self._store[key]
            self._stats.deletes += 1
            
            if broadcast:
                self._notify_listeners("delete", {"key": key, "node_id": self.node_id})
            
            return True
    
    def invalidate(self, key: str, source_node: Optional[str] = None):
        with self._lock:
            if key in self._store:
                del self._store[key]
                self._stats.invalidations += 1
                
                if source_node and source_node != self.node_id:
                    self._stats.last_sync = datetime.now()
    
    def apply_invalidation(self, key: str, source_node: str):
        self.invalidate(key, source_node)
        self._notify_listeners("invalidated", {"key": key, "source": source_node})
    
    def sync_entry(self, entry_data: Dict[str, Any], source_node: str) -> bool:
        with self._lock:
            try:
                incoming = DistributedCacheEntry.from_dict(entry_data)
                existing = self._store.get(incoming.key)
                
                if existing and existing.version >= incoming.version:
                    return False
                
                self._store[incoming.key] = incoming
                self._stats.last_sync = datetime.now()
                return True
                
            except Exception:
                self._stats.sync_errors += 1
                return False
    
    def get_version(self, key: str) -> Optional[int]:
        with self._lock:
            entry = self._store.get(key)
            return entry.version if entry else None
    
    def compare_and_set(
        self,
        key: str,
        expected_version: int,
        new_value: Any,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        with self._lock:
            entry = self._store.get(key)
            
            if entry is None or entry.version != expected_version:
                return False
            
            return self.set(key, new_value, ttl_seconds)
    
    def get_all_keys(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())
    
    def get_entries_by_node(self, node_id: str) -> List[DistributedCacheEntry]:
        with self._lock:
            return [
                e for e in self._store.values()
                if e.node_id == node_id
            ]
    
    def cleanup_expired(self) -> int:
        with self._lock:
            now = datetime.now()
            expired_keys = [
                k for k, v in self._store.items()
                if v.expires_at and now > v.expires_at
            ]
            
            for key in expired_keys:
                del self._store[key]
            
            return len(expired_keys)
    
    def _compute_checksum(self, value: Any) -> str:
        import hashlib
        try:
            data = json.dumps(value, sort_keys=True)
            return hashlib.md5(data.encode()).hexdigest()[:16]
        except Exception:
            return ""
    
    def get_stats(self) -> L2Stats:
        with self._lock:
            return L2Stats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                writes=self._stats.writes,
                deletes=self._stats.deletes,
                invalidations=self._stats.invalidations,
                sync_errors=self._stats.sync_errors,
                last_sync=self._stats.last_sync,
            )
    
    def register_sync_handler(self, event_type: str, handler: Callable):
        self._sync_handlers[event_type] = handler
    
    def add_listener(self, callback: Callable):
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable):
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self, event: str, data: Any):
        for callback in self._listeners:
            try:
                callback(event, data)
            except Exception:
                pass
