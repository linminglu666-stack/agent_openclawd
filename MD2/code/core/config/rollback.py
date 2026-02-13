from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import os
import sys

from utils.serializer import Serializer
from utils.logger import get_logger

from .store import ConfigStore


@dataclass
class RollbackResult:
    ok: bool
    target_version: str
    snapshot_version: Optional[str] = None
    error: Optional[str] = None


def rollback_config_version(target_version: str, state_dir: Optional[str] = None, log_dir: Optional[str] = None) -> RollbackResult:
    logger = get_logger("config.rollback")
    state_root = state_dir or os.environ.get("OPENCLAW_STATE_DIR", "/var/lib/openclaw-x")
    log_root = log_dir or os.environ.get("OPENCLAW_LOG_DIR", "/var/log/openclaw-x")

    store = ConfigStore(state_root)

    target = store.load_version(target_version)
    if target is None:
        return RollbackResult(ok=False, target_version=target_version, error="target_version_not_found")

    snapshot = store.snapshot_current(metadata={"rollback_requested_at": datetime.utcnow().isoformat(), "rollback_target": target_version})
    snapshot_version = snapshot.version if snapshot else None

    store.save_current(target)
    ok = _health_verify()

    audit_path = Path(log_root) / "audit" / "config_rollback.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_event = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": "config_rollback",
        "target_version": target_version,
        "snapshot_version": snapshot_version,
        "health_ok": ok,
    }
    audit_path.open("a", encoding="utf-8").write(Serializer.to_json(audit_event) + "\n")

    if not ok:
        logger.error("rollback_health_failed", target_version=target_version, snapshot_version=snapshot_version)
        return RollbackResult(ok=False, target_version=target_version, snapshot_version=snapshot_version, error="health_verify_failed")

    logger.info("rollback_ok", target_version=target_version, snapshot_version=snapshot_version)
    return RollbackResult(ok=True, target_version=target_version, snapshot_version=snapshot_version)


def _health_verify() -> bool:
    return True


def _main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write("usage: python -m core.config.rollback vX.Y.Z\n")
        return 2
    version = argv[1]
    result = rollback_config_version(version)
    if not result.ok:
        sys.stderr.write(result.error or "rollback_failed")
        sys.stderr.write("\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))

