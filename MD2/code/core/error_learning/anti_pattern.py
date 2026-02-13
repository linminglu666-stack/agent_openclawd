"""
反模式检测器
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import threading


class AntiPatternType(Enum):
    CODE_SMELL = "code_smell"
    ARCHITECTURAL = "architectural"
    PERFORMANCE = "performance"
    SECURITY = "security"
    PROCESS = "process"
    ORGANIZATIONAL = "organizational"


class Confidence(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Remediation:
    title: str
    description: str
    priority: int = 5
    effort: str = "medium"
    impact: str = "medium"
    
    code_example: Optional[str] = None
    references: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "effort": self.effort,
            "impact": self.impact,
            "code_example": self.code_example,
            "references": self.references,
        }


@dataclass
class AntiPattern:
    pattern_id: str
    name: str
    type: AntiPatternType
    description: str
    
    symptoms: List[str] = field(default_factory=list)
    causes: List[str] = field(default_factory=list)
    
    detection_rules: List[str] = field(default_factory=list)
    
    remediations: List[Remediation] = field(default_factory=list)
    
    severity: str = "medium"
    confidence: Confidence = Confidence.MEDIUM
    
    detection_count: int = 0
    last_detected: Optional[datetime] = None
    
    applicable_contexts: List[str] = field(default_factory=list)
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "symptoms": self.symptoms,
            "causes": self.causes,
            "detection_rules": self.detection_rules,
            "remediations": [r.to_dict() for r in self.remediations],
            "severity": self.severity,
            "confidence": self.confidence.value,
            "detection_count": self.detection_count,
            "last_detected": self.last_detected.isoformat() if self.last_detected else None,
            "applicable_contexts": self.applicable_contexts,
            "metadata": self.metadata,
        }


@dataclass
class Detection:
    detection_id: str
    pattern_id: str
    location: str
    
    context: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=datetime.now)
    
    severity: str = "medium"
    confidence: str = "medium"
    
    acknowledged: bool = False
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "detection_id": self.detection_id,
            "pattern_id": self.pattern_id,
            "location": self.location,
            "context": self.context,
            "detected_at": self.detected_at.isoformat(),
            "severity": self.severity,
            "confidence": self.confidence,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
        }


class AntiPatternDetector:
    
    def __init__(self):
        self._patterns: Dict[str, AntiPattern] = {}
        self._detections: Dict[str, Detection] = {}
        self._lock = threading.Lock()
        self._listeners: List[Callable] = []
        
        self._initialize_common_patterns()
    
    def _initialize_common_patterns(self):
        common_patterns = [
            AntiPattern(
                pattern_id="god_object",
                name="God Object",
                type=AntiPatternType.CODE_SMELL,
                description="A class that knows too much or does too much",
                symptoms=[
                    "Class has many methods",
                    "Class has many dependencies",
                    "Changes frequently",
                    "Difficult to test",
                ],
                causes=[
                    "Lack of proper decomposition",
                    "Organic growth over time",
                ],
                remediations=[
                    Remediation(
                        title="Decompose into smaller classes",
                        description="Split responsibilities into focused classes following Single Responsibility Principle",
                        priority=1,
                        effort="high",
                        impact="high",
                    ),
                ],
                severity="high",
            ),
            AntiPattern(
                pattern_id="spaghetti_code",
                name="Spaghetti Code",
                type=AntiPatternType.CODE_SMELL,
                description="Code with complex and tangled control structures",
                symptoms=[
                    "Deeply nested conditionals",
                    "Long methods",
                    "GOTO statements",
                    "Hard to follow logic",
                ],
                causes=[
                    "Lack of design planning",
                    "Quick fixes accumulating",
                ],
                remediations=[
                    Remediation(
                        title="Refactor with design patterns",
                        description="Apply Extract Method, Replace Conditional with Polymorphism",
                        priority=2,
                        effort="medium",
                        impact="high",
                    ),
                ],
                severity="high",
            ),
            AntiPattern(
                pattern_id="premature_optimization",
                name="Premature Optimization",
                type=AntiPatternType.PERFORMANCE,
                description="Optimizing code before measuring actual bottlenecks",
                symptoms=[
                    "Complex code for marginal gains",
                    "Difficult to maintain",
                    "No performance metrics",
                ],
                causes=[
                    "Assumptions about performance",
                    "Micro-optimization mindset",
                ],
                remediations=[
                    Remediation(
                        title="Profile first, optimize later",
                        description="Use profiling tools to identify real bottlenecks before optimizing",
                        priority=3,
                        effort="low",
                        impact="medium",
                    ),
                ],
                severity="medium",
            ),
            AntiPattern(
                pattern_id="magic_numbers",
                name="Magic Numbers",
                type=AntiPatternType.CODE_SMELL,
                description="Using unexplained numeric constants directly in code",
                symptoms=[
                    "Unexplained numeric literals",
                    "Same number in multiple places",
                    "Unclear meaning",
                ],
                causes=[
                    "Quick coding without refactoring",
                    "Lack of constants file",
                ],
                remediations=[
                    Remediation(
                        title="Extract to named constants",
                        description="Replace magic numbers with well-named constants",
                        priority=4,
                        effort="low",
                        impact="low",
                    ),
                ],
                severity="low",
            ),
            AntiPattern(
                pattern_id="copy_paste_programming",
                name="Copy-Paste Programming",
                type=AntiPatternType.CODE_SMELL,
                description="Duplicating code instead of creating reusable abstractions",
                symptoms=[
                    "Identical code blocks",
                    "Similar code with minor variations",
                    "Bug fixes needed in multiple places",
                ],
                causes=[
                    "Time pressure",
                    "Lack of refactoring discipline",
                ],
                remediations=[
                    Remediation(
                        title="Extract common functionality",
                        description="Create reusable functions or classes for duplicated logic",
                        priority=2,
                        effort="medium",
                        impact="high",
                    ),
                ],
                severity="medium",
            ),
            AntiPattern(
                pattern_id="big_ball_of_mud",
                name="Big Ball of Mud",
                type=AntiPatternType.ARCHITECTURAL,
                description="System with no discernible architecture",
                symptoms=[
                    "Circular dependencies",
                    "Everything depends on everything",
                    "No clear module boundaries",
                ],
                causes=[
                    "Organic growth",
                    "Lack of architectural vision",
                ],
                remediations=[
                    Remediation(
                        title="Introduce layered architecture",
                        description="Define clear layers and module boundaries",
                        priority=1,
                        effort="high",
                        impact="high",
                    ),
                ],
                severity="critical",
            ),
        ]
        
        for pattern in common_patterns:
            self._patterns[pattern.pattern_id] = pattern
    
    def register_pattern(self, pattern: AntiPattern) -> bool:
        with self._lock:
            if pattern.pattern_id in self._patterns:
                return False
            
            self._patterns[pattern.pattern_id] = pattern
            self._notify_listeners("pattern_registered", pattern)
            return True
    
    def detect(
        self,
        code_or_config: str,
        location: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Detection]:
        import uuid
        
        detections = []
        
        for pattern in self._patterns.values():
            if self._matches_pattern(code_or_config, pattern, context):
                detection = Detection(
                    detection_id=f"det-{uuid.uuid4().hex[:8]}",
                    pattern_id=pattern.pattern_id,
                    location=location,
                    context=context or {},
                    severity=pattern.severity,
                    confidence=pattern.confidence.value,
                )
                
                with self._lock:
                    self._detections[detection.detection_id] = detection
                    pattern.detection_count += 1
                    pattern.last_detected = datetime.now()
                
                detections.append(detection)
                self._notify_listeners("detected", detection)
        
        return detections
    
    def _matches_pattern(
        self,
        code_or_config: str,
        pattern: AntiPattern,
        context: Optional[Dict] = None
    ) -> bool:
        import re
        
        for rule in pattern.detection_rules:
            try:
                if re.search(rule, code_or_config, re.IGNORECASE | re.MULTILINE):
                    return True
            except re.error:
                continue
        
        return False
    
    def get_pattern(self, pattern_id: str) -> Optional[AntiPattern]:
        return self._patterns.get(pattern_id)
    
    def get_patterns_by_type(self, pattern_type: AntiPatternType) -> List[AntiPattern]:
        return [
            p for p in self._patterns.values()
            if p.type == pattern_type
        ]
    
    def get_detection(self, detection_id: str) -> Optional[Detection]:
        return self._detections.get(detection_id)
    
    def acknowledge_detection(self, detection_id: str) -> bool:
        with self._lock:
            detection = self._detections.get(detection_id)
            if not detection:
                return False
            
            detection.acknowledged = True
            return True
    
    def resolve_detection(self, detection_id: str) -> bool:
        with self._lock:
            detection = self._detections.get(detection_id)
            if not detection:
                return False
            
            detection.resolved = True
            return True
    
    def get_recent_detections(
        self,
        limit: int = 100,
        pattern_type: Optional[AntiPatternType] = None,
        unacknowledged_only: bool = False
    ) -> List[Detection]:
        detections = list(self._detections.values())
        
        if unacknowledged_only:
            detections = [d for d in detections if not d.acknowledged]
        
        detections.sort(key=lambda x: x.detected_at, reverse=True)
        return detections[:limit]
    
    def get_top_patterns(self, limit: int = 10) -> List[AntiPattern]:
        patterns = list(self._patterns.values())
        patterns.sort(key=lambda x: x.detection_count, reverse=True)
        return patterns[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        total_detections = len(self._detections)
        acknowledged = sum(1 for d in self._detections.values() if d.acknowledged)
        resolved = sum(1 for d in self._detections.values() if d.resolved)
        
        by_type = {}
        for pt in AntiPatternType:
            patterns = self.get_patterns_by_type(pt)
            by_type[pt.value] = {
                "pattern_count": len(patterns),
                "total_detections": sum(p.detection_count for p in patterns),
            }
        
        return {
            "total_patterns": len(self._patterns),
            "total_detections": total_detections,
            "acknowledged_detections": acknowledged,
            "resolved_detections": resolved,
            "by_type": by_type,
        }
    
    def add_listener(self, callback: Callable):
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable):
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self, event: str, data: Any):
        for callback in self._listeners:
            try:
                callback(event, data)
            except Exception:
                pass
