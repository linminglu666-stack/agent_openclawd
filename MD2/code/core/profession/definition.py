from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ProfessionCategory(Enum):
    SOFTWARE = "software"
    DATA = "data"
    CONTENT = "content"
    RESEARCH = "research"
    GENERAL = "general"


@dataclass(frozen=True)
class Skill:
    name: str
    level: int
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "level": self.level,
            "description": self.description,
        }


@dataclass(frozen=True)
class CollaborationConfig:
    upstream: List[str] = field(default_factory=list)
    downstream: List[str] = field(default_factory=list)
    review_required: bool = False
    review_by: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProfessionConfig:
    preferred_model: str = "gpt-4"
    max_concurrent_tasks: int = 3
    timeout_multiplier: float = 1.0
    quality_threshold: float = 0.85
    retry_policy: str = "exponential_backoff"
    max_retries: int = 3


@dataclass
class Profession:
    profession_id: str
    name: str
    category: ProfessionCategory
    description: str = ""
    skills: List[Skill] = field(default_factory=list)
    task_types: List[str] = field(default_factory=list)
    collaboration: CollaborationConfig = field(default_factory=CollaborationConfig)
    config: ProfessionConfig = field(default_factory=ProfessionConfig)
    tags: List[str] = field(default_factory=list)
    
    def get_skill_level(self, skill_name: str) -> int:
        for skill in self.skills:
            if skill.name == skill_name:
                return skill.level
        return 0
    
    def has_skill(self, skill_name: str, min_level: int = 1) -> bool:
        return self.get_skill_level(skill_name) >= min_level
    
    def can_handle_task(self, task_type: str) -> bool:
        return task_type in self.task_types
    
    def get_upstream_professions(self) -> List[str]:
        return self.collaboration.upstream
    
    def get_downstream_professions(self) -> List[str]:
        return self.collaboration.downstream
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "profession_id": self.profession_id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "skills": [s.to_dict() for s in self.skills],
            "task_types": self.task_types,
            "collaboration": {
                "upstream": self.collaboration.upstream,
                "downstream": self.collaboration.downstream,
                "review_required": self.collaboration.review_required,
                "review_by": self.collaboration.review_by,
            },
            "config": {
                "preferred_model": self.config.preferred_model,
                "max_concurrent_tasks": self.config.max_concurrent_tasks,
                "timeout_multiplier": self.config.timeout_multiplier,
                "quality_threshold": self.config.quality_threshold,
            },
            "tags": self.tags,
        }


