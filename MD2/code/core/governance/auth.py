from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import uuid
import asyncio

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocols.interfaces import IAuthProvider


@dataclass
class TokenRecord:
    token: str
    user: Dict[str, Any]
    expires_at: datetime
    refresh_token: Optional[str] = None


class InMemoryAuthProvider(IAuthProvider):
    def __init__(self, token_ttl_seconds: int = 3600, refresh_ttl_seconds: int = 86400):
        self._token_ttl = int(token_ttl_seconds)
        self._refresh_ttl = int(refresh_ttl_seconds)
        self._tokens: Dict[str, TokenRecord] = {}
        self._refresh_index: Dict[str, TokenRecord] = {}
        self._lock = asyncio.Lock()

    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        user_id = credentials.get("user_id") or credentials.get("username")
        if not user_id:
            return None

        now = datetime.utcnow()
        token = str(uuid.uuid4())
        refresh_token = str(uuid.uuid4())
        record = TokenRecord(
            token=token,
            user={"user_id": str(user_id), "roles": credentials.get("roles", [])},
            expires_at=now + timedelta(seconds=self._token_ttl),
            refresh_token=refresh_token,
        )

        refresh_record = TokenRecord(
            token=refresh_token,
            user=record.user,
            expires_at=now + timedelta(seconds=self._refresh_ttl),
            refresh_token=None,
        )

        async with self._lock:
            self._tokens[token] = record
            self._refresh_index[refresh_token] = refresh_record

        return {
            "token": token,
            "refresh_token": refresh_token,
            "expires_at": record.expires_at.isoformat(),
            "user": record.user,
        }

    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            record = self._tokens.get(token)
        if not record:
            return None
        if record.expires_at < datetime.utcnow():
            await self.revoke_token(token)
            return None
        return {"token": record.token, "user": record.user, "expires_at": record.expires_at.isoformat()}

    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            record = self._refresh_index.get(refresh_token)
        if not record:
            return None
        if record.expires_at < datetime.utcnow():
            await self.revoke_token(refresh_token)
            return None
        return await self.authenticate({"user_id": record.user.get("user_id"), "roles": record.user.get("roles", [])})

    async def revoke_token(self, token: str) -> bool:
        async with self._lock:
            if token in self._tokens:
                record = self._tokens.pop(token)
                if record.refresh_token:
                    self._refresh_index.pop(record.refresh_token, None)
                return True
            if token in self._refresh_index:
                self._refresh_index.pop(token, None)
                return True
            return False

