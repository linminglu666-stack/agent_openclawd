from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from protocols.interfaces import IMessageBus, IModule
from protocols.trace import TraceContext
from utils.logger import get_logger


Handler = Callable[[Dict[str, Any]], Any]


@dataclass
class Message:
    message_id: str
    topic: str
    payload: Dict[str, Any]
    trace_id: Optional[str] = None
    timestamp: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))
    headers: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Subscription:
    subscription_id: str
    topic: str
    handler: Handler
    created_at: int = field(default_factory=lambda: int(datetime.now(tz=timezone.utc).timestamp()))
    message_count: int = 0
    error_count: int = 0


@dataclass
class MessageBusStats:
    total_published: int
    total_delivered: int
    total_errors: int
    active_subscriptions: int
    topics: List[str]


class MessageBus(IModule, IMessageBus):
    def __init__(self):
        self._subscriptions: Dict[str, Subscription] = {}
        self._topic_subscriptions: Dict[str, List[str]] = {}
        self._message_history: Dict[str, List[Message]] = {}
        self._history_limit: int = 100
        self._initialized = False
        self._logger = get_logger("message_bus")
        self._subscription_counter = 0
        self._message_counter = 0
        self._stats = {"published": 0, "delivered": 0, "errors": 0}

    @property
    def name(self) -> str:
        return "message_bus"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self, config: Dict[str, Any]) -> bool:
        if config.get("history_limit"):
            self._history_limit = config["history_limit"]

        self._initialized = True
        self._logger.info("Message bus initialized", history_limit=self._history_limit)
        return True

    async def shutdown(self) -> bool:
        self._subscriptions.clear()
        self._topic_subscriptions.clear()
        self._initialized = False
        self._logger.info("Message bus shutdown")
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {
            "component": self.name,
            "initialized": self._initialized,
            "active_subscriptions": len(self._subscriptions),
            "topics": list(self._topic_subscriptions.keys()),
            "stats": self._stats,
        }

    async def execute(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if command == "publish":
            success = await self.publish(args.get("topic", ""), args.get("payload", {}), args.get("trace_id"))
            return {"success": success}
        elif command == "subscribe":
            sub_id = await self.subscribe(args.get("topic", ""), args.get("handler"))
            return {"subscription_id": sub_id}
        elif command == "unsubscribe":
            success = await self.unsubscribe(args.get("subscription_id", ""))
            return {"success": success}
        elif command == "stats":
            stats = self.get_stats()
            return stats.__dict__
        else:
            return {"error": f"Unknown command: {command}"}

    async def publish(self, topic: str, payload: Dict[str, Any], trace_id: Optional[str] = None) -> bool:
        self._message_counter += 1
        message_id = f"msg_{self._message_counter}"

        message = Message(
            message_id=message_id,
            topic=topic,
            payload=payload,
            trace_id=trace_id,
        )

        if topic not in self._message_history:
            self._message_history[topic] = []
        self._message_history[topic].append(message)
        if len(self._message_history[topic]) > self._history_limit:
            self._message_history[topic] = self._message_history[topic][-self._history_limit :]

        self._stats["published"] += 1

        subscription_ids = self._topic_subscriptions.get(topic, [])
        for sub_id in subscription_ids:
            sub = self._subscriptions.get(sub_id)
            if not sub:
                continue

            try:
                result = sub.handler(message.__dict__)
                if hasattr(result, "__await__"):
                    await result
                sub.message_count += 1
                self._stats["delivered"] += 1
            except Exception as e:
                sub.error_count += 1
                self._stats["errors"] += 1
                self._logger.error(
                    "Message handler error",
                    topic=topic,
                    subscription_id=sub_id,
                    error=str(e),
                )

        self._logger.debug("Message published", topic=topic, message_id=message_id, subscribers=len(subscription_ids))
        return True

    async def subscribe(self, topic: str, handler: Any) -> str:
        self._subscription_counter += 1
        subscription_id = f"sub_{self._subscription_counter}"

        sub = Subscription(
            subscription_id=subscription_id,
            topic=topic,
            handler=handler,
        )

        self._subscriptions[subscription_id] = sub

        if topic not in self._topic_subscriptions:
            self._topic_subscriptions[topic] = []
        self._topic_subscriptions[topic].append(subscription_id)

        self._logger.info("Subscription created", topic=topic, subscription_id=subscription_id)
        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        sub = self._subscriptions.pop(subscription_id, None)
        if not sub:
            return False

        if sub.topic in self._topic_subscriptions:
            if subscription_id in self._topic_subscriptions[sub.topic]:
                self._topic_subscriptions[sub.topic].remove(subscription_id)

        self._logger.info("Subscription removed", subscription_id=subscription_id)
        return True

    def get_history(self, topic: str, limit: int = 10) -> List[Dict[str, Any]]:
        messages = self._message_history.get(topic, [])
        return [m.__dict__ for m in messages[-limit:]]

    def get_stats(self) -> MessageBusStats:
        return MessageBusStats(
            total_published=self._stats["published"],
            total_delivered=self._stats["delivered"],
            total_errors=self._stats["errors"],
            active_subscriptions=len(self._subscriptions),
            topics=list(self._topic_subscriptions.keys()),
        )

    def get_subscription_info(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        sub = self._subscriptions.get(subscription_id)
        if not sub:
            return None
        return {
            "subscription_id": sub.subscription_id,
            "topic": sub.topic,
            "created_at": sub.created_at,
            "message_count": sub.message_count,
            "error_count": sub.error_count,
        }

    def list_subscriptions(self, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        if topic:
            sub_ids = self._topic_subscriptions.get(topic, [])
            return [self.get_subscription_info(sid) for sid in sub_ids if self.get_subscription_info(sid)]
        else:
            return [self.get_subscription_info(sid) for sid in self._subscriptions.keys()]
