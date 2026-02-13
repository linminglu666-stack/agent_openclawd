"""
OpenClaw-X 可视化追踪系统 - 核心数据结构
整合版本：统一Span追踪、决策树、推理链的数据模型
"""

import uuid
import time
import json
import asyncio
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field, asdict
from collections import defaultdict


class SpanType(Enum):
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    TOOL = "tool"
    DECISION = "decision"
    SYNTHESIZE = "synthesize"
    MEMORY = "memory"


class SpanStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ReasoningStrategy(Enum):
    COT = "cot"
    TOT = "tot"
    REFLEXION = "reflexion"
    SELF_CONSISTENCY = "self_consistency"
    REACT = "react"
    TRUTH_GATE = "truth_gate"


@dataclass
class VisualSpan:
    """可视化Span - 追踪基本单元"""
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = ""
    parent_id: Optional[str] = None
    name: str = ""
    span_type: SpanType = SpanType.THOUGHT
    status: SpanStatus = SpanStatus.PENDING
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    depth: int = 0

    def end(self, status: SpanStatus = SpanStatus.COMPLETED):
        self.end_time = time.time()
        self.status = status

    def add_event(self, name: str, payload: Dict[str, Any] = None):
        self.events.append({
            "event_id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "name": name,
            "payload": payload or {}
        })

    @property
    def duration_ms(self) -> int:
        if self.end_time:
            return int((self.end_time - self.start_time) * 1000)
        return 0

    def to_dict(self) -> Dict:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "type": self.span_type.value,
            "status": self.status.value,
            "start_ms": int(self.start_time * 1000),
            "duration_ms": self.duration_ms,
            "depth": self.depth,
            "metadata": self.metadata,
            "events": self.events
        }


