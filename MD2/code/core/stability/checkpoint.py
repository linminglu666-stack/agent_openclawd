from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .context import WorkflowContext


class CheckpointTrigger(Enum):
    EXECUTION_START = "execution_start"
    STAGE_COMPLETE = "stage_complete"
    STAGE_START = "stage_start"
    PERIODIC = "periodic"
    CRITICAL_OPERATION = "critical_operation"
    MANUAL = "manual"
    FAILURE = "failure"


@dataclass
class Checkpoint:
    checkpoint_id: str
    execution_id: str
    context_snapshot: Dict[str, Any]
    trigger: CheckpointTrigger
    created_at: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    size_bytes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "execution_id": self.execution_id,
            "context_snapshot": self.context_snapshot,
            "trigger": self.trigger.value,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "size_bytes": self.size_bytes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Checkpoint:
        return cls(
            checkpoint_id=data["checkpoint_id"],
            execution_id=data["execution_id"],
            context_snapshot=data["context_snapshot"],
            trigger=CheckpointTrigger(data["trigger"]),
            created_at=data["created_at"],
            metadata=data.get("metadata", {}),
            size_bytes=data.get("size_bytes", 0),
        )


class CheckpointStorage:
    def __init__(self, base_path: str):
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)
    
    async def save(self, checkpoint: Checkpoint) -> str:
        execution_dir = self._base_path / checkpoint.execution_id
        execution_dir.mkdir(parents=True, exist_ok=True)
        
        checkpoints_dir = execution_dir / "checkpoints"
        checkpoints_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = checkpoints_dir / f"{checkpoint.checkpoint_id}.json"
        
        data = checkpoint.to_dict()
        content = json.dumps(data, indent=2, ensure_ascii=False)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._write_file,
            file_path,
            content,
        )
        
        return str(file_path)
    
    def _write_file(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")
    
    async def load(self, checkpoint_id: str, execution_id: str) -> Optional[Checkpoint]:
        file_path = (
            self._base_path / execution_id / "checkpoints" / f"{checkpoint_id}.json"
        )
        
        if not file_path.exists():
            return None
        
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(
            None,
            self._read_file,
            file_path,
        )
        
        data = json.loads(content)
        return Checkpoint.from_dict(data)
    
    def _read_file(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")
    
    async def delete(self, checkpoint_id: str, execution_id: str) -> bool:
        file_path = (
            self._base_path / execution_id / "checkpoints" / f"{checkpoint_id}.json"
        )
        
        if not file_path.exists():
            return False
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, file_path.unlink)
        return True
    
    async def list_checkpoints(self, execution_id: str) -> List[Checkpoint]:
        checkpoints_dir = self._base_path / execution_id / "checkpoints"
        
        if not checkpoints_dir.exists():
            return []
        
        checkpoints = []
        for file_path in checkpoints_dir.glob("*.json"):
            content = file_path.read_text(encoding="utf-8")
            data = json.loads(content)
            checkpoints.append(Checkpoint.from_dict(data))
        
        return sorted(checkpoints, key=lambda c: c.created_at)
    
    async def get_latest_checkpoint(
        self,
        execution_id: str,
    ) -> Optional[Checkpoint]:
        checkpoints = await self.list_checkpoints(execution_id)
        return checkpoints[-1] if checkpoints else None


class CheckpointManager:
    def __init__(
        self,
        storage_path: str,
        checkpoint_interval: int = 300,
        max_checkpoints: int = 20,
    ):
        self._storage = CheckpointStorage(storage_path)
        self._checkpoint_interval = checkpoint_interval
        self._max_checkpoints = max_checkpoints
        self._checkpoints: Dict[str, List[Checkpoint]] = {}
        self._periodic_task: Optional[asyncio.Task] = None
        self._active_contexts: Dict[str, WorkflowContext] = {}
    
    async def create_checkpoint(
        self,
        execution_id: str,
        context: WorkflowContext,
        trigger: CheckpointTrigger,
        metadata: Optional[Dict] = None,
    ) -> Checkpoint:
        checkpoint_id = self._generate_checkpoint_id(execution_id)
        
        snapshot = context.to_dict()
        snapshot_json = json.dumps(snapshot)
        
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            execution_id=execution_id,
            context_snapshot=snapshot,
            trigger=trigger,
            created_at=int(datetime.now(tz=timezone.utc).timestamp()),
            metadata=metadata or {},
            size_bytes=len(snapshot_json.encode()),
        )
        
        await self._storage.save(checkpoint)
        
        if execution_id not in self._checkpoints:
            self._checkpoints[execution_id] = []
        self._checkpoints[execution_id].append(checkpoint)
        
        await self._maybe_compact_checkpoints(execution_id)
        
        return checkpoint
    
    async def restore_from_checkpoint(
        self,
        execution_id: str,
        checkpoint_id: Optional[str] = None,
    ) -> WorkflowContext:
        if checkpoint_id:
            checkpoint = await self._storage.load(checkpoint_id, execution_id)
        else:
            checkpoint = await self._storage.get_latest_checkpoint(execution_id)
        
        if not checkpoint:
            raise CheckpointNotFoundError(
                f"No checkpoint found for execution: {execution_id}",
            )
        
        context = WorkflowContext.from_dict(checkpoint.context_snapshot)
        
        return context
    
    async def get_checkpoint(
        self,
        execution_id: str,
        checkpoint_id: str,
    ) -> Optional[Checkpoint]:
        return await self._storage.load(checkpoint_id, execution_id)
    
    async def list_checkpoints(
        self,
        execution_id: str,
    ) -> List[Checkpoint]:
        return await self._storage.list_checkpoints(execution_id)
    
    async def delete_checkpoint(
        self,
        execution_id: str,
        checkpoint_id: str,
    ) -> bool:
        result = await self._storage.delete(checkpoint_id, execution_id)
        
        if result and execution_id in self._checkpoints:
            self._checkpoints[execution_id] = [
                c for c in self._checkpoints[execution_id]
                if c.checkpoint_id != checkpoint_id
            ]
        
        return result
    
    def register_context(
        self,
        execution_id: str,
        context: WorkflowContext,
    ) -> None:
        self._active_contexts[execution_id] = context
    
    def unregister_context(self, execution_id: str) -> None:
        self._active_contexts.pop(execution_id, None)
    
    async def start_periodic_checkpoints(self) -> None:
        if self._periodic_task is not None:
            return
        
        self._periodic_task = asyncio.create_task(
            self._periodic_checkpoint_loop(),
        )
    
    async def stop_periodic_checkpoints(self) -> None:
        if self._periodic_task is not None:
            self._periodic_task.cancel()
            try:
                await self._periodic_task
            except asyncio.CancelledError:
                pass
            self._periodic_task = None
    
    async def _periodic_checkpoint_loop(self) -> None:
        while True:
            await asyncio.sleep(self._checkpoint_interval)
            
            for execution_id, context in list(self._active_contexts.items()):
                try:
                    await self.create_checkpoint(
                        execution_id=execution_id,
                        context=context,
                        trigger=CheckpointTrigger.PERIODIC,
                    )
                except Exception:
                    pass
    
    async def _maybe_compact_checkpoints(self, execution_id: str) -> None:
        checkpoints = self._checkpoints.get(execution_id, [])
        
        if len(checkpoints) <= self._max_checkpoints:
            return
        
        keep_count = self._max_checkpoints // 2
        to_remove = checkpoints[:-keep_count]
        
        for checkpoint in to_remove:
            if checkpoint.trigger != CheckpointTrigger.EXECUTION_START:
                await self._storage.delete(
                    checkpoint.checkpoint_id,
                    execution_id,
                )
        
        self._checkpoints[execution_id] = checkpoints[-keep_count:]
    
    def _generate_checkpoint_id(self, execution_id: str) -> str:
        timestamp = int(datetime.now(tz=timezone.utc).timestamp())
        return f"cp_{timestamp}_{uuid.uuid4().hex[:8]}"


class CheckpointNotFoundError(Exception):
    pass
