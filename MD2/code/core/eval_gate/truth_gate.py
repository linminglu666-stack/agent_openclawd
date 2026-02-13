from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocols.interfaces import ITruthGate
from utils.logger import get_logger


@dataclass
class TruthGateConfig:
    min_evidence_items: int = 1
    min_score: float = 0.5
    require_non_empty_claim: bool = True


class TruthGate(ITruthGate):
    def __init__(self, config: Optional[TruthGateConfig] = None):
        self._config = config or TruthGateConfig()
        self._logger = get_logger("eval.truth_gate")

    async def check(self, claim: Dict[str, Any], evidence: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        reasons: List[str] = []

        claim_text = str(claim.get("text") or claim.get("claim") or "").strip()
        if self._config.require_non_empty_claim and not claim_text:
            reasons.append("empty_claim")

        evidence_items = evidence or []
        if len(evidence_items) < self._config.min_evidence_items:
            reasons.append("insufficient_evidence")

        score = 1.0
        if reasons:
            score = max(0.0, 1.0 - 0.5 * len(reasons))

        for ev in evidence_items:
            if ev.get("score") is not None:
                try:
                    score = min(score, float(ev["score"]))
                except Exception:
                    reasons.append("invalid_evidence_score")

        ok = score >= self._config.min_score and not reasons

        return {
            "ok": ok,
            "score": score,
            "reasons": reasons,
            "claim": claim,
            "evidence_count": len(evidence_items),
        }

