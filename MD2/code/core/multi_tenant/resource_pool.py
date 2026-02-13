"""
资源池管理
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import threading


class ResourceState(Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"
    DRAINED = "drained"


@dataclass
class Resource:
    resource_id: str
    resource_type: str
    state: ResourceState = ResourceState.AVAILABLE
    
    capacity: float = 1.0
    used: float = 0.0
    
    tenant_id: Optional[str] = None
    allocated_at: Optional[datetime] = None
    
    priority: int = 5
    tags: Dict[str, str] = field(default_factory=dict)
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def available_capacity(self) -> float:
        return max(0, self.capacity - self.used)
    
    @property
    def utilization(self) -> float:
        if self.capacity == 0:
            return 0.0
        return self.used / self.capacity
    
    @property
    def is_available(self) -> bool:
        return self.state == ResourceState.AVAILABLE and self.available_capacity > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "state": self.state.value,
            "capacity": self.capacity,
            "used": self.used,
            "available_capacity": self.available_capacity,
            "utilization": self.utilization,
            "tenant_id": self.tenant_id,
            "allocated_at": self.allocated_at.isoformat() if self.allocated_at else None,
            "priority": self.priority,
            "tags": self.tags,
        }


@dataclass
class Allocation:
    allocation_id: str
    resource_id: str
    tenant_id: str
    
    amount: float
    allocated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    status: str = "active"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allocation_id": self.allocation_id,
            "resource_id": self.resource_id,
            "tenant_id": self.tenant_id,
            "amount": self.amount,
            "allocated_at": self.allocated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status,
        }


class ResourcePool:
    
    def __init__(self, pool_id: str, resource_type: str):
        self.pool_id = pool_id
        self.resource_type = resource_type
        self._resources: Dict[str, Resource] = {}
        self._allocations: Dict[str, Allocation] = {}
        self._tenant_allocations: Dict[str, List[str]] = {}
        self._lock = threading.Lock()
        self._listeners: List[Callable] = []
    
    def add_resource(self, resource: Resource) -> bool:
        with self._lock:
            if resource.resource_id in self._resources:
                return False
            
            self._resources[resource.resource_id] = resource
            self._notify_listeners("resource_added", resource)
            return True
    
    def remove_resource(self, resource_id: str) -> bool:
        with self._lock:
            if resource_id not in self._resources:
                return False
            
            resource = self._resources[resource_id]
            
            if resource.state != ResourceState.AVAILABLE:
                return False
            
            del self._resources[resource_id]
            self._notify_listeners("resource_removed", resource)
            return True
    
    def allocate(
        self,
        tenant_id: str,
        amount: float,
        preferred_resource_id: Optional[str] = None
    ) -> Optional[Allocation]:
        import uuid
        
        with self._lock:
            target_resource = None
            
            if preferred_resource_id:
                target_resource = self._resources.get(preferred_resource_id)
                if not target_resource or not target_resource.is_available:
                    target_resource = None
            
            if not target_resource:
                for resource in self._resources.values():
                    if resource.is_available and resource.available_capacity >= amount:
                        if target_resource is None or resource.utilization < target_resource.utilization:
                            target_resource = resource
            
            if not target_resource:
                self._notify_listeners("allocation_failed", {
                    "tenant_id": tenant_id,
                    "amount": amount,
                    "reason": "no_available_resource",
                })
                return None
            
            allocation = Allocation(
                allocation_id=f"alloc-{uuid.uuid4().hex[:8]}",
                resource_id=target_resource.resource_id,
                tenant_id=tenant_id,
                amount=amount,
            )
            
            target_resource.used += amount
            target_resource.tenant_id = tenant_id
            target_resource.allocated_at = datetime.now()
            
            if target_resource.available_capacity == 0:
                target_resource.state = ResourceState.IN_USE
            
            self._allocations[allocation.allocation_id] = allocation
            
            if tenant_id not in self._tenant_allocations:
                self._tenant_allocations[tenant_id] = []
            self._tenant_allocations[tenant_id].append(allocation.allocation_id)
            
            self._notify_listeners("allocated", allocation)
            return allocation
    
    def release(self, allocation_id: str) -> bool:
        with self._lock:
            allocation = self._allocations.get(allocation_id)
            if not allocation or allocation.status != "active":
                return False
            
            resource = self._resources.get(allocation.resource_id)
            if resource:
                resource.used = max(0, resource.used - allocation.amount)
                if resource.available_capacity > 0:
                    resource.state = ResourceState.AVAILABLE
            
            allocation.status = "released"
            
            if allocation.tenant_id in self._tenant_allocations:
                if allocation_id in self._tenant_allocations[allocation.tenant_id]:
                    self._tenant_allocations[allocation.tenant_id].remove(allocation_id)
            
            self._notify_listeners("released", allocation)
            return True
    
    def get_resource(self, resource_id: str) -> Optional[Resource]:
        return self._resources.get(resource_id)
    
    def get_available_resources(self) -> List[Resource]:
        return [r for r in self._resources.values() if r.is_available]
    
    def get_tenant_allocations(self, tenant_id: str) -> List[Allocation]:
        allocation_ids = self._tenant_allocations.get(tenant_id, [])
        return [
            self._allocations[aid]
            for aid in allocation_ids
            if aid in self._allocations
        ]
    
    def get_total_capacity(self) -> float:
        return sum(r.capacity for r in self._resources.values())
    
    def get_available_capacity(self) -> float:
        return sum(r.available_capacity for r in self._resources.values())
    
    def get_utilization(self) -> float:
        total = self.get_total_capacity()
        if total == 0:
            return 0.0
        used = sum(r.used for r in self._resources.values())
        return used / total
    
    def drain(self, resource_id: str) -> bool:
        with self._lock:
            resource = self._resources.get(resource_id)
            if not resource:
                return False
            
            resource.state = ResourceState.DRAINED
            self._notify_listeners("drained", resource)
            return True
    
    def set_maintenance(self, resource_id: str, maintenance: bool = True) -> bool:
        with self._lock:
            resource = self._resources.get(resource_id)
            if not resource:
                return False
            
            if maintenance and resource.state != ResourceState.AVAILABLE:
                return False
            
            resource.state = ResourceState.MAINTENANCE if maintenance else ResourceState.AVAILABLE
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "pool_id": self.pool_id,
            "resource_type": self.resource_type,
            "total_resources": len(self._resources),
            "available_resources": len(self.get_available_resources()),
            "total_capacity": self.get_total_capacity(),
            "available_capacity": self.get_available_capacity(),
            "utilization": self.get_utilization(),
            "active_allocations": sum(
                1 for a in self._allocations.values() if a.status == "active"
            ),
            "tenants_served": len(self._tenant_allocations),
        }
    
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


class ResourcePoolManager:
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._pools: Dict[str, ResourcePool] = {}
        self._listeners: List[Callable] = []
        self._initialized = True
    
    def create_pool(self, pool_id: str, resource_type: str) -> ResourcePool:
        if pool_id in self._pools:
            raise ValueError(f"Pool '{pool_id}' already exists")
        
        pool = ResourcePool(pool_id, resource_type)
        self._pools[pool_id] = pool
        return pool
    
    def get_pool(self, pool_id: str) -> Optional[ResourcePool]:
        return self._pools.get(pool_id)
    
    def get_pools_by_type(self, resource_type: str) -> List[ResourcePool]:
        return [
            p for p in self._pools.values()
            if p.resource_type == resource_type
        ]
    
    def allocate_from_any(
        self,
        resource_type: str,
        tenant_id: str,
        amount: float
    ) -> Optional[tuple[str, Allocation]]:
        pools = self.get_pools_by_type(resource_type)
        
        pools.sort(key=lambda p: p.get_utilization())
        
        for pool in pools:
            allocation = pool.allocate(tenant_id, amount)
            if allocation:
                return pool.pool_id, allocation
        
        return None
    
    def get_global_stats(self) -> Dict[str, Any]:
        pool_stats = {pid: pool.get_stats() for pid, pool in self._pools.items()}
        
        return {
            "total_pools": len(self._pools),
            "pools": pool_stats,
            "resource_types": list(set(p.resource_type for p in self._pools.values())),
        }
