"""
模型提供者抽象层
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Union
import asyncio
import time


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


@dataclass
class ChatMessage:
    role: MessageRole
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"role": self.role.value, "content": self.content}
        if self.name:
            result["name"] = self.name
        if self.function_call:
            result["function_call"] = self.function_call
        return result


@dataclass
class FunctionDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass
class ModelRequest:
    messages: List[ChatMessage]
    model: str
    
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    
    functions: Optional[List[FunctionDefinition]] = None
    function_call: Optional[Union[str, Dict[str, str]]] = None
    
    stream: bool = False
    stop: Optional[List[str]] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    request_id: str = ""
    timeout_ms: int = 60000
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "model": self.model,
            "messages": [m.to_dict() for m in self.messages],
        }
        if self.temperature is not None:
            result["temperature"] = self.temperature
        if self.top_p is not None:
            result["top_p"] = self.top_p
        if self.max_tokens is not None:
            result["max_tokens"] = self.max_tokens
        if self.functions:
            result["functions"] = [f.to_dict() for f in self.functions]
        if self.function_call:
            result["function_call"] = self.function_call
        if self.stream:
            result["stream"] = self.stream
        if self.stop:
            result["stop"] = self.stop
        return result
    
    @classmethod
    def from_prompt(cls, prompt: str, model: str, **kwargs) -> "ModelRequest":
        return cls(
            messages=[ChatMessage(role=MessageRole.USER, content=prompt)],
            model=model,
            **kwargs
        )


@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    
    def to_dict(self) -> Dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class ModelResponse:
    request_id: str
    model: str
    
    content: str
    finish_reason: str
    
    usage: TokenUsage
    
    function_call: Optional[Dict[str, Any]] = None
    
    latency_ms: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "request_id": self.request_id,
            "model": self.model,
            "content": self.content,
            "finish_reason": self.finish_reason,
            "usage": self.usage.to_dict(),
            "latency_ms": self.latency_ms,
            "created_at": self.created_at.isoformat(),
        }
        if self.function_call:
            result["function_call"] = self.function_call
        return result


@dataclass
class StreamChunk:
    request_id: str
    model: str
    content: str
    finish_reason: Optional[str] = None
    delta: Dict[str, Any] = field(default_factory=dict)


class ModelProvider(ABC):
    
    provider_name: str = "base"
    
    @abstractmethod
    async def complete(self, request: ModelRequest) -> ModelResponse:
        pass
    
    @abstractmethod
    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamChunk]:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass
    
    @abstractmethod
    def get_supported_models(self) -> List[str]:
        pass
    
    def count_tokens(self, text: str) -> int:
        return len(text) // 4
    
    def estimate_tokens(self, messages: List[ChatMessage]) -> int:
        total = 0
        for msg in messages:
            total += self.count_tokens(msg.content)
            total += 4
        return total


class MockModelProvider(ModelProvider):
    provider_name = "mock"
    
    def __init__(self):
        self._models = ["mock-model-1", "mock-model-2"]
        self._healthy = True
    
    async def complete(self, request: ModelRequest) -> ModelResponse:
        start_time = time.time()
        
        await asyncio.sleep(0.1)
        
        prompt_tokens = self.estimate_tokens(request.messages)
        completion_tokens = 50
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return ModelResponse(
            request_id=request.request_id or "mock-request",
            model=request.model,
            content=f"[Mock Response] This is a simulated response for model {request.model}.",
            finish_reason="stop",
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            latency_ms=latency_ms,
        )
    
    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamChunk]:
        words = ["This", "is", "a", "mock", "streaming", "response", "."]
        
        for word in words:
            await asyncio.sleep(0.05)
            yield StreamChunk(
                request_id=request.request_id or "mock-request",
                model=request.model,
                content=word + " ",
            )
        
        yield StreamChunk(
            request_id=request.request_id or "mock-request",
            model=request.model,
            content="",
            finish_reason="stop",
        )
    
    async def health_check(self) -> bool:
        return self._healthy
    
    def get_supported_models(self) -> List[str]:
        return self._models
    
    def set_healthy(self, healthy: bool):
        self._healthy = healthy
