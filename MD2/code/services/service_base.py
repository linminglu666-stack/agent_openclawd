from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import asyncio
import os
import signal
import socket

from utils.logger import get_logger


@dataclass
class ServiceConfig:
    name: str
    tick_interval_sec: float = 1.0


class ServiceBase:
    def __init__(self, config: ServiceConfig):
        self._config = config
        self._logger = get_logger(f"service.{config.name}")
        self._stop_event = asyncio.Event()
        self._watchdog_interval_sec = self._detect_watchdog_interval_sec()
        self._state_dir = Path(os.environ.get("OPENCLAW_STATE_DIR", "/var/lib/openclaw-x"))
        self._log_dir = Path(os.environ.get("OPENCLAW_LOG_DIR", "/var/log/openclaw-x"))
        self._runtime_dir = Path(os.environ.get("OPENCLAW_RUNTIME_DIR", "/run/openclaw-x"))
        self._exit_code = 0
        self._tick_count = 0

    async def initialize(self) -> bool:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._runtime_dir.mkdir(parents=True, exist_ok=True)
        return True

    async def shutdown(self) -> bool:
        return True

    async def tick(self) -> None:
        return None

    async def health(self) -> Dict[str, Any]:
        return {"service": self._config.name, "timestamp": datetime.utcnow().isoformat(), "ok": True}

    async def run(self) -> int:
        self._install_signal_handlers()
        ok = await self.initialize()
        if not ok:
            self.notify("STATUS=init_failed")
            return 1

        await self._maybe_recover()

        self.notify("READY=1")
        self.notify(f"STATUS=running:{self._config.name}")

        watchdog_task = None
        if self._watchdog_interval_sec is not None:
            watchdog_task = asyncio.create_task(self._watchdog_loop())

        try:
            while not self._stop_event.is_set():
                await self.tick()
                self._tick_count += 1
                if self._tick_count % max(1, int(1.0 / max(0.001, self._config.tick_interval_sec))) == 0:
                    await self._self_heal_check()
                await asyncio.sleep(self._config.tick_interval_sec)
        finally:
            if watchdog_task:
                watchdog_task.cancel()
                try:
                    await watchdog_task
                except asyncio.CancelledError:
                    pass
            await self.shutdown()
            self.notify("STOPPING=1")

        return int(self._exit_code)

    def request_stop(self) -> None:
        self._stop_event.set()

    def notify(self, message: str) -> bool:
        notify_socket = os.environ.get("NOTIFY_SOCKET")
        if not notify_socket:
            return False

        address = notify_socket
        if address.startswith("@"):
            address = "\0" + address[1:]

        data = (message.strip() + "\n").encode("utf-8")
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            sock.connect(address)
            sock.sendall(data)
            return True
        except Exception:
            return False
        finally:
            try:
                sock.close()
            except Exception:
                pass

    def _install_signal_handlers(self) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.request_stop)
            except NotImplementedError:
                signal.signal(sig, lambda *_: self.request_stop())

    def _detect_watchdog_interval_sec(self) -> Optional[float]:
        usec = os.environ.get("WATCHDOG_USEC")
        if not usec:
            return None
        try:
            interval = float(usec) / 1_000_000.0
        except Exception:
            return None
        if interval <= 0:
            return None
        return max(1.0, interval / 2.0)

    async def _watchdog_loop(self) -> None:
        while not self._stop_event.is_set():
            self.notify("WATCHDOG=1")
            await asyncio.sleep(self._watchdog_interval_sec or 10.0)

    async def _maybe_recover(self) -> None:
        rt = getattr(self, "_rt", None)
        if not rt:
            return
        state_db = getattr(rt, "state_db", None)
        wal = getattr(rt, "wal", None)
        if not state_db:
            return
        try:
            from core.recovery.startup import recover_runtime
            recover_runtime(state_db=state_db, wal=wal)
        except Exception as e:
            self._logger.error("recovery_failed", error=str(e))

    async def _self_heal_check(self) -> None:
        try:
            h = await self.health()
        except Exception as e:
            self._logger.error("health_check_failed", error=str(e))
            self._exit_code = 2
            self.request_stop()
            return
        ok = True
        if isinstance(h, dict) and "ok" in h:
            ok = bool(h.get("ok"))
        elif isinstance(h, dict) and "state" in h:
            ok = str(h.get("state")) not in {"unhealthy", "error", "failed"}
        if not ok:
            self.notify("STATUS=unhealthy_exit")
            self._exit_code = 2
            self.request_stop()

    @classmethod
    def main(cls, service: "ServiceBase") -> int:
        return asyncio.run(service.run())
