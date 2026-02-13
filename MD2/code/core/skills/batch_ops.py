from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .registry import SkillsRegistry


@dataclass
class SkillToggle:
    name: str
    version: str
    enabled: bool


class SkillsBatchOps:
    def __init__(self, registry_path: str):
        self._registry_path = registry_path

    def apply(self, toggles: List[SkillToggle]) -> Dict[str, Any]:
        reg = SkillsRegistry.load(self._registry_path)
        updated = 0
        for t in toggles:
            versions = reg.skills.get(t.name)
            if not versions:
                continue
            entry = versions.get(t.version)
            if not entry:
                continue
            entry.status = "enabled" if t.enabled else "disabled"
            updated += 1

        reg.save(self._registry_path)
        return {"ok": True, "updated": updated}