BUILTIN_PROFESSIONS: List[Dict[str, Any]] = [
    {
        "profession_id": "product_manager",
        "name": "产品经理",
        "category": "software",
        "description": "负责产品需求分析、规划和设计",
        "skills": [
            {"name": "requirement_analysis", "level": 9, "description": "需求分析能力"},
            {"name": "prototyping", "level": 7, "description": "原型设计能力"},
            {"name": "prioritization", "level": 8, "description": "优先级排序能力"},
            {"name": "communication", "level": 8, "description": "沟通协调能力"},
        ],
        "task_types": ["prd_writing", "requirement_review", "roadmap_planning", "feature_design"],
        "collaboration": {
            "upstream": [],
            "downstream": ["architect", "developer"],
            "review_required": False,
            "review_by": [],
        },
        "config": {
            "preferred_model": "gpt-4",
            "max_concurrent_tasks": 3,
            "timeout_multiplier": 1.2,
            "quality_threshold": 0.85,
        },
        "tags": ["planning", "documentation", "communication"],
    },
    {
        "profession_id": "architect",
        "name": "架构师",
        "category": "software",
        "description": "负责系统架构设计和技术选型",
        "skills": [
            {"name": "system_design", "level": 9, "description": "系统设计能力"},
            {"name": "tech_selection", "level": 8, "description": "技术选型能力"},
            {"name": "evaluation", "level": 8, "description": "技术评估能力"},
            {"name": "documentation", "level": 7, "description": "文档编写能力"},
        ],
        "task_types": ["architecture_design", "tech_proposal", "code_review", "performance_analysis"],
        "collaboration": {
            "upstream": ["product_manager"],
            "downstream": ["developer"],
            "review_required": True,
            "review_by": ["tech_lead"],
        },
        "config": {
            "preferred_model": "gpt-4",
            "max_concurrent_tasks": 2,
            "timeout_multiplier": 1.5,
            "quality_threshold": 0.90,
        },
        "tags": ["design", "technical", "review"],
    },
    {
        "profession_id": "developer",
        "name": "开发工程师",
        "category": "software",
        "description": "负责功能开发和代码实现",
        "skills": [
            {"name": "coding", "level": 9, "description": "代码编写能力"},
            {"name": "debugging", "level": 8, "description": "调试排错能力"},
            {"name": "refactoring", "level": 7, "description": "代码重构能力"},
            {"name": "testing", "level": 7, "description": "单元测试能力"},
        ],
        "task_types": ["feature_development", "bug_fix", "code_refactoring", "code_review"],
        "collaboration": {
            "upstream": ["product_manager", "architect"],
            "downstream": ["qa_engineer"],
            "review_required": True,
            "review_by": ["architect", "senior_developer"],
        },
        "config": {
            "preferred_model": "gpt-4",
            "max_concurrent_tasks": 5,
            "timeout_multiplier": 1.0,
            "quality_threshold": 0.85,
        },
        "tags": ["coding", "implementation", "debugging"],
    },
    {
        "profession_id": "qa_engineer",
        "name": "测试工程师",
        "category": "software",
        "description": "负责测试设计和质量保障",
        "skills": [
            {"name": "test_design", "level": 8, "description": "测试设计能力"},
            {"name": "automation", "level": 7, "description": "自动化测试能力"},
            {"name": "performance_testing", "level": 6, "description": "性能测试能力"},
            {"name": "bug_tracking", "level": 8, "description": "缺陷管理能力"},
        ],
        "task_types": ["test_case_design", "test_execution", "bug_verification", "test_report"],
        "collaboration": {
            "upstream": ["developer"],
            "downstream": ["devops"],
            "review_required": False,
            "review_by": [],
        },
        "config": {
            "preferred_model": "gpt-4",
            "max_concurrent_tasks": 4,
            "timeout_multiplier": 1.0,
            "quality_threshold": 0.90,
        },
        "tags": ["testing", "quality", "automation"],
    },
    {
        "profession_id": "data_engineer",
        "name": "数据工程师",
        "category": "data",
        "description": "负责数据管道和数据仓库建设",
        "skills": [
            {"name": "etl", "level": 9, "description": "ETL开发能力"},
            {"name": "data_modeling", "level": 8, "description": "数据建模能力"},
            {"name": "sql", "level": 9, "description": "SQL能力"},
            {"name": "pipeline", "level": 8, "description": "管道开发能力"},
        ],
        "task_types": ["etl_development", "data_pipeline", "data_warehouse", "data_cleaning"],
        "collaboration": {
            "upstream": [],
            "downstream": ["data_analyst"],
            "review_required": False,
            "review_by": [],
        },
        "config": {
            "preferred_model": "gpt-4",
            "max_concurrent_tasks": 3,
            "timeout_multiplier": 1.2,
            "quality_threshold": 0.85,
        },
        "tags": ["data", "etl", "pipeline"],
    },
    {
        "profession_id": "data_analyst",
        "name": "数据分析师",
        "category": "data",
        "description": "负责数据分析和洞察挖掘",
        "skills": [
            {"name": "statistical_analysis", "level": 9, "description": "统计分析能力"},
            {"name": "visualization", "level": 8, "description": "数据可视化能力"},
            {"name": "insight", "level": 8, "description": "洞察挖掘能力"},
            {"name": "reporting", "level": 7, "description": "报告撰写能力"},
        ],
        "task_types": ["data_analysis", "report_generation", "dashboard_creation", "ad_hoc_query"],
        "collaboration": {
            "upstream": ["data_engineer"],
            "downstream": [],
            "review_required": False,
            "review_by": [],
        },
        "config": {
            "preferred_model": "gpt-4",
            "max_concurrent_tasks": 4,
            "timeout_multiplier": 1.0,
            "quality_threshold": 0.85,
        },
        "tags": ["analysis", "visualization", "reporting"],
    },
    {
        "profession_id": "content_writer",
        "name": "内容创作者",
        "category": "content",
        "description": "负责内容创作和文案撰写",
        "skills": [
            {"name": "writing", "level": 9, "description": "写作能力"},
            {"name": "editing", "level": 8, "description": "编辑能力"},
            {"name": "research", "level": 7, "description": "资料调研能力"},
            {"name": "seo", "level": 6, "description": "SEO优化能力"},
        ],
        "task_types": ["article_writing", "copywriting", "script_writing", "content_editing"],
        "collaboration": {
            "upstream": ["content_planner"],
            "downstream": ["content_editor"],
            "review_required": True,
            "review_by": ["content_editor"],
        },
        "config": {
            "preferred_model": "gpt-4",
            "max_concurrent_tasks": 5,
            "timeout_multiplier": 1.0,
            "quality_threshold": 0.85,
        },
        "tags": ["writing", "content", "creative"],
    },
    {
        "profession_id": "researcher",
        "name": "研究员",
        "category": "research",
        "description": "负责研究和分析工作",
        "skills": [
            {"name": "research_methodology", "level": 9, "description": "研究方法论"},
            {"name": "literature_review", "level": 8, "description": "文献综述能力"},
            {"name": "experiment_design", "level": 8, "description": "实验设计能力"},
            {"name": "academic_writing", "level": 8, "description": "学术写作能力"},
        ],
        "task_types": ["literature_review", "experiment_design", "data_analysis", "paper_writing"],
        "collaboration": {
            "upstream": [],
            "downstream": ["data_analyst"],
            "review_required": True,
            "review_by": ["senior_researcher"],
        },
        "config": {
            "preferred_model": "gpt-4",
            "max_concurrent_tasks": 2,
            "timeout_multiplier": 1.5,
            "quality_threshold": 0.90,
        },
        "tags": ["research", "analysis", "academic"],
    },
]
