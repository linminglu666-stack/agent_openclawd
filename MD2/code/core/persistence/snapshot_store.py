from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import json


@dataclass
class SnapshotMeta:
    snapshot_id: str
    created_at: str
    path: str


class SnapshotStore:
    def __init__(self, root_dir: str):
        self._root = Path(root_dir)
        self._dir = self._root / "snapshots"
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, snapshot_id: str, state: Dict[str, Any]) -> SnapshotMeta:
        path = self._dir / f"{snapshot_id}.json"
        payload = {"snapshot_id": snapshot_id, "created_at": datetime.utcnow().isoformat(), "state": state}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return SnapshotMeta(snapshot_id=snapshot_id, created_at=str(payload["created_at"]), path=str(path))

    def load(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        path = self._dir / f"{snapshot_id}.json"
        if not path.exists():
            return None
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj.get("state", {})

    def list(self) -> List[SnapshotMeta]:
        metas: List[SnapshotMeta] = []
        for p in sorted(self._dir.glob("*.json")):
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
                metas.append(SnapshotMeta(snapshot_id=str(obj.get("snapshot_id", p.stem)), created_at=str(obj.get("created_at", "")), path=str(p)))
            except Exception:
                continue
        return metas

