from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AuditDimension(Enum):
    CODE_QUALITY = "code_quality"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    COMPLIANCE = "compliance"


@dataclass(frozen=True)
class CodeLocation:
    file_path: str
    line_start: int
    line_end: Optional[int] = None
    function_name: Optional[str] = None
    class_name: Optional[str] = None


@dataclass(frozen=True)
class AuditIssue:
    issue_id: str
    severity: Severity
    category: str
    dimension: AuditDimension
    location: Optional[CodeLocation]
    description: str
    suggestion: str
    rule_id: Optional[str] = None
    references: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class DimensionScore:
    dimension: AuditDimension
    score: float
    max_score: float = 100.0
    details: List[str] = field(default_factory=list)
    issues_count: int = 0
    
    @property
    def percentage(self) -> float:
        return (self.score / self.max_score) * 100 if self.max_score > 0 else 0


@dataclass(frozen=True)
class Recommendation:
    recommendation_id: str
    priority: int
    category: str
    description: str
    impact: str
    effort: str


@dataclass(frozen=True)
class CodeArtifacts:
    files: Dict[str, str]
    language: str = "python"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditReport:
    report_id: str
    execution_id: str
    auditor_instance: str
    
    overall_score: float
    passed: bool
    
    dimensions: List[DimensionScore]
    issues: List[AuditIssue]
    recommendations: List[Recommendation]
    
    code_artifacts_hash: str = ""
    audit_duration_ms: int = 0
    created_at: int = 0
    
    def __post_init__(self):
        if self.created_at == 0:
            object.__setattr__(
                self,
                "created_at",
                int(datetime.now(tz=timezone.utc).timestamp()),
            )
    
    def get_issues_by_severity(self, severity: Severity) -> List[AuditIssue]:
        return [i for i in self.issues if i.severity == severity]
    
    def get_critical_issues(self) -> List[AuditIssue]:
        return self.get_issues_by_severity(Severity.CRITICAL)
    
    def get_high_issues(self) -> List[AuditIssue]:
        return self.get_issues_by_severity(Severity.HIGH)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "execution_id": self.execution_id,
            "auditor_instance": self.auditor_instance,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "dimensions": [
                {
                    "dimension": d.dimension.value,
                    "score": d.score,
                    "max_score": d.max_score,
                    "percentage": d.percentage,
                    "issues_count": d.issues_count,
                }
                for d in self.dimensions
            ],
            "issues": [
                {
                    "issue_id": i.issue_id,
                    "severity": i.severity.value,
                    "category": i.category,
                    "description": i.description,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ],
            "recommendations": [
                {
                    "priority": r.priority,
                    "category": r.category,
                    "description": r.description,
                }
                for r in self.recommendations
            ],
            "created_at": self.created_at,
        }


@dataclass
class AuditTask:
    audit_id: str
    execution_id: str
    code_artifacts: CodeArtifacts
    auditor_instance: str
    standards: List[str]
    required_score: float = 0.8
    dimensions: List[AuditDimension] = field(default_factory=list)
    created_at: int = 0
    
    def __post_init__(self):
        if self.created_at == 0:
            object.__setattr__(
                self,
                "created_at",
                int(datetime.now(tz=timezone.utc).timestamp()),
            )


@dataclass
class AuditContext:
    audit_id: str
    standards: List[str]
    isolation_mode: bool = True
    executor_identity_hidden: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeedbackAction:
    action_type: str
    target_stage: Optional[str] = None
    issues: List[AuditIssue] = field(default_factory=list)
    max_retries: int = 3
    message: str = ""
