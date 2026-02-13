from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class SkillSpec:
    name: str
    capability: str
    version: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)


@dataclass
class SkillsRegistrySnapshot:
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    skills: Dict[str, Dict[str, Any]] = field(default_factory=dict)

