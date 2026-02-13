from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import json

from core.persistence import JsonlWAL, StateDB
from protocols.events import EventEnvelope
from protocols.trace import TraceContext

from .event_bus import InMemoryEventBus


Handler = Callable[[Dict[str, Any]], Any]


@dataclass
class ChannelStats:
    topic: str
    published: int
    subscribers: int


class PersistentEventBus:
    def __init__(self, wal: JsonlWAL, state_db: StateDB):
        self._wal = wal
        self._db = state_db
        self._mem = InMemoryEventBus()
        self._published: Dict[str, int] = {}

    async def publish(self, topic: str, event: Dict[str, Any]) -> bool:
        env = EventEnvelope(
            topic=str(topic),
            version=str((event or {}).get("version", "v1")),
            event_id=str((event or {}).get("event_id", "")) or "",
            trace=_trace_from_event(event),
            payload=dict((event or {}).get("payload") or event or {}),
            meta=dict((event or {}).get("meta") or {}),
        )
        self._wal.append("event_bus.publish", {"topic": topic, "envelope": _as_dict(env)})
        self._published[topic] = int(self._published.get(topic, 0)) + 1
        return await self._mem.publish(topic, _as_dict(env))

    async def subscribe(self, topic: str, handler: Handler) -> str:
        return await self._mem.subscribe(topic, handler)

    async def unsubscribe(self, subscription_id: str) -> bool:
        return await self._mem.unsubscribe(subscription_id)

    def get_channel_stats(self) -> List[ChannelStats]:
        stats: List[ChannelStats] = []
        for topic, count in self._published.items():
            stats.append(ChannelStats(topic=topic, published=int(count), subscribers=0))
        return stats

    def replay(self, subscriber_id: str, topic: str, handler: Handler, max_records: int = 1000) -> int:
        offset = int(self._db.get_event_offset(subscriber_id=subscriber_id, topic=topic))
        delivered = 0
        for i, rec in enumerate(self._wal.iter_records()):
            if rec.type != "event_bus.publish":
                continue
            data = rec.data or {}
            if str(data.get("topic")) != str(topic):
                continue
            if i < offset:
                continue
            env = data.get("envelope") or {}
            try:
                handler(dict(env))
            except Exception:
                pass
            delivered += 1
            offset = i + 1
            if delivered >= int(max_records):
                break
        self._db.set_event_offset(subscriber_id=subscriber_id, topic=topic, offset=offset)
        return delivered


def _as_dict(env: EventEnvelope) -> Dict[str, Any]:
    return {
        "topic": env.topic,
        "version": env.version,
        "event_id": env.event_id,
        "created_at": env.created_at,
        "payload": env.payload,
        "meta": env.meta,
        "trace": {
            "trace_id": env.trace.trace_id,
            "span_id": env.trace.span_id,
            "traceparent": env.trace.traceparent,
            "tracestate": env.trace.tracestate,
            "sampled": env.trace.sampled,
        }
        if env.trace
        else None,
    }


def _trace_from_event(event: Dict[str, Any]) -> Optional[TraceContext]:
    t = (event or {}).get("trace")
    if isinstance(t, TraceContext):
        return t
    if isinstance(t, dict):
        tp = str(t.get("traceparent", ""))
        ctx = TraceContext.from_headers({"traceparent": tp, "tracestate": str(t.get("tracestate", ""))})
        if ctx:
            return ctx
    return None

