from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import statistics
import re


class QualityDimension(Enum):
    CONSISTENCY = "consistency"
    CALIBRATION = "calibration"
    STRUCTURE = "structure"
    SEMANTICS = "semantics"
    COMPLETENESS = "completeness"
    RELEVANCE = "relevance"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class QualityScore:
    dimension: QualityDimension
    score: float
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))


@dataclass(frozen=True)
class QualityAssessment:
    assessment_id: str
    overall_score: float
    dimension_scores: Dict[QualityDimension, QualityScore]
    risk_level: RiskLevel
    confidence_interval: Tuple[float, float]
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))


@dataclass(frozen=True)
class FeedbackSignal:
    signal_id: str
    signal_type: str
    source: str
    target_dimension: QualityDimension
    adjustment: float
    reason: str
    timestamp: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))


class QualityValidator(ABC):
    @abstractmethod
    def validate(self, content: Any, context: Dict[str, Any]) -> QualityScore:
        pass
    
    @abstractmethod
    def get_dimension(self) -> QualityDimension:
        pass


class ConsistencyValidator(QualityValidator):
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
        self._history: List[Dict[str, Any]] = []
    
    def get_dimension(self) -> QualityDimension:
        return QualityDimension.CONSISTENCY
    
    def validate(self, content: Any, context: Dict[str, Any]) -> QualityScore:
        if isinstance(content, str):
            return self._validate_text_consistency(content, context)
        elif isinstance(content, dict):
            return self._validate_dict_consistency(content, context)
        elif isinstance(content, list):
            return self._validate_list_consistency(content, context)
        return QualityScore(
            dimension=self.get_dimension(),
            score=1.0,
            confidence=1.0,
            details={"message": "Unknown content type, assuming consistent"},
        )
    
    def _validate_text_consistency(self, text: str, context: Dict[str, Any]) -> QualityScore:
        issues = []
        score = 1.0
        
        contradictions = self._detect_contradictions(text)
        if contradictions:
            score -= 0.3 * len(contradictions)
            issues.extend(contradictions)
        
        if context.get("previous_outputs"):
            alignment = self._check_alignment(text, context["previous_outputs"])
            score *= alignment
            if alignment < 0.8:
                issues.append(f"Low alignment with previous outputs: {alignment:.2f}")
        
        score = max(0.0, min(1.0, score))
        
        return QualityScore(
            dimension=self.get_dimension(),
            score=score,
            confidence=0.9 if len(issues) == 0 else 0.7,
            details={
                "issues": issues,
                "contradiction_count": len([i for i in issues if "contradiction" in i.lower()]),
            },
        )
    
    def _validate_dict_consistency(self, data: Dict[str, Any], context: Dict[str, Any]) -> QualityScore:
        issues = []
        score = 1.0
        
        if "confidence" in data:
            conf = data["confidence"]
            if not 0 <= conf <= 1:
                issues.append(f"Invalid confidence value: {conf}")
                score -= 0.2
        
        if "steps" in data and isinstance(data["steps"], list):
            step_consistency = self._validate_list_consistency(data["steps"], context)
            score *= step_consistency.score
            if step_consistency.score < 0.8:
                issues.append("Inconsistent reasoning steps")
        
        return QualityScore(
            dimension=self.get_dimension(),
            score=max(0.0, min(1.0, score)),
            confidence=0.85,
            details={"issues": issues},
        )
    
    def _validate_list_consistency(self, items: List[Any], context: Dict[str, Any]) -> QualityScore:
        if not items:
            return QualityScore(
                dimension=self.get_dimension(),
                score=1.0,
                confidence=1.0,
                details={"message": "Empty list is consistent"},
            )
        
        if all(isinstance(i, dict) for i in items):
            keys_sets = [set(i.keys()) for i in items]
            common_keys = set.intersection(*keys_sets) if keys_sets else set()
            consistency = len(common_keys) / max(len(k) for k in keys_sets) if keys_sets else 1.0
            
            return QualityScore(
                dimension=self.get_dimension(),
                score=consistency,
                confidence=0.9,
                details={
                    "common_keys": len(common_keys),
                    "max_keys": max(len(k) for k in keys_sets) if keys_sets else 0,
                },
            )
        
        return QualityScore(
            dimension=self.get_dimension(),
            score=1.0,
            confidence=0.8,
            details={"message": "Non-dict list items"},
        )
    
    def _detect_contradictions(self, text: str) -> List[str]:
        contradictions = []
        
        patterns = [
            (r"\b(yes|true|correct)\b.*\b(no|false|incorrect)\b", "Possible yes/no contradiction"),
            (r"\b(can|will|should)\b.*\b(cannot|won't|shouldn't)\b", "Possible modal contradiction"),
            (r"\b(increase|rise|grow)\b.*\b(decrease|fall|shrink)\b", "Possible directional contradiction"),
        ]
        
        for pattern, message in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                contradictions.append(message)
        
        return contradictions
    
    def _check_alignment(self, text: str, previous_outputs: List[str]) -> float:
        if not previous_outputs:
            return 1.0
        
        current_words = set(text.lower().split())
        alignment_scores = []
        
        for prev in previous_outputs[-3:]:
            prev_words = set(prev.lower().split())
            overlap = len(current_words & prev_words)
            union = len(current_words | prev_words)
            if union > 0:
                alignment_scores.append(overlap / union)
        
        return statistics.mean(alignment_scores) if alignment_scores else 1.0


