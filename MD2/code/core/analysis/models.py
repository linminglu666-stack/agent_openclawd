from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskType(Enum):
    FEATURE_DEVELOPMENT = "feature_development"
    BUG_FIX = "bug_fix"
    DATA_ANALYSIS = "data_analysis"
    CONTENT_CREATION = "content_creation"
    CODE_REFACTORING = "code_refactoring"
    SYSTEM_DESIGN = "system_design"
    RESEARCH = "research"
    GENERAL = "general"


class ComplexityLevel(Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditLevel(Enum):
    NONE = "none"
    BASIC = "basic"
    STANDARD = "standard"
    DEEP = "deep"
    EXPERT = "expert"


@dataclass(frozen=True)
class SkillRequirement:
    skill_name: str
    min_level: int
    priority: int = 5
    description: str = ""


@dataclass(frozen=True)
class Dependency:
    dependency_id: str
    dependency_type: str
    description: str
    is_resolved: bool = False


@dataclass(frozen=True)
class AuditRequirement:
    level: AuditLevel
    dimensions: List[str]
    required_score: float = 0.8
    max_retries: int = 3


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    name: str
    profession_id: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)
    next_stages: List[str] = field(default_factory=list)
    is_audit_stage: bool = False
    timeout: int = 300


@dataclass(frozen=True)
class ParallelGroup:
    group_id: str
    stages: List[str]
    merge_strategy: str = "all"


@dataclass(frozen=True)
class WorkflowRecommendation:
    template_id: str
    stages: List[StageSpec]
    required_professions: List[str]
    audit_stages: List[str]
    estimated_duration: int
    parallel_opportunities: List[ParallelGroup] = field(default_factory=list)


@dataclass(frozen=True)
class TaskContext:
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    project_id: Optional[str] = None
    previous_tasks: List[str] = field(default_factory=list)
    available_resources: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskAnalysis:
    task_id: str
    request: str
    task_type: TaskType
    complexity: ComplexityLevel
    skills_needed: List[SkillRequirement]
    dependencies: List[Dependency]
    risk_level: RiskLevel
    estimated_time: int
    audit_requirement: AuditRequirement
    workflow_recommendation: WorkflowRecommendation
    context: TaskContext
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "request": self.request,
            "task_type": self.task_type.value,
            "complexity": self.complexity.value,
            "skills_needed": [
                {
                    "skill_name": s.skill_name,
                    "min_level": s.min_level,
                    "priority": s.priority,
                }
                for s in self.skills_needed
            ],
            "dependencies": [
                {
                    "dependency_id": d.dependency_id,
                    "dependency_type": d.dependency_type,
                    "description": d.description,
                }
                for d in self.dependencies
            ],
            "risk_level": self.risk_level.value,
            "estimated_time": self.estimated_time,
            "audit_requirement": {
                "level": self.audit_requirement.level.value,
                "dimensions": self.audit_requirement.dimensions,
                "required_score": self.audit_requirement.required_score,
            },
            "workflow_recommendation": {
                "template_id": self.workflow_recommendation.template_id,
                "stages": [
                    {
                        "stage_id": s.stage_id,
                        "name": s.name,
                        "profession_id": s.profession_id,
                        "is_audit_stage": s.is_audit_stage,
                    }
                    for s in self.workflow_recommendation.stages
                ],
                "audit_stages": self.workflow_recommendation.audit_stages,
            },
            "confidence": self.confidence,
        }
