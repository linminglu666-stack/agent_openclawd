from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import hashlib
import json
import uuid
import asyncio

from utils.serializer import Serializer


@dataclass
class EvidenceRecord:
    evidence_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    evidence_type: str = ""
    content: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    digest: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "content": self.content,
            "trace_id": self.trace_id,
            "created_at": self.created_at.isoformat(),
            "digest": self.digest,
        }


class EvidenceStore:
    def __init__(self):
        self._records: Dict[str, EvidenceRecord] = {}
        self._trace_index: Dict[str, List[str]] = {}
        self._lock = asyncio.Lock()

    async def add(self, evidence_type: str, content: Dict[str, Any], trace_id: Optional[str] = None) -> EvidenceRecord:
        record = EvidenceRecord(evidence_type=evidence_type, content=content or {}, trace_id=trace_id)
        record.digest = self._digest(record.content)
        async with self._lock:
            self._records[record.evidence_id] = record
            if trace_id:
                if trace_id not in self._trace_index:
                    self._trace_index[trace_id] = []
                self._trace_index[trace_id].append(record.evidence_id)
        return record

    async def get(self, evidence_id: str) -> Optional[EvidenceRecord]:
        async with self._lock:
            return self._records.get(evidence_id)

    async def list_by_trace(self, trace_id: str) -> List[EvidenceRecord]:
        async with self._lock:
            ids = list(self._trace_index.get(trace_id, []))
            return [self._records[i] for i in ids if i in self._records]

    def _digest(self, content: Dict[str, Any]) -> str:
        normalized = Serializer.from_json(Serializer.to_json(content))
        payload = json.dumps(normalized, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
