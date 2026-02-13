# 多模型并行支持架构设计

## 1. 概述

OpenClaw-X 多模型并行支持架构旨在实现：

- **多模型同时在线**：支持多个大语言模型同时运行，包括不同厂商（OpenAI、Claude、本地模型等）
- **智能路由选择**：根据任务类型、成本、延迟、质量要求自动选择最优模型
- **负载均衡**：在多个模型实例间分配请求，避免单点过载
- **故障转移**：自动检测模型故障并切换到备用模型
- **成本优化**：在保证质量的前提下最小化调用成本

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OpenClaw-X 多模型架构                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        应用层 (Application Layer)                     │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │   │
│  │  │ Copilot  │ │ Agent    │ │ Reasoning│ │ Workflow │               │   │
│  │  │ Chat     │ │ Tasks    │ │ Engine   │ │ Executor │               │   │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘               │   │
│  └───────┼────────────┼────────────┼────────────┼──────────────────────┘   │
│          │            │            │            │                           │
│          ▼            ▼            ▼            ▼                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     智能路由层 (Smart Routing Layer)                  │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │   │
│  │  │ ModelSelector │  │ LoadBalancer  │  │ FailoverMgr   │           │   │
│  │  │ 任务复杂度评估  │  │ 负载均衡策略   │  │ 故障检测转移   │           │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘           │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │   │
│  │  │ CostOptimizer │  │ QualityTracker│  │ UsageAnalytics│           │   │
│  │  │ 成本优化策略   │  │ 质量追踪评估   │  │ 使用统计分析   │           │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     模型注册层 (Model Registry Layer)                 │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │                    ModelRegistry                             │   │   │
│  │  │  • 模型元数据管理  • 能力声明  • 健康状态  • 配置管理         │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     适配层 (Provider Adapter Layer)                   │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │ OpenAI  │ │ Claude  │ │ Gemini  │ │ Local   │ │ Custom  │       │   │
│  │  │ Adapter │ │ Adapter │ │ Adapter │ │ Model   │ │ Model   │       │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

| 组件 | 职责 | 关键特性 |
|------|------|----------|
| **ModelRegistry** | 模型注册中心 | 模型发现、元数据管理、健康检查 |
| **ModelSelector** | 智能选择器 | 复杂度评估、能力匹配、成本计算 |
| **LoadBalancer** | 负载均衡器 | 多策略支持、动态权重、会话亲和 |
| **FailoverManager** | 故障转移管理器 | 健康检测、自动切换、熔断机制 |
| **CostOptimizer** | 成本优化器 | Token计费、预算控制、用量预测 |
| **QualityTracker** | 质量追踪器 | 响应评估、A/B测试、反馈学习 |

## 3. 数据模型

### 3.1 模型元数据

```python
@dataclass
class ModelMetadata:
    """模型元数据"""
    model_id: str                    # 模型唯一标识
    provider: str                    # 提供商 (openai, anthropic, local, etc.)
    model_name: str                  # 模型名称 (gpt-4, claude-3-opus, etc.)
    
    # 能力声明
    capabilities: ModelCapabilities
    
    # 性能指标
    performance: ModelPerformance
    
    # 成本信息
    pricing: ModelPricing
    
    # 配置
    config: ModelConfig
    
    # 状态
    status: ModelStatus
    health: HealthStatus
    
    # 统计
    stats: ModelStats
```

### 3.2 模型能力

```python
@dataclass
class ModelCapabilities:
    """模型能力声明"""
    # 基础能力
    supports_streaming: bool = True
    supports_functions: bool = True
    supports_vision: bool = False
    supports_audio: bool = False
    
    # 上下文窗口
    max_context_tokens: int = 4096
    max_output_tokens: int = 2048
    
    # 推理能力评分 (0-1)
    reasoning_score: float = 0.8
    coding_score: float = 0.8
    creative_score: float = 0.7
    
    # 任务类型适配
    task_scores: Dict[str, float] = field(default_factory=dict)
    # e.g., {"analysis": 0.9, "generation": 0.85, "summarization": 0.9}
```

### 3.3 路由请求

