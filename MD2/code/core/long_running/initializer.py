from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .base_types import (
    EnvironmentSetup,
    Feature,
    FeatureStatus,
    Priority,
    SessionContext,
    SessionState,
    SessionType,
)


@dataclass
class InitializerConfig:
    project_root: str
    spec_prompt: str
    feature_categories: List[str] = field(default_factory=lambda: [
        "functional",
        "ui",
        "api",
        "performance",
        "security",
        "accessibility",
    ])
    max_features: int = 500
    auto_detect_dependencies: bool = True
    create_git_repo: bool = True
    init_script_template: str = "standard"


class InitializerAgent:
    def __init__(self, config: InitializerConfig):
        self._config = config
        self._features: List[Feature] = []
        self._context: Optional[SessionContext] = None
        self._llm_callback: Optional[Callable] = None
        self._tools: Dict[str, Callable] = {}

    def set_llm_callback(self, callback: Callable) -> None:
        self._llm_callback = callback

    def register_tool(self, name: str, handler: Callable) -> None:
        self._tools[name] = handler

    def initialize(self, spec_prompt: Optional[str] = None) -> EnvironmentSetup:
        prompt = spec_prompt or self._config.spec_prompt
        self._context = self._create_session_context()
        self._context.state = SessionState.INITIALIZING

        try:
            self._setup_project_structure()
            self._features = self._generate_feature_list(prompt)
            self._write_feature_list()
            init_script = self._generate_init_script()
            self._write_init_script(init_script)
            self._write_progress_file()
            commit_hash = self._create_initial_commit()
            config_files = self._detect_or_create_configs()

            self._context.state = SessionState.ACTIVE

            return EnvironmentSetup(
                project_root=self._config.project_root,
                feature_list=self._features,
                init_script_content=init_script,
                initial_commit_hash=commit_hash,
                config_files=config_files,
                dependencies=self._detect_dependencies(),
                setup_timestamp=int(datetime.now(tz=timezone.utc).timestamp()),
            )
        except Exception as e:
            self._context.state = SessionState.FAILED
            raise e

    def _create_session_context(self) -> SessionContext:
        import uuid

        return SessionContext(
            session_id=f"init-{uuid.uuid4().hex[:8]}",
            session_type=SessionType.INITIALIZER,
            state=SessionState.PENDING,
            project_root=self._config.project_root,
            start_time=int(datetime.now(tz=timezone.utc).timestamp()),
        )

    def _setup_project_structure(self) -> None:
        os.makedirs(self._config.project_root, exist_ok=True)
        for subdir in ["src", "tests", "docs", "config"]:
            os.makedirs(os.path.join(self._config.project_root, subdir), exist_ok=True)

    def _generate_feature_list(self, spec_prompt: str) -> List[Feature]:
        features = []

        if self._llm_callback:
            features = self._llm_feature_generation(spec_prompt)
        else:
            features = self._template_feature_generation(spec_prompt)

        return features[: self._config.max_features]

    def _llm_feature_generation(self, spec_prompt: str) -> List[Feature]:
        generation_prompt = f"""
You are a feature decomposition specialist. Given the following specification,
generate a comprehensive list of atomic, testable features.

Specification:
{spec_prompt}

For each feature, provide:
1. A unique feature_id (e.g., "feat-001")
2. Category (functional, ui, api, performance, security, accessibility)
3. Description (clear, testable statement)
4. Test steps (list of verification steps)
5. Priority (critical, high, medium, low)
6. Dependencies (list of feature_ids this depends on)

Output as JSON array. Each feature should be independently testable.
"""
        if self._llm_callback:
            result = self._llm_callback(generation_prompt)
            return self._parse_llm_features(result)
        return []

    def _parse_llm_features(self, llm_output: str) -> List[Feature]:
        features = []
        try:
            data = json.loads(llm_output)
            for i, item in enumerate(data):
                feature = Feature(
                    feature_id=item.get("feature_id", f"feat-{i+1:03d}"),
                    category=item.get("category", "functional"),
                    description=item.get("description", ""),
                    steps=item.get("test_steps", item.get("steps", [])),
                    status=FeatureStatus.PENDING,
                    priority=Priority[item.get("priority", "MEDIUM").upper()],
                    dependencies=item.get("dependencies", []),
                    test_criteria=item.get("test_criteria", []),
                )
                features.append(feature)
        except (json.JSONDecodeError, KeyError):
            pass
        return features

    def _template_feature_generation(self, spec_prompt: str) -> List[Feature]:
        features = []
        words = spec_prompt.lower().split()

        base_features = [
            Feature(
                feature_id="feat-001",
                category="functional",
                description="Application starts and displays main interface",
                steps=["Start application", "Verify main interface loads", "Check no errors in console"],
                priority=Priority.CRITICAL,
            ),
            Feature(
                feature_id="feat-002",
                category="functional",
                description="User can perform basic operations",
                steps=["Navigate to main feature", "Perform basic action", "Verify expected result"],
                priority=Priority.HIGH,
            ),
            Feature(
                feature_id="feat-003",
                category="ui",
                description="UI components render correctly",
                steps=["Load application", "Check all UI elements visible", "Verify responsive layout"],
                priority=Priority.MEDIUM,
            ),
        ]

        features.extend(base_features)
        return features

    def _write_feature_list(self) -> None:
        path = os.path.join(self._config.project_root, "feature_list.json")
        data = {
            "version": "1.0",
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "features": [
                {
                    "feature_id": f.feature_id,
                    "category": f.category,
                    "description": f.description,
                    "steps": f.steps,
                    "status": f.status.value,
                    "priority": f.priority.value,
                    "dependencies": f.dependencies,
                    "test_criteria": f.test_criteria,
                }
                for f in self._features
            ],
            "statistics": {
                "total": len(self._features),
                "by_category": self._count_by_category(),
                "by_priority": self._count_by_priority(),
            },
        }
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=2, ensure_ascii=False)

    def _count_by_category(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for f in self._features:
            counts[f.category] = counts.get(f.category, 0) + 1
        return counts

    def _count_by_priority(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for f in self._features:
            key = f.priority.name
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _generate_init_script(self) -> str:
        template = self._config.init_script_template

        if template == "standard":
            return self._standard_init_script()
        return self._minimal_init_script()

    def _standard_init_script(self) -> str:
        return '''#!/bin/bash
set -e

echo "Initializing project environment..."

if [ -f "package.json" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi

if [ -f "requirements.txt" ]; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
fi

if [ -f "setup.py" ]; then
    echo "Setting up Python package..."
    pip install -e .
fi

echo "Starting development server..."
if [ -f "package.json" ]; then
    npm run dev 2>&1 &
elif [ -f "manage.py" ]; then
    python manage.py runserver 2>&1 &
fi

echo "Environment ready!"
'''

    def _minimal_init_script(self) -> str:
        return '''#!/bin/bash
echo "Minimal environment setup complete."
'''

    def _write_init_script(self, content: str) -> None:
        path = os.path.join(self._config.project_root, "init.sh")
        with open(path, "w", encoding="utf-8") as fp:
            fp.write(content)
        os.chmod(path, 0o755)

    def _write_progress_file(self) -> None:
        path = os.path.join(self._config.project_root, "progress.jsonl")
        entry = {
            "timestamp": int(datetime.now(tz=timezone.utc).timestamp()),
            "session_id": self._context.session_id if self._context else "unknown",
            "action": "initialize",
            "description": "Project initialized with feature list",
            "feature_id": None,
            "files_changed": ["feature_list.json", "init.sh", "progress.jsonl"],
            "next_steps": ["Run init.sh", "Start implementing first feature"],
        }
        with open(path, "w", encoding="utf-8") as fp:
            fp.write(json.dumps(entry) + "\n")

    def _create_initial_commit(self) -> str:
        if not self._config.create_git_repo:
            return ""

        git_dir = os.path.join(self._config.project_root, ".git")
        if not os.path.exists(git_dir):
            os.system(f"cd {self._config.project_root} && git init")

        os.system(f"cd {self._config.project_root} && git add -A")
        commit_msg = "Initial commit: Project scaffolding and feature list"
        os.system(f'cd {self._config.project_root} && git commit -m "{commit_msg}"')

        import subprocess

        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self._config.project_root,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except Exception:
            return "initial-commit"

    def _detect_or_create_configs(self) -> Dict[str, str]:
        configs = {}
        config_templates = {
            ".gitignore": "*.pyc\n__pycache__/\n.env\nnode_modules/\n",
            "README.md": f"# Project\n\nInitialized at {datetime.now(tz=timezone.utc).isoformat()}\n",
        }

        for filename, content in config_templates.items():
            path = os.path.join(self._config.project_root, filename)
            if not os.path.exists(path):
                with open(path, "w") as fp:
                    fp.write(content)
                configs[filename] = content

        return configs

    def _detect_dependencies(self) -> List[str]:
        dependencies = []
        project_root = self._config.project_root

        package_json = os.path.join(project_root, "package.json")
        if os.path.exists(package_json):
            with open(package_json, "r") as fp:
                data = json.load(fp)
                dependencies.extend(data.get("dependencies", {}).keys())

        requirements = os.path.join(project_root, "requirements.txt")
        if os.path.exists(requirements):
            with open(requirements, "r") as fp:
                for line in fp:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        dependencies.append(line.split("==")[0].split(">=")[0])

        return dependencies

    def get_features(self) -> List[Feature]:
        return self._features.copy()

    def get_context(self) -> Optional[SessionContext]:
        return self._context
