from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import hashlib
import json


@dataclass
class SkillEntry:
    name: str
    version: str
    capability: str = ""
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    source_file: str = ""
    checksum_sha256: str = ""
    status: str = "enabled"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "capability": self.capability,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "tags": self.tags,
            "constraints": self.constraints,
            "source_file": self.source_file,
            "checksum_sha256": self.checksum_sha256,
            "status": self.status,
        }


class SkillsRegistry:
    def __init__(self):
        self.generated_at = datetime.utcnow().isoformat()
        self.skills: Dict[str, Dict[str, SkillEntry]] = {}

    def add(self, entry: SkillEntry) -> bool:
        if entry.name not in self.skills:
            self.skills[entry.name] = {}
        self.skills[entry.name][entry.version] = entry
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "skills": {
                name: {version: entry.to_dict() for version, entry in versions.items()}
                for name, versions in self.skills.items()
            },
        }

    def save(self, path: str) -> bool:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return True

    @classmethod
    def load(cls, path: str) -> "SkillsRegistry":
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        reg = cls()
        reg.generated_at = str(data.get("generated_at", reg.generated_at))
        for name, versions in (data.get("skills") or {}).items():
            for version, entry in (versions or {}).items():
                reg.add(
                    SkillEntry(
                        name=str(entry.get("name", name)),
                        version=str(entry.get("version", version)),
                        capability=str(entry.get("capability", "")),
                        inputs=list(entry.get("inputs") or []),
                        outputs=list(entry.get("outputs") or []),
                        tags=list(entry.get("tags") or []),
                        constraints=list(entry.get("constraints") or []),
                        source_file=str(entry.get("source_file", "")),
                        checksum_sha256=str(entry.get("checksum_sha256", "")),
                        status=str(entry.get("status", "enabled")),
                    )
                )
        return reg

    @classmethod
    def build_from_dir(cls, skills_dir: str) -> "SkillsRegistry":
        root = Path(skills_dir)
        reg = cls()
        for path in sorted(root.glob("*.skills.json")):
            checksum = _sha256_file(path)
            items = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(items, list):
                continue
            for it in items:
                if not isinstance(it, dict):
                    continue
                name = str(it.get("name", "")).strip()
                version = str(it.get("version", "")).strip()
                if not name or not version:
                    continue
                reg.add(
                    SkillEntry(
                        name=name,
                        version=version,
                        capability=str(it.get("capability", "")),
                        inputs=list(it.get("inputs") or []),
                        outputs=list(it.get("outputs") or []),
                        tags=list(it.get("tags") or []),
                        constraints=list(it.get("constraints") or []),
                        source_file=str(path.name),
                        checksum_sha256=checksum,
                        status="enabled",
                    )
                )
        return reg


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