```python
@dataclass
class RoutingRequest:
    """路由请求"""
    request_id: str
    prompt: str
    
    # 任务特征
    task_type: str = "general"          # general, reasoning, coding, creative, etc.
    complexity: Optional[float] = None  # 复杂度评分 (0-1)，None表示自动评估
    priority: int = 5                   # 优先级 (1-10)
    
    # 约束条件
    max_latency_ms: Optional[int] = None
    max_cost: Optional[float] = None
    required_capabilities: List[str] = field(default_factory=list)
    
    # 偏好设置
    prefer_quality: bool = True         # 质量优先 vs 成本优先
    prefer_provider: Optional[str] = None
    
    # 会话上下文
    session_id: Optional[str] = None    # 会话亲和
    conversation_history: List[Dict] = field(default_factory=list)
```

### 3.4 路由决策

```python
@dataclass
class RoutingDecision:
    """路由决策"""
    request_id: str
    selected_model: ModelMetadata
    selected_endpoint: str
    
    # 决策依据
    reason: str
    confidence: float
    
    # 预估指标
    estimated_latency_ms: int
    estimated_cost: float
    estimated_tokens: int
    
    # 备选方案
    alternatives: List[ModelMetadata]
    
    # 决策时间
    decision_time_ms: int
```

## 4. 智能路由策略

### 4.1 路由决策流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         路由决策流程                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────┐                                                           │
│  │ 接收请求 │                                                           │
│  └────┬─────┘                                                           │
│       │                                                                 │
│       ▼                                                                 │
│  ┌──────────────┐     ┌──────────────┐                                 │
│  │ 复杂度评估    │────→│ 任务分类     │                                 │
│  │ (Prompt分析) │     │ (类型识别)   │                                 │
│  └──────┬───────┘     └──────┬───────┘                                 │
│         │                    │                                          │
│         └────────┬───────────┘                                          │
│                  ▼                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                      候选模型筛选                                  │  │
│  │  • 能力匹配 (是否支持所需功能)                                     │  │
│  │  • 约束过滤 (延迟/成本上限)                                        │  │
│  │  • 状态过滤 (健康检查)                                             │  │
│  └────────────────────────────┬─────────────────────────────────────┘  │
│                               │                                         │
│                               ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                      模型评分排序                                  │  │
│  │  score = w1 × quality_score                                      │  │
│  │        + w2 × cost_score                                         │  │
│  │        + w3 × latency_score                                      │  │
│  │        + w4 × load_score                                         │  │
│  │        + w5 × task_affinity                                      │  │
│  └────────────────────────────┬─────────────────────────────────────┘  │
│                               │                                         │
│                               ▼                                         │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐           │
│  │ 负载均衡检查  │────→│ 会话亲和检查  │────→│ 最终选择    │           │
│  │              │     │              │     │              │           │
│  └──────────────┘     └──────────────┘     └──────────────┘           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 复杂度评估算法

```python
class ComplexityEstimator:
    """任务复杂度评估器"""
    
    def estimate(self, prompt: str, history: List[Dict]) -> ComplexityScore:
        factors = []
        
        # 1. 长度因子
        length_factor = self._calc_length_factor(prompt, history)
        factors.append(("length", length_factor, 0.2))
        
        # 2. 结构复杂度
        structure_factor = self._calc_structure_factor(prompt)
        factors.append(("structure", structure_factor, 0.15))
        
        # 3. 推理需求
        reasoning_factor = self._calc_reasoning_factor(prompt)
        factors.append(("reasoning", reasoning_factor, 0.25))
        
        # 4. 专业领域
        domain_factor = self._calc_domain_factor(prompt)
        factors.append(("domain", domain_factor, 0.2))
        
        # 5. 上下文依赖
        context_factor = self._calc_context_factor(history)
        factors.append(("context", context_factor, 0.2))
        
        # 加权综合
        total = sum(score * weight for _, score, weight in factors)
        
        return ComplexityScore(
            overall=total,
            factors={name: score for name, score, _ in factors}
        )
```

### 4.3 负载均衡策略

| 策略 | 描述 | 适用场景 |
|------|------|----------|
| **RoundRobin** | 轮询分配 | 同质模型集群 |
| **WeightedRoundRobin** | 加权轮询 | 异构模型集群 |
| **LeastConnections** | 最少连接 | 长连接场景 |
| **LeastLatency** | 最低延迟 | 实时性要求高 |
| **Random** | 随机选择 | 测试/调试 |
| **SessionAffinity** | 会话亲和 | 需要上下文连续性 |
| **CostAware** | 成本感知 | 预算敏感场景 |

