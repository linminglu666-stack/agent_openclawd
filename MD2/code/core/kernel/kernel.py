from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from protocols.interfaces import IModule, IToolAdapter, IMemoryAdapter, IContextBus, ExecutionResult
from utils.logger import get_logger


@dataclass
class KernelConfig:
    seed: Optional[int] = None
    work_dir: str = "/tmp/openclaw"
    max_command_timeout: int = 300
    enable_sandbox: bool = True
    allowed_commands: List[str] = field(default_factory=list)


class ToolAdapter(IToolAdapter):
    def __init__(self, config: Optional[KernelConfig] = None):
        self._config = config or KernelConfig()
        self._logger = get_logger("kernel.tool_adapter")

    async def exec_command(self, command: str, opts: Dict[str, Any]) -> ExecutionResult:
        start = time.time()
        trace_id = opts.get("trace_id") or self._generate_trace_id()
        timeout = min(opts.get("timeout", 60), self._config.max_command_timeout)
        cwd = opts.get("cwd", self._config.work_dir)

        if self._config.enable_sandbox:
            blocked = self._check_blocked(command)
            if blocked:
                self._logger.warn("Command blocked", command=command, trace_id=trace_id)
                return ExecutionResult(success=False, error=f"Command blocked: {blocked}", trace_id=trace_id)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            latency_ms = int((time.time() - start) * 1000)
            self._logger.info("Command executed", command=command, code=result.returncode, latency_ms=latency_ms, trace_id=trace_id)
            return ExecutionResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                trace_id=trace_id,
                latency_ms=latency_ms,
                metadata={"return_code": result.returncode},
            )
        except subprocess.TimeoutExpired:
            latency_ms = int((time.time() - start) * 1000)
            self._logger.error("Command timeout", command=command, timeout=timeout, trace_id=trace_id)
            return ExecutionResult(success=False, error=f"Timeout after {timeout}s", trace_id=trace_id, latency_ms=latency_ms)
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            self._logger.error("Command failed", command=command, error=str(e), trace_id=trace_id)
            return ExecutionResult(success=False, error=str(e), trace_id=trace_id, latency_ms=latency_ms)

    async def read_file(self, path: str) -> ExecutionResult:
        start = time.time()
        trace_id = self._generate_trace_id()
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            latency_ms = int((time.time() - start) * 1000)
            return ExecutionResult(success=True, output=content, trace_id=trace_id, latency_ms=latency_ms)
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            return ExecutionResult(success=False, error=str(e), trace_id=trace_id, latency_ms=latency_ms)

    async def write_file(self, path: str, content: str) -> ExecutionResult:
        start = time.time()
        trace_id = self._generate_trace_id()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            latency_ms = int((time.time() - start) * 1000)
            return ExecutionResult(success=True, output=path, trace_id=trace_id, latency_ms=latency_ms)
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            return ExecutionResult(success=False, error=str(e), trace_id=trace_id, latency_ms=latency_ms)

    async def list_dir(self, path: str) -> ExecutionResult:
        start = time.time()
        trace_id = self._generate_trace_id()
        try:
            entries = os.listdir(path)
            latency_ms = int((time.time() - start) * 1000)
            return ExecutionResult(success=True, output=entries, trace_id=trace_id, latency_ms=latency_ms)
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            return ExecutionResult(success=False, error=str(e), trace_id=trace_id, latency_ms=latency_ms)

    def _generate_trace_id(self) -> str:
        return hashlib.sha256(f"{time.time()}{random.randint(0, 1000000)}".encode()).hexdigest()[:16]

    def _check_blocked(self, command: str) -> Optional[str]:
        dangerous = ["rm -rf /", "mkfs", "dd if=/dev/zero", ":(){ :|:& };:", "> /dev/sda"]
        for d in dangerous:
            if d in command:
                return d
        return None


