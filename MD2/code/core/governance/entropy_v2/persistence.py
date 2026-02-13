from __future__ import annotations

import json
import os
import sqlite3
import threading
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from base_types import (
    utc_now, EntropyCategory, EntropyLevel, EntropySample, EntropyThreshold,
    EntropyAlert, AlertSeverity, SweepAction, SweepPriority, SweepStatus,
    TrendAnalysis, AttributionResult, AdaptiveThreshold, EntropyReport
)


T = TypeVar("T")


def _serialize_datetime(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _deserialize_datetime(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _serialize_enum(e) -> str:
    if hasattr(e, "value"):
        return str(e.value)
    return str(e)


def _deserialize_enum(cls: Type[T], value) -> T:
    if isinstance(value, int):
        return cls(value)
    if isinstance(value, str) and value.isdigit():
        return cls(int(value))
    return cls(value)


class EntropyPersistence:
    SCHEMA_VERSION = 1

    def __init__(
        self,
        db_path: Optional[str] = None,
        auto_save_interval_seconds: float = 60.0,
        max_records: int = 100000,
    ):
        self._db_path = db_path or self._default_db_path()
        self._auto_save_interval = auto_save_interval_seconds
        self._max_records = max_records
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None
        self._initialize_db()

    def _default_db_path(self) -> str:
        base_dir = Path.home() / ".openclaw" / "entropy"
        base_dir.mkdir(parents=True, exist_ok=True)
        return str(base_dir / "entropy_v2.db")

    def _initialize_db(self) -> None:
        with self._lock:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._create_tables()

    def _create_tables(self) -> None:
        cursor = self._conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entropy_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                category TEXT NOT NULL,
                level TEXT NOT NULL,
                source TEXT NOT NULL,
                value REAL NOT NULL,
                raw_metrics TEXT,
                tags TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_samples_timestamp
            ON entropy_samples(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_samples_category_source
            ON entropy_samples(category, source)
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entropy_alerts (
                alert_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                severity TEXT NOT NULL,
                category TEXT NOT NULL,
                source TEXT NOT NULL,
                current_value REAL NOT NULL,
                threshold REAL NOT NULL,
                message TEXT,
                suggested_actions TEXT,
                acknowledged INTEGER DEFAULT 0,
                acknowledged_by TEXT,
                acknowledged_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sweep_actions (
                action_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                priority INTEGER NOT NULL,
                category TEXT NOT NULL,
                source TEXT,
                executor TEXT,
                status TEXT NOT NULL,
                estimated_impact REAL,
                actual_impact REAL,
                created_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS thresholds (
                category TEXT PRIMARY KEY,
                warning REAL NOT NULL,
                critical REAL NOT NULL,
                emergency REAL NOT NULL,
                weight REAL NOT NULL,
                updated_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS adaptive_thresholds (
                category TEXT PRIMARY KEY,
                base_warning REAL NOT NULL,
                base_critical REAL NOT NULL,
                base_emergency REAL NOT NULL,
                adaptive_factor REAL,
                learning_rate REAL,
                history_window INTEGER,
                min_samples INTEGER,
                updated_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trend_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                source TEXT NOT NULL,
                computed_at TEXT NOT NULL,
                samples_count INTEGER,
                time_range_hours REAL,
                mean REAL,
                std_dev REAL,
                min_val REAL,
                max_val REAL,
                slope REAL,
                trend_direction TEXT,
                prediction_1h REAL,
                prediction_24h REAL,
                confidence REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entropy_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_entropy REAL,
                health_score REAL,
                by_category TEXT,
                by_level TEXT,
                recommendations TEXT
            )
        """)
        cursor.execute("SELECT version FROM schema_version LIMIT 1")
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (self.SCHEMA_VERSION,)
            )
        self._conn.commit()

    def save_sample(self, sample: EntropySample) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                INSERT INTO entropy_samples
                (timestamp, category, level, source, value, raw_metrics, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                _serialize_datetime(sample.timestamp),
                _serialize_enum(sample.category),
                _serialize_enum(sample.level),
                sample.source,
                sample.value,
                json.dumps(sample.raw_metrics),
                json.dumps(sample.tags),
            ))
            self._conn.commit()
            self._prune_samples()

    def save_samples_batch(self, samples: List[EntropySample]) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            data = [
                (
                    _serialize_datetime(s.timestamp),
                    _serialize_enum(s.category),
                    _serialize_enum(s.level),
                    s.source,
                    s.value,
                    json.dumps(s.raw_metrics),
                    json.dumps(s.tags),
                )
                for s in samples
            ]
            cursor.executemany("""
                INSERT INTO entropy_samples
                (timestamp, category, level, source, value, raw_metrics, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, data)
            self._conn.commit()
            self._prune_samples()

    def load_samples(
        self,
        category: Optional[EntropyCategory] = None,
        source: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 10000,
    ) -> List[EntropySample]:
        with self._lock:
            cursor = self._conn.cursor()
            query = "SELECT * FROM entropy_samples WHERE 1=1"
            params: List[Any] = []
            if category:
                query += " AND category = ?"
                params.append(_serialize_enum(category))
            if source:
                query += " AND source = ?"
                params.append(source)
            if since:
                query += " AND timestamp >= ?"
                params.append(_serialize_datetime(since))
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            samples: List[EntropySample] = []
            for row in rows:
                samples.append(EntropySample(
                    timestamp=_deserialize_datetime(row["timestamp"]) or utc_now(),
                    category=_deserialize_enum(EntropyCategory, row["category"]),
                    level=_deserialize_enum(EntropyLevel, row["level"]),
                    source=row["source"],
                    value=row["value"],
                    raw_metrics=json.loads(row["raw_metrics"] or "{}"),
                    tags=json.loads(row["tags"] or "{}"),
                ))
            return samples

    def _prune_samples(self) -> None:
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM entropy_samples")
        count = cursor.fetchone()[0]
        if count > self._max_records:
            delete_count = count - self._max_records
            cursor.execute("""
                DELETE FROM entropy_samples
                WHERE id IN (
                    SELECT id FROM entropy_samples
                    ORDER BY timestamp ASC
                    LIMIT ?
                )
            """, (delete_count,))
            self._conn.commit()

    def save_alert(self, alert: EntropyAlert) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO entropy_alerts
                (alert_id, timestamp, severity, category, source, current_value,
                 threshold, message, suggested_actions, acknowledged,
                 acknowledged_by, acknowledged_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.alert_id,
                _serialize_datetime(alert.timestamp),
                _serialize_enum(alert.severity),
                _serialize_enum(alert.category),
                alert.source,
                alert.current_value,
                alert.threshold,
                alert.message,
                json.dumps(alert.suggested_actions),
                1 if alert.acknowledged else 0,
                alert.acknowledged_by,
                _serialize_datetime(alert.acknowledged_at),
            ))
            self._conn.commit()

    def load_alerts(
        self,
        unacknowledged_only: bool = False,
        severity: Optional[AlertSeverity] = None,
        limit: int = 1000,
    ) -> List[EntropyAlert]:
        with self._lock:
            cursor = self._conn.cursor()
            query = "SELECT * FROM entropy_alerts WHERE 1=1"
            params: List[Any] = []
            if unacknowledged_only:
                query += " AND acknowledged = 0"
            if severity:
                query += " AND severity = ?"
                params.append(_serialize_enum(severity))
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            alerts: List[EntropyAlert] = []
            for row in rows:
                alerts.append(EntropyAlert(
                    alert_id=row["alert_id"],
                    timestamp=_deserialize_datetime(row["timestamp"]) or utc_now(),
                    severity=_deserialize_enum(AlertSeverity, row["severity"]),
                    category=_deserialize_enum(EntropyCategory, row["category"]),
                    source=row["source"],
                    current_value=row["current_value"],
                    threshold=row["threshold"],
                    message=row["message"] or "",
                    suggested_actions=json.loads(row["suggested_actions"] or "[]"),
                    acknowledged=bool(row["acknowledged"]),
                    acknowledged_by=row["acknowledged_by"],
                    acknowledged_at=_deserialize_datetime(row["acknowledged_at"]),
                ))
            return alerts

    def save_sweep_action(self, action: SweepAction) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sweep_actions
                (action_id, name, description, priority, category, source,
                 executor, status, estimated_impact, actual_impact,
                 created_at, started_at, completed_at, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                action.action_id,
                action.name,
                action.description,
                action.priority.value,
                _serialize_enum(action.category),
                action.source,
                action.executor,
                _serialize_enum(action.status),
                action.estimated_impact,
                action.actual_impact,
                _serialize_datetime(action.created_at),
                _serialize_datetime(action.started_at),
                _serialize_datetime(action.completed_at),
                action.error_message,
            ))
            self._conn.commit()

    def load_sweep_actions(
        self,
        status: Optional[SweepStatus] = None,
        limit: int = 1000,
    ) -> List[SweepAction]:
        with self._lock:
            cursor = self._conn.cursor()
            query = "SELECT * FROM sweep_actions WHERE 1=1"
            params: List[Any] = []
            if status:
                query += " AND status = ?"
                params.append(_serialize_enum(status))
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            actions: List[SweepAction] = []
            for row in rows:
                actions.append(SweepAction(
                    action_id=row["action_id"],
                    name=row["name"],
                    description=row["description"] or "",
                    priority=SweepPriority(row["priority"]),
                    category=_deserialize_enum(EntropyCategory, row["category"]),
                    source=row["source"] or "",
                    estimated_impact=row["estimated_impact"] or 0.0,
                    executor=row["executor"],
                    status=_deserialize_enum(SweepStatus, row["status"]),
                    created_at=_deserialize_datetime(row["created_at"]) or utc_now(),
                    started_at=_deserialize_datetime(row["started_at"]),
                    completed_at=_deserialize_datetime(row["completed_at"]),
                    error_message=row["error_message"],
                    actual_impact=row["actual_impact"],
                ))
            return actions

    def save_threshold(self, threshold: EntropyThreshold) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO thresholds
                (category, warning, critical, emergency, weight, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                _serialize_enum(threshold.category),
                threshold.warning,
                threshold.critical,
                threshold.emergency,
                threshold.weight,
                _serialize_datetime(utc_now()),
            ))
            self._conn.commit()

    def load_thresholds(self) -> Dict[EntropyCategory, EntropyThreshold]:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM thresholds")
            rows = cursor.fetchall()
            thresholds: Dict[EntropyCategory, EntropyThreshold] = {}
            for row in rows:
                cat = _deserialize_enum(EntropyCategory, row["category"])
                thresholds[cat] = EntropyThreshold(
                    category=cat,
                    warning=row["warning"],
                    critical=row["critical"],
                    emergency=row["emergency"],
                    weight=row["weight"],
                )
            return thresholds

    def save_report(self, report: EntropyReport) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                INSERT INTO entropy_reports
                (timestamp, total_entropy, health_score, by_category, by_level, recommendations)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                _serialize_datetime(report.timestamp),
                report.total_entropy,
                report.health_score,
                json.dumps({k.value: v for k, v in report.by_category.items()}),
                json.dumps({k.value: v for k, v in report.by_level.items()}),
                json.dumps(report.recommendations),
            ))
            self._conn.commit()

    def load_reports(
        self,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[EntropyReport]:
        with self._lock:
            cursor = self._conn.cursor()
            query = "SELECT * FROM entropy_reports WHERE 1=1"
            params: List[Any] = []
            if since:
                query += " AND timestamp >= ?"
                params.append(_serialize_datetime(since))
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            reports: List[EntropyReport] = []
            for row in rows:
                by_category_raw = json.loads(row["by_category"] or "{}")
                by_level_raw = json.loads(row["by_level"] or "{}")
                reports.append(EntropyReport(
                    timestamp=_deserialize_datetime(row["timestamp"]) or utc_now(),
                    total_entropy=row["total_entropy"],
                    by_category={EntropyCategory(k): v for k, v in by_category_raw.items()},
                    by_level={EntropyLevel(k): v for k, v in by_level_raw.items()},
                    top_contributors=[],
                    active_alerts=[],
                    pending_sweeps=[],
                    trends=[],
                    health_score=row["health_score"],
                    recommendations=json.loads(row["recommendations"] or "[]"),
                ))
            return reports

    def close(self) -> None:
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
