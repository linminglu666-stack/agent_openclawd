from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class CheckpointTrigger(Enum):
    EXECUTION_START = "execution_start"
    STAGE_COMPLETE = "stage_complete"
    STAGE_START = "stage_start"
    PERIODIC = "periodic"
    CRITICAL_OPERATION = "critical_operation"
    MANUAL = "manual"
    FAILURE = "failure"


class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOVERING = "recovering"


@dataclass(frozen=True)
class OriginalRequest:
    user_input: str
    task_type: str
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_input": self.user_input,
            "task_type": self.task_type,
            "constraints": self.constraints,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> OriginalRequest:
        return cls(
            user_input=data["user_input"],
            task_type=data["task_type"],
            constraints=data.get("constraints", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Decision:
    decision_id: str
    stage_id: str
    description: str
    rationale: str
    alternatives: List[str] = field(default_factory=list)
    timestamp: int = 0
    
    def __post_init__(self):
        if self.timestamp == 0:
            object.__setattr__(
                self,
                "timestamp",
                int(datetime.now(tz=timezone.utc).timestamp()),
            )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "stage_id": self.stage_id,
            "description": self.description,
            "rationale": self.rationale,
            "alternatives": self.alternatives,
            "timestamp": self.timestamp,
        }


@dataclass
class Fact:
    fact_id: str
    content: str
    source: str
    confidence: float = 1.0
    timestamp: int = 0
    
    def __post_init__(self):
        if self.timestamp == 0:
            object.__setattr__(
                self,
                "timestamp",
                int(datetime.now(tz=timezone.utc).timestamp()),
            )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "content": self.content,
            "source": self.source,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class StageOutput:
    stage_id: str
    output_data: Dict[str, Any]
    decisions: List[Decision] = field(default_factory=list)
    learned_facts: List[Fact] = field(default_factory=list)
    input_dependencies: Set[str] = field(default_factory=set)
    produced_fields: Set[str] = field(default_factory=set)
    updated_state: Optional[Dict[str, Any]] = None
    timestamp: int = 0
    
    def __post_init__(self):
        if self.timestamp == 0:
            object.__setattr__(
                self,
                "timestamp",
                int(datetime.now(tz=timezone.utc).timestamp()),
            )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "output_data": self.output_data,
            "decisions": [d.to_dict() for d in self.decisions],
            "learned_facts": [f.to_dict() for f in self.learned_facts],
            "input_dependencies": list(self.input_dependencies),
            "produced_fields": list(self.produced_fields),
            "updated_state": self.updated_state,
            "timestamp": self.timestamp,
        }


@dataclass
class AccumulatedKnowledge:
    stage_outputs: Dict[str, StageOutput] = field(default_factory=dict)
    decisions: List[Decision] = field(default_factory=list)
    learned_facts: List[Fact] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_outputs": {
                k: v.to_dict() for k, v in self.stage_outputs.items()
            },
            "decisions": [d.to_dict() for d in self.decisions],
            "learned_facts": [f.to_dict() for f in self.learned_facts],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AccumulatedKnowledge:
        return cls(
            stage_outputs={
                k: StageOutput(**v) for k, v in data.get("stage_outputs", {}).items()
            },
            decisions=[Decision(**d) for d in data.get("decisions", [])],
            learned_facts=[Fact(**f) for f in data.get("learned_facts", [])],
        )


@dataclass
class CurrentState:
    current_stage: str
    pending_tasks: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    status: ExecutionStatus = ExecutionStatus.RUNNING
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_stage": self.current_stage,
            "pending_tasks": self.pending_tasks,
            "variables": self.variables,
            "status": self.status.value,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CurrentState:
        return cls(
            current_stage=data["current_stage"],
            pending_tasks=data.get("pending_tasks", []),
            variables=data.get("variables", {}),
            status=ExecutionStatus(data.get("status", "running")),
        )


@dataclass
class TransformRecord:
    stage_id: str
    timestamp: int
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    transform_type: str = "process"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "timestamp": self.timestamp,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "transform_type": self.transform_type,
        }


@dataclass
class InformationLineage:
    input_sources: Dict[str, str] = field(default_factory=dict)
    transformation_log: List[TransformRecord] = field(default_factory=list)
    
    def trace_field_origin(self, field_name: str) -> List[str]:
        chain = []
        current = field_name
        while current in self.input_sources:
            source = self.input_sources[current]
            chain.append(source)
            current = source
        return chain
    
    def get_all_dependencies(self, stage_id: str) -> Set[str]:
        deps = set()
        for field_name, source in self.input_sources.items():
            if source.startswith(f"{stage_id}."):
                dep_stage = source.split(".")[0]
                deps.add(dep_stage)
        return deps
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_sources": self.input_sources,
            "transformation_log": [t.to_dict() for t in self.transformation_log],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InformationLineage:
        return cls(
            input_sources=data.get("input_sources", {}),
            transformation_log=[
                TransformRecord(**t) for t in data.get("transformation_log", [])
            ],
        )


@dataclass
class ContextMetadata:
    workflow_id: str
    execution_id: str
    version: int = 1
    created_at: int = 0
    updated_at: int = 0
    checksum: str = ""
    
    def __post_init__(self):
        if self.created_at == 0:
            object.__setattr__(
                self,
                "created_at",
                int(datetime.now(tz=timezone.utc).timestamp()),
            )
        if self.updated_at == 0:
            object.__setattr__(self, "updated_at", self.created_at)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "checksum": self.checksum,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ContextMetadata:
        return cls(
            workflow_id=data["workflow_id"],
            execution_id=data["execution_id"],
            version=data.get("version", 1),
            created_at=data.get("created_at", 0),
            updated_at=data.get("updated_at", 0),
            checksum=data.get("checksum", ""),
        )


