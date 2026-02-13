"""
多级缓存管理器
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import threading

from .l1_local import L1LocalCache, CacheStats as L1Stats
from .l2_distributed import L2DistributedCache, L2Stats
from .invalidation import InvalidationBroadcaster, InvalidationEvent, InvalidationType


@dataclass
class CacheConfig:
    l1_max_entries: int = 10000
    l1_max_size_bytes: int = 100 * 1024 * 1024
    l1_default_ttl_seconds: int = 300
    
    l2_default_ttl_seconds: int = 3600
    
    enable_l1: bool = True
    enable_l2: bool = True
    
    read_through: bool = True
    write_through: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "l1_max_entries": self.l1_max_entries,
            "l1_max_size_bytes": self.l1_max_size_bytes,
            "l1_default_ttl_seconds": self.l1_default_ttl_seconds,
            "l2_default_ttl_seconds": self.l2_default_ttl_seconds,
            "enable_l1": self.enable_l1,
            "enable_l2": self.enable_l2,
            "read_through": self.read_through,
            "write_through": self.write_through,
        }


@dataclass
class MultiTierStats:
    l1_stats: L1Stats
    l2_stats: L2Stats
    
    total_hits: int = 0
    total_misses: int = 0
    l1_hits: int = 0
    l2_hits: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "l1": self.l1_stats.to_dict(),
            "l2": self.l2_stats.to_dict(),
            "total_hits": self.total_hits,
            "total_misses": self.total_misses,
            "l1_hits": self.l1_hits,
            "l2_hits": self.l2_hits,
            "overall_hit_rate": self.total_hits / (self.total_hits + self.total_misses) if (self.total_hits + self.total_misses) > 0 else 0,
        }


class MultiTierCacheManager:
    
    def __init__(
        self,
        config: Optional[CacheConfig] = None,
        node_id: str = "node-1"
    ):
        self.config = config or CacheConfig()
        self.node_id = node_id
        
        self._l1: Optional[L1LocalCache] = None
        self._l2: Optional[L2DistributedCache] = None
        self._broadcaster: Optional[InvalidationBroadcaster] = None
        
        if self.config.enable_l1:
            self._l1 = L1LocalCache(
                max_entries=self.config.l1_max_entries,
                max_size_bytes=self.config.l1_max_size_bytes,
                default_ttl_seconds=self.config.l1_default_ttl_seconds,
            )
        
        if self.config.enable_l2:
            self._l2 = L2DistributedCache(
                node_id=node_id,
                default_ttl_seconds=self.config.l2_default_ttl_seconds,
            )
        
        self._broadcaster = InvalidationBroadcaster(node_id)
        
        self._setup_invalidation_handling()
        
        self._lock = threading.RLock()
        self._listeners: List[Callable] = []
        
        self._l1_hits = 0
        self._l2_hits = 0
        self._total_misses = 0
    
    def _setup_invalidation_handling(self):
        if self._broadcaster:
            self._broadcaster.register_handler(self._handle_invalidation_event)
    
    def _handle_invalidation_event(self, event: InvalidationEvent):
        if not self._l1:
            return
        
        if event.invalidation_type == InvalidationType.KEY:
            self._l1.invalidate(event.target)
        elif event.invalidation_type == InvalidationType.TAG:
            self._l1.invalidate_by_tag(event.target)
        elif event.invalidation_type == InvalidationType.PREFIX:
            self._invalidate_by_prefix(event.target)
        elif event.invalidation_type == InvalidationType.ALL:
            self._l1.invalidate_all()
    
    def _invalidate_by_prefix(self, prefix: str):
        if not self._l1:
            return
        
        keys = list(self._l1._entries.keys())
        for key in keys:
            if key.startswith(prefix):
                self._l1.invalidate(key)
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if self._l1:
                value = self._l1.get(key)
                if value is not None:
                    self._l1_hits += 1
                    return value
            
            if self._l2:
                value = self._l2.get(key)
                if value is not None:
                    self._l2_hits += 1
                    
                    if self._l1 and self.config.read_through:
                        self._l1.set(key, value)
                    
                    return value
            
            self._total_misses += 1
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        with self._lock:
            l1_ttl = ttl_seconds or self.config.l1_default_ttl_seconds
            l2_ttl = ttl_seconds or self.config.l2_default_ttl_seconds
            
            if self._l1:
                self._l1.set(key, value, l1_ttl, tags)
            
            if self._l2 and self.config.write_through:
                self._l2.set(key, value, l2_ttl)
            
            return True
    
    def delete(self, key: str) -> bool:
        with self._lock:
            deleted = False
            
            if self._l1:
                deleted = self._l1.delete(key) or deleted
            
            if self._l2:
                deleted = self._l2.delete(key) or deleted
            
            if deleted:
                self._broadcaster.broadcast_key_invalidation(key)
            
            return deleted
    
    def invalidate(self, key: str):
        with self._lock:
            if self._l1:
                self._l1.invalidate(key)
            
            if self._l2:
                self._l2.invalidate(key)
            
            self._broadcaster.broadcast_key_invalidation(key)
    
    def invalidate_by_tag(self, tag: str):
        with self._lock:
            if self._l1:
                self._l1.invalidate_by_tag(tag)
            
            self._broadcaster.broadcast_tag_invalidation(tag)
    
    def invalidate_by_prefix(self, prefix: str):
        with self._lock:
            self._invalidate_by_prefix(prefix)
            self._broadcaster.broadcast_prefix_invalidation(prefix)
    
    def invalidate_all(self):
        with self._lock:
            if self._l1:
                self._l1.invalidate_all()
            
            self._broadcaster.broadcast_all_invalidation()
    
    def get_or_set(
        self,
        key: str,
        loader: Callable[[], Any],
        ttl_seconds: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> Any:
        value = self.get(key)
        if value is not None:
            return value
        
        value = loader()
        self.set(key, value, ttl_seconds, tags)
        return value
    
    def exists(self, key: str) -> bool:
        with self._lock:
            if self._l1 and self._l1.exists(key):
                return True
            
            if self._l2:
                value = self._l2.get(key)
                return value is not None
            
            return False
    
    def get_ttl(self, key: str) -> Optional[float]:
        with self._lock:
            if self._l1:
                ttl = self._l1.get_ttl(key)
                if ttl is not None:
                    return ttl
            
            return None
    
    def refresh_ttl(self, key: str, ttl_seconds: Optional[int] = None) -> bool:
        with self._lock:
            refreshed = False
            
            if self._l1:
                refreshed = self._l1.refresh_ttl(key, ttl_seconds) or refreshed
            
            return refreshed
    
    def cleanup_expired(self) -> Dict[str, int]:
        result = {}
        
        if self._l1:
            result["l1_expired"] = self._l1.cleanup_expired()
        
        if self._l2:
            result["l2_expired"] = self._l2.cleanup_expired()
        
        return result
    
    def get_stats(self) -> MultiTierStats:
        l1_stats = self._l1.get_stats() if self._l1 else None
        l2_stats = self._l2.get_stats() if self._l2 else None
        
        from .l1_local import CacheStats as L1CacheStats
        from .l2_distributed import L2Stats as L2CacheStats
        
        return MultiTierStats(
            l1_stats=l1_stats or L1CacheStats(),
            l2_stats=l2_stats or L2CacheStats(),
            total_hits=self._l1_hits + self._l2_hits,
            total_misses=self._total_misses,
            l1_hits=self._l1_hits,
            l2_hits=self._l2_hits,
        )
    
    def get_l1(self) -> Optional[L1LocalCache]:
        return self._l1
    
    def get_l2(self) -> Optional[L2DistributedCache]:
        return self._l2
    
    def get_broadcaster(self) -> Optional[InvalidationBroadcaster]:
        return self._broadcaster
    
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
