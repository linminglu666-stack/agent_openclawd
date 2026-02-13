"""
错误模式与反模式学习模块
"""

from .error_registry import ErrorPatternRegistry, ErrorPattern, ErrorInstance
from .anti_pattern import AntiPatternDetector, AntiPattern, Remediation
from .failure_analyzer import FailureAnalyzer, FailureReport
from .learning_queue import LearningQueue, LearningTask

__all__ = [
    "ErrorPatternRegistry",
    "ErrorPattern",
    "ErrorInstance",
    "AntiPatternDetector",
    "AntiPattern",
    "Remediation",
    "FailureAnalyzer",
    "FailureReport",
    "LearningQueue",
    "LearningTask",
]
