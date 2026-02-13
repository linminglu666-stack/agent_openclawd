from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class FeatureFlag:
    flag_key: str
    scope: str
    rule: str
    default: bool = False


class FeatureFlagEvaluator:
    def evaluate(self, flag: FeatureFlag, context: Dict[str, Any]) -> bool:
        if not flag.rule:
            return bool(flag.default)
        result = self._eval_rule(flag.rule, context)
        if result is None:
            return bool(flag.default)
        return bool(result)

    def _eval_rule(self, rule: str, context: Dict[str, Any]) -> Optional[bool]:
        r = str(rule).strip()
        if "==" not in r:
            return None
        left, right = r.split("==", 1)
        left = left.strip()
        right = right.strip()

        if right.startswith(("'", '"')) and right.endswith(("'", '"')) and len(right) >= 2:
            right_value: Any = right[1:-1]
        elif right.lower() in {"true", "false"}:
            right_value = right.lower() == "true"
        else:
            right_value = right

        actual = self._resolve_path(left, context)
        if actual is None:
            return None
        return str(actual) == str(right_value)

    def _resolve_path(self, expr: str, context: Dict[str, Any]) -> Any:
        parts = [p.strip() for p in expr.split(".") if p.strip()]
        if not parts:
            return None
        cur: Any = context
        for p in parts:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
                continue
            return None
        return cur
