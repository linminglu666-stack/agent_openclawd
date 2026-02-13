from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class LearningReport:
    report_id: str
    agent_id: str
    summary: str
    new_skills: List[Dict[str, Any]] = field(default_factory=list)
    memory_delta: List[Dict[str, Any]] = field(default_factory=list)
    validation: Dict[str, Any] = field(default_factory=dict)
    rollback_info: Dict[str, Any] = field(default_factory=dict)
    created_at: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))

