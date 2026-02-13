from __future__ import annotations

from typing import Any, Dict, List, Optional

import asyncio

from core.central_brain import Router, RoutingStrategy, ModelRouter
from core.eval_gate import EvalGateModule
from core.memory_hub import MemoryHub, LayeredMemoryHub, MemoryLayerName
from core.observability import InMemoryEventBus, InMemoryTracer, InMemoryMetricsCollector, EvidenceStore
from core.governance import InMemoryAuthProvider, InMemoryAuthorizer, SimplePolicyEngine, InMemoryAuditSink, SimpleRedactor
from core.metacognition import SimpleMetacognitionLoop, FailurePatternLibrary, CognitiveDebtLedger
from core.reasoning import StrategyRouter, NeuroSymbolicKGReasoner


async def build_components() -> Dict[str, Any]:
    components: Dict[str, Any] = {}

    components["event_bus"] = InMemoryEventBus()
    components["tracer"] = InMemoryTracer()
    components["metrics"] = InMemoryMetricsCollector()
    components["evidence"] = EvidenceStore()

    components["auth"] = InMemoryAuthProvider()
    components["rbac"] = InMemoryAuthorizer()
    components["policy"] = SimplePolicyEngine(default_allow=False)
    components["audit"] = InMemoryAuditSink()
    components["redactor"] = SimpleRedactor()

    components["metacognition"] = SimpleMetacognitionLoop(
        failure_library=FailurePatternLibrary(),
        debt_ledger=CognitiveDebtLedger(),
    )

    components["router"] = Router(strategy=RoutingStrategy.ADAPTIVE)
    components["model_router"] = ModelRouter()

    components["eval_gate"] = EvalGateModule()

    components["memory_hub"] = MemoryHub()
    components["layered_memory_hub"] = LayeredMemoryHub()

    components["strategy_router"] = StrategyRouter()
    components["kg_reasoner"] = NeuroSymbolicKGReasoner()

    return components


async def demo_flow(task: Dict[str, Any]) -> Dict[str, Any]:
    c = await build_components()

    span_id = c["tracer"].start_span("demo_flow")
    trace_id = c["tracer"]._span_index.get(span_id)

    auth_result = await c["auth"].authenticate({"user_id": task.get("user_id", "demo"), "roles": ["user"]})
    token = auth_result["token"] if auth_result else ""
    user = (await c["auth"].validate_token(token) or {}).get("user", {})

    allowed = await c["rbac"].check_permission(user.get("user_id", ""), resource="task", action="execute")
    policy = await c["policy"].decide(subject=user, action="execute", resource={"type": "task"}, context={"trace_id": trace_id})

    if not allowed or not policy.get("allowed", False):
        await c["audit"].emit({"trace_id": trace_id, "outcome": "denied", "user": user})
        c["tracer"].end_span(span_id, status="denied")
        return {"ok": False, "error": "denied", "policy": policy}

    route_decision = c["model_router"].decide(task).to_dict()

    kg_context = {
        "triples": task.get("triples", []),
        "query": task.get("kg_query", {}),
        "enable_is_a_closure": True,
    }
    kg_result = await c["kg_reasoner"].reason(problem=str(task.get("prompt", "")), context=kg_context)

    evidence = await c["evidence"].add("kg_result", kg_result, trace_id=trace_id)
    c["tracer"].add_event(span_id, {"event": "evidence", "evidence_id": evidence.evidence_id})

    eval_result = await c["eval_gate"].evaluate(
        task={"task_id": task.get("task_id"), "task_type": task.get("task_type")},
        result={"confidence": kg_result.get("confidence", 0.0), "conclusion": kg_result, "evidence": [evidence.to_dict()]},
        context={"trace_id": trace_id},
    )

    await c["layered_memory_hub"].writeback(
        key=f"task:{task.get('task_id','unknown')}:result",
        value={"route": route_decision, "kg": kg_result, "eval": eval_result},
        context={"trace_id": trace_id, "confidence": eval_result.get("score", 0.0), "is_ephemeral": True},
    )

    await c["metacognition"].observe({"trace_id": trace_id, "confidence": eval_result.get("score", 0.0), "message": "demo"})

    c["tracer"].end_span(span_id, status="ok")
    return {"ok": True, "route": route_decision, "kg": kg_result, "eval": eval_result}


async def _main():
    task = {
        "task_id": "t1",
        "task_type": "reasoning",
        "prompt": "query",
        "user_id": "demo_user",
        "kg_query": {"subject": "A", "predicate": "is_a"},
        "triples": [{"s": "A", "p": "is_a", "o": "B"}, {"s": "B", "p": "is_a", "o": "C"}],
    }
    await demo_flow(task)
