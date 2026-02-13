from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class OutputTarget(Enum):
    WORKSPACE = "workspace"
    CLOUDRIVE = "cloudrive"
    DATASETS = "datasets"
    ANALYSIS = "analysis"
    TEMP = "temp"


class OutputCategory(Enum):
    CODE = "code"
    CONFIG = "config"
    DOCUMENT = "document"
    DATA = "data"
    IMAGE = "image"
    ARCHIVE = "archive"
    TRAINING = "training"
    ANALYSIS_DOC = "analysis_doc"
    OTHER = "other"


@dataclass(frozen=True)
class OutputContext:
    task_type: str = "general"
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    user_specified_target: Optional[OutputTarget] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RouteResult:
    target: OutputTarget
    path: str
    category: OutputCategory
    reason: str


@dataclass
class RoutingRule:
    pattern: str
    target: OutputTarget
    category: OutputCategory
    priority: int = 50
    description: str = ""


class OutputRouter:
    DEFAULT_RULES: List[RoutingRule] = [
        RoutingRule(
            pattern=r"\.py$|\.js$|\.ts$|\.go$|\.java$|\.rs$|\.cpp$|\.c$|\.h$",
            target=OutputTarget.WORKSPACE,
            category=OutputCategory.CODE,
            priority=100,
            description="Source code files",
        ),
        RoutingRule(
            pattern=r"\.yaml$|\.yml$|\.json$|\.toml$|\.ini$|\.cfg$|\.conf$",
            target=OutputTarget.WORKSPACE,
            category=OutputCategory.CONFIG,
            priority=90,
            description="Configuration files",
        ),
        RoutingRule(
            pattern=r"\.sh$|\.bat$|\.ps1$",
            target=OutputTarget.WORKSPACE,
            category=OutputCategory.CODE,
            priority=85,
            description="Script files",
        ),
        RoutingRule(
            pattern=r"\.xlsx$|\.xls$|\.csv$",
            target=OutputTarget.CLOUDRIVE,
            category=OutputCategory.DATA,
            priority=80,
            description="Spreadsheet files",
        ),
        RoutingRule(
            pattern=r"\.docx$|\.doc$|\.pdf$|\.pptx$|\.ppt$|\.odt$",
            target=OutputTarget.CLOUDRIVE,
            category=OutputCategory.DOCUMENT,
            priority=80,
            description="Document files",
        ),
        RoutingRule(
            pattern=r"\.png$|\.jpg$|\.jpeg$|\.gif$|\.svg$|\.webp$|\.bmp$",
            target=OutputTarget.CLOUDRIVE,
            category=OutputCategory.IMAGE,
            priority=70,
            description="Image files",
        ),
        RoutingRule(
            pattern=r"\.zip$|\.tar\.gz$|\.rar$|\.7z$|\.tar$|\.gz$",
            target=OutputTarget.CLOUDRIVE,
            category=OutputCategory.ARCHIVE,
            priority=60,
            description="Archive files",
        ),
        RoutingRule(
            pattern=r"\.pt$|\.pth$|\.bin$|\.onnx$|\.h5$|\.pkl$|\.model$",
            target=OutputTarget.DATASETS,
            category=OutputCategory.TRAINING,
            priority=95,
            description="Model files",
        ),
        RoutingRule(
            pattern=r"\.md$",
            target=OutputTarget.CLOUDRIVE,
            category=OutputCategory.DOCUMENT,
            priority=50,
            description="Markdown files",
        ),
    ]
    
    def __init__(
        self,
        rules: Optional[List[RoutingRule]] = None,
        default_target: OutputTarget = OutputTarget.CLOUDRIVE,
        strict_mode: bool = True,
    ):
        self._rules = sorted(
            rules or self.DEFAULT_RULES,
            key=lambda r: r.priority,
            reverse=True,
        )
        self._default_target = default_target
        self._strict_mode = strict_mode
        self._audit_log: List[Dict[str, Any]] = []
    
    def route(
        self,
        filename: str,
        context: Optional[OutputContext] = None,
    ) -> RouteResult:
        ctx = context or OutputContext()
        
        if ctx.user_specified_target:
            result = RouteResult(
                target=ctx.user_specified_target,
                path=self._build_path(ctx.user_specified_target, filename),
                category=OutputCategory.OTHER,
                reason="User specified target",
            )
            self._log_routing(filename, result, ctx)
            return result
        
        if ctx.task_type == "training":
            result = RouteResult(
                target=OutputTarget.DATASETS,
                path=self._build_path(OutputTarget.DATASETS, filename),
                category=OutputCategory.TRAINING,
                reason="Training task output",
            )
            self._log_routing(filename, result, ctx)
            return result
        
        if ctx.task_type == "analysis" and ctx.metadata.get("is_analysis_doc"):
            result = RouteResult(
                target=OutputTarget.ANALYSIS,
                path=self._build_path(OutputTarget.ANALYSIS, filename),
                category=OutputCategory.ANALYSIS_DOC,
                reason="Analysis document",
            )
            self._log_routing(filename, result, ctx)
            return result
        
        for rule in self._rules:
            if re.search(rule.pattern, filename, re.IGNORECASE):
                result = RouteResult(
                    target=rule.target,
                    path=self._build_path(rule.target, filename),
                    category=rule.category,
                    reason=rule.description,
                )
                self._log_routing(filename, result, ctx)
                return result
        
        result = RouteResult(
            target=self._default_target,
            path=self._build_path(self._default_target, filename),
            category=OutputCategory.OTHER,
            reason="Default routing",
        )
        self._log_routing(filename, result, ctx)
        return result
    
    def _build_path(self, target: OutputTarget, filename: str) -> str:
        date_prefix = datetime.now(tz=timezone.utc).strftime("%Y/%m/%d")
        return f"{target.value}/{date_prefix}/{filename}"
    
    def _log_routing(
        self,
        filename: str,
        result: RouteResult,
        context: OutputContext,
    ) -> None:
        self._audit_log.append({
            "timestamp": int(datetime.now(tz=timezone.utc).timestamp()),
            "filename": filename,
            "target": result.target.value,
            "category": result.category.value,
            "reason": result.reason,
            "task_type": context.task_type,
            "user_id": context.user_id,
        })
    
    def add_rule(self, rule: RoutingRule) -> None:
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._audit_log[-limit:]
    
    def validate_output(
        self,
        filename: str,
        actual_path: str,
        context: Optional[OutputContext] = None,
    ) -> bool:
        if not self._strict_mode:
            return True
        
        expected = self.route(filename, context)
        expected_prefix = expected.target.value
        
        if not actual_path.startswith(expected_prefix):
            self._audit_log.append({
                "timestamp": int(datetime.now(tz=timezone.utc).timestamp()),
                "event": "violation",
                "filename": filename,
                "expected_target": expected.target.value,
                "actual_path": actual_path,
                "user_id": context.user_id if context else None,
            })
            return False
        
        return True
    
    def get_target_root(self, target: OutputTarget) -> str:
        return target.value
    
    def classify_content(self, filename: str) -> OutputCategory:
        for rule in self._rules:
            if re.search(rule.pattern, filename, re.IGNORECASE):
                return rule.category
        return OutputCategory.OTHER
