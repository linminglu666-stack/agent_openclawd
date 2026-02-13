"""
租户管理核心
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import threading
import uuid


class TenantStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"
    TRIAL = "trial"


class Priority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class TenantQuota:
    max_requests_per_minute: int = 100
    max_requests_per_hour: int = 1000
    max_requests_per_day: int = 10000
    
    max_concurrent_tasks: int = 10
    max_queue_depth: int = 100
    
    max_tokens_per_day: int = 1000000
    max_storage_mb: int = 1024
    
    max_agents: int = 5
    max_workflows: int = 20
    
    cost_budget_daily: float = 100.0
    cost_budget_monthly: float = 2000.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_requests_per_minute": self.max_requests_per_minute,
            "max_requests_per_hour": self.max_requests_per_hour,
            "max_requests_per_day": self.max_requests_per_day,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "max_queue_depth": self.max_queue_depth,
            "max_tokens_per_day": self.max_tokens_per_day,
            "max_storage_mb": self.max_storage_mb,
            "max_agents": self.max_agents,
            "max_workflows": self.max_workflows,
            "cost_budget_daily": self.cost_budget_daily,
            "cost_budget_monthly": self.cost_budget_monthly,
        }


@dataclass
class TenantConfig:
    priority: Priority = Priority.MEDIUM
    
    enable_priority_queue: bool = True
    enable_cost_tracking: bool = True
    enable_audit_log: bool = True
    
    data_retention_days: int = 30
    max_trace_history: int = 1000
    
    allowed_providers: List[str] = field(default_factory=list)
    blocked_features: List[str] = field(default_factory=list)
    
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "priority": self.priority.value,
            "enable_priority_queue": self.enable_priority_queue,
            "enable_cost_tracking": self.enable_cost_tracking,
            "enable_audit_log": self.enable_audit_log,
            "data_retention_days": self.data_retention_days,
            "max_trace_history": self.max_trace_history,
            "allowed_providers": self.allowed_providers,
            "blocked_features": self.blocked_features,
            "custom_settings": self.custom_settings,
        }


@dataclass
class TenantUsage:
    requests_minute: int = 0
    requests_hour: int = 0
    requests_day: int = 0
    
    concurrent_tasks: int = 0
    queue_depth: int = 0
    
    tokens_used_today: int = 0
    storage_used_mb: float = 0.0
    
    active_agents: int = 0
    active_workflows: int = 0
    
    cost_today: float = 0.0
    cost_month: float = 0.0
    
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "requests_minute": self.requests_minute,
            "requests_hour": self.requests_hour,
            "requests_day": self.requests_day,
            "concurrent_tasks": self.concurrent_tasks,
            "queue_depth": self.queue_depth,
            "tokens_used_today": self.tokens_used_today,
            "storage_used_mb": self.storage_used_mb,
            "active_agents": self.active_agents,
            "active_workflows": self.active_workflows,
            "cost_today": self.cost_today,
            "cost_month": self.cost_month,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class Tenant:
    tenant_id: str
    name: str
    status: TenantStatus
    
    quota: TenantQuota = field(default_factory=TenantQuota)
    config: TenantConfig = field(default_factory=TenantConfig)
    usage: TenantUsage = field(default_factory=TenantUsage)
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(cls, name: str, **kwargs) -> "Tenant":
        return cls(
            tenant_id=f"tenant-{uuid.uuid4().hex[:8]}",
            name=name,
            status=TenantStatus.ACTIVE,
            **kwargs
        )
    
    def is_within_quota(self) -> bool:
        if self.usage.requests_minute >= self.quota.max_requests_per_minute:
            return False
        if self.usage.requests_hour >= self.quota.max_requests_per_hour:
            return False
        if self.usage.requests_day >= self.quota.max_requests_per_day:
            return False
        if self.usage.concurrent_tasks >= self.quota.max_concurrent_tasks:
            return False
        if self.usage.cost_today >= self.quota.cost_budget_daily:
            return False
        if self.usage.cost_month >= self.quota.cost_budget_monthly:
            return False
        return True
    
    def check_quota(self, resource: str) -> tuple[bool, str]:
        quota_checks = {
            "requests_minute": (self.usage.requests_minute, self.quota.max_requests_per_minute),
            "requests_hour": (self.usage.requests_hour, self.quota.max_requests_per_hour),
            "requests_day": (self.usage.requests_day, self.quota.max_requests_per_day),
            "concurrent_tasks": (self.usage.concurrent_tasks, self.quota.max_concurrent_tasks),
            "tokens": (self.usage.tokens_used_today, self.quota.max_tokens_per_day),
            "storage": (self.usage.storage_used_mb, self.quota.max_storage_mb),
            "cost_daily": (self.usage.cost_today, self.quota.cost_budget_daily),
            "cost_monthly": (self.usage.cost_month, self.quota.cost_budget_monthly),
        }
        
        if resource in quota_checks:
            used, limit = quota_checks[resource]
            if used >= limit:
                return False, f"Quota exceeded for {resource}: {used}/{limit}"
            return True, f"Quota available for {resource}: {used}/{limit}"
        
        return True, "Resource not tracked"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "status": self.status.value,
            "quota": self.quota.to_dict(),
            "config": self.config.to_dict(),
            "usage": self.usage.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


class TenantManager:
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
        
        self._tenants: Dict[str, Tenant] = {}
        self._name_index: Dict[str, str] = {}
        self._listeners: List = []
        self._initialized = True
    
    def create_tenant(
        self,
        name: str,
        quota: Optional[TenantQuota] = None,
        config: Optional[TenantConfig] = None,
        metadata: Optional[Dict] = None
    ) -> Tenant:
        if name in self._name_index:
            raise ValueError(f"Tenant with name '{name}' already exists")
        
        tenant = Tenant.create(
            name=name,
            quota=quota or TenantQuota(),
            config=config or TenantConfig(),
            metadata=metadata or {}
        )
        
        self._tenants[tenant.tenant_id] = tenant
        self._name_index[name] = tenant.tenant_id
        
        self._notify_listeners("created", tenant)
        return tenant
    
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id)
    
    def get_tenant_by_name(self, name: str) -> Optional[Tenant]:
        tenant_id = self._name_index.get(name)
        if tenant_id:
            return self._tenants.get(tenant_id)
        return None
    
    def update_tenant(self, tenant_id: str, **kwargs) -> bool:
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        for key, value in kwargs.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        
        tenant.updated_at = datetime.now()
        self._notify_listeners("updated", tenant)
        return True
    
    def update_usage(self, tenant_id: str, **kwargs) -> bool:
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        for key, value in kwargs.items():
            if hasattr(tenant.usage, key):
                setattr(tenant.usage, key, value)
        
        tenant.usage.last_updated = datetime.now()
        return True
    
    def delete_tenant(self, tenant_id: str) -> bool:
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        del self._tenants[tenant_id]
        if tenant.name in self._name_index:
            del self._name_index[tenant.name]
        
        self._notify_listeners("deleted", tenant)
        return True
    
    def suspend_tenant(self, tenant_id: str) -> bool:
        return self.update_tenant(tenant_id, status=TenantStatus.SUSPENDED)
    
    def activate_tenant(self, tenant_id: str) -> bool:
        return self.update_tenant(tenant_id, status=TenantStatus.ACTIVE)
    
    def list_tenants(self, status: Optional[TenantStatus] = None) -> List[Tenant]:
        tenants = list(self._tenants.values())
        if status:
            tenants = [t for t in tenants if t.status == status]
        return tenants
    
    def get_active_tenants(self) -> List[Tenant]:
        return self.list_tenants(status=TenantStatus.ACTIVE)
    
    def check_tenant_quota(self, tenant_id: str, resource: str) -> tuple[bool, str]:
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False, "Tenant not found"
        
        if tenant.status != TenantStatus.ACTIVE:
            return False, f"Tenant is {tenant.status.value}"
        
        return tenant.check_quota(resource)
    
    def add_listener(self, callback):
        self._listeners.append(callback)
    
    def remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self, event: str, tenant: Tenant):
        for callback in self._listeners:
            try:
                callback(event, tenant)
            except Exception:
                pass
    
    def get_stats(self) -> Dict[str, Any]:
        tenants = list(self._tenants.values())
        return {
            "total_tenants": len(tenants),
            "active_tenants": sum(1 for t in tenants if t.status == TenantStatus.ACTIVE),
            "suspended_tenants": sum(1 for t in tenants if t.status == TenantStatus.SUSPENDED),
            "trial_tenants": sum(1 for t in tenants if t.status == TenantStatus.TRIAL),
            "total_cost_today": sum(t.usage.cost_today for t in tenants),
            "total_cost_month": sum(t.usage.cost_month for t in tenants),
        }
