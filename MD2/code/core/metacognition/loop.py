from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocols.interfaces import IMetacognitionLoop

from .failure_library import FailurePatternLibrary, FailurePattern
from .cognitive_debt import CognitiveDebtLedger, CognitiveDebtItem


@dataclass
class MetacognitionConfig:
    failure_score: float = 1.0
    low_confidence_score: float = 0.5
    min_confidence: float = 0.6


class SimpleMetacognitionLoop(IMetacognitionLoop):
    def __init__(
        self,
        config: Optional[MetacognitionConfig] = None,
        failure_library: Optional[FailurePatternLibrary] = None,
        debt_ledger: Optional[CognitiveDebtLedger] = None,
    ):
        self._config = config or MetacognitionConfig()
        self._failures = failure_library or FailurePatternLibrary()
        self._debt = debt_ledger or CognitiveDebtLedger()
        self._last_trace: Optional[Dict[str, Any]] = None

    async def observe(self, trace: Dict[str, Any]) -> bool:
        self._last_trace = trace or {}
        trace_id = self._last_trace.get("trace_id")
        text = str(self._last_trace.get("error") or self._last_trace.get("message") or "")

        matched = await self._failures.match(text)
        if matched:
            await self._debt.add(
                CognitiveDebtItem(
                    debt_type="failure_pattern",
                    score=self._config.failure_score,
                    trace_id=trace_id,
                    details={"matched": [m.pattern_id for m in matched]},
                )
            )

        confidence = self._extract_confidence(self._last_trace)
        if confidence is not None and confidence < self._config.min_confidence:
            await self._debt.add(
                CognitiveDebtItem(
                    debt_type="low_confidence",
                    score=self._config.low_confidence_score,
                    trace_id=trace_id,
                    details={"confidence": confidence},
                )
            )

        return True

    async def propose_updates(self, window: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        last = self._last_trace or {}
        proposals: List[Dict[str, Any]] = []

        text = str(last.get("error") or last.get("message") or "")
        if text:
            proposals.append(
                {
                    "type": "add_failure_pattern",
                    "name": "auto_extracted",
                    "pattern": self._escape_for_regex(text[:80]),
                    "severity": "medium",
                    "remediation": ["increase_eval_threshold", "enable_fallback_route", "request_more_evidence"],
                }
            )

        if self._extract_confidence(last) is not None and self._extract_confidence(last) < self._config.min_confidence:
            proposals.append({"type": "tune_eval_gate", "min_score_delta": +0.05})

        return proposals

    async def apply_update(self, update: Dict[str, Any]) -> bool:
        update_type = update.get("type")
        if update_type == "add_failure_pattern":
            pattern = FailurePattern(
                name=str(update.get("name") or ""),
                pattern=str(update.get("pattern") or ""),
                severity=str(update.get("severity") or "medium"),
                remediation=list(update.get("remediation") or []),
                metadata=dict(update.get("metadata") or {}),
            )
            await self._failures.add(pattern)
            return True
        return False

    def _extract_confidence(self, trace: Dict[str, Any]) -> Optional[float]:
        if not trace:
            return None
        for k in ["confidence", "score"]:
            if k in trace:
                try:
                    return float(trace[k])
                except Exception:
                    return None
        return None

    def _escape_for_regex(self, text: str) -> str:
        return "".join("\\" + c if c in ".^$*+?{}[]\\|()" else c for c in text)

