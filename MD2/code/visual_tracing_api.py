"""
OpenClaw-X 可视化追踪系统 - FastAPI后端服务
"""

import time
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

from visual_tracing_core import (
    VisualTrace, VisualSpan, VisualDecisionTree, VisualDecisionTree as DecisionTree,
    ReasoningChain, ReasoningStep, SpanType, SpanStatus, TraceCollector
)

app = FastAPI(
    title="OpenClaw-X Visual Tracing API",
    description="可视化追踪系统API - 支持决策树、时间线、推理链可视化",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

collector = TraceCollector()


class TraceCreateRequest(BaseModel):
    trace_id: Optional[str] = None


class SpanCreateRequest(BaseModel):
    name: str
    span_type: str = "thought"
    parent_id: Optional[str] = None


class SpanEndRequest(BaseModel):
    status: str = "completed"


class DecisionTreeCreateRequest(BaseModel):
    trace_id: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    selected_path: List[str]


class ReasoningChainCreateRequest(BaseModel):
    trace_id: str
    chain_type: str = "react"
    model: str = "gpt-4"
    temperature: float = 0.7


class ReasoningStepRequest(BaseModel):
    action: str
    name: str
    prompt: str
    response: str
    duration_ms: int = 0
    confidence: float = 0.0
    tokens: int = 0


@app.get("/")
async def root():
    return {
        "message": "OpenClaw-X Visual Tracing API",
        "version": "1.0.0",
        "endpoints": [
            "/api/v1/traces",
            "/api/v1/traces/{trace_id}",
            "/api/v1/traces/{trace_id}/waterfall",
            "/api/v1/traces/{trace_id}/decision-tree",
            "/api/v1/traces/{trace_id}/reasoning-chain"
        ]
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/api/v1/traces")
async def create_trace(request: TraceCreateRequest = None):
    """创建新的追踪"""
    trace_id = request.trace_id if request else None
    trace = collector.create_trace(trace_id)
    return {
        "trace_id": trace.trace_id,
        "created_at": datetime.now().isoformat()
    }


@app.get("/api/v1/traces")
async def list_traces(
    limit: int = Query(default=20, le=100),
    status: Optional[str] = Query(default=None)
):
    """获取追踪列表"""
    traces = collector.list_traces(limit=limit, status=status)
    return {
        "traces": traces,
        "total": len(traces),
        "limit": limit
    }


@app.get("/api/v1/traces/{trace_id}")
async def get_trace(trace_id: str):
    """获取追踪详情"""
    trace = collector.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    return {
        "trace_id": trace.trace_id,
        "status": "completed" if trace.end_time else "running",
        "total_duration_ms": trace.total_duration_ms,
        "span_count": len(trace.spans),
        "root_name": trace.root_span.name if trace.root_span else None,
        "has_decision_tree": trace.decision_tree is not None,
        "has_reasoning_chain": trace.reasoning_chain is not None,
        "created_at": datetime.fromtimestamp(trace.start_time).isoformat()
    }


@app.get("/api/v1/traces/{trace_id}/waterfall")
async def get_waterfall(trace_id: str):
    """获取瀑布图数据"""
    trace = collector.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    return trace.get_waterfall_data()


@app.get("/api/v1/traces/{trace_id}/decision-tree")
async def get_decision_tree(trace_id: str):
    """获取决策树数据"""
    trace = collector.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    if trace.decision_tree:
        return trace.decision_tree.serialize()
    
    return {
        "tree_id": None,
        "trace_id": trace_id,
        "nodes": [],
        "edges": [],
        "selected_path": [],
        "message": "No decision tree data available"
    }


@app.get("/api/v1/traces/{trace_id}/reasoning-chain")
async def get_reasoning_chain(trace_id: str):
    """获取推理链数据"""
    trace = collector.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    if trace.reasoning_chain:
        return trace.reasoning_chain.to_dict()
    
    return {
        "chain_id": None,
        "trace_id": trace_id,
        "chain_type": "unknown",
        "steps": [],
        "total_duration_ms": 0,
        "model_info": {"model": "unknown", "total_tokens": 0},
        "message": "No reasoning chain data available"
    }


@app.post("/api/v1/traces/{trace_id}/spans")
async def create_span(trace_id: str, request: SpanCreateRequest):
    """创建Span"""
    trace = collector.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    try:
        span_type = SpanType(request.span_type)
    except ValueError:
        span_type = SpanType.THOUGHT
    
    span = trace.start_span(request.name, span_type, request.parent_id)
    return {
        "span_id": span.span_id,
        "trace_id": trace_id,
        "status": "started"
    }


@app.put("/api/v1/traces/{trace_id}/spans/{span_id}")
async def end_span(trace_id: str, span_id: str, request: SpanEndRequest):
    """结束Span"""
    trace = collector.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    if span_id not in trace.span_map:
        raise HTTPException(status_code=404, detail="Span not found")
    
    span = trace.span_map[span_id]
    try:
        status = SpanStatus(request.status)
    except ValueError:
        status = SpanStatus.COMPLETED
    
    trace.end_span(span, status)
    return {
        "span_id": span_id,
        "status": "ended",
        "duration_ms": span.duration_ms
    }


@app.post("/api/v1/traces/{trace_id}/decision-tree")
async def create_decision_tree(trace_id: str, request: DecisionTreeCreateRequest):
    """创建决策树"""
    trace = collector.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    tree = VisualDecisionTree(trace_id)
    node_map = {}
    
    for node_data in request.nodes:
        parent_id = None
        for edge in request.edges:
            if edge["to"] == node_data["id"]:
                parent_id = edge["from"]
                break
        
        parent = node_map.get(parent_id) if parent_id else None
        node = tree.add_node(
            parent,
            node_data.get("content", node_data.get("label", "")),
            node_data.get("score", node_data.get("confidence", 0.0)),
            node_data.get("reasoning", "")
        )
        node.id = node_data["id"]
        if node_data["id"] in request.selected_path:
            node.selected = True
        node_map[node_data["id"]] = node
    
    trace.decision_tree = tree
    return tree.serialize()


@app.post("/api/v1/traces/{trace_id}/reasoning-chain")
async def create_reasoning_chain(trace_id: str, request: ReasoningChainCreateRequest):
    """创建推理链"""
    trace = collector.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    chain = ReasoningChain(
        trace_id=trace_id,
        chain_type=request.chain_type,
        model=request.model,
        temperature=request.temperature
    )
    trace.reasoning_chain = chain
    
    return {"chain_id": chain.chain_id, "status": "created"}


@app.post("/api/v1/traces/{trace_id}/reasoning-chain/steps")
async def add_reasoning_step(trace_id: str, request: ReasoningStepRequest):
    """添加推理步骤"""
    trace = collector.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    if not trace.reasoning_chain:
        trace.reasoning_chain = ReasoningChain(trace_id=trace_id)
    
    step = trace.reasoning_chain.add_step(
        action=request.action,
        name=request.name,
        prompt=request.prompt,
        response=request.response,
        duration_ms=request.duration_ms,
        confidence=request.confidence,
        tokens=request.tokens
    )
    
    return {
        "step_id": step.step_id,
        "status": "added"
    }


@app.websocket("/api/v1/traces/{trace_id}/stream")
async def trace_stream(websocket: WebSocket, trace_id: str):
    """WebSocket实时追踪流"""
    await websocket.accept()
    collector.register_ws_client(websocket)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "trace_id": trace_id,
            "timestamp": datetime.now().isoformat()
        })
        
        trace = collector.get_trace(trace_id)
        if trace:
            await websocket.send_json({
                "type": "trace_data",
                "data": trace.to_dict()
            })
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif message.get("type") == "get_trace":
                trace = collector.get_trace(trace_id)
                if trace:
                    await websocket.send_json({
                        "type": "trace_data",
                        "data": trace.to_dict()
                    })
                    
    except WebSocketDisconnect:
        pass
    finally:
        collector.unregister_ws_client(websocket)


