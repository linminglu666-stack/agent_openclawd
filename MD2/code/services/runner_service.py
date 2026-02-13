from __future__ import annotations

from typing import Any, Dict

import hashlib

from core.central_brain import Coordinator
from core.central_brain import RouteModule
from core.kernel import Kernel
from core.memory_hub import MemoryHub
from core.eval_gate import EvalGateModule
from core.runtime import build_runtime_container
from core.skills.loader import SkillsLoader
from core.reasoning import ReasoningOrchestrator
from protocols.messages import TaskRequest
from services.service_base import ServiceBase, ServiceConfig
from utils.serializer import Serializer


class RunnerService(ServiceBase):
    def __init__(self):
        super().__init__(ServiceConfig(name="runner", tick_interval_sec=1.0))
        self._rt = build_runtime_container()
        self._coordinator = Coordinator()
        self._router_module = RouteModule()
        self._kernel = Kernel()
        self._memory_hub = MemoryHub()
        self._eval_gate = EvalGateModule()
        self._reasoning = ReasoningOrchestrator()
        self._skills_loader = SkillsLoader()
        self._loaded_skills = []

    async def initialize(self) -> bool:
        ok = await super().initialize()
        if not ok:
            return False
        self._rt.paths.ensure()

        # Load Skills
        try:
            self._loaded_skills = self._skills_loader.load()
            self._logger.info("skills_loaded", count=len(self._loaded_skills), skills=[s.name for s in self._loaded_skills])
        except Exception as e:
            self._logger.error("skills_load_failed", error=str(e))
            # Continue without skills? Or fail? 
            # For resilience, let's continue but warn.
        
        await self._coordinator.initialize({})
        await self._router_module.initialize({})
        await self._kernel.initialize({})
        await self._memory_hub.initialize({})
        await self._eval_gate.initialize({})
        await self._reasoning.initialize({})

        self._coordinator.register_module("router", self._router_module)
        self._coordinator.register_module("kernel", self._kernel)
        self._coordinator.register_module("memory_hub", self._memory_hub)
        self._coordinator.register_module("eval_gate", self._eval_gate)
        self._coordinator.register_module("reasoning", self._reasoning)
        return True

    async def shutdown(self) -> bool:
        await self._coordinator.shutdown()
        await super().shutdown()
        return True

    async def tick(self) -> None:
        self._rt.state_db.reclaim_expired_leases()
        
        skill_names = [s.name for s in self._loaded_skills]
        
        self._rt.state_db.write_agent_heartbeat(
            agent_id=self._config.name,
            status="idle",
            cpu=0.0,
            mem=0.0,
            queue_depth=0,
            skills=skill_names,
            metrics={},
        )
        work_item = self._rt.state_db.claim_work_item(agent_id=self._config.name, lease_ttl_sec=60)
        if not work_item:
            return

        task_id = str(work_item.task_id)
        idem_key = str(work_item.idempotency_key or f"task:{task_id}")

        try:
            self._rt.state_db.write_agent_heartbeat(
                agent_id=self._config.name,
                status="running",
                cpu=0.0,
                mem=0.0,
                queue_depth=1,
                skills=skill_names,
                metrics={},
            )
            marked = self._rt.state_db.mark_work_item_running(task_id=task_id, agent_id=self._config.name)
            if not marked:
                self._rt.wal.append("runner_mark_running_failed", {"task_id": task_id})
                self._write_audit(task_id=task_id, ok=False, trace_id=self._trace_id_from_work_item(work_item.payload), result={"task_id": task_id, "error": "mark_running_failed"})
                self._rt.state_db.ack_work_item(task_id=task_id, agent_id=self._config.name, ok=False)
                return
            if self._rt.idempotency.has(idem_key):
                self._rt.wal.append("runner_skip_idempotent", {"task_id": task_id, "idempotency_key": idem_key})
                self._write_audit(task_id=task_id, ok=True, trace_id=self._trace_id_from_work_item(work_item.payload), result={"skipped": "idempotent"})
                self._rt.state_db.ack_work_item(task_id=task_id, agent_id=self._config.name, ok=True)
                return

            payload = dict(work_item.payload or {})
            req = TaskRequest(
                task_id=task_id,
                task_type=str(payload.get("task_type") or "default"),
                task_data=dict(payload.get("task_data") or {}),
                context=dict(payload.get("context") or {}),
            )
            result = await self._coordinator.process_task(req)
            result_payload = getattr(result, "payload", None) or {}
            self._rt.idempotency.put(idem_key, {"task_id": task_id, "result": result_payload})
            self._rt.wal.append("runner_task_done", {"task_id": task_id, "idempotency_key": idem_key})
            trace_id = self._trace_id_from_work_item(work_item.payload)
            self._write_evidence(trace_id=trace_id, evidence_type="work_item_result", content={"task_id": task_id, "result": result_payload})
            self._write_audit(task_id=task_id, ok=True, trace_id=trace_id, result={"task_id": task_id})
            self._rt.state_db.ack_work_item(task_id=task_id, agent_id=self._config.name, ok=True)
        except Exception as e:
            self._rt.wal.append("runner_task_error", {"task_id": task_id, "error": str(e)})
            trace_id = self._trace_id_from_work_item(work_item.payload)
            self._write_evidence(trace_id=trace_id, evidence_type="work_item_error", content={"task_id": task_id, "error": str(e)})
            self._write_audit(task_id=task_id, ok=False, trace_id=trace_id, result={"task_id": task_id, "error": str(e)})
            self._rt.state_db.ack_work_item(task_id=task_id, agent_id=self._config.name, ok=False)

    async def health(self) -> Dict[str, Any]:
        return await self._coordinator.health_check()

    def _trace_id_from_work_item(self, payload: Dict[str, Any] | None) -> str:
        ctx = dict((payload or {}).get("context") or {})
        run_id = str(ctx.get("run_id") or "")
        if run_id:
            run = self._rt.state_db.get_run(run_id)
            if run:
                return str(run.trace_id)
        return str(ctx.get("trace_id") or "")

    def _write_evidence(self, trace_id: str, evidence_type: str, content: Dict[str, Any]) -> str:
        data = Serializer.to_json(content)
        digest = hashlib.sha256(data.encode("utf-8")).hexdigest()
        return self._rt.state_db.add_evidence(trace_id=trace_id or "unknown", evidence_type=evidence_type, content=content, content_hash=digest)

    def _write_audit(self, task_id: str, ok: bool, trace_id: str, result: Dict[str, Any]) -> str:
        return self._rt.state_db.add_audit_log(
            trace_id=trace_id or "unknown",
            actor=self._config.name,
            action="work_item.execute",
            resource=str(task_id),
            result={"ok": bool(ok), **(result or {})},
        )


def main() -> int:
    return RunnerService.main(RunnerService())


if __name__ == "__main__":
    raise SystemExit(main())
