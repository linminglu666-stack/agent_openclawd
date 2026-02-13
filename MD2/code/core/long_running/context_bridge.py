from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base_types import (
    BridgedContext,
    CheckpointData,
    Feature,
    FeatureStatus,
    Priority,
    ProgressEntry,
    SessionContext,
    SessionType,
)


@dataclass
class ContextBridgeConfig:
    project_root: str
    feature_list_path: str = "feature_list.json"
    progress_file_path: str = "progress.jsonl"
    checkpoint_dir: str = ".checkpoints"
    git_history_limit: int = 20
    progress_history_limit: int = 10


class ContextBridge:
    def __init__(self, config: ContextBridgeConfig):
        self._config = config

    def bridge(self, source_session: str, target_session: str) -> BridgedContext:
        feature_list = self._load_feature_list()
        recent_progress = self._load_recent_progress()
        last_checkpoint = self._load_last_checkpoint()
        git_history = self._load_git_history()
        environment_state = self._analyze_environment()
        recommendations = self._generate_recommendations(feature_list, recent_progress)
        urgent_issues = self._identify_urgent_issues(recent_progress, environment_state)

        return BridgedContext(
            source_session=source_session,
            target_session=target_session,
            feature_list=feature_list,
            recent_progress=recent_progress,
            last_checkpoint=last_checkpoint,
            git_history=git_history,
            environment_state=environment_state,
            recommendations=recommendations,
            urgent_issues=urgent_issues,
        )

    def _load_feature_list(self) -> List[Feature]:
        features = []
        path = os.path.join(self._config.project_root, self._config.feature_list_path)

        if not os.path.exists(path):
            return features

        with open(path, "r", encoding="utf-8") as fp:
            data = json.load(fp)

        for item in data.get("features", []):
            try:
                feature = Feature(
                    feature_id=item["feature_id"],
                    category=item["category"],
                    description=item["description"],
                    steps=item.get("steps", []),
                    status=FeatureStatus[item.get("status", "PENDING").upper()],
                    priority=Priority[item.get("priority", "MEDIUM").upper()],
                    dependencies=item.get("dependencies", []),
                    test_criteria=item.get("test_criteria", []),
                    created_at=item.get("created_at", 0),
                    updated_at=item.get("updated_at", 0),
                )
                features.append(feature)
            except (KeyError, ValueError):
                continue

        return features

    def _load_recent_progress(self) -> List[ProgressEntry]:
        entries = []
        path = os.path.join(self._config.project_root, self._config.progress_file_path)

        if not os.path.exists(path):
            return entries

        with open(path, "r", encoding="utf-8") as fp:
            lines = fp.readlines()[-self._config.progress_history_limit :]

        for line in lines:
            try:
                data = json.loads(line)
                entry = ProgressEntry(
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
                entries.append(entry)
            except (json.JSONDecodeError, KeyError):
                continue

        return entries

    def _load_last_checkpoint(self) -> Optional[CheckpointData]:
        checkpoint_dir = os.path.join(self._config.project_root, self._config.checkpoint_dir)

        if not os.path.exists(checkpoint_dir):
            return None

        checkpoints = []
        for filename in os.listdir(checkpoint_dir):
            if filename.endswith(".json"):
                path = os.path.join(checkpoint_dir, filename)
                try:
                    with open(path, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                    checkpoints.append((data.get("timestamp", 0), data))
                except (json.JSONDecodeError, KeyError):
                    continue

        if not checkpoints:
            return None

        checkpoints.sort(reverse=True)
        latest = checkpoints[0][1]

        feature_states = {}
        for fid, status in latest.get("feature_states", {}).items():
            try:
                feature_states[fid] = FeatureStatus[status.upper()]
            except KeyError:
                feature_states[fid] = FeatureStatus.PENDING

        return CheckpointData(
            checkpoint_id=latest["checkpoint_id"],
            session_id=latest["session_id"],
            timestamp=latest["timestamp"],
            feature_states=feature_states,
            progress_summary=latest.get("progress_summary", ""),
            pending_tasks=latest.get("pending_tasks", []),
            files_snapshot=latest.get("files_snapshot", {}),
            git_status=latest.get("git_status", {}),
            health_metrics=latest.get("health_metrics", {}),
            recovery_hint=latest.get("recovery_hint"),
        )

    def _load_git_history(self) -> List[Dict[str, Any]]:
        commits = []
        try:
            result = subprocess.run(
                ["git", "log", f"-{self._config.git_history_limit}", "--format=%H|%s|%an|%ci"],
                cwd=self._config.project_root,
                capture_output=True,
                text=True,
            )

            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("|")
                    if len(parts) >= 4:
                        commits.append(
                            {
                                "hash": parts[0],
                                "message": parts[1],
                                "author": parts[2],
                                "date": parts[3],
                            }
                        )
        except Exception:
            pass

        return commits

    def _analyze_environment(self) -> Dict[str, Any]:
        state = {
            "git_clean": self._is_git_clean(),
            "feature_list_exists": os.path.exists(
                os.path.join(self._config.project_root, self._config.feature_list_path)
            ),
            "progress_file_exists": os.path.exists(
                os.path.join(self._config.project_root, self._config.progress_file_path)
            ),
            "init_script_exists": os.path.exists(
                os.path.join(self._config.project_root, "init.sh")
            ),
            "has_checkpoints": os.path.exists(
                os.path.join(self._config.project_root, self._config.checkpoint_dir)
            ),
            "current_branch": self._get_current_branch(),
        }

        state["issues"] = []
        if not state["feature_list_exists"]:
            state["issues"].append("Missing feature_list.json")
        if not state["git_clean"]:
            state["issues"].append("Uncommitted changes detected")
        if not state["init_script_exists"]:
            state["issues"].append("Missing init.sh script")

        return state

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
            return True

    def _get_current_branch(self) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self._config.project_root,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip() or "unknown"
        except Exception:
            return "unknown"

    def _generate_recommendations(
        self, features: List[Feature], progress: List[ProgressEntry]
    ) -> List[str]:
        recommendations = []

        next_feature = None
        for f in sorted(features, key=lambda x: x.priority.value):
            if f.status in (FeatureStatus.PENDING, FeatureStatus.FAILED):
                deps_satisfied = all(
                    any(d.feature_id == dep and d.status == FeatureStatus.PASSED for d in features)
                    for dep in f.dependencies
                )
                if deps_satisfied:
                    next_feature = f
                    break

        if next_feature:
            recommendations.append(f"Continue with feature: {next_feature.feature_id} - {next_feature.description}")
        else:
            pending = [f for f in features if f.status == FeatureStatus.PENDING]
            if pending:
                recommendations.append(f"Review blocked features: {[f.feature_id for f in pending]}")

        failed_features = [f for f in features if f.status == FeatureStatus.FAILED]
        if failed_features:
            recommendations.append(f"Retry failed features: {[f.feature_id for f in failed_features]}")

        in_progress = [f for f in features if f.status == FeatureStatus.IN_PROGRESS]
        if in_progress:
            recommendations.append(f"Resume in-progress features: {[f.feature_id for f in in_progress]}")

        recent_blockers = []
        for entry in progress[-5:]:
            recent_blockers.extend(entry.blockers)
        if recent_blockers:
            recommendations.append(f"Address recent blockers: {list(set(recent_blockers))}")

        return recommendations

    def _identify_urgent_issues(
        self, progress: List[ProgressEntry], environment: Dict[str, Any]
    ) -> List[str]:
        issues = []

        issues.extend(environment.get("issues", []))

        for entry in progress[-3:]:
            if entry.test_results and not entry.test_results.get("passed"):
                issues.append(f"Recent test failure in {entry.feature_id}")

        for entry in progress[-5:]:
            for blocker in entry.blockers:
                issues.append(f"Active blocker: {blocker}")

        return list(set(issues))

    def quick_handoff(self, session_id: str) -> Dict[str, Any]:
        feature_list = self._load_feature_list()
        recent = self._load_recent_progress()

        completed = len([f for f in feature_list if f.status == FeatureStatus.PASSED])
        total = len(feature_list)
        next_feature = None

        for f in sorted(feature_list, key=lambda x: x.priority.value):
            if f.status == FeatureStatus.PENDING:
                next_feature = {
                    "feature_id": f.feature_id,
                    "description": f.description,
                    "priority": f.priority.name,
                }
                break

        return {
            "session_id": session_id,
            "timestamp": int(datetime.now(tz=timezone.utc).timestamp()),
            "progress_summary": {
                "completed": completed,
                "total": total,
                "percentage": (completed / total * 100) if total > 0 else 0,
            },
            "next_feature": next_feature,
            "last_action": recent[-1].action if recent else None,
            "last_description": recent[-1].description if recent else None,
            "git_branch": self._get_current_branch(),
            "is_clean": self._is_git_clean(),
        }

    def create_handoff_document(self, session_id: str) -> str:
        context = self.bridge(session_id, f"{session_id}-next")

        lines = [
            f"# Session Handoff Document",
            f"",
            f"**From Session:** {context.source_session}",
            f"**To Session:** {context.target_session}",
            f"**Generated:** {datetime.now(tz=timezone.utc).isoformat()}",
            f"",
            f"## Current State",
            f"",
            f"- **Completed Features:** {len([f for f in context.feature_list if f.status == FeatureStatus.PASSED])}",
            f"- **Pending Features:** {len([f for f in context.feature_list if f.status == FeatureStatus.PENDING])}",
            f"- **Failed Features:** {len([f for f in context.feature_list if f.status == FeatureStatus.FAILED])}",
            f"- **Git Branch:** {context.environment_state.get('current_branch', 'unknown')}",
            f"- **Working Tree Clean:** {context.environment_state.get('git_clean', False)}",
            f"",
            f"## Recommendations",
            f"",
        ]

        for rec in context.recommendations:
            lines.append(f"- {rec}")

        lines.extend(
            [
                f"",
                f"## Urgent Issues",
                f"",
            ]
        )

        if context.urgent_issues:
            for issue in context.urgent_issues:
                lines.append(f"- ⚠️ {issue}")
        else:
            lines.append("- No urgent issues")

        next_feature = context.get_next_feature()
        if next_feature:
            lines.extend(
                [
                    f"",
                    f"## Next Feature to Work On",
                    f"",
                    f"**Feature ID:** {next_feature.feature_id}",
                    f"**Category:** {next_feature.category}",
                    f"**Priority:** {next_feature.priority.name}",
                    f"**Description:** {next_feature.description}",
                    f"",
                    f"### Test Steps",
                    f"",
                ]
            )
            for i, step in enumerate(next_feature.steps, 1):
                lines.append(f"{i}. {step}")

        blockers = context.get_active_blockers()
        if blockers:
            lines.extend(
                [
                    f"",
                    f"## Active Blockers",
                    f"",
                ]
            )
            for blocker in blockers:
                lines.append(f"- {blocker}")

        lines.extend(
            [
                f"",
                f"## Recent Git Commits",
                f"",
            ]
        )
        for commit in context.git_history[:5]:
            lines.append(f"- `{commit['hash'][:8]}` {commit['message']}")

        return "\n".join(lines)
