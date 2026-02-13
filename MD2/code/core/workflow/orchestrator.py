from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .definition import (
    Workflow,
    WorkflowStage,
    WorkflowExecution,
    StageExecution,
    StageStatus,
    ExecutionStatus,
    StageInput,
)


@dataclass
class CollaborationMessage:
    message_id: str
    source_instance: str
    target_instance: str
    message_type: str
    payload: Dict[str, Any]
    workflow_id: str = ""
    stage_id: str = ""
    task_id: str = ""
    trace_id: str = ""
    priority: int = 5
    requires_ack: bool = False
    created_at: int = 0
    expires_at: Optional[int] = None
    
    def __post_init__(self):
        if self.created_at == 0:
            object.__setattr__(
                self,
                "created_at",
                int(datetime.now(tz=timezone.utc).timestamp()),
            )


@dataclass
class TaskResult:
    task_id: str
    instance_id: str
    stage_id: str
    success: bool
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: int = 0


class CollaborationManager:
    def __init__(self):
        self._channels: Dict[str, List[CollaborationMessage]] = {}
        self._pending_acks: Dict[str, CollaborationMessage] = {}
    
    def send_message(
        self,
        source_instance: str,
        target_instance: str,
        message_type: str,
        payload: Dict[str, Any],
        workflow_id: str = "",
        stage_id: str = "",
        task_id: str = "",
        trace_id: str = "",
        priority: int = 5,
        requires_ack: bool = False,
        expires_in: Optional[int] = None,
    ) -> CollaborationMessage:
        message = CollaborationMessage(
            message_id=str(uuid.uuid4()),
            source_instance=source_instance,
            target_instance=target_instance,
            message_type=message_type,
            payload=payload,
            workflow_id=workflow_id,
            stage_id=stage_id,
            task_id=task_id,
            trace_id=trace_id,
            priority=priority,
            requires_ack=requires_ack,
            expires_at=int(datetime.now(tz=timezone.utc).timestamp()) + expires_in
                       if expires_in else None,
        )
        
        channel_key = f"{source_instance}:{target_instance}"
        if channel_key not in self._channels:
            self._channels[channel_key] = []
        self._channels[channel_key].append(message)
        
        if requires_ack:
            self._pending_acks[message.message_id] = message
        
        return message
    
    def receive_messages(
        self,
        target_instance: str,
        limit: int = 10,
    ) -> List[CollaborationMessage]:
        messages = []
        for channel_key, channel_messages in self._channels.items():
            if channel_key.endswith(f":{target_instance}"):
                messages.extend(channel_messages[-limit:])
        return messages
    
    def ack_message(self, message_id: str) -> bool:
        if message_id in self._pending_acks:
            del self._pending_acks[message_id]
            return True
        return False
    
    def get_pending_acks(self, instance_id: str) -> List[CollaborationMessage]:
        return [
            msg for msg in self._pending_acks.values()
            if msg.target_instance == instance_id
        ]


class TaskRouter:
    def __init__(self):
        self._task_queue: Dict[str, List[Dict[str, Any]]] = {}
        self._results: Dict[str, TaskResult] = {}
    
    def dispatch(
        self,
        instance_id: str,
        task_id: str,
        stage_id: str,
        input_data: Dict[str, Any],
        timeout: int = 300,
    ) -> str:
        task = {
            "task_id": task_id,
            "stage_id": stage_id,
            "input": input_data,
            "timeout": timeout,
            "dispatched_at": int(datetime.now(tz=timezone.utc).timestamp()),
        }
        
        if instance_id not in self._task_queue:
            self._task_queue[instance_id] = []
        self._task_queue[instance_id].append(task)
        
        return task_id
    
    def get_pending_tasks(self, instance_id: str) -> List[Dict[str, Any]]:
        return self._task_queue.get(instance_id, [])
    
    def complete_task(
        self,
        task_id: str,
        instance_id: str,
        stage_id: str,
        success: bool,
        output: Dict[str, Any],
        error: Optional[str] = None,
        duration_ms: int = 0,
    ) -> TaskResult:
        result = TaskResult(
            task_id=task_id,
            instance_id=instance_id,
            stage_id=stage_id,
            success=success,
            output=output,
            error=error,
            duration_ms=duration_ms,
        )
        
        self._results[task_id] = result
        
        if instance_id in self._task_queue:
            self._task_queue[instance_id] = [
                t for t in self._task_queue[instance_id]
                if t["task_id"] != task_id
            ]
        
        return result
    
    def get_result(self, task_id: str) -> Optional[TaskResult]:
        return self._results.get(task_id)


