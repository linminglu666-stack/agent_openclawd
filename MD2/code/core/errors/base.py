from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class ErrorCategory(Enum):
    KERNEL = "kernel"
    AGENT = "agent"
    REASONING = "reasoning"
    MEMORY = "memory"
    TASK = "task"
    CONFIG = "config"
    NETWORK = "network"
    VALIDATION = "validation"
    AUTH = "auth"
    SYSTEM = "system"


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ErrorContext:
    trace_id: Optional[str] = None
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    timestamp: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))
    additional: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OpenClawError:
    code: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    context: Optional[ErrorContext] = None
    cause: Optional["OpenClawError"] = None
    remediation: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def with_context(self, **kwargs: Any) -> "OpenClawError":
        current = self.context or ErrorContext()
        new_context = ErrorContext(
            trace_id=kwargs.get("trace_id", current.trace_id),
            agent_id=kwargs.get("agent_id", current.agent_id),
            task_id=kwargs.get("task_id", current.task_id),
            additional={**current.additional, **kwargs.get("additional", {})},
        )
        return OpenClawError(
            code=self.code,
            message=self.message,
            category=self.category,
            severity=self.severity,
            context=new_context,
            cause=self.cause,
            remediation=self.remediation,
            metadata=self.metadata,
        )

    def with_cause(self, cause: "OpenClawError") -> "OpenClawError":
        return OpenClawError(
            code=self.code,
            message=self.message,
            category=self.category,
            severity=self.severity,
            context=self.context,
            cause=cause,
            remediation=self.remediation,
            metadata=self.metadata,
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "code": self.code,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "remediation": self.remediation,
        }
        if self.context:
            result["context"] = {
                "trace_id": self.context.trace_id,
                "agent_id": self.context.agent_id,
                "task_id": self.context.task_id,
                "timestamp": self.context.timestamp,
                "additional": self.context.additional,
            }
        if self.cause:
            result["cause"] = self.cause.to_dict()
        return result


class KernelError:
    CONFIG_ERROR = OpenClawError(
        code="KERNEL_CONFIG_ERROR",
        message="Kernel configuration error",
        category=ErrorCategory.KERNEL,
        severity=ErrorSeverity.HIGH,
        remediation=["Check configuration file format", "Verify required fields"],
    )

    ADAPTER_ERROR = OpenClawError(
        code="KERNEL_ADAPTER_ERROR",
        message="Adapter initialization failed",
        category=ErrorCategory.KERNEL,
        severity=ErrorSeverity.HIGH,
        remediation=["Check adapter dependencies", "Verify adapter configuration"],
    )

    INIT_ERROR = OpenClawError(
        code="KERNEL_INIT_ERROR",
        message="Kernel initialization failed",
        category=ErrorCategory.KERNEL,
        severity=ErrorSeverity.CRITICAL,
        remediation=["Check system resources", "Review initialization logs"],
    )


class AgentError:
    NOT_FOUND = OpenClawError(
        code="AGENT_NOT_FOUND",
        message="Agent not found",
        category=ErrorCategory.AGENT,
        severity=ErrorSeverity.MEDIUM,
        remediation=["Register the agent", "Check agent ID"],
    )

    NO_AVAILABLE = OpenClawError(
        code="AGENT_NO_AVAILABLE",
        message="No available agent for task",
        category=ErrorCategory.AGENT,
        severity=ErrorSeverity.HIGH,
        remediation=["Wait for agent to become idle", "Scale up agent pool"],
    )

    ASSIGNMENT_FAILED = OpenClawError(
        code="AGENT_ASSIGNMENT_FAILED",
        message="Failed to assign task to agent",
        category=ErrorCategory.AGENT,
        severity=ErrorSeverity.MEDIUM,
        remediation=["Retry assignment", "Check agent state"],
    )

    HEARTBEAT_TIMEOUT = OpenClawError(
        code="AGENT_HEARTBEAT_TIMEOUT",
        message="Agent heartbeat timeout",
        category=ErrorCategory.AGENT,
        severity=ErrorSeverity.HIGH,
        remediation=["Check agent health", "Restart agent"],
    )

    EXECUTION_FAILED = OpenClawError(
        code="AGENT_EXECUTION_FAILED",
        message="Agent execution failed",
        category=ErrorCategory.AGENT,
        severity=ErrorSeverity.HIGH,
        remediation=["Check error logs", "Retry with different agent"],
    )


class ReasoningError:
    STRATEGY_ERROR = OpenClawError(
        code="REASONING_STRATEGY_ERROR",
        message="Reasoning strategy execution failed",
        category=ErrorCategory.REASONING,
        severity=ErrorSeverity.MEDIUM,
        remediation=["Try alternative strategy", "Check input format"],
    )

    TIMEOUT = OpenClawError(
        code="REASONING_TIMEOUT",
        message="Reasoning timeout exceeded",
        category=ErrorCategory.REASONING,
        severity=ErrorSeverity.MEDIUM,
        remediation=["Increase timeout", "Simplify problem"],
    )

    LOW_CONFIDENCE = OpenClawError(
        code="REASONING_LOW_CONFIDENCE",
        message="Reasoning result has low confidence",
        category=ErrorCategory.REASONING,
        severity=ErrorSeverity.LOW,
        remediation=["Request more evidence", "Try alternative approach"],
    )

    INVALID_OUTPUT = OpenClawError(
        code="REASONING_INVALID_OUTPUT",
        message="Reasoning output validation failed",
        category=ErrorCategory.REASONING,
        severity=ErrorSeverity.MEDIUM,
        remediation=["Check output schema", "Review reasoning steps"],
    )


