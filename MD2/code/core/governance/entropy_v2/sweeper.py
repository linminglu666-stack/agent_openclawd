from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Set
import threading
import uuid

from base_types import (
    utc_now, EntropyCategory, EntropyLevel, SweepAction, SweepPriority, SweepStatus,
    AlertSeverity
)
from calculator import EntropyCalculator
from monitor import EntropyMonitor


@dataclass
class SweepStrategy:
    strategy_id: str
    name: str
    category: EntropyCategory
    priority: SweepPriority
    condition: Callable[[float], bool]
    action_generator: Callable[[], List[SweepAction]]
    estimated_duration_seconds: float = 60.0
    auto_execute: bool = False
    max_concurrent: int = 1


@dataclass
class SweepExecutionResult:
    action_id: str
    success: bool
    entropy_before: float
    entropy_after: float
    impact: float
    duration_seconds: float
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SweepSchedule:
    schedule_id: str
    cron_expression: str
    strategies: List[str]
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class EntropySweeper:
    def __init__(
        self,
        calculator: EntropyCalculator,
        monitor: EntropyMonitor,
        max_history: int = 1000,
        execution_timeout_seconds: float = 300.0,
    ):
        self._calculator = calculator
        self._monitor = monitor
        self._max_history = max_history
        self._execution_timeout = execution_timeout_seconds
        self._strategies: Dict[str, SweepStrategy] = {}
        self._actions: Dict[str, SweepAction] = {}
        self._execution_history: List[SweepExecutionResult] = []
        self._executors: Dict[str, Callable[[SweepAction], bool]] = {}
        self._running_actions: Set[str] = set()
        self._lock = threading.RLock()
        self._register_default_strategies()
        self._register_default_executors()

    def _register_default_strategies(self) -> None:
        default_strategies = [
            SweepStrategy(
                strategy_id="clear_stale_inbox",
                name="Clear Stale Inbox Items",
                category=EntropyCategory.INPUT,
                priority=SweepPriority.HIGH,
                condition=lambda e: e > 0.3,
                action_generator=lambda: self._generate_inbox_actions(),
                estimated_duration_seconds=30.0,
                auto_execute=True,
            ),
            SweepStrategy(
                strategy_id="index_unindexed",
                name="Index Unindexed Outputs",
                category=EntropyCategory.EVOLUTION,
                priority=SweepPriority.MEDIUM,
                condition=lambda e: e > 0.4,
                action_generator=lambda: self._generate_index_actions(),
                estimated_duration_seconds=120.0,
                auto_execute=True,
            ),
            SweepStrategy(
                strategy_id="merge_duplicates",
                name="Merge Duplicate Topics",
                category=EntropyCategory.DATA,
                priority=SweepPriority.LOW,
                condition=lambda e: e > 0.5,
                action_generator=lambda: self._generate_duplicate_actions(),
                estimated_duration_seconds=180.0,
                auto_execute=False,
            ),
            SweepStrategy(
                strategy_id="cleanup_orphans",
                name="Cleanup Orphaned Resources",
                category=EntropyCategory.STRUCTURE,
                priority=SweepPriority.MEDIUM,
                condition=lambda e: e > 0.35,
                action_generator=lambda: self._generate_orphan_actions(),
                estimated_duration_seconds=90.0,
                auto_execute=True,
            ),
            SweepStrategy(
                strategy_id="compress_history",
                name="Compress Historical Data",
                category=EntropyCategory.DATA,
                priority=SweepPriority.DEFERRED,
                condition=lambda e: e > 0.6,
                action_generator=lambda: self._generate_compress_actions(),
                estimated_duration_seconds=300.0,
                auto_execute=False,
            ),
        ]
        for strategy in default_strategies:
            self._strategies[strategy.strategy_id] = strategy

    def _register_default_executors(self) -> None:
        self._executors["clear_inbox_item"] = self._execute_clear_inbox
        self._executors["index_output"] = self._execute_index_output
        self._executors["merge_topic"] = self._execute_merge_topic
        self._executors["delete_orphan"] = self._execute_delete_orphan
        self._executors["compress_data"] = self._execute_compress_data

    def _generate_inbox_actions(self) -> List[SweepAction]:
        actions: List[SweepAction] = []
        return actions

    def _generate_index_actions(self) -> List[SweepAction]:
        return []

    def _generate_duplicate_actions(self) -> List[SweepAction]:
        return []

    def _generate_orphan_actions(self) -> List[SweepAction]:
        return []

    def _generate_compress_actions(self) -> List[SweepAction]:
        return []

    def register_strategy(self, strategy: SweepStrategy) -> None:
        with self._lock:
            self._strategies[strategy.strategy_id] = strategy

    def register_executor(
        self, action_type: str, executor: Callable[[SweepAction], bool]
    ) -> None:
        with self._lock:
            self._executors[action_type] = executor

    def plan_sweep(
        self,
        categories: Optional[List[EntropyCategory]] = None,
        auto_only: bool = False,
    ) -> List[SweepAction]:
        now = utc_now()
        planned_actions: List[SweepAction] = []
        with self._lock:
            categories_to_check = categories or list(EntropyCategory)
            for category in categories_to_check:
                entropy_value = self._calculator.compute_entropy(category=category)
                for strategy in self._strategies.values():
                    if strategy.category != category:
                        continue
                    if auto_only and not strategy.auto_execute:
                        continue
                    if strategy.condition(entropy_value):
                        actions = strategy.action_generator()
                        for action in actions:
                            if action.action_id not in self._actions:
                                self._actions[action.action_id] = action
                                planned_actions.append(action)
        planned_actions.sort(key=lambda a: (a.priority.value, -a.estimated_impact))
        return planned_actions

    def prioritize_actions(
        self,
        actions: List[SweepAction],
        max_actions: int = 10,
    ) -> List[SweepAction]:
        def score(action: SweepAction) -> float:
            priority_score = {
                SweepPriority.CRITICAL: 100,
                SweepPriority.HIGH: 75,
                SweepPriority.MEDIUM: 50,
                SweepPriority.LOW: 25,
                SweepPriority.DEFERRED: 10,
            }.get(action.priority, 0)
            impact_score = action.estimated_impact * 50
            age_hours = (utc_now() - action.created_at).total_seconds() / 3600
            urgency_score = min(age_hours * 2, 20)
            return priority_score + impact_score + urgency_score
        scored = [(action, score(action)) for action in actions]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [action for action, _ in scored[:max_actions]]

    def execute_action(
        self,
        action: SweepAction,
        dry_run: bool = False,
    ) -> SweepExecutionResult:
        start_time = utc_now()
        entropy_before = self._calculator.compute_entropy(category=action.category)
        success = False
        error_message = None
        details: Dict[str, Any] = {}
        with self._lock:
            if action.action_id in self._running_actions:
                return SweepExecutionResult(
                    action_id=action.action_id,
                    success=False,
                    entropy_before=entropy_before,
                    entropy_after=entropy_before,
                    impact=0.0,
                    duration_seconds=0.0,
                    error_message="Action already running",
                )
            self._running_actions.add(action.action_id)
            action.status = SweepStatus.RUNNING
            action.started_at = start_time
        try:
            if dry_run:
                success = True
                details["dry_run"] = True
            else:
                executor = self._executors.get(action.executor or "default")
                if executor:
                    success = executor(action)
                else:
                    success = self._default_executor(action)
        except Exception as e:
            error_message = str(e)
            success = False
        finally:
            with self._lock:
                self._running_actions.discard(action.action_id)
                action.completed_at = utc_now()
                action.status = SweepStatus.COMPLETED if success else SweepStatus.FAILED
                action.error_message = error_message
        end_time = utc_now()
        duration = (end_time - start_time).total_seconds()
        entropy_after = self._calculator.compute_entropy(category=action.category)
        impact = entropy_before - entropy_after
        action.actual_impact = impact
        result = SweepExecutionResult(
            action_id=action.action_id,
            success=success,
            entropy_before=entropy_before,
            entropy_after=entropy_after,
            impact=impact,
            duration_seconds=duration,
            error_message=error_message,
            details=details,
        )
        with self._lock:
            self._execution_history.append(result)
            if len(self._execution_history) > self._max_history:
                self._execution_history = self._execution_history[-self._max_history:]
        return result

    def execute_batch(
        self,
        actions: List[SweepAction],
        parallel: bool = False,
        stop_on_failure: bool = False,
        dry_run: bool = False,
    ) -> List[SweepExecutionResult]:
        results: List[SweepExecutionResult] = []
        if parallel:
            threads: List[threading.Thread] = []
            results_lock = threading.Lock()
            def execute_and_store(action: SweepAction) -> None:
                result = self.execute_action(action, dry_run=dry_run)
                with results_lock:
                    results.append(result)
            for action in actions:
                thread = threading.Thread(target=execute_and_store, args=(action,))
                thread.start()
                threads.append(thread)
            for thread in threads:
                thread.join(timeout=self._execution_timeout)
        else:
            for action in actions:
                result = self.execute_action(action, dry_run=dry_run)
                results.append(result)
                if not result.success and stop_on_failure:
                    break
        return results

    def auto_sweep(
        self,
        max_actions: int = 5,
        categories: Optional[List[EntropyCategory]] = None,
    ) -> List[SweepExecutionResult]:
        planned = self.plan_sweep(categories=categories, auto_only=True)
        prioritized = self.prioritize_actions(planned, max_actions=max_actions)
        return self.execute_batch(prioritized, parallel=False, stop_on_failure=False)

    def _default_executor(self, action: SweepAction) -> bool:
        return True

    def _execute_clear_inbox(self, action: SweepAction) -> bool:
        return True

    def _execute_index_output(self, action: SweepAction) -> bool:
        return True

    def _execute_merge_topic(self, action: SweepAction) -> bool:
        return True

    def _execute_delete_orphan(self, action: SweepAction) -> bool:
        return True

    def _execute_compress_data(self, action: SweepAction) -> bool:
        return True

    def get_pending_actions(
        self,
        category: Optional[EntropyCategory] = None,
        priority: Optional[SweepPriority] = None,
        limit: int = 100,
    ) -> List[SweepAction]:
        with self._lock:
            result = [
                a for a in self._actions.values()
                if a.status == SweepStatus.PENDING
            ]
            if category:
                result = [a for a in result if a.category == category]
            if priority:
                result = [a for a in result if a.priority == priority]
            result.sort(key=lambda a: (a.priority.value, -a.estimated_impact))
            return result[:limit]

    def get_execution_history(
        self,
        category: Optional[EntropyCategory] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[SweepExecutionResult]:
        with self._lock:
            result = self._execution_history.copy()
        if category:
            result = [r for r in result if self._actions.get(r.action_id, None) is not None and self._actions[r.action_id].category == category]
        if since:
            result = [r for r in result if self._actions.get(r.action_id, None) is not None and self._actions[r.action_id].completed_at and self._actions[r.action_id].completed_at >= since]
        return result[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            total_actions = len(self._actions)
            pending = sum(1 for a in self._actions.values() if a.status == SweepStatus.PENDING)
            running = sum(1 for a in self._actions.values() if a.status == SweepStatus.RUNNING)
            completed = sum(1 for a in self._actions.values() if a.status == SweepStatus.COMPLETED)
            failed = sum(1 for a in self._actions.values() if a.status == SweepStatus.FAILED)
            total_impact = sum(r.impact for r in self._execution_history if r.success)
            avg_duration = 0.0
            if self._execution_history:
                avg_duration = sum(r.duration_seconds for r in self._execution_history) / len(self._execution_history)
        return {
            "total_actions": total_actions,
            "pending": pending,
            "running": running,
            "completed": completed,
            "failed": failed,
            "total_entropy_reduction": total_impact,
            "avg_duration_seconds": avg_duration,
        }
