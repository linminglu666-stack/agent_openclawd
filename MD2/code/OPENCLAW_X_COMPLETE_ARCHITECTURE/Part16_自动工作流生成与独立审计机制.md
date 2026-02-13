# OpenClaw-X 完整架构整合文档

## 文档说明

本文档整合了事无巨细的设计思路、流程图、实现细节、模块间数据接口与通信协议。

---


# 第十六部分：自动工作流生成与独立审计机制

## 16.1 设计思路

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    自动工作流与独立审计设计目标                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  核心理念:                                                              │
│  • 智能分析 - 首个Agent自动分析任务，识别所需工作流                     │
│  • 自动编排 - 根据任务特征自动生成最优工作流                            │
│  • 独立审计 - 审计者与执行者完全隔离，确保公正性                        │
│  • 双轨制 - 执行轨道与审计轨道并行但独立                                │
│                                                                         │
│  关键约束:                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 约束                    │ 说明                                  │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │ 审计者独立性            │ 审计实例不能参与代码编写/执行         │   │
│  │ 执行者回避              │ 执行实例不能审计自己产出的代码        │   │
│  │ 公正性保障              │ 审计结果基于客观标准，不受执行者影响  │   │
│  │ 反馈闭环                │ 审计发现必须反馈给执行者修正          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  工作流程:                                                              │
│  ─────────────────────────────────────────────────────────────────────  │
│  用户请求 → 任务分析 → 自动生成工作流 → 执行轨道 → 审计轨道            │
│                              ↓              ↓           ↓              │
│                           工作流池      执行实例群   审计实例群         │
│                              ↓              ↓           ↓              │
│                           调度执行      产出代码    审计报告            │
│                                             ↓           ↓              │
│                                          反馈修正 ← 审计反馈            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 16.2 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    自动工作流与独立审计架构                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      用户请求入口                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      任务分析层                                  │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │   │
│  │  │TaskAnalyzer│  │ Intent    │  │ Complexity│  │Workflow   │   │   │
│  │  │ 任务分析器 │  │ Classifier│  │ Assessor  │  │Recommender│   │   │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      工作流生成层                                │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │   │
│  │  │Auto       │  │ Template  │  │ Stage     │  │ Workflow  │   │   │
│  │  │Generator  │  │ Library   │  │ Assembler │  │ Validator │   │   │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│              ┌───────────────┴───────────────┐                          │
│              ▼                               ▼                          │
│  ┌───────────────────────┐     ┌───────────────────────┐              │
│  │      执行轨道         │     │      审计轨道         │              │
│  │  ┌─────────────────┐ │     │  ┌─────────────────┐ │              │
│  │  │ Execution Pool  │ │     │  │  Audit Pool     │ │              │
│  │  │ 执行实例池       │ │     │  │  审计实例池     │ │              │
│  │  └─────────────────┘ │     │  └─────────────────┘ │              │
│  │  ┌─────────────────┐ │     │  ┌─────────────────┐ │              │
│  │  │ Code Producer   │ │     │  │ Code Auditor    │ │              │
│  │  │ 代码生产者       │ │     │  │ 代码审计者      │ │              │
│  │  └─────────────────┘ │     │  └─────────────────┘ │              │
│  │  ┌─────────────────┐ │     │  ┌─────────────────┐ │              │
│  │  │ Test Runner     │ │     │  │ Quality Gate    │ │              │
│  │  │ 测试执行者       │ │     │  │ 质量门禁        │ │              │
│  │  └─────────────────┘ │     │  └─────────────────┘ │              │
│  └───────────────────────┘     └───────────────────────┘              │
│              │                               │                          │
│              └───────────────┬───────────────┘                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      反馈闭环层                                  │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │   │
│  │  │Feedback   │  │ Issue     │  │ Fix       │  │ Verify    │   │   │
│  │  │Aggregator │  │ Tracker   │  │ Scheduler │  │ Loop      │   │   │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 16.3 任务分析与工作流自动生成

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    任务分析流程                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  分析维度:                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 维度              │ 分析内容                    │ 输出          │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │ 任务类型          │ 开发/分析/创作/研究         │ task_type     │   │
│  │ 复杂度评估        │ 简单/中等/复杂/超复杂       │ complexity    │   │
│  │ 所需技能          │ 技能列表及优先级            │ skills_needed │   │
│  │ 依赖关系          │ 前置条件与依赖项            │ dependencies  │   │
│  │ 风险评估          │ 高/中/低风险                │ risk_level    │   │
│  │ 预估工时          │ 预计完成时间                │ estimated_time│   │
│  │ 审计需求          │ 是否需要审计/审计级别       │ audit_require │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  工作流生成规则:                                                        │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  任务类型 → 工作流模板:                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 任务类型          │ 工作流模板                                  │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │ 功能开发          │ 分析→设计→开发→测试→审计→部署              │   │
│  │ Bug修复           │ 定位→修复→测试→审计→合并                   │   │
│  │ 数据分析          │ 采集→清洗→分析→可视化→报告→审计            │   │
│  │ 内容创作          │ 策划→写作→编辑→审核→发布                   │   │
│  │ 代码重构          │ 分析→规划→重构→测试→审计→验证              │   │
│  │ 系统设计          │ 需求→架构→评审→文档→审计                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  复杂度 → 实例配置:                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 复杂度    │ 实例数量  │ 审计级别    │ 验证轮次                  │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │ 简单      │ 1-2       │ 基础审计    │ 1                         │   │
│  │ 中等      │ 2-4       │ 标准审计    │ 2                         │   │
│  │ 复杂      │ 4-6       │ 深度审计    │ 3                         │   │
│  │ 超复杂    │ 6+        │ 专家审计    │ 3+                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 任务分析输出结构