class WorkflowOrchestrator:
    def __init__(self):
        self._workflows: Dict[str, Workflow] = {}
        self._executions: Dict[str, WorkflowExecution] = {}
        self._collaboration_manager = CollaborationManager()
        self._task_router = TaskRouter()
        self._instance_manager = None
    
    def set_instance_manager(self, instance_manager: Any) -> None:
        self._instance_manager = instance_manager
    
    def register_workflow(self, workflow: Workflow) -> None:
        self._workflows[workflow.workflow_id] = workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        return self._workflows.get(workflow_id)
    
    def list_workflows(self) -> List[Workflow]:
        return list(self._workflows.values())
    
    async def start_workflow(
        self,
        workflow_id: str,
        input_data: Dict[str, Any],
        variables: Optional[Dict[str, Any]] = None,
    ) -> WorkflowExecution:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        execution = WorkflowExecution(
            execution_id=self._generate_id(),
            workflow_id=workflow_id,
            workflow=workflow,
            input=input_data,
            variables={**workflow.variables, **(variables or {})},
            status=ExecutionStatus.RUNNING,
            started_at=int(datetime.now(tz=timezone.utc).timestamp()),
            trace_id=self._generate_trace_id(),
        )
        
        self._executions[execution.execution_id] = execution
        
        entry_stage = workflow.get_entry_stage()
        if entry_stage:
            await self._schedule_stage(execution, entry_stage)
        
        return execution
    
    async def _schedule_stage(
        self,
        execution: WorkflowExecution,
        stage: WorkflowStage,
    ) -> None:
        stage_exec = StageExecution(
            stage_id=stage.stage_id,
            status=StageStatus.WAITING,
        )
        execution.set_stage_execution(stage_exec)
        
        execution.current_stages.append(stage.stage_id)
    
    async def _execute_stage(
        self,
        execution: WorkflowExecution,
        stage: WorkflowStage,
    ) -> None:
        stage_exec = execution.get_stage_execution(stage.stage_id)
        if not stage_exec:
            stage_exec = StageExecution(stage_id=stage.stage_id)
        
        object.__setattr__(stage_exec, "status", StageStatus.RUNNING)
        object.__setattr__(
            stage_exec,
            "started_at",
            int(datetime.now(tz=timezone.utc).timestamp()),
        )
        
        input_data = self._prepare_stage_input(execution, stage)
        object.__setattr__(stage_exec, "input_data", input_data)
        
        execution.set_stage_execution(stage_exec)
        
        instance = None
        if self._instance_manager:
            instance = await self._instance_manager.get_available_instance(
                stage.profession_id,
            )
            
            if not instance:
                instance = await self._instance_manager.create_instance(
                    profession_id=stage.profession_id,
                    name=f"{stage.stage_id}_{execution.execution_id[:8]}",
                )
        
        if instance:
            object.__setattr__(stage_exec, "instance_id", instance.instance_id)
            
            task_id = self._task_router.dispatch(
                instance_id=instance.instance_id,
                task_id=self._generate_id(),
                stage_id=stage.stage_id,
                input_data=input_data,
                timeout=stage.timeout,
            )
            
            if self._instance_manager:
                await self._instance_manager.assign_task(
                    instance.instance_id,
                    task_id,
                )
    
    def _prepare_stage_input(
        self,
        execution: WorkflowExecution,
        stage: WorkflowStage,
    ) -> Dict[str, Any]:
        input_data = {}
        
        for input_name, stage_input in stage.inputs.items():
            if stage_input.static_value is not None:
                input_data[input_name] = stage_input.static_value
            elif stage_input.source_stage and stage_input.source_output:
                value = execution.get_stage_output(
                    stage_input.source_stage,
                    stage_input.source_output,
                )
                if value is not None:
                    input_data[input_name] = value
        
        return input_data
    
    async def complete_stage(
        self,
        execution_id: str,
        stage_id: str,
        success: bool,
        output: Dict[str, Any],
        error: Optional[str] = None,
    ) -> bool:
        execution = self._executions.get(execution_id)
        if not execution:
            return False
        
        stage_exec = execution.get_stage_execution(stage_id)
        if not stage_exec:
            return False
        
        object.__setattr__(
            stage_exec,
            "status",
            StageStatus.COMPLETED if success else StageStatus.FAILED,
        )
        object.__setattr__(stage_exec, "output_data", output)
        object.__setattr__(stage_exec, "error", error)
        object.__setattr__(
            stage_exec,
            "completed_at",
            int(datetime.now(tz=timezone.utc).timestamp()),
        )
        
        if stage_id in execution.current_stages:
            execution.current_stages.remove(stage_id)
        if success:
            execution.completed_stages.append(stage_id)
        
        if self._instance_manager and stage_exec.instance_id:
            await self._instance_manager.complete_task(
                stage_exec.instance_id,
                stage_id,
                success,
            )
        
        if success:
            workflow = execution.workflow
            if workflow:
                next_stages = workflow.get_next_stages(stage_id)
                for next_stage in next_stages:
                    if execution.are_dependencies_complete(next_stage):
                        await self._execute_stage(execution, next_stage)
            
            if not execution.current_stages:
                object.__setattr__(execution, "status", ExecutionStatus.COMPLETED)
                object.__setattr__(
                    execution,
                    "completed_at",
                    int(datetime.now(tz=timezone.utc).timestamp()),
                )
                object.__setattr__(execution, "output", output)
        else:
            object.__setattr__(execution, "status", ExecutionStatus.FAILED)
            object.__setattr__(execution, "error", error)
        
        return True
    
    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        return self._executions.get(execution_id)
    
    def list_executions(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
    ) -> List[WorkflowExecution]:
        executions = list(self._executions.values())
        
        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]
        if status:
            executions = [e for e in executions if e.status == status]
        
        return executions
    
    async def cancel_execution(self, execution_id: str) -> bool:
        execution = self._executions.get(execution_id)
        if not execution:
            return False
        
        object.__setattr__(execution, "status", ExecutionStatus.CANCELLED)
        object.__setattr__(
            execution,
            "completed_at",
            int(datetime.now(tz=timezone.utc).timestamp()),
        )
        
        return True
    
    def _generate_id(self) -> str:
        return str(uuid.uuid4())
    
    def _generate_trace_id(self) -> str:
        return f"trace-{uuid.uuid4().hex[:16]}"
