from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import re
import asyncio
import uuid


@dataclass
class FailurePattern:
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    pattern: str = ""
    severity: str = "medium"
    remediation: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def match(self, text: str) -> bool:
        try:
            return re.search(self.pattern, text or "", flags=re.IGNORECASE) is not None
        except re.error:
            return (self.pattern or "").lower() in (text or "").lower()


class FailurePatternLibrary:
    def __init__(self):
        self._patterns: List[FailurePattern] = []
        self._lock = asyncio.Lock()

    async def add(self, pattern: FailurePattern) -> str:
        async with self._lock:
            self._patterns.append(pattern)
        return pattern.pattern_id

    async def match(self, text: str) -> List[FailurePattern]:
        async with self._lock:
            patterns = list(self._patterns)
        return [p for p in patterns if p.match(text)]

    async def list(self) -> List[FailurePattern]:
        async with self._lock:
            return list(self._patterns)

