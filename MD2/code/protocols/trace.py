from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import re


_TRACEPARENT_RE = re.compile(r"^(?P<ver>[0-9a-f]{2})-(?P<trace>[0-9a-f]{32})-(?P<span>[0-9a-f]{16})-(?P<flags>[0-9a-f]{2})$")


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str
    traceparent: str
    tracestate: str = ""
    sampled: bool = False

    @staticmethod
    def from_headers(headers: Dict[str, str]) -> Optional["TraceContext"]:
        tp = _header_get(headers, "traceparent")
        if not tp:
            return None
        m = _TRACEPARENT_RE.match(tp.strip())
        if not m:
            return None
        trace_id = m.group("trace")
        span_id = m.group("span")
        flags = int(m.group("flags"), 16)
        sampled = bool(flags & 0x01)
        ts = _header_get(headers, "tracestate") or ""
        return TraceContext(trace_id=trace_id, span_id=span_id, traceparent=tp.strip(), tracestate=ts, sampled=sampled)

    @staticmethod
    def build(trace_id: str, span_id: str, sampled: bool = False, tracestate: str = "") -> "TraceContext":
        flags = "01" if sampled else "00"
        traceparent = f"00-{trace_id}-{span_id}-{flags}"
        return TraceContext(trace_id=trace_id, span_id=span_id, traceparent=traceparent, tracestate=tracestate or "", sampled=sampled)

    def to_headers(self) -> Dict[str, str]:
        out = {"traceparent": self.traceparent}
        if self.tracestate:
            out["tracestate"] = self.tracestate
        return out


def parse_traceparent(traceparent: str) -> Optional[Tuple[str, str, bool]]:
    m = _TRACEPARENT_RE.match((traceparent or "").strip())
    if not m:
        return None
    flags = int(m.group("flags"), 16)
    return m.group("trace"), m.group("span"), bool(flags & 0x01)


def _header_get(headers: Dict[str, str], key: str) -> str:
    for k, v in (headers or {}).items():
        if str(k).lower() == key.lower():
            return str(v)
    return ""

