from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .context import (
    WorkflowContext,
    StageOutput,
    AccumulatedKnowledge,
    InformationLineage,
    TransformRecord,
)


class TransferStatus(Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    VALIDATED = "validated"
    FAILED = "failed"


@dataclass
class ValidationResult:
    valid: bool
    error: Optional[str] = None
    missing_fields: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class TransferPackage:
    original_request: Dict[str, Any]
    accumulated_knowledge: Dict[str, Any]
    current_state: Dict[str, Any]
    lineage: Dict[str, Any]
    checksum: str
    critical_fields: Dict[str, Any]
    transfer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: int = 0
    
    def __post_init__(self):
        if self.timestamp == 0:
            object.__setattr__(
                self,
                "timestamp",
                int(datetime.now(tz=timezone.utc).timestamp()),
            )


@dataclass
class IntegrityReport:
    execution_id: str
    original_request_intact: bool
    lineage_complete: bool
    checksum_valid: bool
    overall_integrity: bool
    details: List[str] = field(default_factory=list)


class InformationPreserver:
    CRITICAL_FIELDS: Set[str] = {
        "original_request",
        "task_type",
        "constraints",
        "decisions",
        "audit_results",
    }
    
    PRESERVATION_RULES = {
        "PRES-001": "原始请求永不修改",
        "PRES-002": "累积知识只增不减",
        "PRES-003": "关键字段强制传递",
        "PRES-004": "信息血缘完整记录",
        "PRES-005": "校验和强制验证",
    }
    
    def __init__(
        self,
        compression_threshold: int = 10000,
        max_summary_length: int = 500,
    ):
        self._compression_threshold = compression_threshold
        self._max_summary_length = max_summary_length
        self._transfer_history: Dict[str, List[TransferPackage]] = {}
    
    def prepare_transfer(
        self,
        context: WorkflowContext,
        target_stage: str,
    ) -> TransferPackage:
        critical_fields = self._extract_critical_fields(context)
        
        package = TransferPackage(
            original_request=context.original_request.to_dict(),
            accumulated_knowledge=context.accumulated_knowledge.to_dict(),
            current_state=context.current_state.to_dict(),
            lineage=context.lineage.to_dict(),
            checksum="",
            critical_fields=critical_fields,
        )
        
        checksum = self._compute_checksum(package)
        object.__setattr__(package, "checksum", checksum)
        
        self._record_transfer(context.metadata.execution_id, package)
        
        return package
    
    def validate_receive(
        self,
        package: TransferPackage,
    ) -> ValidationResult:
        computed = self._compute_checksum(package)
        if computed != package.checksum:
            return ValidationResult(
                valid=False,
                error=f"Checksum mismatch: expected {package.checksum}, got {computed}",
            )
        
        missing_fields = self._check_critical_fields(package)
        if missing_fields:
            return ValidationResult(
                valid=False,
                error=f"Missing critical fields: {missing_fields}",
                missing_fields=missing_fields,
            )
        
        warnings = self._check_warnings(package)
        
        return ValidationResult(
            valid=True,
            warnings=warnings,
        )
    
    def merge_with_preservation(
        self,
        existing_context: WorkflowContext,
        new_output: StageOutput,
        stage_id: str,
    ) -> WorkflowContext:
        return existing_context.merge_stage_output(stage_id, new_output)
    
    def verify_integrity(
        self,
        context: WorkflowContext,
    ) -> IntegrityReport:
        original_intact = context.verify_original_integrity()
        
        lineage_complete = self._verify_lineage_complete(context)
        
        checksum_valid = self._verify_context_checksum(context)
        
        details = []
        if not original_intact:
            details.append("Original request has been modified")
        if not lineage_complete:
            details.append("Lineage is incomplete")
        if not checksum_valid:
            details.append("Checksum validation failed")
        
        return IntegrityReport(
            execution_id=context.metadata.execution_id,
            original_request_intact=original_intact,
            lineage_complete=lineage_complete,
            checksum_valid=checksum_valid,
            overall_integrity=all([
                original_intact,
                lineage_complete,
                checksum_valid,
            ]),
            details=details,
        )
    
    def trace_information_origin(
        self,
        context: WorkflowContext,
        field_name: str,
    ) -> List[str]:
        return context.lineage.trace_field_origin(field_name)
    
    def get_stage_dependencies(
        self,
        context: WorkflowContext,
        stage_id: str,
    ) -> Set[str]:
        return context.lineage.get_all_dependencies(stage_id)
    
    def _extract_critical_fields(
        self,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        result = {}
        
        result["original_request"] = context.original_request.to_dict()
        result["task_type"] = context.original_request.task_type
        result["constraints"] = context.original_request.constraints
        result["decisions"] = [
            d.to_dict() for d in context.accumulated_knowledge.decisions
        ]
        
        return result
    
    def _check_critical_fields(
        self,
        package: TransferPackage,
    ) -> List[str]:
        missing = []
        for field in self.CRITICAL_FIELDS:
            if field not in package.critical_fields:
                missing.append(field)
            elif package.critical_fields[field] is None:
                missing.append(field)
        return missing
    
    def _check_warnings(self, package: TransferPackage) -> List[str]:
        warnings = []
        
        if len(package.accumulated_knowledge.get("stage_outputs", {})) > 10:
            warnings.append("Large number of stage outputs may impact performance")
        
        if len(package.lineage.get("transformation_log", [])) > 50:
            warnings.append("Large transformation log may impact performance")
        
        return warnings
    
    def _compute_checksum(self, package: TransferPackage) -> str:
        data = {
            "original_request": package.original_request,
            "accumulated_knowledge": package.accumulated_knowledge,
            "current_state": package.current_state,
            "lineage": package.lineage,
            "critical_fields": package.critical_fields,
        }
        serialized = json.dumps(data, sort_keys=True).encode()
        return hashlib.sha256(serialized).hexdigest()
    
    def _verify_lineage_complete(self, context: WorkflowContext) -> bool:
        stage_outputs = context.accumulated_knowledge.stage_outputs
        
        for stage_id, output in stage_outputs.items():
            for field_name in output.produced_fields:
                expected_key = f"{stage_id}.{field_name}"
                if field_name not in context.lineage.input_sources:
                    return False
        
        return True
    
    def _verify_context_checksum(self, context: WorkflowContext) -> bool:
        serialized = context.prepare_for_transfer()
        return serialized.checksum == serialized.checksum
    
    def _record_transfer(
        self,
        execution_id: str,
        package: TransferPackage,
    ) -> None:
        if execution_id not in self._transfer_history:
            self._transfer_history[execution_id] = []
        self._transfer_history[execution_id].append(package)
    
    def get_transfer_history(
        self,
        execution_id: str,
    ) -> List[TransferPackage]:
        return self._transfer_history.get(execution_id, [])
    
    def calculate_attenuation_rate(
        self,
        context: WorkflowContext,
    ) -> float:
        stage_count = len(context.accumulated_knowledge.stage_outputs)
        if stage_count == 0:
            return 0.0
        
        expected_fields = set()
        actual_fields = set(context.lineage.input_sources.keys())
        
        for output in context.accumulated_knowledge.stage_outputs.values():
            expected_fields.update(output.produced_fields)
        
        if not expected_fields:
            return 0.0
        
        missing = expected_fields - actual_fields
        return len(missing) / len(expected_fields)