class WorkflowContext:
    CONTEXT_RULES = {
        "CTX-001": "original_request 永不可修改",
        "CTX-002": "每次传递必须更新 version",
        "CTX-003": "传递前必须计算并验证 checksum",
        "CTX-004": "accumulated_knowledge 只能追加",
        "CTX-005": "所有输出必须记录 lineage",
        "CTX-006": "传递失败必须保留完整上下文",
    }
    
    CRITICAL_FIELDS = {
        "original_request",
        "task_type",
        "constraints",
        "decisions",
        "audit_results",
    }
    
    def __init__(
        self,
        metadata: ContextMetadata,
        original_request: OriginalRequest,
        accumulated_knowledge: Optional[AccumulatedKnowledge] = None,
        current_state: Optional[CurrentState] = None,
        lineage: Optional[InformationLineage] = None,
    ):
        self._metadata = metadata
        self._original_request = original_request
        self._accumulated_knowledge = accumulated_knowledge or AccumulatedKnowledge()
        self._current_state = current_state or CurrentState(current_stage="init")
        self._lineage = lineage or InformationLineage()
        self._frozen_original = self._serialize_original()
    
    @property
    def metadata(self) -> ContextMetadata:
        return self._metadata
    
    @property
    def original_request(self) -> OriginalRequest:
        return self._original_request
    
    @property
    def accumulated_knowledge(self) -> AccumulatedKnowledge:
        return self._accumulated_knowledge
    
    @property
    def current_state(self) -> CurrentState:
        return self._current_state
    
    @property
    def lineage(self) -> InformationLineage:
        return self._lineage
    
    def _serialize_original(self) -> bytes:
        return json.dumps(
            self._original_request.to_dict(),
            sort_keys=True,
        ).encode()
    
    def verify_original_integrity(self) -> bool:
        current = self._serialize_original()
        return current == self._frozen_original
    
    def prepare_for_transfer(self) -> SerializedContext:
        data = self.to_dict()
        serialized = json.dumps(data, sort_keys=True).encode()
        checksum = self._compute_checksum(serialized)
        
        return SerializedContext(
            data=serialized,
            checksum=checksum,
            version=self._metadata.version + 1,
        )
    
    @classmethod
    def validate_on_receive(cls, serialized: SerializedContext) -> bool:
        computed = cls._compute_checksum_static(serialized.data)
        if computed != serialized.checksum:
            raise ContextCorruptionError(
                f"Checksum mismatch: expected {serialized.checksum}, got {computed}",
            )
        return True
    
    def merge_stage_output(
        self,
        stage_id: str,
        output: StageOutput,
    ) -> WorkflowContext:
        new_stage_outputs = {
            **self._accumulated_knowledge.stage_outputs,
            stage_id: output,
        }
        
        new_decisions = [
            *self._accumulated_knowledge.decisions,
            *output.decisions,
        ]
        
        new_facts = [
            *self._accumulated_knowledge.learned_facts,
            *output.learned_facts,
        ]
        
        new_knowledge = AccumulatedKnowledge(
            stage_outputs=new_stage_outputs,
            decisions=new_decisions,
            learned_facts=new_facts,
        )
        
        new_input_sources = dict(self._lineage.input_sources)
        for field_name in output.produced_fields:
            new_input_sources[field_name] = f"{stage_id}.{field_name}"
        
        new_transform_log = [
            *self._lineage.transformation_log,
            TransformRecord(
                stage_id=stage_id,
                timestamp=int(datetime.now(tz=timezone.utc).timestamp()),
                inputs=list(output.input_dependencies),
                outputs=list(output.produced_fields),
            ),
        ]
        
        new_lineage = InformationLineage(
            input_sources=new_input_sources,
            transformation_log=new_transform_log,
        )
        
        new_state = output.updated_state or self._current_state.to_dict()
        if isinstance(new_state, dict):
            new_state = CurrentState.from_dict(new_state)
        
        new_metadata = ContextMetadata(
            workflow_id=self._metadata.workflow_id,
            execution_id=self._metadata.execution_id,
            version=self._metadata.version + 1,
            created_at=self._metadata.created_at,
            updated_at=int(datetime.now(tz=timezone.utc).timestamp()),
        )
        
        return WorkflowContext(
            metadata=new_metadata,
            original_request=self._original_request,
            accumulated_knowledge=new_knowledge,
            current_state=new_state,
            lineage=new_lineage,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self._metadata.to_dict(),
            "original_request": self._original_request.to_dict(),
            "accumulated_knowledge": self._accumulated_knowledge.to_dict(),
            "current_state": self._current_state.to_dict(),
            "lineage": self._lineage.to_dict(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowContext:
        return cls(
            metadata=ContextMetadata.from_dict(data["metadata"]),
            original_request=OriginalRequest.from_dict(data["original_request"]),
            accumulated_knowledge=AccumulatedKnowledge.from_dict(
                data.get("accumulated_knowledge", {}),
            ),
            current_state=CurrentState.from_dict(data.get("current_state", {})),
            lineage=InformationLineage.from_dict(data.get("lineage", {})),
        )
    
    def _compute_checksum(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()
    
    @classmethod
    def _compute_checksum_static(cls, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


@dataclass
class SerializedContext:
    data: bytes
    checksum: str
    version: int
    
    def deserialize(self) -> WorkflowContext:
        WorkflowContext.validate_on_receive(self)
        data = json.loads(self.data.decode())
        return WorkflowContext.from_dict(data)


class ContextCorruptionError(Exception):
    pass


class ContextValidationError(Exception):
    pass