class MemoryAdapter(IMemoryAdapter):
    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._ttls: Dict[str, float] = {}
        self._logger = get_logger("kernel.memory_adapter")

    async def store(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        self._store[key] = value
        if ttl:
            self._ttls[key] = time.time() + ttl
        self._logger.debug("Stored", key=key, ttl=ttl)
        return True

    async def retrieve(self, key: str) -> Optional[Any]:
        if key in self._ttls and time.time() > self._ttls[key]:
            del self._store[key]
            del self._ttls[key]
            return None
        return self._store.get(key)

    async def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            if key in self._ttls:
                del self._ttls[key]
            return True
        return False

    async def query(self, pattern: str) -> List[Dict[str, Any]]:
        results = []
        for key, value in self._store.items():
            if pattern in key:
                results.append({"key": key, "value": value})
        return results


class ContextBus(IContextBus):
    def __init__(self):
        self._stack: Dict[str, List[Any]] = {}
        _context: Dict[str, Any] = {}
        self._trace_id: Optional[str] = None
        self._logger = get_logger("kernel.context_bus")

    def set_trace_id(self, trace_id: Optional[str]) -> None:
        self._trace_id = trace_id

    async def push(self, key: str, value: Any, trace_id: Optional[str] = None) -> bool:
        if key not in self._stack:
            self._stack[key] = []
        self._stack[key].append(value)
        self._logger.debug("Pushed to stack", key=key, trace_id=trace_id or self._trace_id)
        return True

    async def pop(self, key: str) -> Optional[Any]:
        if key in self._stack and self._stack[key]:
            return self._stack[key].pop()
        return None

    async def get(self, key: str) -> Optional[Any]:
        return self._stack.get(key, [None])[-1] if self._stack.get(key) else None

    async def set(self, key: str, value: Any) -> bool:
        if key not in self._stack:
            self._stack[key] = []
        if self._stack[key]:
            self._stack[key][-1] = value
        else:
            self._stack[key].append(value)
        return True

    async def snapshot(self) -> Dict[str, Any]:
        return {
            "stack": {k: list(v) for k, v in self._stack.items()},
            "trace_id": self._trace_id,
            "timestamp": int(datetime.now(tz=timezone.utc).timestamp()),
        }


class OpenClawKernel(IModule):
    def __init__(self, config: Optional[KernelConfig] = None):
        self._config = config or KernelConfig()
        self._tool_adapter = ToolAdapter(self._config)
        self._memory_adapter = MemoryAdapter()
        self._context_bus = ContextBus()
        self._initialized = False
        self._logger = get_logger("kernel")

        if self._config.seed is not None:
            random.seed(self._config.seed)

    @property
    def name(self) -> str:
        return "openclaw_kernel"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def tools(self) -> ToolAdapter:
        return self._tool_adapter

    @property
    def memory(self) -> MemoryAdapter:
        return self._memory_adapter

    @property
    def context(self) -> ContextBus:
        return self._context_bus

    async def initialize(self, config: Dict[str, Any]) -> bool:
        if config.get("seed"):
            self._config.seed = config["seed"]
            random.seed(self._config.seed)
        if config.get("work_dir"):
            self._config.work_dir = config["work_dir"]
        os.makedirs(self._config.work_dir, exist_ok=True)
        self._initialized = True
        self._logger.info("Kernel initialized", seed=self._config.seed, work_dir=self._config.work_dir)
        return True

    async def shutdown(self) -> bool:
        self._initialized = False
        self._logger.info("Kernel shutdown")
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {
            "component": self.name,
            "initialized": self._initialized,
            "work_dir": self._config.work_dir,
            "seed": self._config.seed,
        }

    async def execute(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if command == "exec":
            result = await self._tool_adapter.exec_command(args.get("cmd", ""), args)
            return result.__dict__
        elif command == "read":
            result = await self._tool_adapter.read_file(args.get("path", ""))
            return result.__dict__
        elif command == "write":
            result = await self._tool_adapter.write_file(args.get("path", ""), args.get("content", ""))
            return result.__dict__
        elif command == "snapshot":
            return await self._context_bus.snapshot()
        else:
            return {"error": f"Unknown command: {command}"}

    def create_snapshot(self) -> Dict[str, Any]:
        return {
            "config": {
                "seed": self._config.seed,
                "work_dir": self._config.work_dir,
            },
            "context": self._context_bus._stack,
            "timestamp": int(datetime.now(tz=timezone.utc).timestamp()),
        }
