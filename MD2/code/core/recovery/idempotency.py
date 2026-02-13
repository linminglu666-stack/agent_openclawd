from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import json
import uuid
import os


@dataclass
class Lease:
    lease_id: str
    key: str
    owner: str
    expires_at: str

    def is_expired(self) -> bool:
        try:
            return datetime.fromisoformat(self.expires_at) <= datetime.utcnow()
        except Exception:
            return True


class LeaseStore:
    def __init__(self, root_dir: str):
        self._dir = Path(root_dir) / "leases"
        self._dir.mkdir(parents=True, exist_ok=True)

    def acquire(self, key: str, owner: str, ttl_sec: int = 60) -> Optional[Lease]:
        lease_path = self._dir / f"{_safe_key(key)}.json"
        existing = self._read(lease_path)
        if existing and not existing.is_expired():
            return None
        lease = Lease(lease_id=uuid.uuid4().hex, key=key, owner=owner, expires_at=(datetime.utcnow() + timedelta(seconds=ttl_sec)).isoformat())
        lease_path.write_text(json.dumps(lease.__dict__, ensure_ascii=False), encoding="utf-8")
        return lease

    def release(self, key: str, owner: str) -> bool:
        lease_path = self._dir / f"{_safe_key(key)}.json"
        existing = self._read(lease_path)
        if not existing:
            return False
        if existing.owner != owner:
            return False
        try:
            lease_path.unlink()
        except FileNotFoundError:
            pass
        return True

    def _read(self, path: Path) -> Optional[Lease]:
        if not path.exists():
            return None
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            return Lease(lease_id=str(obj.get("lease_id", "")), key=str(obj.get("key", "")), owner=str(obj.get("owner", "")), expires_at=str(obj.get("expires_at", "")))
        except Exception:
            return None


class IdempotencyStore:
    def __init__(self, root_dir: str):
        self._dir = Path(root_dir) / "idempotency"
        self._dir.mkdir(parents=True, exist_ok=True)

    def has(self, key: str) -> bool:
        return (self._dir / f"{_safe_key(key)}.json").exists()

    def put(self, key: str, value: Dict[str, Any]) -> bool:
        path = self._dir / f"{_safe_key(key)}.json"
        payload = {"key": key, "created_at": datetime.utcnow().isoformat(), "value": value}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return True

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        path = self._dir / f"{_safe_key(key)}.json"
        if not path.exists():
            return None
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            return obj.get("value", {})
        except Exception:
            return None


def _safe_key(key: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in str(key))