class CalibrationValidator(QualityValidator):
    def __init__(self):
        self._predictions: List[Tuple[float, bool]] = []
    
    def get_dimension(self) -> QualityDimension:
        return QualityDimension.CALIBRATION
    
    def validate(self, content: Any, context: Dict[str, Any]) -> QualityScore:
        confidence = self._extract_confidence(content)
        if confidence is None:
            return QualityScore(
                dimension=self.get_dimension(),
                score=0.5,
                confidence=0.5,
                details={"message": "No confidence value found"},
            )
        
        calibration_error = self._compute_calibration_error(confidence, context)
        
        score = 1.0 - calibration_error
        
        return QualityScore(
            dimension=self.get_dimension(),
            score=max(0.0, min(1.0, score)),
            confidence=0.85,
            details={
                "reported_confidence": confidence,
                "calibration_error": calibration_error,
                "sample_size": len(self._predictions),
            },
        )
    
    def _extract_confidence(self, content: Any) -> Optional[float]:
        if isinstance(content, dict):
            return content.get("confidence")
        if isinstance(content, str):
            match = re.search(r"confidence[:\s]+(\d+\.?\d*)", content, re.IGNORECASE)
            if match:
                return float(match.group(1))
        return None
    
    def _compute_calibration_error(self, confidence: float, context: Dict[str, Any]) -> float:
        actual_outcome = context.get("actual_outcome")
        if actual_outcome is not None:
            self._predictions.append((confidence, actual_outcome))
        
        if len(self._predictions) < 10:
            return 0.1
        
        bins = {i: [] for i in range(10)}
        for conf, outcome in self._predictions:
            bin_idx = min(int(conf * 10), 9)
            bins[bin_idx].append(outcome)
        
        total_error = 0.0
        total_count = 0
        
        for bin_idx, outcomes in bins.items():
            if outcomes:
                expected = (bin_idx + 0.5) / 10
                actual = sum(outcomes) / len(outcomes)
                total_error += abs(expected - actual) * len(outcomes)
                total_count += len(outcomes)
        
        return total_error / total_count if total_count > 0 else 0.0
    
    def record_outcome(self, predicted_confidence: float, actual_outcome: bool) -> None:
        self._predictions.append((predicted_confidence, actual_outcome))


