from __future__ import annotations

from typing import Any, Dict, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocols.interfaces import IRedactor


class SimpleRedactor(IRedactor):
    def __init__(self, mask: str = "***", default_sensitive_keys: Optional[list] = None):
        self._mask = mask
        self._sensitive_keys = set(
            k.lower()
            for k in (default_sensitive_keys or ["password", "token", "refresh_token", "secret", "api_key", "authorization"])
        )

    def redact(self, data: Any, policy: Optional[Dict[str, Any]] = None) -> Any:
        sensitive_keys = set(self._sensitive_keys)
        if policy and policy.get("sensitive_keys"):
            sensitive_keys |= set(str(k).lower() for k in policy["sensitive_keys"])

        return self._redact_any(data, sensitive_keys)

    def _redact_any(self, value: Any, sensitive_keys: set) -> Any:
        if isinstance(value, dict):
            out = {}
            for k, v in value.items():
                if str(k).lower() in sensitive_keys:
                    out[k] = self._mask
                else:
                    out[k] = self._redact_any(v, sensitive_keys)
            return out
        if isinstance(value, list):
            return [self._redact_any(v, sensitive_keys) for v in value]
        if isinstance(value, tuple):
            return tuple(self._redact_any(v, sensitive_keys) for v in value)
        return value

