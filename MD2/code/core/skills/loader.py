from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import os

from .registry import SkillsRegistry


@dataclass
class LoadedSkill:
    name: str
    version: str
    capability: str
    tags: List[str]
    constraints: List[str]


class SkillsLoader:
    def __init__(self, registry_path: Optional[str] = None):
        self._registry_path = registry_path or self._default_registry_path()

    def load(self) -> List[LoadedSkill]:
        reg = SkillsRegistry.load(self._registry_path)
        loaded: List[LoadedSkill] = []
        for name, versions in reg.skills.items():
            for version, entry in versions.items():
                if entry.status != "enabled":
                    continue
                loaded.append(
                    LoadedSkill(
                        name=entry.name,
                        version=entry.version,
                        capability=entry.capability,
                        tags=entry.tags,
                        constraints=entry.constraints,
                    )
                )
        return loaded

    def _default_registry_path(self) -> str:
        code_dir = os.environ.get("OPENCLAW_CODE_DIR")
        if code_dir:
            md2_dir = str(Path(code_dir).parent)
            return str(Path(md2_dir) / "skills" / "registry.json")
        return str(Path.cwd().parent / "skills" / "registry.json")

