"""
离线评测集
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import json
import threading


class TestCaseType(Enum):
    STANDARD = "standard"
    EDGE_CASE = "edge_case"
    REGRESSION = "regression"
    PERFORMANCE = "performance"
    SAFETY = "safety"
    ADVERSARIAL = "adversarial"


@dataclass
class TestCase:
    case_id: str
    name: str
    test_type: TestCaseType
    
    input_data: Any
    expected_output: Any
    
    evaluation_criteria: Dict[str, Any] = field(default_factory=dict)
    
    tags: List[str] = field(default_factory=list)
    priority: int = 5
    
    timeout_seconds: int = 30
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "name": self.name,
            "test_type": self.test_type.value,
            "input_data": self.input_data,
            "expected_output": self.expected_output,
            "evaluation_criteria": self.evaluation_criteria,
            "tags": self.tags,
            "priority": self.priority,
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata,
        }


@dataclass
class TestResult:
    case_id: str
    passed: bool
    
    actual_output: Any = None
    error: Optional[str] = None
    
    execution_time_ms: int = 0
    
    score: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    
    executed_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "passed": self.passed,
            "actual_output": str(self.actual_output)[:500] if self.actual_output else None,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "score": self.score,
            "details": self.details,
            "executed_at": self.executed_at.isoformat(),
        }


@dataclass
class BenchmarkSuite:
    suite_id: str
    name: str
    description: str
    
    test_cases: List[TestCase] = field(default_factory=list)
    
    version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "name": self.name,
            "description": self.description,
            "test_cases": [c.to_dict() for c in self.test_cases],
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
        }
    
    def add_test_case(self, test_case: TestCase):
        self.test_cases.append(test_case)
        self.updated_at = datetime.now()
    
    def get_cases_by_type(self, test_type: TestCaseType) -> List[TestCase]:
        return [c for c in self.test_cases if c.test_type == test_type]
    
    def get_cases_by_tag(self, tag: str) -> List[TestCase]:
        return [c for c in self.test_cases if tag in c.tags]


@dataclass
class BenchmarkRun:
    run_id: str
    suite_id: str
    component: str
    version: str
    
    results: List[TestResult] = field(default_factory=list)
    
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    
    total_score: float = 0.0
    avg_score: float = 0.0
    
    total_time_ms: int = 0
    
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "suite_id": self.suite_id,
            "component": self.component,
            "version": self.version,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "pass_rate": self.pass_rate,
            "total_score": self.total_score,
            "avg_score": self.avg_score,
            "total_time_ms": self.total_time_ms,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
    
    @property
    def pass_rate(self) -> float:
        if self.total_cases == 0:
            return 0.0
        return self.passed_cases / self.total_cases
    
    def add_result(self, result: TestResult):
        self.results.append(result)
        
        if result.passed:
            self.passed_cases += 1
        else:
            self.failed_cases += 1
        
        self.total_cases += 1
        self.total_score += result.score
        self.total_time_ms += result.execution_time_ms
        self.avg_score = self.total_score / self.total_cases if self.total_cases > 0 else 0.0


class OfflineBenchmark:
    
    def __init__(self):
        self._suites: Dict[str, BenchmarkSuite] = {}
        self._runs: Dict[str, BenchmarkRun] = {}
        self._evaluators: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self._listeners: List[Callable] = []
        
        self._initialize_default_evaluators()
    
    def _initialize_default_evaluators(self):
        def exact_match_evaluator(test_case: TestCase, actual_output: Any) -> tuple[bool, float]:
            expected = test_case.expected_output
            passed = actual_output == expected
            score = 1.0 if passed else 0.0
            return passed, score
        
        def contains_evaluator(test_case: TestCase, actual_output: Any) -> tuple[bool, float]:
            expected = test_case.expected_output
            if isinstance(actual_output, str) and isinstance(expected, str):
                passed = expected.lower() in actual_output.lower()
                score = 1.0 if passed else 0.5
                return passed, score
            return False, 0.0
        
        def json_match_evaluator(test_case: TestCase, actual_output: Any) -> tuple[bool, float]:
            expected = test_case.expected_output
            try:
                if isinstance(actual_output, str):
                    actual = json.loads(actual_output)
                else:
                    actual = actual_output
                
                if isinstance(expected, str):
                    expected = json.loads(expected)
                
                passed = actual == expected
                score = 1.0 if passed else 0.0
                return passed, score
            except (json.JSONDecodeError, TypeError):
                return False, 0.0
        
        self._evaluators["exact_match"] = exact_match_evaluator
        self._evaluators["contains"] = contains_evaluator
        self._evaluators["json_match"] = json_match_evaluator
    
    def register_evaluator(self, name: str, evaluator: Callable):
        self._evaluators[name] = evaluator
    
    def create_suite(
        self,
        name: str,
        description: str,
        tags: Optional[List[str]] = None
    ) -> BenchmarkSuite:
        import uuid
        
        suite = BenchmarkSuite(
            suite_id=f"suite-{uuid.uuid4().hex[:8]}",
            name=name,
            description=description,
            tags=tags or [],
        )
        
        with self._lock:
            self._suites[suite.suite_id] = suite
        
        return suite
    
    def add_test_case(
        self,
        suite_id: str,
        name: str,
        input_data: Any,
        expected_output: Any,
        test_type: TestCaseType = TestCaseType.STANDARD,
        evaluation_criteria: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[TestCase]:
        import uuid
        
        suite = self._suites.get(suite_id)
        if not suite:
            return None
        
        test_case = TestCase(
            case_id=f"case-{uuid.uuid4().hex[:8]}",
            name=name,
            test_type=test_type,
            input_data=input_data,
            expected_output=expected_output,
            evaluation_criteria=evaluation_criteria or {},
            tags=tags or [],
        )
        
        suite.add_test_case(test_case)
        return test_case
    
    def run_benchmark(
        self,
        suite_id: str,
        component: str,
        version: str,
        executor: Callable,
        evaluator_name: str = "exact_match"
    ) -> Optional[BenchmarkRun]:
        import uuid
        import time
        
        suite = self._suites.get(suite_id)
        if not suite:
            return None
        
        run = BenchmarkRun(
            run_id=f"run-{uuid.uuid4().hex[:8]}",
            suite_id=suite_id,
            component=component,
            version=version,
        )
        
        evaluator = self._evaluators.get(evaluator_name, self._evaluators["exact_match"])
        
        for test_case in suite.test_cases:
            try:
                start_time = time.time()
                
                actual_output = executor(test_case.input_data, test_case.timeout_seconds)
                
                execution_time_ms = int((time.time() - start_time) * 1000)
                
                passed, score = evaluator(test_case, actual_output)
                
                result = TestResult(
                    case_id=test_case.case_id,
                    passed=passed,
                    actual_output=actual_output,
                    execution_time_ms=execution_time_ms,
                    score=score,
                )
                
            except Exception as e:
                result = TestResult(
                    case_id=test_case.case_id,
                    passed=False,
                    error=str(e),
                    execution_time_ms=test_case.timeout_seconds * 1000,
                    score=0.0,
                )
            
            run.add_result(result)
        
        run.completed_at = datetime.now()
        
        with self._lock:
            self._runs[run.run_id] = run
        
        self._notify_listeners("completed", run)
        return run
    
    def get_suite(self, suite_id: str) -> Optional[BenchmarkSuite]:
        return self._suites.get(suite_id)
    
    def get_run(self, run_id: str) -> Optional[BenchmarkRun]:
        return self._runs.get(run_id)
    
    def get_runs_by_component(
        self,
        component: str,
        limit: int = 100
    ) -> List[BenchmarkRun]:
        runs = [r for r in self._runs.values() if r.component == component]
        runs.sort(key=lambda x: x.started_at, reverse=True)
        return runs[:limit]
    
    def compare_runs(
        self,
        run_id_1: str,
        run_id_2: str
    ) -> Dict[str, Any]:
        run1 = self._runs.get(run_id_1)
        run2 = self._runs.get(run_id_2)
        
        if not run1 or not run2:
            return {"error": "One or both runs not found"}
        
        return {
            "run_1": run_id_1,
            "run_2": run_id_2,
            "pass_rate_diff": run2.pass_rate - run1.pass_rate,
            "avg_score_diff": run2.avg_score - run1.avg_score,
            "execution_time_diff_ms": run2.total_time_ms - run1.total_time_ms,
            "regression": run2.pass_rate < run1.pass_rate,
        }
    
    def get_regression_report(
        self,
        component: str,
        baseline_run_id: str
    ) -> Dict[str, Any]:
        baseline = self._runs.get(baseline_run_id)
        if not baseline:
            return {"error": "Baseline run not found"}
        
        recent_runs = self.get_runs_by_component(component, limit=10)
        recent_runs = [r for r in recent_runs if r.run_id != baseline_run_id]
        
        regressions = []
        for run in recent_runs:
            comparison = self.compare_runs(baseline_run_id, run.run_id)
            if comparison.get("regression"):
                regressions.append({
                    "run_id": run.run_id,
                    "version": run.version,
                    "pass_rate": run.pass_rate,
                    "baseline_pass_rate": baseline.pass_rate,
                    "diff": comparison["pass_rate_diff"],
                })
        
        return {
            "component": component,
            "baseline_run_id": baseline_run_id,
            "baseline_pass_rate": baseline.pass_rate,
            "regressions_found": len(regressions),
            "regressions": regressions,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_suites": len(self._suites),
            "total_runs": len(self._runs),
            "total_test_cases": sum(len(s.test_cases) for s in self._suites.values()),
            "evaluators_available": list(self._evaluators.keys()),
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
