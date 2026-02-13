from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional, Set

from .models import (
    TaskAnalysis,
    TaskContext,
    TaskType,
    ComplexityLevel,
    RiskLevel,
    AuditLevel,
    AuditRequirement,
    SkillRequirement,
    Dependency,
    StageSpec,
    WorkflowRecommendation,
    ParallelGroup,
)


class ComplexityAnalyzer:
    COMPLEXITY_INDICATORS = {
        ComplexityLevel.SIMPLE: {
            "keywords": ["简单", "single", "basic", "minor", "小", "simple"],
            "max_files": 1,
            "max_functions": 3,
        },
        ComplexityLevel.MEDIUM: {
            "keywords": ["中等", "medium", "moderate", "几个", "multiple"],
            "max_files": 5,
            "max_functions": 10,
        },
        ComplexityLevel.COMPLEX: {
            "keywords": ["复杂", "complex", "complicated", "系统", "system"],
            "max_files": 15,
            "max_functions": 30,
        },
        ComplexityLevel.VERY_COMPLEX: {
            "keywords": ["非常复杂", "very complex", "架构", "architecture", "重构", "refactor"],
            "max_files": 50,
            "max_functions": 100,
        },
    }
    
    async def assess(self, request: str, context: TaskContext) -> ComplexityLevel:
        request_lower = request.lower()
        
        for level, indicators in self.COMPLEXITY_INDICATORS.items():
            for keyword in indicators["keywords"]:
                if keyword in request_lower:
                    return level
        
        word_count = len(request.split())
        if word_count < 20:
            return ComplexityLevel.SIMPLE
        elif word_count < 50:
            return ComplexityLevel.MEDIUM
        elif word_count < 150:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.VERY_COMPLEX


class RiskAssessor:
    HIGH_RISK_PATTERNS = [
        r"删除|delete|drop|remove",
        r"生产环境|production|线上",
        r"数据库|database|db",
        r"权限|permission|auth|security",
        r"支付|payment|transaction",
        r"用户数据|user data|personal",
    ]
    
    MEDIUM_RISK_PATTERNS = [
        r"修改|modify|update|change",
        r"配置|config|setting",
        r"接口|api|endpoint",
        r"部署|deploy|release",
    ]
    
    async def assess(
        self,
        request: str,
        task_type: TaskType,
        complexity: ComplexityLevel,
    ) -> RiskLevel:
        request_lower = request.lower()
        
        for pattern in self.HIGH_RISK_PATTERNS:
            if re.search(pattern, request_lower):
                return RiskLevel.HIGH
        
        for pattern in self.MEDIUM_RISK_PATTERNS:
            if re.search(pattern, request_lower):
                return RiskLevel.MEDIUM
        
        if task_type in (TaskType.BUG_FIX, TaskType.CODE_REFACTORING):
            return RiskLevel.MEDIUM
        
        if complexity in (ComplexityLevel.COMPLEX, ComplexityLevel.VERY_COMPLEX):
            return RiskLevel.MEDIUM
        
        return RiskLevel.LOW


