from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class FeatureFlagRule:
    flag_key: str
    scope: str
    rule: str
    default: bool = False


@dataclass
class ConfigSnapshot:
    version: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any] = field(default_factory=dict)
    feature_flags: List[FeatureFlagRule] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

