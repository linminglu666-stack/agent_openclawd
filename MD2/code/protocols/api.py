from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Generic, Optional, TypeVar


T = TypeVar("T")


class ErrorCode(Enum):
    INVALID_ARGUMENT = "invalid_argument"
    UNAUTHENTICATED = "unauthenticated"
    PERMISSION_DENIED = "permission_denied"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    PRECONDITION_FAILED = "precondition_failed"
    RATE_LIMITED = "rate_limited"
    INTERNAL = "internal"
    UNAVAILABLE = "unavailable"


@dataclass
class ApiError:
    code: ErrorCode
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RequestMeta:
    request_id: str = ""
    trace_id: str = ""
    actor: str = ""
    idempotency_key: str = ""
    received_at: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))


@dataclass
class ApiResponse(Generic[T]):
    ok: bool
    data: Optional[T] = None
    error: Optional[ApiError] = None
    meta: RequestMeta = field(default_factory=RequestMeta)


@dataclass
class PageRequest:
    limit: int = 50
    cursor: str = ""


@dataclass
class PageResponse:
    next_cursor: str = ""

