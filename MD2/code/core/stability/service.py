from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from .context import (
    WorkflowContext,
    ContextMetadata,
    OriginalRequest,
    CurrentState,
    ExecutionStatus,
    StageOutput,
    CheckpointTrigger,
)
from .preserver import InformationPreserver, ValidationResult
from .checkpoint import CheckpointManager
from .recovery import (
    RecoveryManager,
    RecoveryResult,
    FailureInfo,
    FailureType,
)


@dataclass
class ExecutionContext:
    execution_id: str
    workflow_id: str
    context: WorkflowContext
    status: ExecutionStatus = ExecutionStatus.PENDING
    current_stage: str = ""
    started_at: int = 0
    completed_at: int = 0
    
    def __post_init__(self):
        if self.started_at == 0:
            self.started_at = int(datetime.now(tz=timezone.utc).timestamp())


@dataclass
class IntegrityReport:
    execution_id: str
    original_request_intact: bool
    lineage_complete: bool
    checksum_valid: bool
    overall_integrity: bool
    details: Dict[str, Any] = field(default_factory=dict)


class ExecutionNotFoundError(Exception):
    pass


class WorkflowStabilityService:
    def __init__(
        self,
        storage_path: str,
        checkpoint_interval: int = 300,
        max_retries: int = 3,
    ):
        self._checkpoint_manager = CheckpointManager(
            storage_path=storage_path,
            checkpoint_interval=checkpoint_interval,
        )
        self._info_preserver = InformationPreserver()
        self._recovery_manager = RecoveryManager(
            checkpoint_manager=self._checkpoint_manager,
            max_retries=max_retries,
        )
        self._active_executions: Dict[str, ExecutionContext] = {}
        self._execution_history: List[Dict[str, Any]] = []
    
    async def start_execution(
        self,
        workflow_id: str,
        initial_context: WorkflowContext,
    ) -> str:
        execution_id = self._generate_id()
        
        await self._checkpoint_manager.create_checkpoint(
            execution_id=execution_id,
            context=initial_context,
            trigger=CheckpointTrigger.EXECUTION_START,
        )
        
        exec_context = ExecutionContext(
            execution_id=execution_id,
            workflow_id=workflow_id,
            context=initial_context,
            status=ExecutionStatus.RUNNING,
            current_stage=initial_context.current_state.current_stage,
        )
        
        self._active_executions[execution_id] = exec_context
        
        self._record_execution_start(execution_id, workflow_id)
        
        return execution_id
    
    async def transfer_to_stage(
        self,
        execution_id: str,
        target_stage: str,
        current_output: StageOutput,
    ) -> WorkflowContext:
        exec_ctx = self._get_execution_context(execution_id)
        
        new_context = self._info_preserver.merge_with_preservation(
            existing_context=exec_ctx.context,
            new_output=current_output,
            stage_id=exec_ctx.current_stage,
        )
        
        await self._checkpoint_manager.create_checkpoint(
            execution_id=execution_id,
            context=new_context,
            trigger=CheckpointTrigger.STAGE_COMPLETE,
            metadata={"completed_stage": exec_ctx.current_stage},
        )
        
        exec_ctx.context = new_context
        exec_ctx.current_stage = target_stage
        
        return new_context
    
    async def complete_stage(
        self,
        execution_id: str,
        stage_id: str,
        output: StageOutput,
    ) -> bool:
        exec_ctx = self._get_execution_context(execution_id)
        
        exec_ctx.context.merge_stage_output(stage_id, output)
        
        await self._checkpoint_manager.create_checkpoint(
            execution_id=execution_id,
            context=exec_ctx.context,
            trigger=CheckpointTrigger.STAGE_COMPLETE,
            metadata={"completed_stage": stage_id},
        )
        
        return True
    
    async def handle_failure(
        self,
        execution_id: str,
        failure_info: FailureInfo,
    ) -> RecoveryResult:
        exec_ctx = self._get_execution_context(execution_id)
        exec_ctx.status = ExecutionStatus.RECOVERING
        
        result = await self._recovery_manager.recover_execution(
            execution_id=execution_id,
            failure_info=failure_info,
        )
        
        if result.success and result.context:
            exec_ctx.context = result.context
            exec_ctx.status = ExecutionStatus.RUNNING
        else:
            exec_ctx.status = ExecutionStatus.FAILED
        
        return result
    
    async def complete_execution(
        self,
        execution_id: str,
        success: bool = True,
    ) -> bool:
        exec_ctx = self._get_execution_context(execution_id)
        
        exec_ctx.status = ExecutionStatus.COMPLETED if success else ExecutionStatus.FAILED
        exec_ctx.completed_at = int(datetime.now(tz=timezone.utc).timestamp())
        
        await self._checkpoint_manager.create_checkpoint(
            execution_id=execution_id,
            context=exec_ctx.context,
            trigger=CheckpointTrigger.STAGE_COMPLETE,
            metadata={"final": True, "success": success},
        )
        
        self._record_execution_complete(execution_id, success)
        
        return True
    
    async def get_execution_context(
        self,
        execution_id: str,
    ) -> Optional[WorkflowContext]:
        exec_ctx = self._active_executions.get(execution_id)
        return exec_ctx.context if exec_ctx else None
    
    async def get_execution_status(
        self,
        execution_id: str,
    ) -> Optional[Dict[str, Any]]:
        exec_ctx = self._active_executions.get(execution_id)
        if not exec_ctx:
            return None
        
        return {
            "execution_id": exec_ctx.execution_id,
            "workflow_id": exec_ctx.workflow_id,
            "status": exec_ctx.status.value,
            "current_stage": exec_ctx.current_stage,
            "started_at": exec_ctx.started_at,
            "completed_at": exec_ctx.completed_at,
        }
    
    async def verify_information_integrity(
        self,
        execution_id: str,
    ) -> IntegrityReport:
        exec_ctx = self._get_execution_context(execution_id)
        context = exec_ctx.context
        
        integrity = self._info_preserver.verify_integrity(context)
        
        return IntegrityReport(
            execution_id=execution_id,
            original_request_intact=integrity["original_request_intact"],
            lineage_complete=integrity["lineage_complete"],
            checksum_valid=integrity["knowledge_consistent"],
            overall_integrity=integrity["overall_integrity"],
            details=integrity,
        )
    
    async def create_periodic_checkpoint(
        self,
        execution_id: str,
    ) -> bool:
        exec_ctx = self._get_execution_context(execution_id)
        
        await self._checkpoint_manager.create_checkpoint(
            execution_id=execution_id,
            context=exec_ctx.context,
            trigger=CheckpointTrigger.PERIODIC,
        )
        
        return True
    
    async def restore_execution(
        self,
        execution_id: str,
    ) -> Optional[WorkflowContext]:
        context = await self._checkpoint_manager.restore_from_checkpoint(execution_id)
        
        exec_ctx = ExecutionContext(
            execution_id=execution_id,
            workflow_id=context.metadata.workflow_id,
            context=context,
            status=ExecutionStatus.RUNNING,
            current_stage=context.current_state.current_stage,
        )
        
        self._active_executions[execution_id] = exec_ctx
        
        return context
    
    def list_active_executions(self) -> List[str]:
        return list(self._active_executions.keys())
    
    def get_execution_history(
        self,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        return self._execution_history[-limit:]
    
    def _get_execution_context(self, execution_id: str) -> ExecutionContext:
        exec_ctx = self._active_executions.get(execution_id)
        if not exec_ctx:
            raise ExecutionNotFoundError(f"Execution not found: {execution_id}")
        return exec_ctx
    
    def _record_execution_start(
        self,
        execution_id: str,
        workflow_id: str,
    ) -> None:
        self._execution_history.append({
            "event": "start",
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "timestamp": int(datetime.now(tz=timezone.utc).timestamp()),
        })
    
    def _record_execution_complete(
        self,
        execution_id: str,
        success: bool,
    ) -> None:
        self._execution_history.append({
            "event": "complete",
            "execution_id": execution_id,
            "success": success,
            "timestamp": int(datetime.now(tz=timezone.utc).timestamp()),
        })
    
    def _generate_id(self) -> str:
        return f"exec-{uuid.uuid4().hex[:12]}"
    
    async def execute_with_stability(
        self,
        workflow_id: str,
        initial_context: WorkflowContext,
        stage_executor: Any,
    ) -> WorkflowContext:
        execution_id = await self.start_execution(workflow_id, initial_context)
        
        try:
            current_context = initial_context
            
            while current_context.current_state.status != ExecutionStatus.COMPLETED:
                stage_id = current_context.current_state.current_stage
                
                try:
                    output = await self._recovery_manager.execute_with_idempotency(
                        f"{execution_id}_{stage_id}",
                        stage_executor.execute_stage,
                        stage_id,
                        current_context,
                    )
                    
                    current_context = await self.transfer_to_stage(
                        execution_id,
                        output.next_stage,
                        output,
                    )
                    
                except Exception as e:
                    failure_info = self._recovery_manager.create_failure_info(
                        execution_id=execution_id,
                        failure_type=FailureType.STAGE_EXECUTION_ERROR,
                        stage_id=stage_id,
                        error_message=str(e),
                    )
                    
                    result = await self.handle_failure(execution_id, failure_info)
                    
                    if not result.success:
                        raise
                    
                    current_context = result.context
            
            await self.complete_execution(execution_id, success=True)
            return current_context
            
        except Exception as e:
            await self.complete_execution(execution_id, success=False)
            raise
