from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class StateStore(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def put(self, key: str, value: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    def compare_and_swap(self, key: str, expected_version: Optional[str], value: Dict[str, Any]) -> bool:
        pass

