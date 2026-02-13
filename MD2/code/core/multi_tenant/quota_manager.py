"""
配额管理器
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
import threading


@dataclass
class QuotaUsage:
    resource_type: str
    tenant_id: str
    
    used: float = 0.0
    limit: float = 0.0
    
    period_start: datetime = field(default_factory=datetime.now)
    period_end: Optional[datetime] = None
    
    reservations: float = 0.0
    
    @property
    def available(self) -> float:
        return max(0, self.limit - self.used - self.reservations)
    
    @property
    def utilization(self) -> float:
        if self.limit == 0:
            return 0.0
        return self.used / self.limit
    
    @property
    def is_exceeded(self) -> bool:
        return self.used >= self.limit
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "tenant_id": self.tenant_id,
            "used": self.used,
            "limit": self.limit,
            "available": self.available,
            "reservations": self.reservations,
            "utilization": self.utilization,
            "is_exceeded": self.is_exceeded,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat() if self.period_end else None,
        }


@dataclass
class QuotaReservation:
    reservation_id: str
    tenant_id: str
    resource_type: str
    amount: float
    
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    status: str = "active"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "reservation_id": self.reservation_id,
            "tenant_id": self.tenant_id,
            "resource_type": self.resource_type,
            "amount": self.amount,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status,
        }


class QuotaManager:
    
    RESOURCE_TYPES = [
        "requests",
        "tokens",
        "storage",
        "compute_hours",
        "api_calls",
        "bandwidth",
    ]
    
    PERIOD_TYPES = {
        "minute": timedelta(minutes=1),
        "hour": timedelta(hours=1),
        "day": timedelta(days=1),
        "week": timedelta(weeks=1),
        "month": timedelta(days=30),
    }
    
    def __init__(self):
        self._quotas: Dict[str, Dict[str, QuotaUsage]] = {}
        self._reservations: Dict[str, QuotaReservation] = {}
        self._lock = threading.Lock()
        self._listeners: List[Callable] = []
    
    def set_quota(
        self,
        tenant_id: str,
        resource_type: str,
        limit: float,
        period: str = "day"
    ) -> QuotaUsage:
        with self._lock:
            if tenant_id not in self._quotas:
                self._quotas[tenant_id] = {}
            
            now = datetime.now()
            period_duration = self.PERIOD_TYPES.get(period, timedelta(days=1))
            
            quota = QuotaUsage(
                resource_type=resource_type,
                tenant_id=tenant_id,
                limit=limit,
                period_start=now,
                period_end=now + period_duration,
            )
            
            self._quotas[tenant_id][resource_type] = quota
            return quota
    
    def get_quota(self, tenant_id: str, resource_type: str) -> Optional[QuotaUsage]:
        with self._lock:
            if tenant_id not in self._quotas:
                return None
            return self._quotas[tenant_id].get(resource_type)
    
    def consume(
        self,
        tenant_id: str,
        resource_type: str,
        amount: float
    ) -> tuple[bool, QuotaUsage]:
        with self._lock:
            quota = self.get_quota(tenant_id, resource_type)
            if not quota:
                return False, None
            
            if quota.period_end and datetime.now() > quota.period_end:
                self._reset_period(quota)
            
            if quota.used + amount > quota.limit:
                self._notify_listeners(tenant_id, resource_type, "quota_exceeded", quota)
                return False, quota
            
            quota.used += amount
            
            if quota.utilization > 0.9:
                self._notify_listeners(tenant_id, resource_type, "quota_warning", quota)
            
            return True, quota
    
    def reserve(
        self,
        tenant_id: str,
        resource_type: str,
        amount: float,
        ttl_seconds: int = 300
    ) -> Optional[QuotaReservation]:
        import uuid
        
        with self._lock:
            quota = self.get_quota(tenant_id, resource_type)
            if not quota:
                return None
            
            if quota.used + quota.reservations + amount > quota.limit:
                return None
            
            reservation = QuotaReservation(
                reservation_id=f"res-{uuid.uuid4().hex[:8]}",
                tenant_id=tenant_id,
                resource_type=resource_type,
                amount=amount,
                expires_at=datetime.now() + timedelta(seconds=ttl_seconds),
            )
            
            quota.reservations += amount
            self._reservations[reservation.reservation_id] = reservation
            
            return reservation
    
    def commit_reservation(self, reservation_id: str) -> bool:
        with self._lock:
            reservation = self._reservations.get(reservation_id)
            if not reservation or reservation.status != "active":
                return False
            
            quota = self.get_quota(reservation.tenant_id, reservation.resource_type)
            if not quota:
                return False
            
            quota.used += reservation.amount
            quota.reservations -= reservation.amount
            reservation.status = "committed"
            
            return True
    
    def cancel_reservation(self, reservation_id: str) -> bool:
        with self._lock:
            reservation = self._reservations.get(reservation_id)
            if not reservation or reservation.status != "active":
                return False
            
            quota = self.get_quota(reservation.tenant_id, reservation.resource_type)
            if quota:
                quota.reservations -= reservation.amount
            
            reservation.status = "cancelled"
            return True
    
    def release(self, tenant_id: str, resource_type: str, amount: float) -> bool:
        with self._lock:
            quota = self.get_quota(tenant_id, resource_type)
            if not quota:
                return False
            
            quota.used = max(0, quota.used - amount)
            return True
    
    def get_all_quotas(self, tenant_id: str) -> Dict[str, QuotaUsage]:
        with self._lock:
            return dict(self._quotas.get(tenant_id, {}))
    
    def get_utilization_report(self, tenant_id: str) -> Dict[str, Any]:
        quotas = self.get_all_quotas(tenant_id)
        
        return {
            "tenant_id": tenant_id,
            "resources": {
                resource: {
                    "used": quota.used,
                    "limit": quota.limit,
                    "utilization": quota.utilization,
                    "available": quota.available,
                }
                for resource, quota in quotas.items()
            },
            "total_utilization": sum(q.utilization for q in quotas.values()) / len(quotas) if quotas else 0,
            "exceeded_resources": [r for r, q in quotas.items() if q.is_exceeded],
        }
    
    def _reset_period(self, quota: QuotaUsage):
        now = datetime.now()
        quota.period_start = now
        
        if quota.period_end:
            duration = quota.period_end - quota.period_start
            quota.period_end = now + duration
        
        quota.used = 0.0
        quota.reservations = 0.0
    
    def cleanup_expired_reservations(self):
        with self._lock:
            now = datetime.now()
            expired = []
            
            for res_id, reservation in self._reservations.items():
                if reservation.status == "active" and reservation.expires_at:
                    if now > reservation.expires_at:
                        expired.append(res_id)
            
            for res_id in expired:
                self.cancel_reservation(res_id)
            
            return len(expired)
    
    def add_listener(self, callback: Callable):
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable):
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(
        self,
        tenant_id: str,
        resource: str,
        event: str,
        quota: QuotaUsage
    ):
        for callback in self._listeners:
            try:
                callback(tenant_id, resource, event, quota)
            except Exception:
                pass
