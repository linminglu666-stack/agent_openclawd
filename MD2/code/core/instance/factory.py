from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .instance import (
    Instance,
    InstanceConfig,
    InstanceCreateRequest,
    InstanceCreateResponse,
    InstanceEndpoints,
    InstanceStatus,
    ResourceQuota,
)


@dataclass
class InstanceFactoryConfig:
    base_api_port: int = 8000
    base_ws_port: int = 9000
    health_check_interval: int = 30
    max_instances: int = 50


class InstanceFactory:
    def __init__(self, config: InstanceFactoryConfig):
        self._config = config
        self._port_allocator: Dict[str, int] = {}
        self._next_api_port = config.base_api_port
        self._next_ws_port = config.base_ws_port
        self._instance_processes: Dict[str, Any] = {}
    
    async def create(
        self,
        profession_id: str,
        name: str,
        config: InstanceConfig,
        resources: ResourceQuota,
    ) -> Instance:
        instance_id = self._generate_id()
        
        api_port = self._allocate_api_port(instance_id)
        ws_port = self._allocate_ws_port(instance_id)
        
        endpoints = InstanceEndpoints(
            api=f"http://localhost:{api_port}",
            websocket=f"ws://localhost:{ws_port}",
            health=f"http://localhost:{api_port}/health",
        )
        
        instance = Instance(
            instance_id=instance_id,
            name=name,
            profession_id=profession_id,
            status=InstanceStatus.CREATING,
            config=config,
            resources=resources,
            endpoints=endpoints,
        )
        
        await self._initialize_instance(instance)
        
        return instance
    
    async def destroy(self, instance: Instance) -> bool:
        if instance.instance_id in self._instance_processes:
            del self._instance_processes[instance.instance_id]
        
        if instance.instance_id in self._port_allocator:
            del self._port_allocator[instance.instance_id]
        
        return True
    
    async def _initialize_instance(self, instance: Instance) -> None:
        object.__setattr__(instance, "status", InstanceStatus.INITIALIZING)
        
        await asyncio.sleep(0.1)
        
        object.__setattr__(instance, "status", InstanceStatus.READY)
        object.__setattr__(
            instance,
            "updated_at",
            int(datetime.now(tz=timezone.utc).timestamp()),
        )
    
    def _generate_id(self) -> str:
        return f"claw-{uuid.uuid4().hex[:8]}"
    
    def _allocate_api_port(self, instance_id: str) -> int:
        port = self._next_api_port
        self._next_api_port += 1
        self._port_allocator[instance_id] = port
        return port
    
    def _allocate_ws_port(self, instance_id: str) -> int:
        port = self._next_ws_port
        self._next_ws_port += 1
        return port
    
    def release_port(self, instance_id: str) -> None:
        if instance_id in self._port_allocator:
            del self._port_allocator[instance_id]


