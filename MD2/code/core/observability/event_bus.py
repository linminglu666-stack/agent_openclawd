from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocols.interfaces import IEventBus
from utils.logger import get_logger


Handler = Callable[[Dict[str, Any]], Any]


@dataclass
class Subscription:
    subscription_id: str
    topic: str
    handler: Handler


class InMemoryEventBus(IEventBus):
    def __init__(self):
        self._subscriptions: Dict[str, Subscription] = {}
        self._topics: Dict[str, List[str]] = {}
        self._lock = asyncio.Lock()
        self._logger = get_logger("observability.event_bus")

    async def publish(self, topic: str, event: Dict[str, Any]) -> bool:
        async with self._lock:
            subscription_ids = list(self._topics.get(topic, []))

        for sub_id in subscription_ids:
            sub = self._subscriptions.get(sub_id)
            if not sub:
                continue
            try:
                result = sub.handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self._logger.error("event_handler_error", topic=topic, subscription_id=sub_id, error=str(e))

        return True

    async def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> str:
        subscription_id = str(uuid.uuid4())
        sub = Subscription(subscription_id=subscription_id, topic=topic, handler=handler)

        async with self._lock:
            self._subscriptions[subscription_id] = sub
            if topic not in self._topics:
                self._topics[topic] = []
            self._topics[topic].append(subscription_id)

        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        async with self._lock:
            sub = self._subscriptions.pop(subscription_id, None)
            if not sub:
                return False
            if sub.topic in self._topics and subscription_id in self._topics[sub.topic]:
                self._topics[sub.topic].remove(subscription_id)
            return True