def generate_demo_trace():
    """生成演示数据"""
    trace = collector.create_trace("demo-trace-001")
    
    s1 = trace.start_span("用户请求分析", SpanType.THOUGHT)
    time.sleep(0.1)
    
    s2 = trace.start_span("意图识别", SpanType.DECISION, s1.span_id)
    time.sleep(0.15)
    trace.end_span(s2)
    
    s3 = trace.start_span("知识检索", SpanType.TOOL, s1.span_id)
    time.sleep(0.2)
    trace.end_span(s3)
    
    s4 = trace.start_span("答案生成", SpanType.SYNTHESIZE, s1.span_id)
    time.sleep(0.1)
    trace.end_span(s4)
    
    trace.end_span(s1)
    
    tree = VisualDecisionTree(trace.trace_id)
    root = tree.add_node(None, "用户查询: 如何优化数据库?", 1.0)
    root.selected = True
    c1 = tree.add_node(root, "直接回答", 0.5)
    c2 = tree.add_node(root, "分解问题", 0.9)
    c2.selected = True
    c2_1 = tree.add_node(c2, "分析索引", 0.85)
    c2_1.selected = True
    c2_2 = tree.add_node(c2, "优化查询", 0.8)
    trace.decision_tree = tree
    
    chain = ReasoningChain(
        trace_id=trace.trace_id,
        chain_type="react",
        model="gpt-4"
    )
    chain.add_step("thought", "分析问题", "理解用户需求", "需要优化数据库", 100, 0.9, 50)
    chain.add_step("action", "检索知识", "查询优化策略", "找到5条相关文档", 200, 0.85, 100)
    chain.add_step("synthesize", "生成答案", "综合分析结果", "提供3个优化建议", 150, 0.9, 80)
    chain.final_answer = "建议添加索引、优化查询语句、调整配置"
    chain.final_confidence = 0.88
    trace.reasoning_chain = chain
    
    return trace


generate_demo_trace()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
