from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import uuid

from .checkpoint import CheckpointManager, CheckpointNotFoundError


class FailureType(Enum):
    INSTANCE_CRASH = "instance_crash"
    STAGE_EXECUTION_ERROR = "stage_execution_error"
    DATA_CORRUPTION = "data_corruption"
    NETWORK_ERROR = "network_error"
    STORAGE_ERROR = "storage_error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    CHECKPOINT_RESTORE = "checkpoint_restore"
    IDEMPOTENT_RETRY = "idempotent_retry"
    BACKUP_RESTORE = "backup_restore"
    RESUME_TRANSFER = "resume_transfer"
    MANUAL_INTERVENTION = "manual_intervention"


@dataclass
class FailureInfo:
    failure_id: str
    failure_type: FailureType
    execution_id: str
    stage_id: Optional[str] = None
    error_message: str = ""
    error_details: Dict[str, Any] = field(default_factory=dict)
    timestamp: int = 0
    recoverable: bool = True
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = int(datetime.now(tz=timezone.utc).timestamp())


@dataclass
class RecoveryResult:
    success: bool
    context: Optional[Any] = None
    resume_from_stage: Optional[str] = None
    message: str = ""
    recovery_strategy: Optional[RecoveryStrategy] = None
    retry_count: int = 0


class RecoveryFailedError(Exception):
    pass


class UnsupportedRecoveryStrategyError(Exception):
    pass


