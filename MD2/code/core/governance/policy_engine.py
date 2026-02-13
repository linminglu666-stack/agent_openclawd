from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import asyncio

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocols.interfaces import IPolicyEngine


@dataclass
class PolicyRule:
    rule_id: str
    effect: str
    action: str = "*"
    resource: str = "*"
    condition: Dict[str, Any] = field(default_factory=dict)
    obligations: List[Dict[str, Any]] = field(default_factory=list)


class SimplePolicyEngine(IPolicyEngine):
    def __init__(self, default_allow: bool = False):
        self._default_allow = bool(default_allow)
        self._rules: List[PolicyRule] = []
        self._lock = asyncio.Lock()

    async def decide(
        self,
        subject: Dict[str, Any],
        action: str,
        resource: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        matched: List[PolicyRule] = []
        async with self._lock:
            rules = list(self._rules)

        for rule in rules:
            if not self._match(rule.action, action):
                continue
            if not self._match(rule.resource, str(resource.get("type", "*"))):
                continue
            if not self._conditions_ok(rule.condition, subject, resource, context):
                continue
            matched.append(rule)

        for rule in matched:
            if rule.effect.lower() == "deny":
                return {
                    "allowed": False,
                    "reason": f"denied_by_rule:{rule.rule_id}",
                    "obligations": rule.obligations,
                }

        for rule in matched:
            if rule.effect.lower() == "allow":
                return {
                    "allowed": True,
                    "reason": f"allowed_by_rule:{rule.rule_id}",
                    "obligations": rule.obligations,
                }

        return {"allowed": self._default_allow, "reason": "default", "obligations": []}

    async def add_rule(self, rule: PolicyRule) -> bool:
        async with self._lock:
            self._rules.append(rule)
        return True

    def _match(self, pattern: str, value: str) -> bool:
        return pattern == "*" or str(pattern) == str(value)

    def _conditions_ok(self, conditions: Dict[str, Any], subject: Dict[str, Any], resource: Dict[str, Any], context: Dict[str, Any]) -> bool:
        if not conditions:
            return True
        for k, expected in conditions.items():
            actual = context.get(k)
            if actual is None:
                actual = subject.get(k)
            if actual is None:
                actual = resource.get(k)
            if str(actual) != str(expected):
                return False
        return True

