from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import os


@dataclass(frozen=True)
class RuntimePaths:
    state_dir: Path
    log_dir: Path
    runtime_dir: Path

    def ensure(self) -> "RuntimePaths":
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        return self


def get_runtime_paths(
    state_dir: Optional[str] = None,
    log_dir: Optional[str] = None,
    runtime_dir: Optional[str] = None,
) -> RuntimePaths:
    return RuntimePaths(
        state_dir=Path(state_dir or os.environ.get("OPENCLAW_STATE_DIR", "/var/lib/openclaw-x")),
        log_dir=Path(log_dir or os.environ.get("OPENCLAW_LOG_DIR", "/var/log/openclaw-x")),
        runtime_dir=Path(runtime_dir or os.environ.get("OPENCLAW_RUNTIME_DIR", "/run/openclaw-x")),
    ).ensure()