class StructureValidator(QualityValidator):
    def __init__(self):
        self._required_fields = {
            "reasoning": ["query", "answer", "steps"],
            "task_result": ["task_id", "success", "output"],
            "agent_response": ["agent_id", "result"],
        }
    
    def get_dimension(self) -> QualityDimension:
        return QualityDimension.STRUCTURE
    
    def validate(self, content: Any, context: Dict[str, Any]) -> QualityScore:
        if not isinstance(content, dict):
            return QualityScore(
                dimension=self.get_dimension(),
                score=0.5,
                confidence=0.8,
                details={"message": "Content is not a dictionary"},
            )
        
        content_type = context.get("content_type", "reasoning")
        required = self._required_fields.get(content_type, [])
        
        present = [f for f in required if f in content]
        missing = [f for f in required if f not in content]
        
        score = len(present) / len(required) if required else 1.0
        
        type_issues = self._check_types(content, content_type)
        
        return QualityScore(
            dimension=self.get_dimension(),
            score=score,
            confidence=0.9,
            details={
                "present_fields": present,
                "missing_fields": missing,
                "type_issues": type_issues,
            },
        )
    
    def _check_types(self, content: Dict[str, Any], content_type: str) -> List[str]:
        issues = []
        
        if content_type == "reasoning":
            if "steps" in content and not isinstance(content["steps"], list):
                issues.append("'steps' should be a list")
            if "confidence" in content and not isinstance(content["confidence"], (int, float)):
                issues.append("'confidence' should be numeric")
        
        if content_type == "task_result":
            if "success" in content and not isinstance(content["success"], bool):
                issues.append("'success' should be boolean")
        
        return issues


class SemanticsValidator(QualityValidator):
    def __init__(self):
        self._stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being"}
    
    def get_dimension(self) -> QualityDimension:
        return QualityDimension.SEMANTICS
    
    def validate(self, content: Any, context: Dict[str, Any]) -> QualityScore:
        if isinstance(content, str):
            return self._validate_text_semantics(content, context)
        elif isinstance(content, dict):
            text_content = content.get("answer", content.get("output", ""))
            if isinstance(text_content, str):
                return self._validate_text_semantics(text_content, context)
        
        return QualityScore(
            dimension=self.get_dimension(),
            score=0.5,
            confidence=0.5,
            details={"message": "Cannot validate semantics for this content type"},
        )
    
    def _validate_text_semantics(self, text: str, context: Dict[str, Any]) -> QualityScore:
        issues = []
        score = 1.0
        
        words = [w for w in text.lower().split() if w not in self._stop_words]
        
        if len(words) < 5:
            issues.append("Response too short")
            score -= 0.2
        
        unique_ratio = len(set(words)) / len(words) if words else 0
        if unique_ratio < 0.3:
            issues.append("Low vocabulary diversity")
            score -= 0.1
        
        query = context.get("query", "")
        if query:
            query_words = set(w for w in query.lower().split() if w not in self._stop_words)
            response_words = set(words)
            overlap = len(query_words & response_words)
            relevance = overlap / len(query_words) if query_words else 0
            
            if relevance < 0.2:
                issues.append("Low relevance to query")
                score -= 0.2
        
        return QualityScore(
            dimension=self.get_dimension(),
            score=max(0.0, min(1.0, score)),
            confidence=0.8,
            details={
                "word_count": len(words),
                "unique_ratio": unique_ratio,
                "issues": issues,
            },
        )


class FeedbackLoop:
    def __init__(self, learning_rate: float = 0.1):
        self.learning_rate = learning_rate
        self._signals: List[FeedbackSignal] = []
        self._adjustments: Dict[QualityDimension, float] = {}
    
    def record_signal(self, signal: FeedbackSignal) -> None:
        self._signals.append(signal)
        self._apply_adjustment(signal)
    
    def _apply_adjustment(self, signal: FeedbackSignal) -> None:
        dim = signal.target_dimension
        current = self._adjustments.get(dim, 0.0)
        self._adjustments[dim] = current + signal.adjustment * self.learning_rate
    
    def get_adjustment(self, dimension: QualityDimension) -> float:
        return self._adjustments.get(dimension, 0.0)
    
    def get_recent_signals(self, count: int = 10) -> List[FeedbackSignal]:
        return self._signals[-count:]
    
    def reset_adjustments(self) -> None:
        self._adjustments.clear()


