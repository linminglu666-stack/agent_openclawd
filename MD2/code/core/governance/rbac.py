from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple

import asyncio

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocols.interfaces import IAuthorizer


Permission = Tuple[str, str]


@dataclass
class Role:
    name: str
    permissions: Set[Permission]


class InMemoryAuthorizer(IAuthorizer):
    def __init__(self):
        self._user_permissions: Dict[str, Set[Permission]] = {}
        self._roles: Dict[str, Role] = {}
        self._user_roles: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def check_permission(self, user_id: str, resource: str, action: str) -> bool:
        perms = await self._get_effective_permissions(user_id)
        return (resource, action) in perms or ("*", action) in perms or (resource, "*") in perms or ("*", "*") in perms

    async def get_permissions(self, user_id: str) -> List[Dict[str, Any]]:
        perms = await self._get_effective_permissions(user_id)
        return [{"resource": r, "action": a} for (r, a) in sorted(perms)]

    async def grant_permission(self, user_id: str, resource: str, action: str) -> bool:
        async with self._lock:
            if user_id not in self._user_permissions:
                self._user_permissions[user_id] = set()
            self._user_permissions[user_id].add((resource, action))
        return True

    async def revoke_permission(self, user_id: str, resource: str, action: str) -> bool:
        async with self._lock:
            if user_id not in self._user_permissions:
                return False
            if (resource, action) not in self._user_permissions[user_id]:
                return False
            self._user_permissions[user_id].remove((resource, action))
            return True

    async def add_role(self, role_name: str, permissions: List[Dict[str, str]]) -> bool:
        perms: Set[Permission] = set((p["resource"], p["action"]) for p in permissions)
        async with self._lock:
            self._roles[role_name] = Role(name=role_name, permissions=perms)
        return True

    async def assign_role(self, user_id: str, role_name: str) -> bool:
        async with self._lock:
            if role_name not in self._roles:
                return False
            if user_id not in self._user_roles:
                self._user_roles[user_id] = set()
            self._user_roles[user_id].add(role_name)
        return True

    async def unassign_role(self, user_id: str, role_name: str) -> bool:
        async with self._lock:
            if user_id not in self._user_roles or role_name not in self._user_roles[user_id]:
                return False
            self._user_roles[user_id].remove(role_name)
        return True

    async def _get_effective_permissions(self, user_id: str) -> Set[Permission]:
        async with self._lock:
            perms: Set[Permission] = set(self._user_permissions.get(user_id, set()))
            for role_name in self._user_roles.get(user_id, set()):
                role = self._roles.get(role_name)
                if role:
                    perms |= role.permissions
            return perms

