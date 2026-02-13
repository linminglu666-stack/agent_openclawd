from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .base_types import (
    BridgedContext,
    CheckpointData,
    EnvironmentSetup,
    Feature,
    FeatureStatus,
    IncrementalProgress,
    Priority,
    ProgressEntry,
    RecoveryStrategy,
    SessionContext,
    SessionState,
    SessionType,
)
from .coding_agent import CodingAgent, CodingAgentConfig
from .context_bridge import ContextBridge, ContextBridgeConfig
from .initializer import InitializerAgent, InitializerConfig
from .progress_tracker import ProgressTracker, ProgressTrackerConfig


@dataclass
class SessionManagerConfig:
    project_root: str
    max_context_windows: int = 100
    auto_checkpoint: bool = True
    checkpoint_interval_features: int = 3
    enable_handoff_docs: bool = True
    llm_callback: Optional[Callable] = None
    test_callback: Optional[Callable] = None


class SessionManager:
    def __init__(self, config: SessionManagerConfig):
        self._config = config
        self._sessions: Dict[str, SessionContext] = {}
        self._current_session: Optional[SessionContext] = None
        self._initializer: Optional[InitializerAgent] = None
        self._coding_agent: Optional[CodingAgent] = None
        self._progress_tracker = ProgressTracker(
            ProgressTrackerConfig(project_root=config.project_root)
        )
        self._context_bridge = ContextBridge(
            ContextBridgeConfig(project_root=config.project_root)
        )

    def initialize_project(self, spec_prompt: str) -> EnvironmentSetup:
        session_id = f"init-{uuid.uuid4().hex[:8]}"
        context = SessionContext(
            session_id=session_id,
            session_type=SessionType.INITIALIZER,
            state=SessionState.PENDING,
            project_root=self._config.project_root,
            start_time=int(datetime.now(tz=timezone.utc).timestamp()),
        )
        self._sessions[session_id] = context
        self._current_session = context

        initializer_config = InitializerConfig(
            project_root=self._config.project_root,
            spec_prompt=spec_prompt,
        )
        self._initializer = InitializerAgent(initializer_config)

        if self._config.llm_callback:
            self._initializer.set_llm_callback(self._config.llm_callback)

        context.state = SessionState.INITIALIZING
        setup = self._initializer.initialize()
        context.state = SessionState.COMPLETED

        self._record_progress(
            session_id,
            "project_initialize",
            f"Project initialized with {len(setup.feature_list)} features",
        )

        return setup

    def start_coding_session(self) -> SessionContext:
        session_id = f"code-{uuid.uuid4().hex[:8]}"
        context = SessionContext(
            session_id=session_id,
            session_type=SessionType.CODING,
            state=SessionState.ACTIVE,
            project_root=self._config.project_root,
            start_time=int(datetime.now(tz=timezone.utc).timestamp()),
        )
        self._sessions[session_id] = context
        self._current_session = context

        coding_config = CodingAgentConfig(
            project_root=self._config.project_root,
            session_id=session_id,
        )
        self._coding_agent = CodingAgent(coding_config)

        if self._config.llm_callback:
            self._coding_agent.set_llm_callback(self._config.llm_callback)
        if self._config.test_callback:
            self._coding_agent.set_test_callback(self._config.test_callback)

        self._coding_agent.start_session(context)

        self._record_progress(
            session_id,
            "session_start",
            "Coding session started",
        )

        return context

    def get_bearings(self) -> Dict[str, Any]:
        if not self._coding_agent:
            return {"error": "No active coding session"}

        bearings = self._coding_agent.get_bearings()
        bearings["session_id"] = self._current_session.session_id if self._current_session else None
        bearings["session_state"] = self._current_session.state.value if self._current_session else None
        return bearings

    def select_next_feature(self) -> Optional[Feature]:
        if not self._coding_agent:
            return None
        return self._coding_agent.select_next_feature()

    def implement_feature(self, feature: Optional[Feature] = None) -> IncrementalProgress:
        if not self._coding_agent:
            raise RuntimeError("No active coding session")

        progress = self._coding_agent.implement_feature(feature)

        if self._config.auto_checkpoint:
            self._maybe_checkpoint()

        return progress

    def run_incremental_cycle(self, max_features: int = 1) -> List[IncrementalProgress]:
        results = []

        for _ in range(max_features):
            feature = self.select_next_feature()
            if not feature:
                break

            progress = self.implement_feature(feature)
            results.append(progress)

            if (
                self._current_session
                and self._current_session.context_window_usage >= 0.85
            ):
                self.create_checkpoint()
                break

        return results

    def create_checkpoint(self) -> CheckpointData:
        if not self._coding_agent:
            raise RuntimeError("No active coding session")

        checkpoint = self._coding_agent.create_checkpoint()

        self._record_progress(
            self._current_session.session_id if self._current_session else "unknown",
            "checkpoint_created",
            f"Checkpoint {checkpoint.checkpoint_id} created",
        )

        return checkpoint

    def _maybe_checkpoint(self) -> None:
        if not self._current_session or not self._coding_agent:
            return

        completed = self._count_completed_features()
        last_checkpoint = self._get_last_checkpoint_feature_count()

        if completed - last_checkpoint >= self._config.checkpoint_interval_features:
            self.create_checkpoint()

    def _count_completed_features(self) -> int:
        path = os.path.join(self._config.project_root, "feature_list.json")
        if not os.path.exists(path):
            return 0

        with open(path, "r", encoding="utf-8") as fp:
            data = json.load(fp)

        return len([f for f in data.get("features", []) if f.get("status") == "passed"])

    def _get_last_checkpoint_feature_count(self) -> int:
        checkpoint_dir = os.path.join(self._config.project_root, ".checkpoints")
        if not os.path.exists(checkpoint_dir):
            return 0

        checkpoints = []
        for filename in os.listdir(checkpoint_dir):
            if filename.endswith(".json"):
                path = os.path.join(checkpoint_dir, filename)
                try:
                    with open(path, "r") as fp:
                        data = json.load(fp)
                    checkpoints.append((data.get("timestamp", 0), data))
                except Exception:
                    continue

        if not checkpoints:
            return 0

        checkpoints.sort(reverse=True)
        return checkpoints[0][1].get("health_metrics", {}).get("features_completed", 0)

    def recover(self, strategy: RecoveryStrategy = RecoveryStrategy.ROLLBACK) -> bool:
        if not self._coding_agent:
            return False

        success = self._coding_agent.recover(strategy)

        self._record_progress(
            self._current_session.session_id if self._current_session else "unknown",
            "recovery",
            f"Recovery attempted with strategy {strategy.value}, success={success}",
        )

        return success

    def bridge_to_next_session(self) -> BridgedContext:
        if not self._current_session:
            raise RuntimeError("No current session to bridge from")

        return self._context_bridge.bridge(
            self._current_session.session_id,
            f"{self._current_session.session_id}-next",
        )

    def create_handoff_document(self) -> str:
        if not self._current_session:
            raise RuntimeError("No current session")

        return self._context_bridge.create_handoff_document(
            self._current_session.session_id
        )

    def end_session(self) -> Dict[str, Any]:
        if not self._coding_agent:
            return {"error": "No active coding session"}

        summary = self._coding_agent.end_session()

        if self._current_session:
            self._current_session.state = SessionState.COMPLETED

            self._record_progress(
                self._current_session.session_id,
                "session_end",
                f"Session completed. Features worked: {summary.get('features_worked', 0)}",
            )

            if self._config.enable_handoff_docs:
                handoff = self.create_handoff_document()
                handoff_path = os.path.join(
                    self._config.project_root,
                    f"HANDOFF_{self._current_session.session_id}.md",
                )
                with open(handoff_path, "w", encoding="utf-8") as fp:
                    fp.write(handoff)

        return summary

    def get_session_progress(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid = session_id or (self._current_session.session_id if self._current_session else None)
        if not sid:
            return {"error": "No session specified"}

        progress = self._progress_tracker.get_session_progress(sid)
        return progress.to_dict()

    def get_overall_progress(self) -> Dict[str, Any]:
        return self._progress_tracker.get_overall_progress()

    def _record_progress(self, session_id: str, action: str, description: str) -> None:
        entry = ProgressEntry(
            entry_id=f"entry-{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            timestamp=int(datetime.now(tz=timezone.utc).timestamp()),
            action=action,
            description=description,
        )
        self._progress_tracker.record(entry)

    def get_active_blockers(self) -> List[Dict[str, Any]]:
        return self._progress_tracker.get_active_blockers()

    def is_project_complete(self) -> bool:
        path = os.path.join(self._config.project_root, "feature_list.json")
        if not os.path.exists(path):
            return False

        with open(path, "r", encoding="utf-8") as fp:
            data = json.load(fp)

        for feature in data.get("features", []):
            if feature.get("status") != "passed":
                return False

        return True

    def get_project_status(self) -> Dict[str, Any]:
        path = os.path.join(self._config.project_root, "feature_list.json")
        if not os.path.exists(path):
            return {"status": "not_initialized"}

        with open(path, "r", encoding="utf-8") as fp:
            data = json.load(fp)

        features = data.get("features", [])
        status_counts = {}
        for f in features:
            status = f.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        total = len(features)
        completed = status_counts.get("passed", 0)

        return {
            "status": "in_progress" if completed < total else "completed",
            "total_features": total,
            "completed": completed,
            "completion_percentage": (completed / total * 100) if total > 0 else 0,
            "status_breakdown": status_counts,
            "current_session": self._current_session.session_id if self._current_session else None,
            "sessions_count": len(self._sessions),
        }

    def list_sessions(self) -> List[Dict[str, Any]]:
        return [
            {
                "session_id": ctx.session_id,
                "type": ctx.session_type.value,
                "state": ctx.state.value,
                "start_time": ctx.start_time,
                "current_feature": ctx.current_feature,
            }
            for ctx in self._sessions.values()
        ]

    def get_current_session(self) -> Optional[SessionContext]:
        return self._current_session

    def set_context_usage(self, usage: float) -> None:
        if self._current_session:
            self._current_session.context_window_usage = usage