## 5. 故障转移机制

### 5.1 健康检查

```python
class HealthChecker:
    """模型健康检查器"""
    
    def __init__(self):
        self.check_interval = 30  # 检查间隔(秒)
        self.timeout = 10         # 超时时间(秒)
        self.failure_threshold = 3  # 连续失败阈值
        self.recovery_threshold = 2  # 连续成功恢复阈值
    
    async def check_health(self, model: ModelMetadata) -> HealthCheckResult:
        try:
            # 发送探测请求
            result = await self._send_probe(model)
            
            if result.success:
                model.health.consecutive_failures = 0
                model.health.consecutive_successes += 1
                
                if model.health.status == HealthStatus.UNHEALTHY:
                    if model.health.consecutive_successes >= self.recovery_threshold:
                        model.health.status = HealthStatus.HEALTHY
            else:
                model.health.consecutive_successes = 0
                model.health.consecutive_failures += 1
                
                if model.health.consecutive_failures >= self.failure_threshold:
                    model.health.status = HealthStatus.UNHEALTHY
                    
            return result
            
        except Exception as e:
            model.health.last_error = str(e)
            model.health.consecutive_failures += 1
            return HealthCheckResult(success=False, error=str(e))
```

### 5.2 熔断机制

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         熔断状态机                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│     ┌──────────┐   失败率 > 阈值    ┌──────────┐                        │
│     │  CLOSED  │ ─────────────────→ │   OPEN   │                        │
│     │  (正常)   │                    │  (熔断)   │                        │
│     └────┬─────┘                    └────┬─────┘                        │
│          │                               │                              │
│          │                               │ 超时后                        │
│          │                               ▼                              │
│          │                         ┌──────────┐                         │
│          │        探测成功         │HALF_OPEN │                         │
│          │ ←────────────────────── │ (半开)    │                         │
│          │                         └────┬─────┘                         │
│          │                               │                              │
│          │                               │ 探测失败                      │
│          │                               ▼                              │
│          │                         ┌──────────┐                         │
│          │                         │   OPEN   │                         │
│          │                         │  (熔断)   │                         │
│          │                         └──────────┘                         │
│          │                                                              │
│          │ 连续成功达到阈值                                               │
│          ▼                                                              │
│     ┌──────────┐                                                        │
│     │  CLOSED  │                                                        │
│     └──────────┘                                                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 6. 成本优化

### 6.1 成本模型

```python
@dataclass
class ModelPricing:
    """模型定价"""
    input_price_per_1k: float      # 输入每1k token价格
    output_price_per_1k: float     # 输出每1k token价格
    
    # 可选：按请求计费
    price_per_request: Optional[float] = None
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        input_cost = (input_tokens / 1000) * self.input_price_per_1k
        output_cost = (output_tokens / 1000) * self.output_price_per_1k
        request_cost = self.price_per_request or 0
        return input_cost + output_cost + request_cost
```

### 6.2 预算控制

```python
class BudgetController:
    """预算控制器"""
    
    def __init__(self):
        self.daily_budget: float = 100.0
        self.monthly_budget: float = 3000.0
        self.current_daily_spend: float = 0.0
        self.current_monthly_spend: float = 0.0
        
    def check_budget(self, estimated_cost: float) -> BudgetDecision:
        if self.current_daily_spend + estimated_cost > self.daily_budget:
            return BudgetDecision(
                allowed=False,
                reason="daily_budget_exceeded",
                remaining_budget=self.daily_budget - self.current_daily_spend
            )
            
        if self.current_monthly_spend + estimated_cost > self.monthly_budget:
            return BudgetDecision(
                allowed=False,
                reason="monthly_budget_exceeded",
                remaining_budget=self.monthly_budget - self.current_monthly_spend
            )
            
        return BudgetDecision(allowed=True)
```

## 7. 配置示例

### 7.1 模型配置文件

