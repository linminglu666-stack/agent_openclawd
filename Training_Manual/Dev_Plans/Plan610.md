# Plan610 SSE 事件总线

## 目标
提供实时事件推送。

## 代码（`src/bff/sse.py`）
```python
from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import dataclass

from flask import Response


@dataclass
class Event:
    type: str
    payload: dict


class EventBus:
    def __init__(self) -> None:
        self._subs: list[queue.Queue] = []
        self._lock = threading.Lock()

    def publish(self, evt: Event) -> None:
        with self._lock:
            for q in self._subs:
                q.put(evt)

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        with self._lock:
            self._subs.append(q)
        return q


bus = EventBus()


def sse_stream() -> Response:
    sub = bus.subscribe()

    def gen():
        while True:
            try:
                evt: Event = sub.get(timeout=10)
                yield f"data: {json.dumps({'type': evt.type, 'payload': evt.payload}, ensure_ascii=False)}\\n\\n"
            except queue.Empty:
                yield f": keepalive {int(time.time())}\\n\\n"

    return Response(gen(), mimetype="text/event-stream")
```

## 验收
- 浏览器可持续接收事件
