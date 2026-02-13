from __future__ import annotations

import json
import logging
import os
import sys
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_LOG_LEVEL = os.environ.get("OPENCLAW_LOG_LEVEL", "INFO").upper()
_LOG_FORMAT = os.environ.get("OPENCLAW_LOG_FORMAT", "json")
_LOGGERS: Dict[str, "StructuredLogger"] = {}
_LOCK = threading.Lock()


class StructuredLogger:
    def __init__(self, name: str, level: str = _LOG_LEVEL):
        self._name = name
        self._level = getattr(logging, level, logging.INFO)
        self._handler = logging.StreamHandler(sys.stdout)
        self._handler.setFormatter(logging.Formatter("%(message)s"))
        self._logger = logging.getLogger(name)
        self._logger.setLevel(self._level)
        self._logger.addHandler(self._handler)
        self._trace_id: Optional[str] = None

    def set_trace_id(self, trace_id: Optional[str]) -> None:
        self._trace_id = trace_id

    def _emit(self, level: str, message: str, **kwargs: Any) -> None:
        record = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level": level,
            "logger": self._name,
            "message": message,
        }
        if self._trace_id:
            record["trace_id"] = self._trace_id
        record.update(kwargs)
        if _LOG_FORMAT == "json":
            line = json.dumps(record, ensure_ascii=False, default=str)
        else:
            parts = [f"[{record['timestamp']}]", f"[{level}]", f"[{self._name}]", message]
            if kwargs:
                parts.append(str(kwargs))
            line = " ".join(parts)
        self._handler.stream.write(line + "\n")
        self._handler.stream.flush()

    def debug(self, message: str, **kwargs: Any) -> None:
        if self._level <= logging.DEBUG:
            self._emit("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        if self._level <= logging.INFO:
            self._emit("INFO", message, **kwargs)

    def warn(self, message: str, **kwargs: Any) -> None:
        if self._level <= logging.WARNING:
            self._emit("WARN", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        if self._level <= logging.ERROR:
            self._emit("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        if self._level <= logging.CRITICAL:
            self._emit("CRITICAL", message, **kwargs)


def get_logger(name: str) -> StructuredLogger:
    with _LOCK:
        if name not in _LOGGERS:
            _LOGGERS[name] = StructuredLogger(name)
        return _LOGGERS[name]
