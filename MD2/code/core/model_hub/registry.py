"""
模型注册中心
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import asyncio
import threading

from .model_metadata import (
    ModelMetadata,
    ModelCapabilities,
    ModelPerformance,
    ModelPricing,
    ModelConfig,
    ModelStatus,
    HealthStatus,
    ModelHealth,
    ModelStats,
)


@dataclass
class RegistryStats:
    total_models: int = 0
    enabled_models: int = 0
    healthy_models: int = 0
    providers: List[str] = field(default_factory=list)


class ModelRegistry:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._models: Dict[str, ModelMetadata] = {}
        self._provider_index: Dict[str, List[str]] = {}
        self._capability_index: Dict[str, List[str]] = {}
        self._listeners: List[Callable] = []
        self._initialized = True
    
    def register(self, model: ModelMetadata) -> bool:
        if model.model_id in self._models:
            return False
        
        self._models[model.model_id] = model
        
        if model.provider not in self._provider_index:
            self._provider_index[model.provider] = []
        self._provider_index[model.provider].append(model.model_id)
        
        self._update_capability_index(model)
        self._notify_listeners("register", model)
        
        return True
    
    def unregister(self, model_id: str) -> bool:
        if model_id not in self._models:
            return False
        
        model = self._models[model_id]
        
        if model.provider in self._provider_index:
            if model_id in self._provider_index[model.provider]:
                self._provider_index[model.provider].remove(model_id)
        
        self._remove_from_capability_index(model)
        del self._models[model_id]
        self._notify_listeners("unregister", model)
        
        return True
    
    def get(self, model_id: str) -> Optional[ModelMetadata]:
        return self._models.get(model_id)
    
    def get_by_provider(self, provider: str) -> List[ModelMetadata]:
        model_ids = self._provider_index.get(provider, [])
        return [self._models[mid] for mid in model_ids if mid in self._models]
    
    def get_by_capability(self, capability: str) -> List[ModelMetadata]:
        model_ids = self._capability_index.get(capability, [])
        return [self._models[mid] for mid in model_ids if mid in self._models]
    
    def get_available_models(self) -> List[ModelMetadata]:
        return [m for m in self._models.values() if m.is_available()]
    
    def get_models_by_status(self, status: ModelStatus) -> List[ModelMetadata]:
        return [m for m in self._models.values() if m.status == status]
    
    def get_models_by_health(self, health_status: HealthStatus) -> List[ModelMetadata]:
        return [m for m in self._models.values() if m.health.status == health_status]
    
    def list_all(self) -> List[ModelMetadata]:
        return list(self._models.values())
    
    def list_providers(self) -> List[str]:
        return list(self._provider_index.keys())
    
    def update_status(self, model_id: str, status: ModelStatus) -> bool:
        model = self.get(model_id)
        if not model:
            return False
        
        model.status = status
        model.updated_at = datetime.now()
        self._notify_listeners("status_change", model)
        return True
    
    def update_health(self, model_id: str, health: ModelHealth) -> bool:
        model = self.get(model_id)
        if not model:
            return False
        
        model.health = health
        model.updated_at = datetime.now()
        self._notify_listeners("health_change", model)
        return True
    
    def update_stats(self, model_id: str, stats: ModelStats) -> bool:
        model = self.get(model_id)
        if not model:
            return False
        
        model.stats = stats
        model.updated_at = datetime.now()
        return True
    
    def update_weight(self, model_id: str, weight: float) -> bool:
        model = self.get(model_id)
        if not model:
            return False
        
        model.weight = max(0.0, min(weight, 10.0))
        model.updated_at = datetime.now()
        return True
    
    def get_stats(self) -> RegistryStats:
        models = list(self._models.values())
        return RegistryStats(
            total_models=len(models),
            enabled_models=sum(1 for m in models if m.status == ModelStatus.ENABLED),
            healthy_models=sum(1 for m in models if m.health.status == HealthStatus.HEALTHY),
            providers=list(self._provider_index.keys()),
        )
    
    def add_listener(self, callback: Callable):
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable):
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _update_capability_index(self, model: ModelMetadata):
        caps = model.capabilities
        if caps.supports_streaming:
            self._add_to_capability_index("streaming", model.model_id)
        if caps.supports_functions:
            self._add_to_capability_index("functions", model.model_id)
        if caps.supports_vision:
            self._add_to_capability_index("vision", model.model_id)
        if caps.supports_audio:
            self._add_to_capability_index("audio", model.model_id)
        if caps.supports_json_mode:
            self._add_to_capability_index("json_mode", model.model_id)
    
    def _add_to_capability_index(self, capability: str, model_id: str):
        if capability not in self._capability_index:
            self._capability_index[capability] = []
        if model_id not in self._capability_index[capability]:
            self._capability_index[capability].append(model_id)
    
    def _remove_from_capability_index(self, model: ModelMetadata):
        for model_ids in self._capability_index.values():
            if model.model_id in model_ids:
                model_ids.remove(model.model_id)
    
    def _notify_listeners(self, event_type: str, model: ModelMetadata):
        for callback in self._listeners:
            try:
                callback(event_type, model)
            except Exception:
                pass
    
    def clear(self):
        self._models.clear()
        self._provider_index.clear()
        self._capability_index.clear()


def create_model_from_config(config: Dict[str, Any]) -> ModelMetadata:
    caps_config = config.get("capabilities", {})
    capabilities = ModelCapabilities(
        supports_streaming=caps_config.get("supports_streaming", True),
        supports_functions=caps_config.get("supports_functions", True),
        supports_vision=caps_config.get("supports_vision", False),
        supports_audio=caps_config.get("supports_audio", False),
        supports_json_mode=caps_config.get("supports_json_mode", False),
        max_context_tokens=caps_config.get("max_context_tokens", 4096),
        max_output_tokens=caps_config.get("max_output_tokens", 2048),
        reasoning_score=caps_config.get("reasoning_score", 0.8),
        coding_score=caps_config.get("coding_score", 0.8),
        creative_score=caps_config.get("creative_score", 0.7),
        analysis_score=caps_config.get("analysis_score", 0.8),
        task_scores=caps_config.get("task_scores", {}),
    )
    
    perf_config = config.get("performance", {})
    performance = ModelPerformance(
        avg_latency_ms=perf_config.get("avg_latency_ms", 1000),
        p50_latency_ms=perf_config.get("p50_latency_ms", 800),
        p95_latency_ms=perf_config.get("p95_latency_ms", 2000),
        p99_latency_ms=perf_config.get("p99_latency_ms", 5000),
        success_rate=perf_config.get("success_rate", 0.99),
        timeout_rate=perf_config.get("timeout_rate", 0.01),
        error_rate=perf_config.get("error_rate", 0.01),
        tokens_per_second=perf_config.get("tokens_per_second", 50.0),
    )
    
    pricing_config = config.get("pricing", {})
    pricing = ModelPricing(
        input_price_per_1k=pricing_config.get("input_price_per_1k", 0.0),
        output_price_per_1k=pricing_config.get("output_price_per_1k", 0.0),
        price_per_request=pricing_config.get("price_per_request"),
    )
    
    model_config_data = config.get("config", {})
    model_config = ModelConfig(
        api_key_env=model_config_data.get("api_key_env", ""),
        base_url=model_config_data.get("base_url", ""),
        timeout_ms=model_config_data.get("timeout_ms", 60000),
        max_retries=model_config_data.get("max_retries", 3),
        retry_delay_ms=model_config_data.get("retry_delay_ms", 1000),
        temperature=model_config_data.get("temperature", 0.7),
        top_p=model_config_data.get("top_p", 1.0),
        extra_params=model_config_data.get("extra_params", {}),
    )
    
    status_str = config.get("status", "enabled")
    status = ModelStatus(status_str) if status_str in [s.value for s in ModelStatus] else ModelStatus.ENABLED
    
    return ModelMetadata(
        model_id=config["model_id"],
        provider=config["provider"],
        model_name=config["model_name"],
        display_name=config.get("display_name", config["model_name"]),
        capabilities=capabilities,
        performance=performance,
        pricing=pricing,
        config=model_config,
        status=status,
        weight=config.get("weight", 1.0),
        priority=config.get("priority", 5),
    )
