from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import json
import uuid


@dataclass
class ConfigSnapshot:
    version: str
    created_at: str
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConfigStore:
    def __init__(self, root_dir: str):
        self._root = Path(root_dir)
        self._versions_dir = self._root / "config" / "versions"
        self._current_path = self._root / "config" / "current.json"

    def list_versions(self) -> List[str]:
        if not self._versions_dir.exists():
            return []
        versions = [p.stem for p in self._versions_dir.glob("*.json")]
        versions.sort()
        return versions

    def load_current(self) -> Optional[ConfigSnapshot]:
        if not self._current_path.exists():
            return None
        data = json.loads(self._current_path.read_text(encoding="utf-8"))
        return ConfigSnapshot(version=str(data.get("version", "current")), created_at=str(data.get("created_at", "")), data=data.get("data", {}), metadata=data.get("metadata", {}))

    def save_current(self, snapshot: ConfigSnapshot) -> bool:
        self._current_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": snapshot.version, "created_at": snapshot.created_at, "data": snapshot.data, "metadata": snapshot.metadata}
        self._current_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return True

    def load_version(self, version: str) -> Optional[ConfigSnapshot]:
        path = self._versions_dir / f"{version}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return ConfigSnapshot(version=str(data.get("version", version)), created_at=str(data.get("created_at", "")), data=data.get("data", {}), metadata=data.get("metadata", {}))

    def save_version(self, data: Dict[str, Any], version: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> ConfigSnapshot:
        self._versions_dir.mkdir(parents=True, exist_ok=True)
        version_id = version or f"v{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        snapshot = ConfigSnapshot(version=version_id, created_at=datetime.utcnow().isoformat(), data=data, metadata=metadata or {})
        path = self._versions_dir / f"{version_id}.json"
        payload = {"version": snapshot.version, "created_at": snapshot.created_at, "data": snapshot.data, "metadata": snapshot.metadata}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return snapshot

    def snapshot_current(self, metadata: Optional[Dict[str, Any]] = None) -> Optional[ConfigSnapshot]:
        current = self.load_current()
        if current is None:
            return None
        return self.save_version(data=current.data, metadata={**(current.metadata or {}), **(metadata or {}), "snapshot_of": current.version})

