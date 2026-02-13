"""
模型元数据定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ModelStatus(Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    MAINTENANCE = "maintenance"


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ModelCapabilities:
    supports_streaming: bool = True
    supports_functions: bool = True
    supports_vision: bool = False
    supports_audio: bool = False
    supports_json_mode: bool = False
    
    max_context_tokens: int = 4096
    max_output_tokens: int = 2048
    
    reasoning_score: float = 0.8
    coding_score: float = 0.8
    creative_score: float = 0.7
    analysis_score: float = 0.8
    
    task_scores: Dict[str, float] = field(default_factory=dict)
    
    def get_task_score(self, task_type: str) -> float:
        if task_type in self.task_scores:
            return self.task_scores[task_type]
        
        task_mapping = {
            "reasoning": self.reasoning_score,
            "coding": self.coding_score,
            "creative": self.creative_score,
            "analysis": self.analysis_score,
            "general": 0.75,
        }
        return task_mapping.get(task_type, 0.7)
    
    def supports_capability(self, capability: str) -> bool:
        capability_map = {
            "streaming": self.supports_streaming,
            "functions": self.supports_functions,
            "vision": self.supports_vision,
            "audio": self.supports_audio,
            "json_mode": self.supports_json_mode,
        }
        return capability_map.get(capability, False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "supports_streaming": self.supports_streaming,
            "supports_functions": self.supports_functions,
            "supports_vision": self.supports_vision,
            "supports_audio": self.supports_audio,
            "supports_json_mode": self.supports_json_mode,
            "max_context_tokens": self.max_context_tokens,
            "max_output_tokens": self.max_output_tokens,
            "reasoning_score": self.reasoning_score,
            "coding_score": self.coding_score,
            "creative_score": self.creative_score,
            "analysis_score": self.analysis_score,
            "task_scores": self.task_scores,
        }


@dataclass
class ModelPerformance:
    avg_latency_ms: int = 1000
    p50_latency_ms: int = 800
    p95_latency_ms: int = 2000
    p99_latency_ms: int = 5000
    
    success_rate: float = 0.99
    timeout_rate: float = 0.01
    error_rate: float = 0.01
    
    tokens_per_second: float = 50.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "avg_latency_ms": self.avg_latency_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "success_rate": self.success_rate,
            "timeout_rate": self.timeout_rate,
            "error_rate": self.error_rate,
            "tokens_per_second": self.tokens_per_second,
        }


@dataclass
class ModelPricing:
    input_price_per_1k: float = 0.0
    output_price_per_1k: float = 0.0
    price_per_request: Optional[float] = None
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        input_cost = (input_tokens / 1000) * self.input_price_per_1k
        output_cost = (output_tokens / 1000) * self.output_price_per_1k
        request_cost = self.price_per_request or 0
        return input_cost + output_cost + request_cost
    
    def estimate_cost(self, estimated_input_tokens: int, estimated_output_tokens: int) -> float:
        return self.calculate_cost(estimated_input_tokens, estimated_output_tokens)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_price_per_1k": self.input_price_per_1k,
            "output_price_per_1k": self.output_price_per_1k,
            "price_per_request": self.price_per_request,
        }


@dataclass
class ModelConfig:
    api_key_env: str = ""
    base_url: str = ""
    timeout_ms: int = 60000
    max_retries: int = 3
    retry_delay_ms: int = 1000
    
    temperature: float = 0.7
    top_p: float = 1.0
    
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "api_key_env": self.api_key_env,
            "base_url": self.base_url,
            "timeout_ms": self.timeout_ms,
            "max_retries": self.max_retries,
            "retry_delay_ms": self.retry_delay_ms,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "extra_params": self.extra_params,
        }


@dataclass
class ModelStats:
    total_requests: int = 0
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    
    requests_today: int = 0
    tokens_today: int = 0
    cost_today: float = 0.0
    
    last_request_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_error_time: Optional[datetime] = None
    last_error_message: Optional[str] = None
    
    def record_request(self, input_tokens: int, output_tokens: int, cost: float, success: bool):
        self.total_requests += 1
        self.total_tokens += input_tokens + output_tokens
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost
        
        self.requests_today += 1
        self.tokens_today += input_tokens + output_tokens
        self.cost_today += cost
        
        now = datetime.now()
        self.last_request_time = now
        
        if success:
            self.last_success_time = now
        else:
            self.last_error_time = now
    
    def reset_daily_stats(self):
        self.requests_today = 0
        self.tokens_today = 0
        self.cost_today = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost": self.total_cost,
            "requests_today": self.requests_today,
            "tokens_today": self.tokens_today,
            "cost_today": self.cost_today,
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "last_error_message": self.last_error_message,
        }


@dataclass
class ModelHealth:
    status: HealthStatus = HealthStatus.UNKNOWN
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_check_time: Optional[datetime] = None
    last_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "last_error": self.last_error,
        }


@dataclass
class ModelMetadata:
    model_id: str
    provider: str
    model_name: str
    display_name: str = ""
    
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    performance: ModelPerformance = field(default_factory=ModelPerformance)
    pricing: ModelPricing = field(default_factory=ModelPricing)
    config: ModelConfig = field(default_factory=ModelConfig)
    
    status: ModelStatus = ModelStatus.ENABLED
    health: ModelHealth = field(default_factory=ModelHealth)
    stats: ModelStats = field(default_factory=ModelStats)
    
    weight: float = 1.0
    priority: int = 5
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.model_name
    
    def is_available(self) -> bool:
        return (
            self.status == ModelStatus.ENABLED and
            self.health.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "model_name": self.model_name,
            "display_name": self.display_name,
            "capabilities": self.capabilities.to_dict(),
            "performance": self.performance.to_dict(),
            "pricing": self.pricing.to_dict(),
            "config": self.config.to_dict(),
            "status": self.status.value,
            "health": self.health.to_dict(),
            "stats": self.stats.to_dict(),
            "weight": self.weight,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