```python
@dataclass
class TaskAnalysis:
    task_id: str
    task_type: TaskType
    complexity: ComplexityLevel
    skills_needed: List[SkillRequirement]
    dependencies: List[Dependency]
    risk_level: RiskLevel
    estimated_time: int
    audit_requirement: AuditRequirement
    
    workflow_recommendation: WorkflowRecommendation
    
@dataclass
class WorkflowRecommendation:
    template_id: str
    stages: List[StageSpec]
    required_professions: List[str]
    audit_stages: List[str]
    estimated_duration: int
    parallel_opportunities: List[ParallelGroup]
```

## 16.4 独立审计机制

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    独立审计架构                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  审计隔离原则:                                                          │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                 │   │
│  │   执行轨道                          审计轨道                   │   │
│  │   ──────────                        ──────────                  │   │
│  │                                                                 │   │
│  │   ┌─────────┐                      ┌─────────┐                 │   │
│  │   │Developer│ ──── 代码产出 ────→ │ Auditor │                 │   │
│  │   │ 开发者   │                      │ 审计者  │                 │   │
│  │   └─────────┘                      └─────────┘                 │   │
│  │        │                                │                       │   │
│  │        │                                │                       │   │
│  │        │    ┌─────────────────────┐     │                       │   │
│  │        │    │   隔离墙            │     │                       │   │
│  │        │    │ • 不同实例池        │     │                       │   │
│  │        │    │ • 不同资源配额      │     │                       │   │
│  │        │    │ • 禁止通信          │     │                       │   │
│  │        │    │ • 独立上下文        │     │                       │   │
│  │        │    └─────────────────────┘     │                       │   │
│  │        │                                │                       │   │
│  │        │←─────── 审计反馈 ──────────────│                       │   │
│  │        │                                │                       │   │
│  │   ┌─────────┐                      ┌─────────┐                 │   │
│  │   │ Fixer   │ ←─── 修正指令 ────── │ Auditor │                 │   │
│  │   │ 修复者  │                      │ 审计者  │                 │   │
│  │   └─────────┘                      └─────────┘                 │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  审计维度:                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 维度          │ 检查项                          │ 权重          │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │ 代码质量      │ 可读性、命名规范、注释完整性    │ 20%           │   │
│  │ 安全性        │ 漏洞扫描、敏感信息、权限控制    │ 25%           │   │
│  │ 性能          │ 算法效率、资源使用、缓存策略    │ 15%           │   │
│  │ 可维护性      │ 模块化、耦合度、测试覆盖率      │ 20%           │   │
│  │ 规范遵循      │ 编码规范、最佳实践、文档完整性  │ 20%           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 审计报告结构

