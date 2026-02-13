from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.observability import InMemoryEventBus, InMemoryTracer, InMemoryMetricsCollector, EvidenceStore
from core.governance import InMemoryAuditSink, SimpleRedactor, EntropyControlCenter
from core.persistence import JsonlWAL, SnapshotStore, SqliteStateStore, StateDB, DbConfig
from core.recovery import LeaseStore, IdempotencyStore
from core.config import ConfigStore
from .paths import RuntimePaths, get_runtime_paths


@dataclass
class RuntimeContainer:
    paths: RuntimePaths
    event_bus: InMemoryEventBus
    tracer: InMemoryTracer
    metrics: InMemoryMetricsCollector
    evidence: EvidenceStore
    audit: InMemoryAuditSink
    redactor: SimpleRedactor
    entropy: EntropyControlCenter
    wal: JsonlWAL
    snapshots: SnapshotStore
    state_store: SqliteStateStore
    state_db: StateDB
    leases: LeaseStore
    idempotency: IdempotencyStore
    config_store: ConfigStore


def build_runtime_container(paths: RuntimePaths | None = None) -> RuntimeContainer:
    p = paths or get_runtime_paths()

    wal_path = str(p.state_dir / "wal" / "events.jsonl")
    sqlite_path = str(p.state_dir / "db" / "state.sqlite3")
    db_path = str(p.state_dir / "db" / "openclaw.db")

    return RuntimeContainer(
        paths=p,
        event_bus=InMemoryEventBus(),
        tracer=InMemoryTracer(),
        metrics=InMemoryMetricsCollector(),
        evidence=EvidenceStore(),
        audit=InMemoryAuditSink(jsonl_path=str(p.log_dir / "audit" / "audit.jsonl")),
        redactor=SimpleRedactor(),
        entropy=EntropyControlCenter(),
        wal=JsonlWAL(wal_path=wal_path),
        snapshots=SnapshotStore(root_dir=str(p.state_dir)),
        state_store=SqliteStateStore(db_path=sqlite_path),
        state_db=StateDB(DbConfig(path=db_path)),
        leases=LeaseStore(root_dir=str(p.state_dir)),
        idempotency=IdempotencyStore(root_dir=str(p.state_dir)),
        config_store=ConfigStore(root_dir=str(p.state_dir)),
    )
