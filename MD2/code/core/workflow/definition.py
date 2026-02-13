from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class WorkflowStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageStatus(Enum):
    PENDING = "pending"
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class StageInput:
    source_stage: Optional[str] = None
    source_output: Optional[str] = None
    static_value: Optional[Any] = None
    transform: Optional[str] = None


@dataclass
class WorkflowStage:
    stage_id: str
    name: str
    profession_id: str
    inputs: Dict[str, StageInput] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)
    next_stages: List[str] = field(default_factory=list)
    condition: Optional[str] = None
    timeout: int = 300
    retry_count: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "name": self.name,
            "profession_id": self.profession_id,
            "inputs": {
                k: {
                    "source_stage": v.source_stage,
                    "source_output": v.source_output,
                    "static_value": v.static_value,
                    "transform": v.transform,
                }
                for k, v in self.inputs.items()
            },
            "outputs": self.outputs,
            "next_stages": self.next_stages,
            "condition": self.condition,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
        }


@dataclass
class Workflow:
    workflow_id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    status: WorkflowStatus = WorkflowStatus.DRAFT
    stages: List[WorkflowStage] = field(default_factory=list)
    entry_stage: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    created_at: int = 0
    updated_at: int = 0
    
    def __post_init__(self):
        if self.created_at == 0:
            now = int(datetime.now(tz=timezone.utc).timestamp())
            object.__setattr__(self, "created_at", now)
            object.__setattr__(self, "updated_at", now)
    
    def get_stage(self, stage_id: str) -> Optional[WorkflowStage]:
        for stage in self.stages:
            if stage.stage_id == stage_id:
                return stage
        return None
    
    def get_entry_stage(self) -> Optional[WorkflowStage]:
        if self.entry_stage:
            return self.get_stage(self.entry_stage)
        return self.stages[0] if self.stages else None
    
    def get_next_stages(self, stage_id: str) -> List[WorkflowStage]:
        stage = self.get_stage(stage_id)
        if not stage:
            return []
        return [
            self.get_stage(next_id)
            for next_id in stage.next_stages
            if self.get_stage(next_id)
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "status": self.status.value,
            "stages": [s.to_dict() for s in self.stages],
            "entry_stage": self.entry_stage,
            "variables": self.variables,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class StageExecution:
    stage_id: str
    status: StageStatus = StageStatus.PENDING
    instance_id: Optional[str] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[int] = None
    completed_at: Optional[int] = None
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "status": self.status.value,
            "instance_id": self.instance_id,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "retry_count": self.retry_count,
        }


@dataclass
class WorkflowExecution:
    execution_id: str
    workflow_id: str
    workflow: Optional[Workflow] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    input: Dict[str, Any] = field(default_factory=dict)
    output: Dict[str, Any] = field(default_factory=dict)
    stage_executions: Dict[str, StageExecution] = field(default_factory=dict)
    current_stages: List[str] = field(default_factory=list)
    completed_stages: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    created_at: int = 0
    started_at: Optional[int] = None
    completed_at: Optional[int] = None
    error: Optional[str] = None
    trace_id: str = ""
    
    def __post_init__(self):
        if self.created_at == 0:
            object.__setattr__(
                self,
                "created_at",
                int(datetime.now(tz=timezone.utc).timestamp()),
            )
    
    def get_stage_execution(self, stage_id: str) -> Optional[StageExecution]:
        return self.stage_executions.get(stage_id)
    
    def set_stage_execution(self, execution: StageExecution) -> None:
        self.stage_executions[execution.stage_id] = execution
    
    def get_stage_output(self, stage_id: str, output_name: str) -> Optional[Any]:
        exec_result = self.stage_executions.get(stage_id)
        if exec_result:
            return exec_result.output_data.get(output_name)
        return None
    
    def set_stage_output(self, stage_id: str, outputs: Dict[str, Any]) -> None:
        exec_result = self.stage_executions.get(stage_id)
        if exec_result:
            object.__setattr__(
                exec_result,
                "output_data",
                {**exec_result.output_data, **outputs},
            )
    
    def is_stage_complete(self, stage_id: str) -> bool:
        exec_result = self.stage_executions.get(stage_id)
        return exec_result is not None and exec_result.status == StageStatus.COMPLETED
    
    def are_dependencies_complete(self, stage: WorkflowStage) -> bool:
        for stage_id, stage_input in stage.inputs.items():
            if stage_input.source_stage:
                if not self.is_stage_complete(stage_input.source_stage):
                    return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "input": self.input,
            "output": self.output,
            "stage_executions": {
                k: v.to_dict() for k, v in self.stage_executions.items()
            },
            "current_stages": self.current_stages,
            "completed_stages": self.completed_stages,
            "variables": self.variables,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "trace_id": self.trace_id,
        }