class ResourceAllocator:
    DEFAULT_QUOTAS: Dict[str, ResourceQuota] = {
        "compute_heavy": ResourceQuota(
            cpu_cores=4.0,
            memory_mb=8192,
            storage_gb=50,
            max_concurrent_tasks=10,
            api_rate_limit=1000,
        ),
        "balanced": ResourceQuota(
            cpu_cores=2.0,
            memory_mb=4096,
            storage_gb=20,
            max_concurrent_tasks=5,
            api_rate_limit=500,
        ),
        "lightweight": ResourceQuota(
            cpu_cores=1.0,
            memory_mb=2048,
            storage_gb=10,
            max_concurrent_tasks=3,
            api_rate_limit=200,
        ),
    }
    
    def __init__(self, total_resources: Optional[ResourceQuota] = None):
        self._total_resources = total_resources or ResourceQuota(
            cpu_cores=16.0,
            memory_mb=32768,
            storage_gb=500,
            max_concurrent_tasks=100,
            api_rate_limit=10000,
        )
        self._allocated: Dict[str, ResourceQuota] = {}
        self._available = ResourceQuota(
            cpu_cores=self._total_resources.cpu_cores,
            memory_mb=self._total_resources.memory_mb,
            storage_gb=self._total_resources.storage_gb,
            max_concurrent_tasks=self._total_resources.max_concurrent_tasks,
            api_rate_limit=self._total_resources.api_rate_limit,
        )
    
    def allocate(
        self,
        quota: Optional[ResourceQuota] = None,
        quota_type: str = "balanced",
    ) -> ResourceQuota:
        requested = quota or self.DEFAULT_QUOTAS.get(quota_type, self.DEFAULT_QUOTAS["lightweight"])
        
        if not self._can_allocate(requested):
            raise RuntimeError("Insufficient resources available")
        
        self._available = ResourceQuota(
            cpu_cores=self._available.cpu_cores - requested.cpu_cores,
            memory_mb=self._available.memory_mb - requested.memory_mb,
            storage_gb=self._available.storage_gb - requested.storage_gb,
            max_concurrent_tasks=self._available.max_concurrent_tasks - requested.max_concurrent_tasks,
            api_rate_limit=self._available.api_rate_limit - requested.api_rate_limit,
        )
        
        return requested
    
    def release(self, quota: ResourceQuota) -> None:
        self._available = ResourceQuota(
            cpu_cores=self._available.cpu_cores + quota.cpu_cores,
            memory_mb=self._available.memory_mb + quota.memory_mb,
            storage_gb=self._available.storage_gb + quota.storage_gb,
            max_concurrent_tasks=self._available.max_concurrent_tasks + quota.max_concurrent_tasks,
            api_rate_limit=self._available.api_rate_limit + quota.api_rate_limit,
        )
    
    def _can_allocate(self, quota: ResourceQuota) -> bool:
        return (
            self._available.cpu_cores >= quota.cpu_cores
            and self._available.memory_mb >= quota.memory_mb
            and self._available.storage_gb >= quota.storage_gb
            and self._available.max_concurrent_tasks >= quota.max_concurrent_tasks
            and self._available.api_rate_limit >= quota.api_rate_limit
        )
    
    def get_available(self) -> ResourceQuota:
        return self._available
    
    def get_utilization(self) -> Dict[str, float]:
        return {
            "cpu": (self._total_resources.cpu_cores - self._available.cpu_cores)
                   / self._total_resources.cpu_cores * 100,
            "memory": (self._total_resources.memory_mb - self._available.memory_mb)
                      / self._total_resources.memory_mb * 100,
            "storage": (self._total_resources.storage_gb - self._available.storage_gb)
                       / self._total_resources.storage_gb * 100,
        }


class HealthChecker:
    def __init__(self, check_interval: int = 30):
        self._check_interval = check_interval
        self._registered: Dict[str, Instance] = {}
        self._health_status: Dict[str, Dict[str, Any]] = {}
        self._running = False
    
    async def register(self, instance: Instance) -> None:
        self._registered[instance.instance_id] = instance
        self._health_status[instance.instance_id] = {
            "last_check": 0,
            "consecutive_failures": 0,
            "is_healthy": True,
        }
    
    async def unregister(self, instance: Instance) -> None:
        if instance.instance_id in self._registered:
            del self._registered[instance.instance_id]
        if instance.instance_id in self._health_status:
            del self._health_status[instance.instance_id]
    
    async def check_health(self, instance_id: str) -> Dict[str, Any]:
        instance = self._registered.get(instance_id)
        if not instance:
            return {"error": "Instance not registered"}
        
        health_info = self._health_status.get(instance_id, {})
        
        is_healthy = instance.status not in (InstanceStatus.ERROR, InstanceStatus.TERMINATED)
        
        health_info["last_check"] = int(datetime.now(tz=timezone.utc).timestamp())
        health_info["is_healthy"] = is_healthy
        
        if not is_healthy:
            health_info["consecutive_failures"] = health_info.get("consecutive_failures", 0) + 1
        else:
            health_info["consecutive_failures"] = 0
        
        self._health_status[instance_id] = health_info
        
        return {
            "instance_id": instance_id,
            "is_healthy": is_healthy,
            "status": instance.status.value,
            "last_check": health_info["last_check"],
            "consecutive_failures": health_info["consecutive_failures"],
        }
    
    async def start_monitoring(self) -> None:
        self._running = True
        while self._running:
            for instance_id in list(self._registered.keys()):
                await self.check_health(instance_id)
            await asyncio.sleep(self._check_interval)
    
    def stop_monitoring(self) -> None:
        self._running = False
    
    def get_unhealthy_instances(self) -> List[str]:
        return [
            iid for iid, info in self._health_status.items()
            if not info.get("is_healthy", True)
        ]