class SelfSupervisedQualityAssessor:
    def __init__(self):
        self._validators: Dict[QualityDimension, QualityValidator] = {
            QualityDimension.CONSISTENCY: ConsistencyValidator(),
            QualityDimension.CALIBRATION: CalibrationValidator(),
            QualityDimension.STRUCTURE: StructureValidator(),
            QualityDimension.SEMANTICS: SemanticsValidator(),
        }
        self._feedback_loop = FeedbackLoop()
        self._history: List[QualityAssessment] = []
    
    def assess(self, content: Any, context: Optional[Dict[str, Any]] = None) -> QualityAssessment:
        ctx = context or {}
        dimension_scores: Dict[QualityDimension, QualityScore] = {}
        
        for dimension, validator in self._validators.items():
            score = validator.validate(content, ctx)
            adjustment = self._feedback_loop.get_adjustment(dimension)
            adjusted_score = QualityScore(
                dimension=score.dimension,
                score=max(0.0, min(1.0, score.score + adjustment)),
                confidence=score.confidence,
                details=score.details,
            )
            dimension_scores[dimension] = adjusted_score
        
        scores = [s.score for s in dimension_scores.values()]
        overall = statistics.mean(scores) if scores else 0.5
        
        confidence_values = [s.score for s in dimension_scores.values()]
        stdev = statistics.stdev(confidence_values) if len(confidence_values) > 1 else 0.1
        ci_lower = max(0.0, overall - 1.96 * stdev)
        ci_upper = min(1.0, overall + 1.96 * stdev)
        
        risk_level = self._determine_risk(overall, dimension_scores)
        recommendations = self._generate_recommendations(dimension_scores)
        
        assessment = QualityAssessment(
            assessment_id=f"qa_{int(datetime.now(tz=timezone.utc).timestamp())}",
            overall_score=overall,
            dimension_scores=dimension_scores,
            risk_level=risk_level,
            confidence_interval=(ci_lower, ci_upper),
            recommendations=recommendations,
            metadata=ctx,
        )
        
        self._history.append(assessment)
        return assessment
    
    def _determine_risk(
        self,
        overall: float,
        dimension_scores: Dict[QualityDimension, QualityScore],
    ) -> RiskLevel:
        if overall < 0.3:
            return RiskLevel.CRITICAL
        if overall < 0.5:
            return RiskLevel.HIGH
        if overall < 0.7:
            low_scores = [s for s in dimension_scores.values() if s.score < 0.5]
            if len(low_scores) >= 2:
                return RiskLevel.HIGH
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
    
    def _generate_recommendations(
        self,
        dimension_scores: Dict[QualityDimension, QualityScore],
    ) -> List[str]:
        recommendations = []
        
        for dimension, score in dimension_scores.items():
            if score.score < 0.5:
                if dimension == QualityDimension.CONSISTENCY:
                    recommendations.append("Review output for internal contradictions")
                elif dimension == QualityDimension.CALIBRATION:
                    recommendations.append("Recalibrate confidence estimates")
                elif dimension == QualityDimension.STRUCTURE:
                    recommendations.append("Ensure all required fields are present")
                elif dimension == QualityDimension.SEMANTICS:
                    recommendations.append("Improve response relevance and clarity")
        
        return recommendations
    
    def record_feedback(
        self,
        dimension: QualityDimension,
        adjustment: float,
        reason: str,
        source: str = "manual",
    ) -> None:
        signal = FeedbackSignal(
            signal_id=f"fb_{int(datetime.now(tz=timezone.utc).timestamp())}",
            signal_type="adjustment",
            source=source,
            target_dimension=dimension,
            adjustment=adjustment,
            reason=reason,
        )
        self._feedback_loop.record_signal(signal)
    
    def get_history(self, limit: int = 100) -> List[QualityAssessment]:
        return self._history[-limit:]
    
    def get_trends(self) -> Dict[QualityDimension, List[float]]:
        trends: Dict[QualityDimension, List[float]] = {dim: [] for dim in QualityDimension}
        
        for assessment in self._history[-50:]:
            for dim, score in assessment.dimension_scores.items():
                trends[dim].append(score.score)
        
        return trends
    
    def add_validator(self, validator: QualityValidator) -> None:
        self._validators[validator.get_dimension()] = validator
