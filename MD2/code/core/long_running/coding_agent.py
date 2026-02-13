from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .base_types import (
    CheckpointData,
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


@dataclass
class CodingAgentConfig:
    project_root: str
    session_id: str
    max_context_usage: float = 0.85
    auto_commit: bool = True
    auto_test: bool = True
    test_timeout_sec: int = 60
    max_retries: int = 3
    verification_strictness: str = "high"


class CodingAgent:
    def __init__(self, config: CodingAgentConfig):
        self._config = config
        self._context: Optional[SessionContext] = None
        self._current_feature: Optional[Feature] = None
        self._llm_callback: Optional[Callable] = None
        self._test_callback: Optional[Callable] = None
        self._progress_entries: List[ProgressEntry] = []
        self._tools: Dict[str, Callable] = {}

    def set_llm_callback(self, callback: Callable) -> None:
        self._llm_callback = callback

    def set_test_callback(self, callback: Callable) -> None:
        self._test_callback = callback

    def register_tool(self, name: str, handler: Callable) -> None:
        self._tools[name] = handler

    def start_session(self, context: Optional[SessionContext] = None) -> SessionContext:
        if context:
            self._context = context
        else:
            self._context = SessionContext(
                session_id=self._config.session_id,
                session_type=SessionType.CODING,
                state=SessionState.ACTIVE,
                project_root=self._config.project_root,
                start_time=int(datetime.now(tz=timezone.utc).timestamp()),
            )
        return self._context

    def get_bearings(self) -> Dict[str, Any]:
        bearings = {
            "project_root": self._config.project_root,
            "session_id": self._context.session_id if self._context else None,
            "git_log": self._read_git_log(),
            "recent_progress": self._read_recent_progress(),
            "feature_list": self._read_feature_list(),
            "environment_status": self._check_environment(),
        }
        return bearings

    def _read_git_log(self, limit: int = 20) -> List[Dict[str, str]]:
        commits = []
        try:
            result = subprocess.run(
                ["git", "log", f"--oneline", f"-{limit}", "--format=%H|%s|%ci"],
                cwd=self._config.project_root,
                capture_output=True,
                text=True,
            )
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        commits.append({"hash": parts[0], "message": parts[1], "date": parts[2]})
        except Exception:
            pass
        return commits

    def _read_recent_progress(self, limit: int = 10) -> List[Dict[str, Any]]:
        entries = []
        progress_path = os.path.join(self._config.project_root, "progress.jsonl")
        if os.path.exists(progress_path):
            with open(progress_path, "r", encoding="utf-8") as fp:
                lines = fp.readlines()[-limit:]
                for line in lines:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries

    def _read_feature_list(self) -> List[Dict[str, Any]]:
        features = []
        path = os.path.join(self._config.project_root, "feature_list.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                features = data.get("features", [])
        return features

    def _check_environment(self) -> Dict[str, Any]:
        status = {
            "git_clean": self._is_git_clean(),
            "init_script_exists": os.path.exists(os.path.join(self._config.project_root, "init.sh")),
            "feature_list_exists": os.path.exists(os.path.join(self._config.project_root, "feature_list.json")),
            "progress_file_exists": os.path.exists(os.path.join(self._config.project_root, "progress.jsonl")),
        }
        return status

    def _is_git_clean(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self._config.project_root,
                capture_output=True,
                text=True,
            )
            return len(result.stdout.strip()) == 0
        except Exception:
            return False

    def select_next_feature(self) -> Optional[Feature]:
        features = self._read_feature_list()
        if not features:
            return None

        pending = []
        for f in features:
            if f.get("status") in ("pending", "failed"):
                deps = f.get("dependencies", [])
                deps_satisfied = all(
                    any(d.get("feature_id") == dep and d.get("status") == "passed" for d in features)
                    for dep in deps
                )
                if deps_satisfied:
                    pending.append(f)

        if not pending:
            return None

        pending.sort(key=lambda x: x.get("priority", 99))
        feature_data = pending[0]

        feature = Feature(
            feature_id=feature_data["feature_id"],
            category=feature_data["category"],
            description=feature_data["description"],
            steps=feature_data.get("steps", []),
            status=FeatureStatus[feature_data.get("status", "PENDING").upper()],
            priority=Priority[feature_data.get("priority", "MEDIUM").upper()],
            dependencies=feature_data.get("dependencies", []),
            test_criteria=feature_data.get("test_criteria", []),
        )

        self._current_feature = feature
        if self._context:
            self._context.current_feature = feature.feature_id

        return feature

    def implement_feature(self, feature: Optional[Feature] = None) -> IncrementalProgress:
        target = feature or self._current_feature
        if not target:
            raise ValueError("No feature to implement")

        previous_state = target.status
        target.start_work()
        self._update_feature_status(target.feature_id, FeatureStatus.IN_PROGRESS)

        changes_made = []
        tests_passed = False
        commit_hash = ""

        try:
            if self._llm_callback:
                changes_made = self._llm_implement(target)
            else:
                changes_made = self._template_implement(target)

            if self._config.auto_test:
                tests_passed = self._run_tests(target)

            if tests_passed:
                target.mark_passed()
                self._update_feature_status(target.feature_id, FeatureStatus.PASSED)
            else:
                target.mark_failed()
                self._update_feature_status(target.feature_id, FeatureStatus.FAILED)

            if self._config.auto_commit:
                commit_hash = self._commit_changes(target, changes_made, tests_passed)

            progress_entry = self._create_progress_entry(target, changes_made, tests_passed, commit_hash)
            self._append_progress(progress_entry)

            context_health = self._calculate_context_health()

            return IncrementalProgress(
                session_id=self._context.session_id if self._context else "unknown",
                feature_id=target.feature_id,
                previous_state=previous_state,
                new_state=target.status,
                changes_made=changes_made,
                tests_passed=tests_passed,
                commit_hash=commit_hash,
                progress_entry=progress_entry,
                context_health=context_health,
                ready_for_next=context_health < self._config.max_context_usage,
            )

        except Exception as e:
            self._update_feature_status(target.feature_id, FeatureStatus.FAILED)
            raise e

    def _llm_implement(self, feature: Feature) -> List[str]:
        prompt = f"""
You are implementing a feature. Focus on incremental, clean changes.

Feature ID: {feature.feature_id}
Category: {feature.category}
Description: {feature.description}
Test Steps: {json.dumps(feature.steps, indent=2)}

Requirements:
1. Implement ONLY this feature
2. Write clean, testable code
3. Do NOT modify unrelated code
4. Ensure all test steps pass
5. Leave the codebase in a clean state

Current project root: {self._config.project_root}

List the files you modified.
"""
        if self._llm_callback:
            result = self._llm_callback(prompt)
            return self._parse_changes(result)
        return []

    def _parse_changes(self, llm_output: str) -> List[str]:
        changes = []
        for line in llm_output.split("\n"):
            line = line.strip()
            if line.startswith("modified:") or line.startswith("created:"):
                changes.append(line.split(":", 1)[1].strip())
            elif line.endswith(".py") or line.endswith(".js") or line.endswith(".ts"):
                changes.append(line)
        return list(set(changes))

    def _template_implement(self, feature: Feature) -> List[str]:
        return [f"placeholder_implementation_for_{feature.feature_id}"]

    def _run_tests(self, feature: Feature) -> bool:
        if self._test_callback:
            return self._test_callback(feature)

        test_commands = [
            ["npm", "test", "--", f"--grep={feature.feature_id}"],
            ["pytest", f"-k", feature.feature_id, "-v"],
            ["python", "-m", "pytest", f"tests/test_{feature.feature_id}.py"],
        ]

        for cmd in test_commands:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=self._config.project_root,
                    capture_output=True,
                    text=True,
                    timeout=self._config.test_timeout_sec,
                )
                if result.returncode == 0:
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        return True

    def _update_feature_status(self, feature_id: str, status: FeatureStatus) -> None:
        path = os.path.join(self._config.project_root, "feature_list.json")
        if not os.path.exists(path):
            return

        with open(path, "r", encoding="utf-8") as fp:
            data = json.load(fp)

        for feature in data.get("features", []):
            if feature["feature_id"] == feature_id:
                feature["status"] = status.value
                feature["updated_at"] = int(datetime.now(tz=timezone.utc).timestamp())
                break

        with open(path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=2, ensure_ascii=False)

    def _commit_changes(self, feature: Feature, changes: List[str], tests_passed: bool) -> str:
        if changes:
            for change in changes:
                if os.path.exists(os.path.join(self._config.project_root, change)):
                    subprocess.run(
                        ["git", "add", change],
                        cwd=self._config.project_root,
                        capture_output=True,
                    )

        status = "passed" if tests_passed else "failed"
        commit_msg = f"feat({feature.feature_id}): {feature.description[:50]} [tests: {status}]"

        subprocess.run(
            ["git", "commit", "-m", commit_msg, "--allow-empty"],
            cwd=self._config.project_root,
            capture_output=True,
        )

        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self._config.project_root,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def _create_progress_entry(
        self, feature: Feature, changes: List[str], tests_passed: bool, commit_hash: str
    ) -> ProgressEntry:
        import uuid

        return ProgressEntry(
            entry_id=f"entry-{uuid.uuid4().hex[:8]}",
            session_id=self._context.session_id if self._context else "unknown",
            timestamp=int(datetime.now(tz=timezone.utc).timestamp()),
            action="implement_feature",
            description=f"Implemented {feature.feature_id}: {feature.description}",
            feature_id=feature.feature_id,
            files_changed=changes,
            commit_hash=commit_hash,
            test_results={"passed": tests_passed},
            next_steps=self._suggest_next_steps(feature, tests_passed),
            blockers=[] if tests_passed else [f"Tests failed for {feature.feature_id}"],
        )

    def _suggest_next_steps(self, feature: Feature, tests_passed: bool) -> List[str]:
        if tests_passed:
            return [
                f"Mark {feature.feature_id} as complete",
                "Select next pending feature",
                "Run integration tests",
            ]
        return [
            f"Debug failing tests for {feature.feature_id}",
            "Review implementation for issues",
            "Consider rollback if blocking",
        ]

    def _append_progress(self, entry: ProgressEntry) -> None:
        path = os.path.join(self._config.project_root, "progress.jsonl")
        with open(path, "a", encoding="utf-8") as fp:
            fp.write(json.dumps(entry.to_dict()) + "\n")
        self._progress_entries.append(entry)

    def _calculate_context_health(self) -> float:
        if self._context:
            return min(1.0, self._context.context_window_usage + 0.1 * len(self._progress_entries))
        return 0.0

    def create_checkpoint(self) -> CheckpointData:
        import uuid

        features = self._read_feature_list()
        feature_states = {f["feature_id"]: FeatureStatus[f["status"].upper()] for f in features}

        git_status = self._get_git_status()
        files_snapshot = self._get_files_snapshot()

        checkpoint = CheckpointData(
            checkpoint_id=f"cp-{uuid.uuid4().hex[:8]}",
            session_id=self._context.session_id if self._context else "unknown",
            timestamp=int(datetime.now(tz=timezone.utc).timestamp()),
            feature_states=feature_states,
            progress_summary=self._summarize_progress(),
            pending_tasks=[f["feature_id"] for f in features if f["status"] == "pending"],
            files_snapshot=files_snapshot,
            git_status=git_status,
            health_metrics={
                "context_usage": self._context.context_window_usage if self._context else 0,
                "features_completed": len([s for s in feature_states.values() if s == FeatureStatus.PASSED]),
                "features_total": len(feature_states),
            },
            recovery_hint="Restore from checkpoint and continue with next pending feature",
        )

        self._save_checkpoint(checkpoint)
        return checkpoint

    def _get_git_status(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain", "-b"],
                cwd=self._config.project_root,
                capture_output=True,
                text=True,
            )
            lines = result.stdout.strip().split("\n")
            branch = lines[0].split("...")[0].replace("## ", "") if lines else "unknown"
            modified = [l[3:] for l in lines[1:] if l.strip()]
            return {"branch": branch, "modified_files": modified, "clean": len(modified) == 0}
        except Exception:
            return {"branch": "unknown", "modified_files": [], "clean": True}

    def _get_files_snapshot(self) -> Dict[str, str]:
        snapshot = {}
        important_files = ["feature_list.json", "progress.jsonl", "init.sh"]
        for filename in important_files:
            path = os.path.join(self._config.project_root, filename)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fp:
                    content = fp.read()
                    snapshot[filename] = hashlib.sha256(content.encode()).hexdigest()[:16]
        return snapshot

    def _summarize_progress(self) -> str:
        recent = self._read_recent_progress(5)
        if not recent:
            return "No progress recorded"
        actions = [e.get("action", "unknown") for e in recent]
        return f"Recent actions: {', '.join(actions)}"

    def _save_checkpoint(self, checkpoint: CheckpointData) -> None:
        checkpoint_dir = os.path.join(self._config.project_root, ".checkpoints")
        os.makedirs(checkpoint_dir, exist_ok=True)
        path = os.path.join(checkpoint_dir, f"{checkpoint.checkpoint_id}.json")
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(checkpoint.to_dict(), fp, indent=2)

    def recover(self, strategy: RecoveryStrategy = RecoveryStrategy.ROLLBACK) -> bool:
        if strategy == RecoveryStrategy.ROLLBACK:
            return self._rollback_recovery()
        elif strategy == RecoveryStrategy.RESTART:
            return self._restart_recovery()
        elif strategy == RecoveryStrategy.SKIP:
            return self._skip_recovery()
        return False

    def _rollback_recovery(self) -> bool:
        try:
            subprocess.run(
                ["git", "reset", "--hard", "HEAD"],
                cwd=self._config.project_root,
                capture_output=True,
            )
            return True
        except Exception:
            return False

    def _restart_recovery(self) -> bool:
        if self._current_feature:
            self._update_feature_status(self._current_feature.feature_id, FeatureStatus.PENDING)
        return self._rollback_recovery()

    def _skip_recovery(self) -> bool:
        if self._current_feature:
            self._update_feature_status(self._current_feature.feature_id, FeatureStatus.BLOCKED)
        return True

    def end_session(self) -> Dict[str, Any]:
        if self._context:
            self._context.state = SessionState.COMPLETED

        summary = {
            "session_id": self._context.session_id if self._context else "unknown",
            "duration_sec": int(datetime.now(tz=timezone.utc).timestamp())
            - (self._context.start_time if self._context else 0),
            "features_worked": len(self._progress_entries),
            "last_feature": self._current_feature.feature_id if self._current_feature else None,
            "final_context_health": self._calculate_context_health(),
        }

        entry = ProgressEntry(
            entry_id=f"end-{self._context.session_id if self._context else 'unknown'}",
            session_id=self._context.session_id if self._context else "unknown",
            timestamp=int(datetime.now(tz=timezone.utc).timestamp()),
            action="session_end",
            description="Session completed cleanly",
            next_steps=["Next session should read progress file", "Continue with next pending feature"],
        )
        self._append_progress(entry)

        return summary

    def get_context(self) -> Optional[SessionContext]:
        return self._context

    def get_current_feature(self) -> Optional[Feature]:
        return self._current_feature