```yaml
# models.yaml
models:
  - model_id: "gpt-4-turbo"
    provider: "openai"
    model_name: "gpt-4-turbo-preview"
    enabled: true
    capabilities:
      supports_streaming: true
      supports_functions: true
      supports_vision: true
      max_context_tokens: 128000
      max_output_tokens: 4096
      reasoning_score: 0.95
      coding_score: 0.95
    pricing:
      input_price_per_1k: 0.01
      output_price_per_1k: 0.03
    config:
      api_key_env: "OPENAI_API_KEY"
      base_url: "https://api.openai.com/v1"
      timeout_ms: 60000
      max_retries: 3
      
  - model_id: "claude-3-opus"
    provider: "anthropic"
    model_name: "claude-3-opus-20240229"
    enabled: true
    capabilities:
      supports_streaming: true
      supports_functions: true
      supports_vision: true
      max_context_tokens: 200000
      max_output_tokens: 4096
      reasoning_score: 0.95
      coding_score: 0.90
    pricing:
      input_price_per_1k: 0.015
      output_price_per_1k: 0.075
    config:
      api_key_env: "ANTHROPIC_API_KEY"
      base_url: "https://api.anthropic.com"
      
  - model_id: "local-llama-70b"
    provider: "local"
    model_name: "llama-3-70b"
    enabled: true
    capabilities:
      supports_streaming: true
      supports_functions: false
      max_context_tokens: 8192
      max_output_tokens: 2048
      reasoning_score: 0.80
      coding_score: 0.75
    pricing:
      input_price_per_1k: 0.0
      output_price_per_1k: 0.0
    config:
      base_url: "http://localhost:8000/v1"

routing:
  default_strategy: "quality_first"
  load_balancer: "weighted_round_robin"
  session_affinity: true
  failover_enabled: true
  
  complexity_weights:
    quality: 0.35
    cost: 0.25
    latency: 0.20
    load: 0.20

budget:
  daily_limit: 100.0
  monthly_limit: 3000.0
  alert_threshold: 0.8
```

## 8. API 接口

### 8.1 模型管理 API

```
# 模型注册
POST /api/v1/models
{
  "model_id": "gpt-4-turbo",
  "provider": "openai",
  "config": {...}
}

# 模型列表
GET /api/v1/models
GET /api/v1/models?status=healthy&provider=openai

# 模型详情
GET /api/v1/models/{model_id}

# 模型状态更新
PUT /api/v1/models/{model_id}/status
{
  "enabled": true,
  "weight": 1.0
}

# 模型注销
DELETE /api/v1/models/{model_id}
```

### 8.2 路由 API

```
# 智能路由
POST /api/v1/routing/select
{
  "prompt": "...",
  "task_type": "reasoning",
  "constraints": {
    "max_latency_ms": 5000,
    "max_cost": 0.01
  }
}

# 路由决策说明
POST /api/v1/routing/explain
{
  "request_id": "xxx"
}

# 路由统计
GET /api/v1/routing/stats?period=24h
```

## 9. 文件结构

```
code/core/model_hub/
├── __init__.py
├── registry.py              # 模型注册中心
├── model_provider.py        # 模型提供者抽象
├── model_metadata.py        # 模型元数据定义
├── router/
│   ├── __init__.py
│   ├── selector.py          # 智能选择器
│   ├── complexity.py        # 复杂度评估
│   └── scoring.py           # 评分算法
├── load_balancer/
│   ├── __init__.py
│   ├── balancer.py          # 负载均衡器
│   └── strategies.py        # 均衡策略
├── failover/
│   ├── __init__.py
│   ├── health_checker.py    # 健康检查
│   ├── circuit_breaker.py   # 熔断器
│   └── failover_manager.py  # 故障转移
├── cost/
│   ├── __init__.py
│   ├── calculator.py        # 成本计算
│   ├── budget.py            # 预算控制
│   └── optimizer.py         # 成本优化
├── adapters/
│   ├── __init__.py
│   ├── base.py              # 适配器基类
│   ├── openai_adapter.py    # OpenAI适配器
│   ├── anthropic_adapter.py # Anthropic适配器
│   ├── gemini_adapter.py    # Gemini适配器
│   └── local_adapter.py     # 本地模型适配器
└── config/
    ├── __init__.py
    ├── loader.py            # 配置加载
    └── models.yaml          # 默认模型配置
```

## 10. 验收标准

| 项目 | 验收标准 |
|------|----------|
| 模型注册 | 支持动态注册/注销模型，元数据完整 |
| 智能路由 | 根据任务类型自动选择最优模型 |
| 负载均衡 | 多实例间请求分配均匀 |
| 故障转移 | 模型故障后3秒内自动切换 |
| 成本控制 | 预算超限自动拦截 |
| 性能 | 路由决策耗时 < 10ms |
