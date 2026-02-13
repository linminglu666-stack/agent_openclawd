"""
L1本地缓存
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar
import hashlib
import threading
import time


K = TypeVar('K')
V = TypeVar('V')


@dataclass
class CacheEntry(Generic[V]):
    key: str
    value: V
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    size_bytes: int = 0
    tags: List[str] = field(default_factory=list)
    
    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.created_at).total_seconds()
    
    @property
    def ttl_remaining(self) -> Optional[float]:
        if self.expires_at is None:
            return None
        remaining = (self.expires_at - datetime.now()).total_seconds()
        return max(0, remaining)


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    updates: int = 0
    
    total_size_bytes: int = 0
    entry_count: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total
    
    @property
    def miss_rate(self) -> float:
        return 1.0 - self.hit_rate
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "expirations": self.expirations,
            "updates": self.updates,
            "total_size_bytes": self.total_size_bytes,
            "entry_count": self.entry_count,
            "hit_rate": self.hit_rate,
            "miss_rate": self.miss_rate,
        }


class LRUEvictionPolicy:
    
    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
    
    def select_for_eviction(
        self,
        entries: Dict[str, CacheEntry]
    ) -> List[str]:
        sorted_entries = sorted(
            entries.items(),
            key=lambda x: x[1].last_accessed
        )
        
        evict_count = len(entries) - self.max_entries + 1
        return [k for k, _ in sorted_entries[:evict_count]]


class LFUEvictionPolicy:
    
    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
    
    def select_for_eviction(
        self,
        entries: Dict[str, CacheEntry]
    ) -> List[str]:
        sorted_entries = sorted(
            entries.items(),
            key=lambda x: (x[1].access_count, x[1].last_accessed)
        )
        
        evict_count = len(entries) - self.max_entries + 1
        return [k for k, _ in sorted_entries[:evict_count]]


class TTLPolicy:
    
    def __init__(self, default_ttl_seconds: int = 300):
        self.default_ttl_seconds = default_ttl_seconds
    
    def get_expired_keys(self, entries: Dict[str, CacheEntry]) -> List[str]:
        return [k for k, v in entries.items() if v.is_expired]


class L1LocalCache:
    
    def __init__(
        self,
        max_entries: int = 10000,
        max_size_bytes: int = 100 * 1024 * 1024,
        default_ttl_seconds: int = 300,
        eviction_policy: str = "lru"
    ):
        self.max_entries = max_entries
        self.max_size_bytes = max_size_bytes
        self.default_ttl_seconds = default_ttl_seconds
        
        self._entries: Dict[str, CacheEntry] = {}
        self._tag_index: Dict[str, set] = {}
        self._stats = CacheStats()
        self._lock = threading.RLock()
        self._listeners: List[Callable] = []
        
        if eviction_policy == "lru":
            self._eviction_policy = LRUEvictionPolicy(max_entries)
        else:
            self._eviction_policy = LFUEvictionPolicy(max_entries)
        
        self._ttl_policy = TTLPolicy(default_ttl_seconds)
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._entries.get(key)
            
            if entry is None:
                self._stats.misses += 1
                return None
            
            if entry.is_expired:
                self._remove_entry(key)
                self._stats.misses += 1
                self._stats.expirations += 1
                return None
            
            entry.last_accessed = datetime.now()
            entry.access_count += 1
            
            self._stats.hits += 1
            return entry.value
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        with self._lock:
            ttl = ttl_seconds or self.default_ttl_seconds
            
            expires_at = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None
            
            size_bytes = self._estimate_size(value)
            
            entry = CacheEntry(
                key=key,
                value=value,
                expires_at=expires_at,
                size_bytes=size_bytes,
                tags=tags or [],
            )
            
            if key in self._entries:
                self._remove_from_tag_index(key, self._entries[key].tags)
                old_entry = self._entries[key]
                self._stats.total_size_bytes -= old_entry.size_bytes
            else:
                self._stats.entry_count += 1
            
            self._entries[key] = entry
            self._add_to_tag_index(key, entry.tags)
            
            self._stats.total_size_bytes += size_bytes
            self._stats.updates += 1
            
            self._enforce_limits()
            
            return True
    
    def delete(self, key: str) -> bool:
        with self._lock:
            if key not in self._entries:
                return False
            
            self._remove_entry(key)
            return True
    
    def invalidate(self, key: str):
        with self._lock:
            if key in self._entries:
                self._remove_entry(key)
                self._notify_listeners("invalidate", key)
    
    def invalidate_by_tag(self, tag: str) -> int:
        with self._lock:
            keys = self._tag_index.get(tag, set())
            count = 0
            
            for key in list(keys):
                if key in self._entries:
                    self._remove_entry(key)
                    count += 1
            
            return count
    
    def invalidate_all(self):
        with self._lock:
            keys = list(self._entries.keys())
            for key in keys:
                self._remove_entry(key)
            
            self._notify_listeners("invalidate_all", len(keys))
    
    def exists(self, key: str) -> bool:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return False
            if entry.is_expired:
                self._remove_entry(key)
                return False
            return True
    
    def get_ttl(self, key: str) -> Optional[float]:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or entry.is_expired:
                return None
            return entry.ttl_remaining
    
    def refresh_ttl(self, key: str, ttl_seconds: Optional[int] = None):
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return False
            
            ttl = ttl_seconds or self.default_ttl_seconds
            entry.expires_at = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None
            return True
    
    def get_or_set(
        self,
        key: str,
        loader: Callable[[], Any],
        ttl_seconds: Optional[int] = None
    ) -> Any:
        value = self.get(key)
        if value is not None:
            return value
        
        value = loader()
        self.set(key, value, ttl_seconds)
        return value
    
    def _remove_entry(self, key: str):
        if key in self._entries:
            entry = self._entries[key]
            self._stats.total_size_bytes -= entry.size_bytes
            self._stats.entry_count -= 1
            self._remove_from_tag_index(key, entry.tags)
            del self._entries[key]
    
    def _add_to_tag_index(self, key: str, tags: List[str]):
        for tag in tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(key)
    
    def _remove_from_tag_index(self, key: str, tags: List[str]):
        for tag in tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(key)
                if not self._tag_index[tag]:
                    del self._tag_index[tag]
    
    def _enforce_limits(self):
        while len(self._entries) > self.max_entries:
            keys_to_evict = self._eviction_policy.select_for_eviction(self._entries)
            for key in keys_to_evict:
                self._remove_entry(key)
                self._stats.evictions += 1
        
        while self._stats.total_size_bytes > self.max_size_bytes:
            keys_to_evict = self._eviction_policy.select_for_eviction(self._entries)
            if not keys_to_evict:
                break
            for key in keys_to_evict[:1]:
                self._remove_entry(key)
                self._stats.evictions += 1
    
    def cleanup_expired(self) -> int:
        with self._lock:
            expired_keys = self._ttl_policy.get_expired_keys(self._entries)
            
            for key in expired_keys:
                self._remove_entry(key)
                self._stats.expirations += 1
            
            return len(expired_keys)
    
    def _estimate_size(self, value: Any) -> int:
        try:
            import sys
            return sys.getsizeof(value)
        except Exception:
            return 100
    
    def get_stats(self) -> CacheStats:
        with self._lock:
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                expirations=self._stats.expirations,
                updates=self._stats.updates,
                total_size_bytes=self._stats.total_size_bytes,
                entry_count=self._stats.entry_count,
            )
    
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
