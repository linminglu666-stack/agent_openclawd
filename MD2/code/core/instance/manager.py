from __future__ import annotations

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
from .factory import InstanceFactory, InstanceFactoryConfig, ResourceAllocator, HealthChecker


class InstanceManager:
    def __init__(
        self,
        factory_config: Optional[InstanceFactoryConfig] = None,
        total_resources: Optional[ResourceQuota] = None,
    ):
        self._factory = InstanceFactory(factory_config or InstanceFactoryConfig())
        self._resource_allocator = ResourceAllocator(total_resources)
        self._health_checker = HealthChecker()
        self._instances: Dict[str, Instance] = {}
        self._profession_index: Dict[str, List[str]] = {}
    
    async def create_instance(
        self,
        profession_id: str,
        name: str,
        config: Optional[InstanceConfig] = None,
        resource_quota: Optional[ResourceQuota] = None,
    ) -> Instance:
        resources = self._resource_allocator.allocate(resource_quota)
        
        instance = await self._factory.create(
            profession_id=profession_id,
            name=name,
            config=config or InstanceConfig(),
            resources=resources,
        )
        
        self._instances[instance.instance_id] = instance
        
        if profession_id not in self._profession_index:
            self._profession_index[profession_id] = []
        self._profession_index[profession_id].append(instance.instance_id)
        
        await self._health_checker.register(instance)
        
        return instance
    
    async def create_from_request(
        self,
        request: InstanceCreateRequest,
    ) -> InstanceCreateResponse:
        instance = await self.create_instance(
            profession_id=request.profession_id,
            name=request.name,
            config=request.config,
            resource_quota=request.resource_quota,
        )
        
        return InstanceCreateResponse(
            instance_id=instance.instance_id,
            status=instance.status,
            endpoints=instance.endpoints,
            created_at=instance.created_at,
        )
    
    async def destroy_instance(self, instance_id: str) -> bool:
        instance = self._instances.get(instance_id)
        if not instance:
            return False
        
        object.__setattr__(instance, "status", InstanceStatus.TERMINATING)
        
        await self._factory.destroy(instance)
        self._resource_allocator.release(instance.resources)
        await self._health_checker.unregister(instance)
        
        del self._instances[instance_id]
        
        if instance.profession_id in self._profession_index:
            if instance_id in self._profession_index[instance.profession_id]:
                self._profession_index[instance.profession_id].remove(instance_id)
        
        return True
    
    async def get_instance(self, instance_id: str) -> Optional[Instance]:
        return self._instances.get(instance_id)
    
    async def list_instances(
        self,
        profession: Optional[str] = None,
        status: Optional[InstanceStatus] = None,
    ) -> List[Instance]:
        instances = list(self._instances.values())
        
        if profession:
            instance_ids = self._profession_index.get(profession, [])
            instances = [i for i in instances if i.instance_id in instance_ids]
        
        if status:
            instances = [i for i in instances if i.status == status]
        
        return instances
    
    async def get_available_instance(
        self,
        profession_id: str,
    ) -> Optional[Instance]:
        instance_ids = self._profession_index.get(profession_id, [])
        
        for instance_id in instance_ids:
            instance = self._instances.get(instance_id)
            if instance and instance.is_available():
                return instance
        
        return None
    
    async def assign_task(
        self,
        instance_id: str,
        task_id: str,
    ) -> bool:
        instance = self._instances.get(instance_id)
        if not instance or not instance.is_available():
            return False
        
        current_tasks = list(instance.current_tasks)
        current_tasks.append(task_id)
        object.__setattr__(instance, "current_tasks", current_tasks)
        object.__setattr__(instance, "status", InstanceStatus.BUSY)
        object.__setattr__(
            instance,
            "updated_at",
            int(__import__("datetime").datetime.now(tz=__import__("datetime").timezone.utc).timestamp()),
        )
        
        return True
    
    async def complete_task(
        self,
        instance_id: str,
        task_id: str,
        success: bool = True,
    ) -> bool:
        instance = self._instances.get(instance_id)
        if not instance:
            return False
        
        current_tasks = list(instance.current_tasks)
        if task_id in current_tasks:
            current_tasks.remove(task_id)
        
        object.__setattr__(instance, "current_tasks", current_tasks)
        object.__setattr__(instance, "completed_tasks", instance.completed_tasks + 1)
        
        if not success:
            object.__setattr__(instance, "error_count", instance.error_count + 1)
        
        new_status = InstanceStatus.IDLE if current_tasks else InstanceStatus.READY
        object.__setattr__(instance, "status", new_status)
        object.__setattr__(
            instance,
            "updated_at",
            int(__import__("datetime").datetime.now(tz=__import__("datetime").timezone.utc).timestamp()),
        )
        
        return True
    
    async def update_instance_status(
        self,
        instance_id: str,
        status: InstanceStatus,
    ) -> bool:
        instance = self._instances.get(instance_id)
        if not instance:
            return False
        
        object.__setattr__(instance, "status", status)
        object.__setattr__(
            instance,
            "updated_at",
            int(__import__("datetime").datetime.now(tz=__import__("datetime").timezone.utc).timestamp()),
        )
        
        return True
    
    async def get_resource_utilization(self) -> Dict[str, Any]:
        return self._resource_allocator.get_utilization()
    
    async def get_available_resources(self) -> ResourceQuota:
        return self._resource_allocator.get_available()
    
    async def health_check(self, instance_id: str) -> Dict[str, Any]:
        return await self._health_checker.check_health(instance_id)
    
    async def get_unhealthy_instances(self) -> List[str]:
        return self._health_checker.get_unhealthy_instances()
    
    def get_instance_count(self) -> int:
        return len(self._instances)
    
    def get_profession_count(self, profession_id: str) -> int:
        return len(self._profession_index.get(profession_id, []))