class RecoveryManager:
    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        exponential_backoff: bool = True,
    ):
        self._checkpoint_manager = checkpoint_manager
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._exponential_backoff = exponential_backoff
        self._idempotency_cache: Dict[str, Any] = {}
        self._operation_results: Dict[str, Any] = {}
        self._recovery_history: List[Dict[str, Any]] = []
    
    async def recover_execution(
        self,
        execution_id: str,
        failure_info: FailureInfo,
    ) -> RecoveryResult:
        self._record_recovery_attempt(execution_id, failure_info)
        
        recovery_strategy = self._determine_strategy(failure_info)
        
        try:
            if recovery_strategy == RecoveryStrategy.CHECKPOINT_RESTORE:
                result = await self._recover_from_checkpoint(execution_id)
            elif recovery_strategy == RecoveryStrategy.IDEMPOTENT_RETRY:
                result = await self._retry_with_idempotency(execution_id, failure_info)
            elif recovery_strategy == RecoveryStrategy.BACKUP_RESTORE:
                result = await self._recover_from_backup(execution_id)
            elif recovery_strategy == RecoveryStrategy.RESUME_TRANSFER:
                result = await self._resume_transfer(execution_id, failure_info)
            else:
                raise UnsupportedRecoveryStrategyError(
                    f"Unknown recovery strategy: {recovery_strategy}",
                )
            
            result.recovery_strategy = recovery_strategy
            self._record_recovery_success(execution_id, result)
            
            return result
            
        except Exception as e:
            self._record_recovery_failure(execution_id, str(e))
            raise RecoveryFailedError(
                f"Recovery failed for execution {execution_id}: {e}",
            )
    
    async def execute_with_idempotency(
        self,
        operation_id: str,
        operation: Callable,
        *args,
        **kwargs,
    ) -> Any:
        if operation_id in self._idempotency_cache:
            return self._idempotency_cache[operation_id]
        
        if operation_id in self._operation_results:
            return self._operation_results[operation_id]
        
        last_error = None
        for attempt in range(self._max_retries):
            try:
                result = await operation(*args, **kwargs)
                self._idempotency_cache[operation_id] = result
                self._operation_results[operation_id] = result
                return result
            except Exception as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    delay = self._calculate_delay(attempt)
                    await asyncio.sleep(delay)
        
        raise RecoveryFailedError(
            f"Operation {operation_id} failed after {self._max_retries} retries: {last_error}",
        )
    
    async def _recover_from_checkpoint(
        self,
        execution_id: str,
    ) -> RecoveryResult:
        try:
            context = await self._checkpoint_manager.restore_from_checkpoint(
                execution_id,
            )
            
            current_stage = context.current_state.current_stage
            
            return RecoveryResult(
                success=True,
                context=context,
                resume_from_stage=current_stage,
                message=f"Restored from checkpoint, resuming from stage: {current_stage}",
            )
        except CheckpointNotFoundError as e:
            return RecoveryResult(
                success=False,
                message=f"Checkpoint not found: {e}",
            )
    
    async def _retry_with_idempotency(
        self,
        execution_id: str,
        failure_info: FailureInfo,
    ) -> RecoveryResult:
        return RecoveryResult(
            success=True,
            resume_from_stage=failure_info.stage_id,
            message="Ready for idempotent retry",
            retry_count=self._get_retry_count(execution_id),
        )
    
    async def _recover_from_backup(
        self,
        execution_id: str,
    ) -> RecoveryResult:
        checkpoints = await self._checkpoint_manager.get_checkpoint_history(
            execution_id,
        )
        
        if len(checkpoints) < 2:
            return RecoveryResult(
                success=False,
                message="No backup checkpoint available",
            )
        
        backup_checkpoint = checkpoints[-2]
        
        context = await self._checkpoint_manager.restore_from_checkpoint(
            execution_id,
            backup_checkpoint.checkpoint_id,
        )
        
        return RecoveryResult(
            success=True,
            context=context,
            resume_from_stage=context.current_state.current_stage,
            message=f"Restored from backup checkpoint: {backup_checkpoint.checkpoint_id}",
        )
    
    async def _resume_transfer(
        self,
        execution_id: str,
        failure_info: FailureInfo,
    ) -> RecoveryResult:
        return RecoveryResult(
            success=True,
            message="Ready to resume transfer from last known state",
        )
    
    def _determine_strategy(self, failure_info: FailureInfo) -> RecoveryStrategy:
        strategy_map = {
            FailureType.INSTANCE_CRASH: RecoveryStrategy.CHECKPOINT_RESTORE,
            FailureType.STAGE_EXECUTION_ERROR: RecoveryStrategy.IDEMPOTENT_RETRY,
            FailureType.DATA_CORRUPTION: RecoveryStrategy.BACKUP_RESTORE,
            FailureType.NETWORK_ERROR: RecoveryStrategy.RESUME_TRANSFER,
            FailureType.STORAGE_ERROR: RecoveryStrategy.BACKUP_RESTORE,
            FailureType.TIMEOUT: RecoveryStrategy.IDEMPOTENT_RETRY,
            FailureType.UNKNOWN: RecoveryStrategy.CHECKPOINT_RESTORE,
        }
        return strategy_map.get(failure_info.failure_type, RecoveryStrategy.CHECKPOINT_RESTORE)
    
    def _calculate_delay(self, attempt: int) -> float:
        if self._exponential_backoff:
            return self._retry_delay * (2 ** attempt)
        return self._retry_delay
    
    def _get_retry_count(self, execution_id: str) -> int:
        count = 0
        for record in self._recovery_history:
            if record.get("execution_id") == execution_id:
                count += 1
        return count
    
    def _record_recovery_attempt(
        self,
        execution_id: str,
        failure_info: FailureInfo,
    ) -> None:
        self._recovery_history.append({
            "timestamp": int(datetime.now(tz=timezone.utc).timestamp()),
            "execution_id": execution_id,
            "failure_type": failure_info.failure_type.value,
            "stage_id": failure_info.stage_id,
            "status": "attempted",
        })
    
    def _record_recovery_success(
        self,
        execution_id: str,
        result: RecoveryResult,
    ) -> None:
        self._recovery_history.append({
            "timestamp": int(datetime.now(tz=timezone.utc).timestamp()),
            "execution_id": execution_id,
            "status": "success",
            "strategy": result.recovery_strategy.value if result.recovery_strategy else None,
        })
    
    def _record_recovery_failure(
        self,
        execution_id: str,
        error: str,
    ) -> None:
        self._recovery_history.append({
            "timestamp": int(datetime.now(tz=timezone.utc).timestamp()),
            "execution_id": execution_id,
            "status": "failed",
            "error": error,
        })
    
    def get_recovery_history(
        self,
        execution_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if execution_id:
            return [
                r for r in self._recovery_history
                if r.get("execution_id") == execution_id
            ]
        return list(self._recovery_history)
    
    def clear_idempotency_cache(self, operation_id: Optional[str] = None) -> None:
        if operation_id:
            self._idempotency_cache.pop(operation_id, None)
            self._operation_results.pop(operation_id, None)
        else:
            self._idempotency_cache.clear()
            self._operation_results.clear()
    
    def create_failure_info(
        self,
        execution_id: str,
        failure_type: FailureType,
        stage_id: Optional[str] = None,
        error_message: str = "",
        error_details: Optional[Dict[str, Any]] = None,
    ) -> FailureInfo:
        return FailureInfo(
            failure_id=str(uuid.uuid4()),
            failure_type=failure_type,
            execution_id=execution_id,
            stage_id=stage_id,
            error_message=error_message,
            error_details=error_details or {},
        )
