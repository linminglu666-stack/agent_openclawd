# Visual Tracing System - 完整设计文档

## 1. 系统概述

Visual Tracing System (可视化追踪系统) 是 OpenClaw-X 架构的核心可观测性组件，专注于：

- **决策过程可视化**：将 Agent 的推理过程 (CoT/ToT) 以决策树形式呈现
- **执行链路追踪**：以瀑布图形式展示任务执行的完整时间线
- **推理链可视化**：清晰展示 Thought-Action-Observation 的迭代过程
- **实时状态监控**：通过 WebSocket 推送实时执行状态

## 2. 核心设计思路

### 2.1 设计哲学

```
┌─────────────────────────────────────────────────────────────┐
│                    设计原则                                   │
├─────────────────────────────────────────────────────────────┤
│  1. 非侵入式采集 - 不影响原有业务逻辑                          │
│  2. 分层解耦    - 采集/存储/展示各层独立                       │
│  3. 可扩展性    - 支持多种推理模式 (CoT/ToT/ReAct)             │
│  4. 实时优先    - WebSocket 优先，REST 补充                   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据流转架构

```
Agent执行
    │
    ▼
┌─────────────────┐
│  TraceCollector │ ← 采集层：拦截关键执行节点
│  (Python SDK)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│   TraceStore    │ ←── │  WebSocketHub   │
│   (存储层)       │     │  (实时推送)      │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────────────────────────────┐
│              FastAPI Server             │
│         (RESTful + WebSocket API)        │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│            Web Frontend (Vue 3)          │
│  ┌─────────┬─────────┬─────────┬──────┐ │
│  │Timeline │Decision │Reasoning│ ToT  │ │
│  │ 瀑布图   │ Tree    │ Chain   │Explorer│ │
│  └─────────┴─────────┴─────────┴──────┘ │
└─────────────────────────────────────────┘
```

## 3. 数据模型详细设计

### 3.1 VisualTrace (追踪主实体)

```python
@dataclass
class VisualTrace:
    trace_id: str                    # 唯一标识
    spans: List[VisualSpan]          # 执行跨度列表
    span_map: Dict[str, VisualSpan]  # ID -> Span 映射
    root_span: Optional[VisualSpan]  # 根节点
    decision_tree: Optional[VisualDecisionTree]  # 决策树
    reasoning_chain: Optional[ReasoningChain]    # 推理链
    start_time: float
    end_time: Optional[float]
    
    @property
    def total_duration_ms(self) -> int:
        """总耗时(毫秒)"""
        
    def get_waterfall_data(self) -> Dict:
        """生成瀑布图数据"""
        
    def to_dict(self) -> Dict:
        """序列化为字典"""
```

### 3.2 VisualSpan (执行跨度)

```python
class SpanType(Enum):
    THOUGHT = "thought"       # 思考节点
    ACTION = "action"         # 动作执行
    TOOL = "tool"            # 工具调用
    DECISION = "decision"     # 决策点
    SYNTHESIZE = "synthesize" # 综合输出

class SpanStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class VisualSpan:
    span_id: str
    trace_id: str
    parent_id: Optional[str]
    name: str
    span_type: SpanType
    status: SpanStatus
    start_time: float
    end_time: Optional[float]
    depth: int                    # 嵌套深度
    metadata: Dict[str, Any]      # 扩展元数据
```

### 3.3 VisualDecisionTree (决策树)

```python
@dataclass
class DecisionNode:
    id: str
    content: str                  # 节点内容
    score: float                  # 评分 (0-1)
    reasoning: str                # 推理依据
    parent: Optional['DecisionNode']
    children: List['DecisionNode']
    selected: bool                # 是否被选中执行
    depth: int

@dataclass  
class VisualDecisionTree:
    tree_id: str
    trace_id: str
    root: Optional[DecisionNode]
    nodes: List[DecisionNode]
    selected_path: List[str]      # 选中路径节点ID列表
    
    def get_selected_path(self) -> List[DecisionNode]:
        """获取选中的执行路径"""
        
    def serialize(self) -> Dict:
        """序列化用于前端渲染"""
```

### 3.4 ReasoningChain (推理链)

```python
@dataclass
class ReasoningStep:
    step_id: str
    action: str                   # thought/action/observation/synthesize
    name: str                     # 步骤名称
    prompt: str                   # 输入提示
    response: str                 # 输出结果
    duration_ms: int
    confidence: float             # 置信度
    tokens: int                   # Token消耗

@dataclass
class ReasoningChain:
    chain_id: str
    trace_id: str
    chain_type: str               # react/cot/tot
    steps: List[ReasoningStep]
    model: str
    temperature: float
    final_answer: Optional[str]
    final_confidence: float
    
    def add_step(...) -> ReasoningStep:
        """添加推理步骤"""
        
    def to_dict(self) -> Dict:
        """序列化"""
```

## 4. API 接口设计

### 4.1 RESTful API

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/traces` | 创建新追踪 |
| GET | `/api/v1/traces` | 列出追踪 (分页) |
| GET | `/api/v1/traces/{trace_id}` | 获取追踪详情 |
| GET | `/api/v1/traces/{trace_id}/waterfall` | 获取瀑布图数据 |
| GET | `/api/v1/traces/{trace_id}/decision-tree` | 获取决策树数据 |
| GET | `/api/v1/traces/{trace_id}/reasoning-chain` | 获取推理链数据 |
| POST | `/api/v1/traces/{trace_id}/spans` | 创建Span |
| PUT | `/api/v1/traces/{trace_id}/spans/{span_id}` | 结束Span |
| POST | `/api/v1/traces/{trace_id}/decision-tree` | 创建决策树 |
| POST | `/api/v1/traces/{trace_id}/reasoning-chain` | 创建推理链 |