class MemoryError:
    NOT_FOUND = OpenClawError(
        code="MEMORY_NOT_FOUND",
        message="Memory entry not found",
        category=ErrorCategory.MEMORY,
        severity=ErrorSeverity.LOW,
        remediation=["Create new entry", "Check entry ID"],
    )

    CONFLICT = OpenClawError(
        code="MEMORY_CONFLICT",
        message="Memory conflict detected",
        category=ErrorCategory.MEMORY,
        severity=ErrorSeverity.MEDIUM,
        remediation=["Resolve conflict manually", "Use conflict resolution policy"],
    )

    CORRUPTION = OpenClawError(
        code="MEMORY_CORRUPTION",
        message="Memory corruption detected",
        category=ErrorCategory.MEMORY,
        severity=ErrorSeverity.HIGH,
        remediation=["Restore from backup", "Run integrity check"],
    )


class TaskError:
    DISPATCH_ERROR = OpenClawError(
        code="TASK_DISPATCH_ERROR",
        message="Task dispatch failed",
        category=ErrorCategory.TASK,
        severity=ErrorSeverity.MEDIUM,
        remediation=["Retry dispatch", "Check agent availability"],
    )

    VALIDATION_ERROR = OpenClawError(
        code="TASK_VALIDATION_ERROR",
        message="Task validation failed",
        category=ErrorCategory.TASK,
        severity=ErrorSeverity.LOW,
        remediation=["Check task format", "Verify required fields"],
    )

    TIMEOUT = OpenClawError(
        code="TASK_TIMEOUT",
        message="Task execution timeout",
        category=ErrorCategory.TASK,
        severity=ErrorSeverity.MEDIUM,
        remediation=["Increase timeout", "Optimize task"],
    )

    NOT_FOUND = OpenClawError(
        code="TASK_NOT_FOUND",
        message="Task not found",
        category=ErrorCategory.TASK,
        severity=ErrorSeverity.LOW,
        remediation=["Check task ID", "Verify task exists"],
    )


class ConfigError:
    NOT_FOUND = OpenClawError(
        code="CONFIG_NOT_FOUND",
        message="Configuration not found",
        category=ErrorCategory.CONFIG,
        severity=ErrorSeverity.MEDIUM,
        remediation=["Create configuration", "Check config path"],
    )

    VALIDATION_ERROR = OpenClawError(
        code="CONFIG_VALIDATION_ERROR",
        message="Configuration validation failed",
        category=ErrorCategory.CONFIG,
        severity=ErrorSeverity.HIGH,
        remediation=["Check config format", "Verify required fields"],
    )

    ROLLBACK_FAILED = OpenClawError(
        code="CONFIG_ROLLBACK_FAILED",
        message="Configuration rollback failed",
        category=ErrorCategory.CONFIG,
        severity=ErrorSeverity.HIGH,
        remediation=["Manual intervention required", "Check backup integrity"],
    )


class NetworkError:
    CONNECTION_ERROR = OpenClawError(
        code="NETWORK_CONNECTION_ERROR",
        message="Network connection error",
        category=ErrorCategory.NETWORK,
        severity=ErrorSeverity.HIGH,
        remediation=["Check network connectivity", "Retry request"],
    )

    TIMEOUT = OpenClawError(
        code="NETWORK_TIMEOUT",
        message="Network request timeout",
        category=ErrorCategory.NETWORK,
        severity=ErrorSeverity.MEDIUM,
        remediation=["Increase timeout", "Check network latency"],
    )

    RATE_LIMITED = OpenClawError(
        code="NETWORK_RATE_LIMITED",
        message="Rate limit exceeded",
        category=ErrorCategory.NETWORK,
        severity=ErrorSeverity.LOW,
        remediation=["Wait and retry", "Reduce request rate"],
    )


class AuthError:
    UNAUTHORIZED = OpenClawError(
        code="AUTH_UNAUTHORIZED",
        message="Unauthorized access",
        category=ErrorCategory.AUTH,
        severity=ErrorSeverity.HIGH,
        remediation=["Check credentials", "Request access"],
    )

    FORBIDDEN = OpenClawError(
        code="AUTH_FORBIDDEN",
        message="Access forbidden",
        category=ErrorCategory.AUTH,
        severity=ErrorSeverity.HIGH,
        remediation=["Request permission", "Contact administrator"],
    )

    TOKEN_EXPIRED = OpenClawError(
        code="AUTH_TOKEN_EXPIRED",
        message="Authentication token expired",
        category=ErrorCategory.AUTH,
        severity=ErrorSeverity.MEDIUM,
        remediation=["Refresh token", "Re-authenticate"],
    )
