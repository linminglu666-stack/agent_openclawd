from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from .models import (
    AuditReport,
    AuditTask,
    AuditContext,
    AuditIssue,
    AuditDimension,
    AuditDimension as Dimension,
    DimensionScore,
    Recommendation,
    CodeArtifacts,
    CodeLocation,
    FeedbackAction,
    Severity,
)
from .isolation import IsolationRuleEngine, IsolationViolationError, AuditStandardsRegistry


class AuditInstancePool:
    def __init__(self, pool_type: str = "audit"):
        self._pool_type = pool_type
        self._instances: Dict[str, Any] = {}
        self._available: Set[str] = set()
        self._busy: Set[str] = set()
    
    def register_instance(self, instance_id: str, instance: Any) -> None:
        self._instances[instance_id] = instance
        self._available.add(instance_id)
    
    def get_instance(self, instance_id: str) -> Optional[Any]:
        return self._instances.get(instance_id)
    
    def get_available_instances(self) -> List[Any]:
        return [
            self._instances[iid]
            for iid in self._available
            if iid in self._instances
        ]
    
    def acquire(self, instance_id: str) -> bool:
        if instance_id in self._available:
            self._available.remove(instance_id)
            self._busy.add(instance_id)
            return True
        return False
    
    def release(self, instance_id: str) -> bool:
        if instance_id in self._busy:
            self._busy.remove(instance_id)
            self._available.add(instance_id)
            return True
        return False
    
    def get_pool_type(self) -> str:
        return self._pool_type


