from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base_types import (
    CheckpointData,
    Feature,
    FeatureStatus,
    Priority,
    ProgressEntry,
    SessionContext,
    SessionState,
)


@dataclass
class SessionProgress:
    session_id: str
    start_time: int
    end_time: Optional[int]
    state: SessionState
    features_completed: int
    features_failed: int
    features_pending: int
    total_changes: int
    commits_made: int
    context_windows_used: int
    checkpoints: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "state": self.state.value,
            "features_completed": self.features_completed,
            "features_failed": self.features_failed,
            "features_pending": self.features_pending,
            "total_changes": self.total_changes,
            "commits_made": self.commits_made,
            "context_windows_used": self.context_windows_used,
            "checkpoints": self.checkpoints,
        }


@dataclass
class ProgressTrackerConfig:
    project_root: str
    progress_file: str = "progress.jsonl"
    checkpoint_dir: str = ".checkpoints"
    max_history_entries: int = 10000
    auto_checkpoint_interval: int = 300
    enable_metrics: bool = True


class ProgressTracker:
    def __init__(self, config: ProgressTrackerConfig):
        self._config = config
        self._entries: List[ProgressEntry] = []
        self._checkpoints: List[CheckpointData] = []
        self._metrics: Dict[str, Any] = {}
        self._load_existing_progress()

    def _load_existing_progress(self) -> None:
        path = os.path.join(self._config.project_root, self._config.progress_file)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fp:
                for line in fp:
                    try:
                        data = json.loads(line)
                        entry = self._dict_to_entry(data)
                        self._entries.append(entry)
                    except (json.JSONDecodeError, KeyError):
                        pass

    def _dict_to_entry(self, data: Dict[str, Any]) -> ProgressEntry:
        return ProgressEntry(
            entry_id=data.get("entry_id", ""),
            session_id=data.get("session_id", ""),
            timestamp=data.get("timestamp", 0),
            action=data.get("action", ""),
            description=data.get("description", ""),
            feature_id=data.get("feature_id"),
            files_changed=data.get("files_changed", []),
            commit_hash=data.get("commit_hash"),
            test_results=data.get("test_results"),
            metrics=data.get("metrics", {}),
            next_steps=data.get("next_steps", []),
            blockers=data.get("blockers", []),
        )

    def record(self, entry: ProgressEntry) -> None:
        self._entries.append(entry)
        self._append_to_file(entry)
        self._update_metrics(entry)
        self._check_auto_checkpoint()

    def _append_to_file(self, entry: ProgressEntry) -> None:
        path = os.path.join(self._config.project_root, self._config.progress_file)
        with open(path, "a", encoding="utf-8") as fp:
            fp.write(json.dumps(entry.to_dict()) + "\n")

    def _update_metrics(self, entry: ProgressEntry) -> None:
        if not self._config.enable_metrics:
            return

        action = entry.action
        if action not in self._metrics:
            self._metrics[action] = {"count": 0, "total_time": 0}
        self._metrics[action]["count"] += 1

    def _check_auto_checkpoint(self) -> None:
        recent = self._entries[-self._config.auto_checkpoint_interval :]
        if len(recent) >= self._config.auto_checkpoint_interval:
            pass

    def get_recent_entries(self, limit: int = 10) -> List[ProgressEntry]:
        return self._entries[-limit:]

    def get_entries_by_session(self, session_id: str) -> List[ProgressEntry]:
        return [e for e in self._entries if e.session_id == session_id]

    def get_entries_by_feature(self, feature_id: str) -> List[ProgressEntry]:
        return [e for e in self._entries if e.feature_id == feature_id]

    def get_entries_by_action(self, action: str) -> List[ProgressEntry]:
        return [e for e in self._entries if e.action == action]

    def get_session_progress(self, session_id: str) -> SessionProgress:
        session_entries = self.get_entries_by_session(session_id)
        if not session_entries:
            return SessionProgress(
                session_id=session_id,
                start_time=0,
                end_time=None,
                state=SessionState.PENDING,
                features_completed=0,
                features_failed=0,
                features_pending=0,
                total_changes=0,
                commits_made=0,
                context_windows_used=1,
                checkpoints=[],
            )

        start_time = min(e.timestamp for e in session_entries)
        end_times = [e.timestamp for e in session_entries if e.action == "session_end"]
        end_time = end_times[0] if end_times else None

        state = SessionState.COMPLETED if end_time else SessionState.ACTIVE

        features_completed = len([e for e in session_entries if e.test_results and e.test_results.get("passed")])
        features_failed = len([e for e in session_entries if e.test_results and not e.test_results.get("passed")])

        total_changes = sum(len(e.files_changed) for e in session_entries)
        commits_made = len([e for e in session_entries if e.commit_hash])

        return SessionProgress(
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            state=state,
            features_completed=features_completed,
            features_failed=features_failed,
            features_pending=0,
            total_changes=total_changes,
            commits_made=commits_made,
            context_windows_used=1,
            checkpoints=[],
        )

    def get_overall_progress(self) -> Dict[str, Any]:
        if not self._entries:
            return {"status": "no_data"}

        sessions = set(e.session_id for e in self._entries)
        features = set(e.feature_id for e in self._entries if e.feature_id)

        return {
            "total_entries": len(self._entries),
            "total_sessions": len(sessions),
            "total_features_touched": len(features),
            "metrics": self._metrics,
            "first_entry": min(e.timestamp for e in self._entries),
            "last_entry": max(e.timestamp for e in self._entries),
        }

    def search_entries(
        self,
        session_id: Optional[str] = None,
        feature_id: Optional[str] = None,
        action: Optional[str] = None,
        since: Optional[int] = None,
        until: Optional[int] = None,
        has_blockers: Optional[bool] = None,
    ) -> List[ProgressEntry]:
        results = self._entries

        if session_id:
            results = [e for e in results if e.session_id == session_id]
        if feature_id:
            results = [e for e in results if e.feature_id == feature_id]
        if action:
            results = [e for e in results if e.action == action]
        if since:
            results = [e for e in results if e.timestamp >= since]
        if until:
            results = [e for e in results if e.timestamp <= until]
        if has_blockers is not None:
            if has_blockers:
                results = [e for e in results if e.blockers]
            else:
                results = [e for e in results if not e.blockers]

        return results

    def get_active_blockers(self) -> List[Dict[str, Any]]:
        blockers = []
        for entry in reversed(self._entries):
            for blocker in entry.blockers:
                blockers.append(
                    {
                        "session_id": entry.session_id,
                        "feature_id": entry.feature_id,
                        "blocker": blocker,
                        "timestamp": entry.timestamp,
                    }
                )
        return blockers

    def summarize_session(self, session_id: str) -> str:
        entries = self.get_entries_by_session(session_id)
        if not entries:
            return f"No progress recorded for session {session_id}"

        features_worked = set(e.feature_id for e in entries if e.feature_id)
        files_changed = set()
        for e in entries:
            files_changed.update(e.files_changed)

        passed = len([e for e in entries if e.test_results and e.test_results.get("passed")])
        failed = len([e for e in entries if e.test_results and not e.test_results.get("passed")])

        summary = f"""Session {session_id} Summary:
- Total entries: {len(entries)}
- Features worked on: {len(features_worked)}
- Files changed: {len(files_changed)}
- Tests passed: {passed}
- Tests failed: {failed}
- Duration: {max(e.timestamp for e in entries) - min(e.timestamp for e in entries)} seconds
"""
        return summary

    def export_progress(self, format: str = "json") -> str:
        if format == "json":
            return json.dumps([e.to_dict() for e in self._entries], indent=2)
        elif format == "markdown":
            lines = ["# Progress Report\n"]
            for entry in self._entries:
                lines.append(f"## {entry.action} @ {entry.timestamp}")
                lines.append(f"Description: {entry.description}")
                if entry.files_changed:
                    lines.append(f"Files: {', '.join(entry.files_changed)}")
                lines.append("")
            return "\n".join(lines)
        return ""

    def cleanup_old_entries(self, max_age_days: int = 30) -> int:
        cutoff = int(datetime.now(tz=timezone.utc).timestamp()) - (max_age_days * 86400)
        old_count = len(self._entries)
        self._entries = [e for e in self._entries if e.timestamp >= cutoff]
        return old_count - len(self._entries)

    def get_metrics(self) -> Dict[str, Any]:
        return self._metrics.copy()