```python
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
    
    created_at: int
    
@dataclass
class AuditIssue:
    issue_id: str
    severity: Severity  # critical, high, medium, low
    category: str
    location: CodeLocation
    description: str
    suggestion: str
    
@dataclass
class DimensionScore:
    dimension: str
    score: float
    max_score: float
    details: List[str]
```

## 16.5 双轨执行流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    双轨执行流程                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  阶段执行流程:                                                          │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                 │   │
│  │  1. 执行阶段                                                    │   │
│  │     ┌─────────┐                                                │   │
│  │     │ 任务分配 │                                                │   │
│  │     └────┬────┘                                                │   │
│  │          ▼                                                      │   │
│  │     ┌─────────┐     ┌─────────┐                               │   │
│  │     │执行实例 │ ──→ │代码产出 │                               │   │
│  │     └─────────┘     └────┬────┘                               │   │
│  │                         │                                      │   │
│  │  2. 审计阶段           │                                      │   │
│  │                         ▼                                      │   │
│  │                    ┌─────────┐                                 │   │
│  │                    │审计队列 │                                 │   │
│  │                    └────┬────┘                                 │   │
│  │                         │                                      │   │
│  │          ┌──────────────┼──────────────┐                       │   │
│  │          ▼              ▼              ▼                       │   │
│  │     ┌─────────┐   ┌─────────┐   ┌─────────┐                   │   │
│  │     │安全审计 │   │质量审计 │   │性能审计 │                   │   │
│  │     └────┬────┘   └────┬────┘   └────┬────┘                   │   │
│  │          │              │              │                       │   │
│  │          └──────────────┼──────────────┘                       │   │
│  │                         ▼                                      │   │
│  │                    ┌─────────┐                                 │   │
│  │                    │审计报告 │                                 │   │
│  │                    └────┬────┘                                 │   │
│  │                         │                                      │   │
│  │  3. 反馈阶段           │                                      │   │
│  │          ┌──────────────┴──────────────┐                       │   │
│  │          ▼                             ▼                       │   │
│  │     ┌─────────┐                  ┌─────────┐                   │   │
│  │     │ 通过    │                  │ 需修正  │                   │   │
│  │     │继续下一 │                  │返回执行 │                   │   │
│  │     │阶段     │                  │者修正   │                   │   │
│  │     └─────────┘                  └────┬────┘                   │   │
│  │                                       │                        │   │
│  │                                       ▼                        │   │
│  │                                  ┌─────────┐                   │   │
│  │                                  │修正执行 │                   │   │
│  │                                  └────┬────┘                   │   │
│  │                                       │                        │   │
│  │                                       ▼                        │   │
│  │                                  ┌─────────┐                   │   │
│  │                                  │重新审计 │                   │   │
│  │                                  └─────────┘                   │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 16.6 审计隔离保障机制

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    审计隔离保障                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  实例池隔离:                                                            │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐     │
│  │     执行实例池              │  │     审计实例池              │     │
│  │  ┌─────┐ ┌─────┐ ┌─────┐  │  │  ┌─────┐ ┌─────┐ ┌─────┐  │     │
│  │  │Dev-1│ │Dev-2│ │Dev-3│  │  │  │Aud-1│ │Aud-2│ │Aud-3│  │     │
│  │  └─────┘ └─────┘ └─────┘  │  │  └─────┘ └─────┘ └─────┘  │     │
│  │  ┌─────┐ ┌─────┐ ┌─────┐  │  │  ┌─────┐ ┌─────┐         │     │
│  │  │QA-1 │ │QA-2 │ │Ops-1│  │  │  │Aud-4│ │Aud-5│         │     │
│  │  └─────┘ └─────┘ └─────┘  │  │  └─────┘ └─────┘         │     │
│  │                             │  │                             │     │
│  │  职业类型:                  │  │  职业类型:                  │     │
│  │  • developer                │  │  • code_auditor            │     │
│  │  • tester                   │  │  • security_auditor        │     │
│  │  • devops                   │  │  • quality_auditor         │     │
│  │  • architect                │  │  • performance_auditor     │     │
│  │                             │  │                             │     │
│  └─────────────────────────────┘  └─────────────────────────────┘     │
│                                                                         │
│  隔离规则:                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 规则ID   │ 规则描述                              │ 强制级别    │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │ ISO-001  │ 审计实例不能分配执行任务              │ 强制        │   │
│  │ ISO-002  │ 执行实例不能审计自己产出的代码        │ 强制        │   │
│  │ ISO-003  │ 同一任务的执行者和审计者必须不同实例  │ 强制        │   │
│  │ ISO-004  │ 审计实例不能访问执行实例的上下文      │ 强制        │   │
│  │ ISO-005  │ 审计结果必须通过独立通道传递          │ 强制        │   │
│  │ ISO-006  │ 审计实例使用独立的模型配置            │ 推荐        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  公正性保障:                                                            │
│  ─────────────────────────────────────────────────────────────────────  │
│  • 审计标准预定义，不可动态修改                                         │
│  • 审计实例不感知执行者身份信息                                         │
│  • 审计评分基于客观指标，排除主观因素                                   │
│  • 审计结果可追溯，支持申诉和复核                                       │
│  • 关键审计结果需多实例交叉验证                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 16.7 服务实现