class IndependentAuditSystem:
    def __init__(self):
        self._audit_pool = AuditInstancePool(pool_type="audit")
        self._execution_pool = AuditInstancePool(pool_type="execution")
        self._isolation_rules = IsolationRuleEngine()
        self._standards_registry = AuditStandardsRegistry()
        self._audit_queue: asyncio.Queue = asyncio.Queue()
        self._reports: Dict[str, AuditReport] = {}
        self._pending_audits: Dict[str, AuditTask] = {}
    
    def register_audit_instance(self, instance_id: str, instance: Any) -> None:
        self._audit_pool.register_instance(instance_id, instance)
    
    def register_execution_instance(self, instance_id: str, instance: Any) -> None:
        self._execution_pool.register_instance(instance_id, instance)
    
    async def submit_for_audit(
        self,
        execution_id: str,
        code_artifacts: CodeArtifacts,
        executor_instance: str,
        task_executors: Optional[Set[str]] = None,
        required_score: float = 0.8,
        dimensions: Optional[List[AuditDimension]] = None,
    ) -> str:
        audit_id = self._generate_id()
        
        self._isolation_rules.validate(
            executor_instance=executor_instance,
            task_executors=task_executors,
        )
        
        auditor = await self._select_auditor(executor_instance, task_executors)
        
        standards = self._standards_registry.get_applicable_standards(
            code_artifacts.language,
        )
        
        audit_task = AuditTask(
            audit_id=audit_id,
            execution_id=execution_id,
            code_artifacts=code_artifacts,
            auditor_instance=auditor,
            standards=standards,
            required_score=required_score,
            dimensions=dimensions or [
                AuditDimension.CODE_QUALITY,
                AuditDimension.SECURITY,
                AuditDimension.MAINTAINABILITY,
            ],
        )
        
        self._pending_audits[audit_id] = audit_task
        await self._audit_queue.put(audit_task)
        
        return audit_id
    
    async def _select_auditor(
        self,
        executor_instance: str,
        task_executors: Optional[Set[str]] = None,
    ) -> str:
        available_auditors = self._audit_pool.get_available_instances()
        
        excluded = self._isolation_rules.get_excluded_auditors(
            executor_instance,
            task_executors,
        )
        
        candidates = [
            a for a in available_auditors
            if getattr(a, "instance_id", str(id(a))) not in excluded
        ]
        
        if not candidates:
            raise RuntimeError(
                f"No available auditor for executor {executor_instance}",
            )
        
        selected = candidates[0]
        instance_id = getattr(selected, "instance_id", str(id(selected)))
        self._audit_pool.acquire(instance_id)
        
        return instance_id
    
    async def execute_audit(self, audit_task: AuditTask) -> AuditReport:
        start_time = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        
        auditor = self._audit_pool.get_instance(audit_task.auditor_instance)
        
        context = AuditContext(
            audit_id=audit_task.audit_id,
            standards=audit_task.standards,
            isolation_mode=True,
            executor_identity_hidden=True,
        )
        
        report = await self._perform_audit(audit_task, context)
        
        end_time = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        object.__setattr__(report, "audit_duration_ms", end_time - start_time)
        
        self._reports[audit_task.audit_id] = report
        
        self._audit_pool.release(audit_task.auditor_instance)
        
        return report
    
    async def _perform_audit(
        self,
        task: AuditTask,
        context: AuditContext,
    ) -> AuditReport:
        issues: List[AuditIssue] = []
        dimensions: List[DimensionScore] = []
        
        for dimension in task.dimensions:
            dim_issues, dim_score = await self._audit_dimension(
                task.code_artifacts,
                dimension,
                context,
            )
            issues.extend(dim_issues)
            dimensions.append(dim_score)
        
        weights = self._standards_registry.get_dimension_weights()
        total_weight = sum(weights.get(d.dimension.value, 0.2) for d in dimensions)
        weighted_score = sum(
            d.score * weights.get(d.dimension.value, 0.2)
            for d in dimensions
        )
        overall_score = weighted_score / total_weight if total_weight > 0 else 0
        
        passed = overall_score >= task.required_score
        
        critical_count = sum(1 for i in issues if i.severity in (Severity.CRITICAL, Severity.HIGH))
        if critical_count > 0:
            passed = False
        
        recommendations = self._generate_recommendations(issues, dimensions)
        
        return AuditReport(
            report_id=self._generate_id(),
            execution_id=task.execution_id,
            auditor_instance=task.auditor_instance,
            overall_score=overall_score,
            passed=passed,
            dimensions=dimensions,
            issues=issues,
            recommendations=recommendations,
            code_artifacts_hash=self._compute_hash(task.code_artifacts),
        )
    
    async def _audit_dimension(
        self,
        artifacts: CodeArtifacts,
        dimension: AuditDimension,
        context: AuditContext,
    ) -> tuple[List[AuditIssue], DimensionScore]:
        issues: List[AuditIssue] = []
        score = 100.0
        
        for file_path, content in artifacts.files.items():
            file_issues = self._analyze_file(file_path, content, dimension)
            issues.extend(file_issues)
        
        for issue in issues:
            penalty = {
                Severity.CRITICAL: 30,
                Severity.HIGH: 20,
                Severity.MEDIUM: 10,
                Severity.LOW: 5,
                Severity.INFO: 0,
            }.get(issue.severity, 0)
            score -= penalty
        
        score = max(0, min(100, score))
        
        return issues, DimensionScore(
            dimension=dimension,
            score=score,
            issues_count=len(issues),
            details=[f"Found {len(issues)} issues"],
        )
    
    def _analyze_file(
        self,
        file_path: str,
        content: str,
        dimension: AuditDimension,
    ) -> List[AuditIssue]:
        issues: List[AuditIssue] = []
        lines = content.split("\n")
        
        if dimension == AuditDimension.SECURITY:
            security_patterns = [
                ("password", "Hardcoded password detected"),
                ("api_key", "Hardcoded API key detected"),
                ("secret", "Hardcoded secret detected"),
                ("eval(", "Use of eval() is dangerous"),
                ("exec(", "Use of exec() is dangerous"),
            ]
            
            for i, line in enumerate(lines, 1):
                for pattern, desc in security_patterns:
                    if pattern.lower() in line.lower():
                        issues.append(AuditIssue(
                            issue_id=self._generate_id(),
                            severity=Severity.HIGH,
                            category="security",
                            dimension=dimension,
                            location=CodeLocation(
                                file_path=file_path,
                                line_start=i,
                            ),
                            description=desc,
                            suggestion=f"Remove or use environment variables for {pattern}",
                        ))
        
        elif dimension == AuditDimension.CODE_QUALITY:
            for i, line in enumerate(lines, 1):
                if len(line) > 120:
                    issues.append(AuditIssue(
                        issue_id=self._generate_id(),
                        severity=Severity.LOW,
                        category="style",
                        dimension=dimension,
                        location=CodeLocation(
                            file_path=file_path,
                            line_start=i,
                        ),
                        description="Line too long",
                        suggestion="Break line into multiple lines",
                    ))
        
        elif dimension == AuditDimension.MAINTAINABILITY:
            for i, line in enumerate(lines, 1):
                if "TODO" in line or "FIXME" in line:
                    issues.append(AuditIssue(
                        issue_id=self._generate_id(),
                        severity=Severity.INFO,
                        category="todo",
                        dimension=dimension,
                        location=CodeLocation(
                            file_path=file_path,
                            line_start=i,
                        ),
                        description="Unresolved TODO/FIXME",
                        suggestion="Resolve or document the TODO item",
                    ))
        
        return issues
    
    def _generate_recommendations(
        self,
        issues: List[AuditIssue],
        dimensions: List[DimensionScore],
    ) -> List[Recommendation]:
        recommendations: List[Recommendation] = []
        
        critical_issues = [i for i in issues if i.severity == Severity.CRITICAL]
        if critical_issues:
            recommendations.append(Recommendation(
                recommendation_id=self._generate_id(),
                priority=1,
                category="critical",
                description=f"Fix {len(critical_issues)} critical issues before deployment",
                impact="High - May cause security vulnerabilities or system failures",
                effort="Medium to High",
            ))
        
        high_issues = [i for i in issues if i.severity == Severity.HIGH]
        if high_issues:
            recommendations.append(Recommendation(
                recommendation_id=self._generate_id(),
                priority=2,
                category="security",
                description=f"Address {len(high_issues)} high-severity issues",
                impact="Medium - May affect security or reliability",
                effort="Medium",
            ))
        
        for dim in dimensions:
            if dim.percentage < 80:
                recommendations.append(Recommendation(
                    recommendation_id=self._generate_id(),
                    priority=3,
                    category=dim.dimension.value,
                    description=f"Improve {dim.dimension.value} score (current: {dim.percentage:.1f}%)",
                    impact="Medium - Improves code quality",
                    effort="Low to Medium",
                ))
        
        return recommendations
    
    async def process_feedback(self, report: AuditReport) -> FeedbackAction:
        if report.passed:
            return FeedbackAction(
                action_type="proceed",
                message="Audit passed. Proceeding to next stage.",
            )
        
        critical_issues = report.get_critical_issues()
        high_issues = report.get_high_issues()
        
        if critical_issues:
            return FeedbackAction(
                action_type="fix_required",
                target_stage="fix",
                issues=critical_issues,
                max_retries=3,
                message=f"Found {len(critical_issues)} critical issues that must be fixed.",
            )
        
        if high_issues:
            return FeedbackAction(
                action_type="fix_required",
                target_stage="fix",
                issues=high_issues,
                max_retries=2,
                message=f"Found {len(high_issues)} high-severity issues that should be fixed.",
            )
        
        return FeedbackAction(
            action_type="warn_and_proceed",
            issues=report.issues,
            message="Minor issues found. Proceeding with warnings.",
        )
    
    def get_report(self, audit_id: str) -> Optional[AuditReport]:
        return self._reports.get(audit_id)
    
    def get_pending_count(self) -> int:
        return self._audit_queue.qsize()
    
    def _compute_hash(self, artifacts: CodeArtifacts) -> str:
        content = "".join(artifacts.files.values())
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _generate_id(self) -> str:
        return str(uuid.uuid4())
