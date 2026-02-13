from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass(frozen=True)
class IsolationRule:
    rule_id: str
    description: str
    check_fn: Callable[..., bool]
    severity: str = "critical"
    enabled: bool = True


class IsolationViolationError(Exception):
    def __init__(self, rule_id: str, description: str):
        self.rule_id = rule_id
        self.description = description
        super().__init__(f"Isolation rule {rule_id} violated: {description}")


class IsolationRuleEngine:
    RULES: List[IsolationRule] = [
        IsolationRule(
            rule_id="ISO-001",
            description="Auditor instance cannot be assigned execution tasks",
            check_fn=lambda ctx: ctx.get("instance_pool_type") != "audit",
            severity="critical",
        ),
        IsolationRule(
            rule_id="ISO-002",
            description="Executor instance cannot audit its own code",
            check_fn=lambda ctx: ctx.get("auditor_id") != ctx.get("executor_id"),
            severity="critical",
        ),
        IsolationRule(
            rule_id="ISO-003",
            description="Same task requires different executor and auditor instances",
            check_fn=lambda ctx: ctx.get("auditor_id") not in ctx.get("task_executors", set()),
            severity="critical",
        ),
        IsolationRule(
            rule_id="ISO-004",
            description="Audit instance cannot access executor instance context",
            check_fn=lambda ctx: not ctx.get("context_shared", False),
            severity="critical",
        ),
        IsolationRule(
            rule_id="ISO-005",
            description="Audit results must be delivered through independent channel",
            check_fn=lambda ctx: ctx.get("channel_isolated", True),
            severity="high",
        ),
        IsolationRule(
            rule_id="ISO-006",
            description="Audit instance should use independent model configuration",
            check_fn=lambda ctx: ctx.get("model_config_isolated", True),
            severity="medium",
        ),
    ]
    
    def __init__(self, custom_rules: Optional[List[IsolationRule]] = None):
        self._rules = list(self.RULES)
        if custom_rules:
            self._rules.extend(custom_rules)
    
    def validate(
        self,
        executor_instance: str,
        auditor_instance: Optional[str] = None,
        task_executors: Optional[Set[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        ctx = {
            "executor_id": executor_instance,
            "auditor_id": auditor_instance,
            "task_executors": task_executors or set(),
            **(context or {}),
        }
        
        violations = []
        
        for rule in self._rules:
            if not rule.enabled:
                continue
            
            try:
                if not rule.check_fn(ctx):
                    violations.append((rule.rule_id, rule.description))
            except Exception:
                pass
        
        if violations:
            rule_id, description = violations[0]
            raise IsolationViolationError(rule_id, description)
        
        return True
    
    def get_excluded_auditors(
        self,
        executor_instance: str,
        task_executors: Optional[Set[str]] = None,
    ) -> Set[str]:
        excluded = {executor_instance}
        if task_executors:
            excluded.update(task_executors)
        return excluded
    
    def add_rule(self, rule: IsolationRule) -> None:
        self._rules.append(rule)
    
    def disable_rule(self, rule_id: str) -> None:
        for rule in self._rules:
            if rule.rule_id == rule_id:
                object.__setattr__(rule, "enabled", False)
                break
    
    def get_rules(self) -> List[IsolationRule]:
        return list(self._rules)


class AuditStandardsRegistry:
    STANDARDS: Dict[str, Dict[str, Any]] = {
        "python": {
            "style": ["pep8", "pep257"],
            "security": ["bandit", "safety"],
            "complexity": ["mccabe", "radon"],
            "typing": ["mypy"],
        },
        "javascript": {
            "style": ["eslint", "prettier"],
            "security": ["npm-audit", "snyk"],
            "complexity": ["eslint-complexity"],
        },
        "typescript": {
            "style": ["eslint", "prettier"],
            "security": ["npm-audit", "snyk"],
            "complexity": ["eslint-complexity"],
            "typing": ["tsc"],
        },
        "go": {
            "style": ["gofmt", "golint"],
            "security": ["gosec"],
            "complexity": ["gocyclo"],
        },
        "java": {
            "style": ["checkstyle", "spotless"],
            "security": ["spotbugs", "dependency-check"],
            "complexity": ["pmd"],
        },
    }
    
    DIMENSION_WEIGHTS: Dict[str, float] = {
        "code_quality": 0.20,
        "security": 0.25,
        "performance": 0.15,
        "maintainability": 0.20,
        "compliance": 0.20,
    }
    
    def __init__(self):
        self._custom_standards: Dict[str, Dict[str, Any]] = {}
    
    def get_applicable_standards(self, language: str) -> List[str]:
        lang_standards = self.STANDARDS.get(language.lower(), {})
        custom_standards = self._custom_standards.get(language.lower(), {})
        
        all_standards = []
        for category, tools in {**lang_standards, **custom_standards}.items():
            all_standards.extend(tools)
        
        return all_standards
    
    def get_dimension_weights(self) -> Dict[str, float]:
        return dict(self.DIMENSION_WEIGHTS)
    
    def register_custom_standard(
        self,
        language: str,
        category: str,
        tools: List[str],
    ) -> None:
        if language.lower() not in self._custom_standards:
            self._custom_standards[language.lower()] = {}
        self._custom_standards[language.lower()][category] = tools
    
    def get_pass_threshold(self, dimension: str) -> float:
        thresholds = {
            "security": 0.9,
            "code_quality": 0.8,
            "performance": 0.75,
            "maintainability": 0.8,
            "compliance": 0.85,
        }
        return thresholds.get(dimension, 0.8)