```python
class TaskAnalyzer:
    def __init__(self, profession_system: ProfessionSystem):
        self._profession_system = profession_system
        self._complexity_analyzer = ComplexityAnalyzer()
        self._risk_assessor = RiskAssessor()
    
    async def analyze(self, request: str, context: TaskContext) -> TaskAnalysis:
        task_type = self._classify_task_type(request)
        complexity = await self._complexity_analyzer.assess(request, context)
        skills = self._identify_required_skills(request, task_type)
        dependencies = self._analyze_dependencies(request, context)
        risk = self._risk_assessor.assess(request, task_type, complexity)
        audit_req = self._determine_audit_requirement(task_type, complexity, risk)
        
        workflow_rec = await self._recommend_workflow(
            task_type, complexity, skills, audit_req,
        )
        
        return TaskAnalysis(
            task_id=self._generate_id(),
            task_type=task_type,
            complexity=complexity,
            skills_needed=skills,
            dependencies=dependencies,
            risk_level=risk,
            estimated_time=self._estimate_time(complexity, skills),
            audit_requirement=audit_req,
            workflow_recommendation=workflow_rec,
        )
    
    async def _recommend_workflow(
        self,
        task_type: TaskType,
        complexity: ComplexityLevel,
        skills: List[SkillRequirement],
        audit_req: AuditRequirement,
    ) -> WorkflowRecommendation:
        template = self._get_template_for_task_type(task_type)
        
        stages = self._adapt_stages_for_complexity(template.stages, complexity)
        
        audit_stages = self._insert_audit_stages(stages, audit_req)
        
        return WorkflowRecommendation(
            template_id=template.template_id,
            stages=stages,
            required_professions=self._map_skills_to_professions(skills),
            audit_stages=audit_stages,
            estimated_duration=self._estimate_duration(stages),
            parallel_opportunities=self._find_parallel_opportunities(stages),
        )


class AutoWorkflowGenerator:
    def __init__(self, orchestrator: WorkflowOrchestrator):
        self._orchestrator = orchestrator
        self._templates: Dict[str, WorkflowTemplate] = {}
        self._load_builtin_templates()
    
    async def generate(
        self,
        analysis: TaskAnalysis,
    ) -> Workflow:
        template = self._templates.get(analysis.workflow_recommendation.template_id)
        if not template:
            raise ValueError(f"Template not found: {analysis.workflow_recommendation.template_id}")
        
        workflow = self._instantiate_workflow(template, analysis)
        
        self._orchestrator.register_workflow(workflow)
        
        return workflow
    
    def _instantiate_workflow(
        self,
        template: WorkflowTemplate,
        analysis: TaskAnalysis,
    ) -> Workflow:
        stages = []
        
        for stage_spec in analysis.workflow_recommendation.stages:
            stage = WorkflowStage(
                stage_id=stage_spec.stage_id,
                name=stage_spec.name,
                profession_id=stage_spec.profession_id,
                inputs=stage_spec.inputs,
                outputs=stage_spec.outputs,
                next_stages=stage_spec.next_stages,
            )
            stages.append(stage)
        
        return Workflow(
            workflow_id=self._generate_id(),
            name=f"Auto-{analysis.task_type.value}-{analysis.task_id[:8]}",
            stages=stages,
            entry_stage=stages[0].stage_id if stages else "",
        )


class IndependentAuditSystem:
    def __init__(self):
        self._audit_pool: InstancePool = InstancePool(pool_type="audit")
        self._execution_pool: InstancePool = InstancePool(pool_type="execution")
        self._isolation_rules = IsolationRuleEngine()
        self._audit_standards = AuditStandardsRegistry()
        self._audit_queue: asyncio.Queue = asyncio.Queue()
        self._reports: Dict[str, AuditReport] = {}
    
    async def submit_for_audit(
        self,
        execution_id: str,
        code_artifacts: CodeArtifacts,
        executor_instance: str,
    ) -> str:
        audit_id = self._generate_id()
        
        self._isolation_rules.validate(
            executor_instance=executor_instance,
            audit_pool=self._audit_pool,
        )
        
        auditor = await self._select_auditor(executor_instance)
        
        audit_task = AuditTask(
            audit_id=audit_id,
            execution_id=execution_id,
            code_artifacts=code_artifacts,
            auditor_instance=auditor.instance_id,
            standards=self._audit_standards.get_applicable_standards(
                code_artifacts.language,
            ),
        )
        
        await self._audit_queue.put(audit_task)
        
        return audit_id
    
    async def _select_auditor(self, executor_instance: str) -> Instance:
        available_auditors = self._audit_pool.get_available_instances()
        
        excluded = self._isolation_rules.get_excluded_auditors(executor_instance)
        
        candidates = [
            a for a in available_auditors
            if a.instance_id not in excluded
        ]
        
        if not candidates:
            raise NoAvailableAuditorError(
                f"No available auditor for executor {executor_instance}",
            )
        
        return self._select_by_workload(candidates)
    
    async def execute_audit(self, audit_task: AuditTask) -> AuditReport:
        auditor = self._audit_pool.get_instance(audit_task.auditor_instance)
        
        context = AuditContext(
            audit_id=audit_task.audit_id,
            standards=audit_task.standards,
            isolation_mode=True,
        )
        
        report = await auditor.execute_audit(
            code_artifacts=audit_task.code_artifacts,
            context=context,
        )
        
        self._reports[audit_task.audit_id] = report
        
        return report
    
    async def process_feedback(
        self,
        report: AuditReport,
    ) -> FeedbackAction:
        if report.passed:
            return FeedbackAction(
                action_type="proceed",
                target_stage=None,
            )
        
        critical_issues = [
            i for i in report.issues
            if i.severity in (Severity.CRITICAL, Severity.HIGH)
        ]
        
        if critical_issues:
            return FeedbackAction(
                action_type="fix_required",
                target_stage="fix",
                issues=critical_issues,
                max_retries=3,
            )
        
        return FeedbackAction(
            action_type="warn_and_proceed",
            issues=report.issues,
        )


class IsolationRuleEngine:
    RULES = [
        IsolationRule(
            rule_id="ISO-001",
            description="Auditor cannot be assigned execution tasks",
            check_fn=lambda ctx: ctx.instance.pool_type != "audit",
            severity="critical",
        ),
        IsolationRule(
            rule_id="ISO-002",
            description="Executor cannot audit own code",
            check_fn=lambda ctx: ctx.auditor_id != ctx.executor_id,
            severity="critical",
        ),
        IsolationRule(
            rule_id="ISO-003",
            description="Same task requires different executor and auditor",
            check_fn=lambda ctx: ctx.auditor_id not in ctx.task_executors,
            severity="critical",
        ),
    ]
    
    def validate(
        self,
        executor_instance: str,
        audit_pool: InstancePool,
    ) -> bool:
        for rule in self.RULES:
            if not rule.check(executor_instance, audit_pool):
                raise IsolationViolationError(
                    f"Rule {rule.rule_id} violated: {rule.description}",
                )
        return True
    
    def get_excluded_auditors(self, executor_instance: str) -> Set[str]:
        return {executor_instance}
```