@dataclass
class DecisionNode:
    """决策树节点 - 用于ToT等策略可视化"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    label: str = ""
    depth: int = 0
    score: float = 0.0
    children: List['DecisionNode'] = field(default_factory=list)
    selected: bool = False
    reasoning: str = ""
    parent_id: Optional[str] = None

    def add_child(self, content: str, score: float = 0.0, reasoning: str = "") -> 'DecisionNode':
        child = DecisionNode(
            content=content,
            label=content[:30] + "..." if len(content) > 30 else content,
            depth=self.depth + 1,
            score=score,
            reasoning=reasoning,
            parent_id=self.id
        )
        self.children.append(child)
        return child


class VisualDecisionTree:
    """可视化决策树"""

    def __init__(self, trace_id: str = ""):
        self.trace_id = trace_id
        self.tree_id = str(uuid.uuid4())
        self.root: Optional[DecisionNode] = None

    def add_node(
        self, 
        parent: Optional[DecisionNode], 
        content: str, 
        score: float = 0.0,
        reasoning: str = ""
    ) -> DecisionNode:
        if parent:
            return parent.add_child(content, score, reasoning)
        else:
            self.root = DecisionNode(
                content=content,
                label=content[:30] + "..." if len(content) > 30 else content,
                depth=0,
                score=score,
                reasoning=reasoning
            )
            return self.root

    def get_selected_path(self) -> List[str]:
        path = []
        def traverse(node: DecisionNode):
            if node.selected:
                path.append(node.id)
            for child in node.children:
                if child.selected:
                    traverse(child)
                    break
        if self.root:
            traverse(self.root)
        return path

    def serialize(self) -> Dict:
        nodes = []
        edges = []
        
        def traverse(node: DecisionNode):
            nodes.append({
                "id": node.id,
                "label": node.label,
                "content": node.content,
                "depth": node.depth,
                "confidence": node.score,
                "type": "decision" if node.selected else "thought",
                "is_selected": node.selected,
                "reasoning": node.reasoning
            })
            for child in node.children:
                edges.append({
                    "from": node.id,
                    "to": child.id,
                    "selected": child.selected
                })
                traverse(child)
        
        if self.root:
            traverse(self.root)
            
        return {
            "tree_id": self.tree_id,
            "trace_id": self.trace_id,
            "nodes": nodes,
            "edges": edges,
            "selected_path": self.get_selected_path()
        }


@dataclass
class ReasoningStep:
    """推理步骤"""
    step_id: int = 0
    action: str = ""
    name: str = ""
    prompt: str = ""
    response: str = ""
    duration_ms: int = 0
    confidence: float = 0.0
    tokens_used: int = 0
    span_id: str = ""


@dataclass  
class ReasoningChain:
    """推理链 - 完整推理过程"""
    chain_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = ""
    chain_type: str = "react"
    steps: List[ReasoningStep] = field(default_factory=list)
    total_duration_ms: int = 0
    model: str = "gpt-4"
    temperature: float = 0.7
    total_tokens: int = 0
    final_answer: str = ""
    final_confidence: float = 0.0

    def add_step(
        self, 
        action: str, 
        name: str,
        prompt: str, 
        response: str,
        duration_ms: int = 0,
        confidence: float = 0.0,
        tokens: int = 0
    ) -> ReasoningStep:
        step = ReasoningStep(
            step_id=len(self.steps) + 1,
            action=action,
            name=name,
            prompt=prompt,
            response=response,
            duration_ms=duration_ms,
            confidence=confidence,
            tokens_used=tokens
        )
        self.steps.append(step)
        self.total_duration_ms += duration_ms
        self.total_tokens += tokens
        return step

    def to_dict(self) -> Dict:
        return {
            "chain_id": self.chain_id,
            "trace_id": self.trace_id,
            "chain_type": self.chain_type,
            "steps": [asdict(s) for s in self.steps],
            "total_duration_ms": self.total_duration_ms,
            "model_info": {
                "model": self.model,
                "temperature": self.temperature,
                "total_tokens": self.total_tokens
            },
            "final_answer": self.final_answer,
            "final_confidence": self.final_confidence
        }


class VisualTrace:
    """可视化追踪 - 完整追踪数据"""

    def __init__(self, trace_id: Optional[str] = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.spans: List[VisualSpan] = []
        self.span_map: Dict[str, VisualSpan] = {}
        self.root_span: Optional[VisualSpan] = None
        self.decision_tree: Optional[VisualDecisionTree] = None
        self.reasoning_chain: Optional[ReasoningChain] = None
        self.start_time = time.time()
        self.end_time: Optional[float] = None

    def start_span(
        self, 
        name: str, 
        span_type: SpanType = SpanType.THOUGHT,
        parent_id: Optional[str] = None
    ) -> VisualSpan:
        depth = 0
        if parent_id and parent_id in self.span_map:
            depth = self.span_map[parent_id].depth + 1
            
        span = VisualSpan(
            trace_id=self.trace_id,
            parent_id=parent_id,
            name=name,
            span_type=span_type,
            status=SpanStatus.RUNNING,
            depth=depth
        )
        self.spans.append(span)
        self.span_map[span.span_id] = span
        
        if not self.root_span:
            self.root_span = span
        return span

    def end_span(self, span: VisualSpan, status: SpanStatus = SpanStatus.COMPLETED):
        span.end(status)
        if not self.end_time or span.end_time > self.end_time:
            self.end_time = span.end_time

    def to_dict(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "start_ms": int(self.start_time * 1000),
            "total_duration_ms": self.total_duration_ms,
            "spans": [s.to_dict() for s in self.spans],
            "decision_tree": self.decision_tree.serialize() if self.decision_tree else None,
            "reasoning_chain": self.reasoning_chain.to_dict() if self.reasoning_chain else None
        }

    @property
    def total_duration_ms(self) -> int:
        if self.end_time:
            return int((self.end_time - self.start_time) * 1000)
        return sum(s.duration_ms for s in self.spans)

    def get_waterfall_data(self) -> Dict:
        """生成瀑布图数据"""
        if not self.spans:
            return {"spans": [], "total_duration_ms": 0}
        
        min_start = min(s.start_time for s in self.spans)
        
        return {
            "trace_id": self.trace_id,
            "total_duration_ms": self.total_duration_ms,
            "spans": [{
                "id": s.span_id,
                "name": s.name,
                "type": s.span_type.value,
                "start_ms": int((s.start_time - min_start) * 1000),
                "duration_ms": s.duration_ms,
                "depth": s.depth,
                "parent_id": s.parent_id,
                "status": s.status.value,
                "confidence": s.metadata.get("confidence", 0.0)
            } for s in self.spans]
        }


class TraceCollector:
    """追踪收集器 - 支持实时推送"""

    def __init__(self):
        self.traces: Dict[str, VisualTrace] = {}
        self.ws_clients: set = set()
        self._event_handlers: List[Callable] = []

    def create_trace(self, trace_id: Optional[str] = None) -> VisualTrace:
        trace = VisualTrace(trace_id)
        self.traces[trace.trace_id] = trace
        return trace

    def get_trace(self, trace_id: str) -> Optional[VisualTrace]:
        return self.traces.get(trace_id)

    def list_traces(self, limit: int = 20, status: Optional[str] = None) -> List[Dict]:
        results = []
        for trace in list(self.traces.values())[-limit:]:
            results.append({
                "trace_id": trace.trace_id,
                "span_count": len(trace.spans),
                "root_name": trace.root_span.name if trace.root_span else "Unknown",
                "total_duration_ms": trace.total_duration_ms,
                "status": "completed" if trace.end_time else "running"
            })
        return results

    async def broadcast_event(self, event_type: str, data: Dict):
        message = json.dumps({"type": event_type, "data": data})
        dead_clients = set()
        for client in self.ws_clients:
            try:
                await client.send(message)
            except Exception:
                dead_clients.add(client)
        self.ws_clients -= dead_clients

    def register_ws_client(self, websocket):
        self.ws_clients.add(websocket)

    def unregister_ws_client(self, websocket):
        self.ws_clients.discard(websocket)

    def on_event(self, handler: Callable):
        self._event_handlers.append(handler)
