from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class LeaseRecord:
    key: str
    owner: str
    expires_at: str
    lease_id: str = ""


@dataclass
class SnapshotMeta:
    snapshot_id: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    path: str = ""


@dataclass
class WalEvent:
    ts: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    type: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