## 16.8 文件结构

```
code/
├── core/
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── task_analyzer.py      # TaskAnalyzer
│   │   ├── complexity.py         # 复杂度评估
│   │   ├── risk_assessor.py      # 风险评估
│   │   └── workflow_recommender.py # 工作流推荐
│   │
│   ├── audit/
│   │   ├── __init__.py
│   │   ├── system.py             # IndependentAuditSystem
│   │   ├── isolation.py          # IsolationRuleEngine
│   │   ├── standards.py          # AuditStandardsRegistry
│   │   ├── report.py             # AuditReport
│   │   └── pool.py               # AuditInstancePool
│   │
│   ├── workflow/
│   │   ├── __init__.py
│   │   ├── orchestrator.py       # WorkflowOrchestrator
│   │   ├── auto_generator.py     # AutoWorkflowGenerator
│   │   ├── templates.py          # 工作流模板库
│   │   └── definition.py         # 工作流定义
│   │
│   └── feedback/
│       ├── __init__.py
│       ├── aggregator.py         # FeedbackAggregator
│       ├── action.py             # FeedbackAction
│       └── loop.py               # 反馈闭环
```

## 16.9 验收标准

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    自动工作流与独立审计验收标准                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  任务分析:                                                              │
│  • 任务类型识别准确率 ≥ 95%                                             │
│  • 复杂度评估准确率 ≥ 90%                                               │
│  • 技能需求识别完整率 ≥ 95%                                             │
│                                                                         │
│  工作流生成:                                                            │
│  • 工作流生成时间 < 5秒                                                 │
│  • 生成的阶段合理性 ≥ 90%                                               │
│  • 审计阶段自动插入准确率 100%                                          │
│                                                                         │
│  审计隔离:                                                              │
│  • 隔离规则违反检测率 100%                                              │
│  • 审计者与执行者冲突检测率 100%                                        │
│  • 审计实例池独立性验证通过率 100%                                      │
│                                                                         │
│  审计质量:                                                              │
│  • 关键问题检出率 ≥ 95%                                                 │
│  • 误报率 ≤ 10%                                                         │
│  • 审计报告生成时间 < 30秒                                              │
│                                                                         │
│  反馈闭环:                                                              │
│  • 反馈传递延迟 < 1秒                                                   │
│  • 修正任务分配准确率 ≥ 95%                                             │
│  • 验证闭环完成率 100%                                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---
