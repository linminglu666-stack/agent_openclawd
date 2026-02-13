from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .trace import TraceContext


@dataclass
class EventEnvelope:
    topic: str
    version: str
    event_id: str
    trace: Optional[TraceContext] = None
    created_at: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))
    payload: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

