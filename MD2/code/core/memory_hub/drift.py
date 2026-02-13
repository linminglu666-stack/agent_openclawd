from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class DriftResult:
    score: float
    signals: List[str]
    details: Dict[str, Any]


class DriftDetector:
    def __init__(self, threshold: float = 0.6):
        self._threshold = threshold

    def detect(self, previous: Dict[str, Any], current: Dict[str, Any]) -> DriftResult:
        signals: List[str] = []
        details: Dict[str, Any] = {}

        prev_topic = str(previous.get("topic") or "").strip().lower()
        cur_topic = str(current.get("topic") or "").strip().lower()
        if prev_topic and cur_topic and prev_topic != cur_topic:
            signals.append("topic_changed")
            details["prev_topic"] = prev_topic
            details["cur_topic"] = cur_topic

        prev_goal = str(previous.get("goal") or "").strip().lower()
        cur_goal = str(current.get("goal") or "").strip().lower()
        if prev_goal and cur_goal and prev_goal != cur_goal:
            signals.append("goal_changed")
            details["prev_goal"] = prev_goal
            details["cur_goal"] = cur_goal

        score = min(1.0, 0.4 * len(signals))
        return DriftResult(score=score, signals=signals, details=details)

    def is_drift(self, previous: Dict[str, Any], current: Dict[str, Any]) -> bool:
        return self.detect(previous, current).score >= self._threshold