class TaskAnalyzer:
    TASK_TYPE_KEYWORDS: Dict[TaskType, List[str]] = {
        TaskType.FEATURE_DEVELOPMENT: [
            "开发", "develop", "实现", "implement", "新增", "add", "功能", "feature",
            "创建", "create", "build", "构建",
        ],
        TaskType.BUG_FIX: [
            "修复", "fix", "bug", "错误", "error", "问题", "issue", "缺陷", "defect",
        ],
        TaskType.DATA_ANALYSIS: [
            "分析", "analyze", "数据", "data", "统计", "statistics", "报表", "report",
            "可视化", "visualization", "excel", "csv",
        ],
        TaskType.CONTENT_CREATION: [
            "写作", "write", "文章", "article", "内容", "content", "文档", "document",
            "创作", "create", "编辑", "edit",
        ],
        TaskType.CODE_REFACTORING: [
            "重构", "refactor", "优化", "optimize", "改进", "improve", "清理", "clean",
        ],
        TaskType.SYSTEM_DESIGN: [
            "设计", "design", "架构", "architecture", "方案", "solution", "规划", "plan",
        ],
        TaskType.RESEARCH: [
            "研究", "research", "调研", "investigate", "分析", "analysis", "探索", "explore",
        ],
    }
    
    SKILL_MAPPING: Dict[TaskType, List[SkillRequirement]] = {
        TaskType.FEATURE_DEVELOPMENT: [
            SkillRequirement("coding", 7, 10, "代码编写"),
            SkillRequirement("debugging", 6, 8, "调试能力"),
            SkillRequirement("testing", 5, 6, "测试能力"),
        ],
        TaskType.BUG_FIX: [
            SkillRequirement("debugging", 8, 10, "调试排错"),
            SkillRequirement("coding", 6, 8, "代码修改"),
            SkillRequirement("testing", 6, 7, "测试验证"),
        ],
        TaskType.DATA_ANALYSIS: [
            SkillRequirement("statistical_analysis", 7, 10, "统计分析"),
            SkillRequirement("visualization", 6, 8, "数据可视化"),
            SkillRequirement("reporting", 5, 6, "报告撰写"),
        ],
        TaskType.CONTENT_CREATION: [
            SkillRequirement("writing", 8, 10, "写作能力"),
            SkillRequirement("editing", 6, 7, "编辑能力"),
            SkillRequirement("research", 5, 5, "资料调研"),
        ],
        TaskType.CODE_REFACTORING: [
            SkillRequirement("refactoring", 8, 10, "重构能力"),
            SkillRequirement("coding", 7, 9, "代码编写"),
            SkillRequirement("testing", 7, 8, "测试能力"),
        ],
        TaskType.SYSTEM_DESIGN: [
            SkillRequirement("system_design", 9, 10, "系统设计"),
            SkillRequirement("documentation", 7, 8, "文档编写"),
            SkillRequirement("evaluation", 7, 7, "技术评估"),
        ],
        TaskType.RESEARCH: [
            SkillRequirement("research_methodology", 8, 10, "研究方法"),
            SkillRequirement("analysis", 7, 8, "分析能力"),
            SkillRequirement("writing", 6, 6, "写作能力"),
        ],
        TaskType.GENERAL: [
            SkillRequirement("general", 5, 5, "通用能力"),
        ],
    }
    
    WORKFLOW_TEMPLATES: Dict[TaskType, str] = {
        TaskType.FEATURE_DEVELOPMENT: "feature_dev_flow",
        TaskType.BUG_FIX: "bug_fix_flow",
        TaskType.DATA_ANALYSIS: "data_analysis_flow",
        TaskType.CONTENT_CREATION: "content_creation_flow",
        TaskType.CODE_REFACTORING: "refactoring_flow",
        TaskType.SYSTEM_DESIGN: "system_design_flow",
        TaskType.RESEARCH: "research_flow",
        TaskType.GENERAL: "general_flow",
    }
    
    def __init__(self):
        self._complexity_analyzer = ComplexityAnalyzer()
        self._risk_assessor = RiskAssessor()
    
    async def analyze(self, request: str, context: Optional[TaskContext] = None) -> TaskAnalysis:
        ctx = context or TaskContext()
        
        task_type = self._classify_task_type(request)
        complexity = await self._complexity_analyzer.assess(request, ctx)
        skills = self._identify_required_skills(task_type, complexity)
        dependencies = self._analyze_dependencies(request, ctx)
        risk = await self._risk_assessor.assess(request, task_type, complexity)
        audit_req = self._determine_audit_requirement(task_type, complexity, risk)
        
        workflow_rec = self._recommend_workflow(task_type, complexity, skills, audit_req)
        
        estimated_time = self._estimate_time(complexity, skills)
        confidence = self._calculate_confidence(task_type, complexity)
        
        return TaskAnalysis(
            task_id=self._generate_id(),
            request=request,
            task_type=task_type,
            complexity=complexity,
            skills_needed=skills,
            dependencies=dependencies,
            risk_level=risk,
            estimated_time=estimated_time,
            audit_requirement=audit_req,
            workflow_recommendation=workflow_rec,
            context=ctx,
            confidence=confidence,
        )
    
    def _classify_task_type(self, request: str) -> TaskType:
        request_lower = request.lower()
        scores: Dict[TaskType, int] = {}
        
        for task_type, keywords in self.TASK_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in request_lower)
            if score > 0:
                scores[task_type] = score
        
        if scores:
            return max(scores, key=scores.get)
        return TaskType.GENERAL
    
    def _identify_required_skills(
        self,
        task_type: TaskType,
        complexity: ComplexityLevel,
    ) -> List[SkillRequirement]:
        base_skills = list(self.SKILL_MAPPING.get(task_type, []))
        
        complexity_multiplier = {
            ComplexityLevel.SIMPLE: 0.8,
            ComplexityLevel.MEDIUM: 1.0,
            ComplexityLevel.COMPLEX: 1.2,
            ComplexityLevel.VERY_COMPLEX: 1.5,
        }
        
        multiplier = complexity_multiplier.get(complexity, 1.0)
        
        adjusted_skills = []
        for skill in base_skills:
            adjusted_level = min(10, int(skill.min_level * multiplier))
            adjusted_skills.append(SkillRequirement(
                skill_name=skill.skill_name,
                min_level=adjusted_level,
                priority=skill.priority,
                description=skill.description,
            ))
        
        return adjusted_skills
    
    def _analyze_dependencies(
        self,
        request: str,
        context: TaskContext,
    ) -> List[Dependency]:
        dependencies = []
        
        if context.previous_tasks:
            for task_id in context.previous_tasks:
                dependencies.append(Dependency(
                    dependency_id=f"prev_task_{task_id}",
                    dependency_type="task",
                    description=f"Depends on previous task: {task_id}",
                ))
        
        return dependencies
    
    def _determine_audit_requirement(
        self,
        task_type: TaskType,
        complexity: ComplexityLevel,
        risk: RiskLevel,
    ) -> AuditRequirement:
        if task_type == TaskType.CONTENT_CREATION:
            return AuditRequirement(
                level=AuditLevel.BASIC,
                dimensions=["quality", "accuracy"],
                required_score=0.7,
            )
        
        if risk == RiskLevel.HIGH:
            return AuditRequirement(
                level=AuditLevel.EXPERT,
                dimensions=["security", "quality", "performance", "maintainability"],
                required_score=0.9,
                max_retries=5,
            )
        
        if risk == RiskLevel.MEDIUM:
            return AuditRequirement(
                level=AuditLevel.STANDARD,
                dimensions=["security", "quality", "maintainability"],
                required_score=0.85,
            )
        
        if complexity in (ComplexityLevel.COMPLEX, ComplexityLevel.VERY_COMPLEX):
            return AuditRequirement(
                level=AuditLevel.DEEP,
                dimensions=["quality", "maintainability", "performance"],
                required_score=0.85,
            )
        
        return AuditRequirement(
            level=AuditLevel.BASIC,
            dimensions=["quality"],
            required_score=0.8,
        )
    
    def _recommend_workflow(
        self,
        task_type: TaskType,
        complexity: ComplexityLevel,
        skills: List[SkillRequirement],
        audit_req: AuditRequirement,
    ) -> WorkflowRecommendation:
        template_id = self.WORKFLOW_TEMPLATES.get(task_type, "general_flow")
        
        stages = self._build_stages(task_type, complexity, audit_req)
        
        professions = list(set(s.profession_id for s in stages if not s.is_audit_stage))
        
        audit_stages = [s.stage_id for s in stages if s.is_audit_stage]
        
        estimated_duration = sum(s.timeout for s in stages)
        
        return WorkflowRecommendation(
            template_id=template_id,
            stages=stages,
            required_professions=professions,
            audit_stages=audit_stages,
            estimated_duration=estimated_duration,
        )
    
    def _build_stages(
        self,
        task_type: TaskType,
        complexity: ComplexityLevel,
        audit_req: AuditRequirement,
    ) -> List[StageSpec]:
        stage_configs = {
            TaskType.FEATURE_DEVELOPMENT: [
                ("analyze", "需求分析", "product_manager", False),
                ("design", "架构设计", "architect", False),
                ("develop", "编码开发", "developer", False),
                ("audit_code", "代码审计", "code_auditor", True),
                ("test", "测试验证", "qa_engineer", False),
                ("audit_final", "最终审计", "code_auditor", True),
            ],
            TaskType.BUG_FIX: [
                ("locate", "问题定位", "developer", False),
                ("fix", "修复实现", "developer", False),
                ("audit_fix", "修复审计", "code_auditor", True),
                ("test", "测试验证", "qa_engineer", False),
            ],
            TaskType.DATA_ANALYSIS: [
                ("collect", "数据采集", "data_engineer", False),
                ("clean", "数据清洗", "data_engineer", False),
                ("analyze", "数据分析", "data_analyst", False),
                ("visualize", "可视化", "data_analyst", False),
                ("audit", "结果审计", "code_auditor", True),
                ("report", "报告生成", "data_analyst", False),
            ],
            TaskType.CONTENT_CREATION: [
                ("plan", "内容策划", "content_planner", False),
                ("write", "内容创作", "content_writer", False),
                ("edit", "内容编辑", "content_editor", False),
            ],
            TaskType.CODE_REFACTORING: [
                ("analyze", "代码分析", "developer", False),
                ("plan", "重构规划", "architect", False),
                ("refactor", "重构执行", "developer", False),
                ("audit", "代码审计", "code_auditor", True),
                ("test", "测试验证", "qa_engineer", False),
            ],
            TaskType.SYSTEM_DESIGN: [
                ("requirement", "需求分析", "product_manager", False),
                ("design", "架构设计", "architect", False),
                ("review", "设计评审", "architect", False),
                ("audit", "方案审计", "code_auditor", True),
            ],
            TaskType.RESEARCH: [
                ("research", "研究调研", "researcher", False),
                ("analyze", "分析总结", "researcher", False),
                ("document", "文档撰写", "researcher", False),
            ],
            TaskType.GENERAL: [
                ("execute", "任务执行", "developer", False),
                ("audit", "结果审计", "code_auditor", True),
            ],
        }
        
        configs = stage_configs.get(task_type, stage_configs[TaskType.GENERAL])
        
        stages = []
        for i, (stage_id, name, profession, is_audit) in enumerate(configs):
            next_stages = []
            if i < len(configs) - 1:
                next_stages = [configs[i + 1][0]]
            
            timeout = 300
            if complexity == ComplexityLevel.COMPLEX:
                timeout = 600
            elif complexity == ComplexityLevel.VERY_COMPLEX:
                timeout = 1200
            
            stages.append(StageSpec(
                stage_id=stage_id,
                name=name,
                profession_id=profession,
                next_stages=next_stages,
                is_audit_stage=is_audit,
                timeout=timeout,
            ))
        
        return stages
    
    def _estimate_time(
        self,
        complexity: ComplexityLevel,
        skills: List[SkillRequirement],
    ) -> int:
        base_time = {
            ComplexityLevel.SIMPLE: 15,
            ComplexityLevel.MEDIUM: 30,
            ComplexityLevel.COMPLEX: 60,
            ComplexityLevel.VERY_COMPLEX: 120,
        }
        
        minutes = base_time.get(complexity, 30)
        
        avg_skill_level = sum(s.min_level for s in skills) / len(skills) if skills else 5
        skill_factor = 1.0 + (10 - avg_skill_level) * 0.05
        
        return int(minutes * skill_factor)
    
    def _calculate_confidence(
        self,
        task_type: TaskType,
        complexity: ComplexityLevel,
    ) -> float:
        if task_type == TaskType.GENERAL:
            return 0.6
        
        if complexity == ComplexityLevel.VERY_COMPLEX:
            return 0.7
        
        return 0.85
    
    def _generate_id(self) -> str:
        return f"task-{uuid.uuid4().hex[:12]}"