### 4.2 WebSocket API

```
ws://host/api/v1/traces/{trace_id}/stream

消息类型:
- connected: 连接确认
- trace_data: 完整追踪数据
- span_started: Span开始事件
- span_ended: Span结束事件
- tree_updated: 决策树更新
- chain_step: 推理步骤添加
- pong: 心跳响应
```

## 5. 前端组件架构

### 5.1 组件层次

```
Tracing.js (主视图)
├── Header (追踪选择器 + 视图切换)
├── Content Area
│   ├── Timeline.js (瀑布图)
│   ├── DecisionTree.js (决策树 D3)
│   ├── ReasoningChain.js (推理链)
│   └── ToTExplorer.js (思维树探索)
└── Footer (状态栏 + 操作按钮)
```

### 5.2 视图模式

| 模式 | 组件 | 用途 |
|------|------|------|
| Timeline | Timeline.js | 展示执行时间线、Span嵌套关系 |
| Decision Tree | DecisionTree.js | 展示决策分支、选中路径 |
| Reasoning Chain | ReasoningChain.js | 展示T-A-O迭代过程 |
| ToT Explorer | ToTExplorer.js | 多路径思维探索 |

### 5.3 数据流

```
Store (Vuex/Reactive)
    │
    ├── traces: List[Trace]      // 追踪列表
    ├── currentTrace: Trace      // 当前追踪
    └── wsConnection: WebSocket  // WebSocket连接
         │
         ▼
    Tracing.js
         │
         ├── treeData → DecisionTree.js
         ├── waterfallData → Timeline.js  
         └── chainData → ReasoningChain.js
```

## 6. 实现要点

### 6.1 采集层实现要点

```python
class TraceCollector:
    _instance = None
    _traces: Dict[str, VisualTrace] = {}
    _ws_clients: List[WebSocket] = []
    
    def create_trace(self, trace_id: Optional[str] = None) -> VisualTrace:
        """创建追踪，自动注册到全局存储"""
        
    def get_trace(self, trace_id: str) -> Optional[VisualTrace]:
        """获取追踪"""
        
    async def broadcast(self, message: Dict):
        """广播消息到所有WebSocket客户端"""
```

### 6.2 前端D3渲染要点

```javascript
// 决策树渲染核心逻辑
initD3() {
    this.svg = d3.select(this.$refs.svg);
    this.g = this.svg.append("g");
    
    this.zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on("zoom", (event) => {
            this.g.attr("transform", event.transform);
        });
    this.svg.call(this.zoom);
}

updateChart() {
    // 层次化布局
    const root = d3.stratify()
        .id(d => d.id)
        .parentId(d => this.findParent(d))(this.data.nodes);
    
    const treeLayout = d3.tree().nodeSize([150, 100]);
    treeLayout(root);
    
    // 渲染连线和节点...
}
```

### 6.3 实时推送机制

```python
@app.websocket("/api/v1/traces/{trace_id}/stream")
async def trace_stream(websocket: WebSocket, trace_id: str):
    await websocket.accept()
    collector.register_ws_client(websocket)
    
    try:
        # 发送初始数据
        trace = collector.get_trace(trace_id)
        if trace:
            await websocket.send_json({
                "type": "trace_data",
                "data": trace.to_dict()
            })
        
        # 保持连接，处理客户端消息
        while True:
            data = await websocket.receive_text()
            # 处理ping/pong等
    finally:
        collector.unregister_ws_client(websocket)
```

## 7. 配置项

| 配置项 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `sampling_rate` | float | 1.0 | 采样率 (0.0-1.0) |
| `max_depth` | int | 50 | 最大追踪深度 |
| `retention_days` | int | 7 | 数据保留天数 |
| `batch_size` | int | 100 | 批量上报大小 |
| `ws_heartbeat` | int | 30000 | WebSocket心跳间隔(ms) |

## 8. 扩展性设计

### 8.1 支持新的推理模式

系统通过 `SpanType` 枚举和 `metadata` 字段支持扩展：

```python
# 添加新的Span类型
class SpanType(Enum):
    THOUGHT = "thought"
    ACTION = "action"
    # 扩展: MCTS节点
    MCTS_NODE = "mcts_node"
    # 扩展: 约束求解
    CONSTRAINT = "constraint"
```

### 8.2 存储后端切换

通过抽象 `TraceStore` 接口支持多种存储：

```python
class TraceStore(ABC):
    @abstractmethod
    def save(self, trace: VisualTrace): pass
    
    @abstractmethod
    def get(self, trace_id: str) -> Optional[VisualTrace]: pass

class MemoryTraceStore(TraceStore): ...
class ClickHouseTraceStore(TraceStore): ...
class ElasticsearchTraceStore(TraceStore): ...
```

## 9. 文件结构

```
MD2/
├── VISUAL_TRACING_DESIGN.md        # 本设计文档
├── code/
│   ├── visual_tracing_core.py      # 核心数据模型 + 采集器
│   └── visual_tracing_api.py       # FastAPI服务
├── web/
│   ├── js/components/modules/
│   │   ├── Tracing.js              # 主视图
│   │   └── tracing/
│   │       ├── DecisionTree.js     # 决策树组件
│   │       ├── Timeline.js         # 时间线组件
│   │       ├── ReasoningChain.js   # 推理链组件
│   │       └── ToTExplorer.js      # ToT探索组件
│   └── css/
│       └── tracing.css             # 追踪专用样式
└── docs/
    └── API_INTERFACE.md            # API接口文档
```
