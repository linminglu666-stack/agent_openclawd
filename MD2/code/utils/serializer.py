
import json
from datetime import datetime
from typing import Any
import uuid

class Serializer:
    @staticmethod
    def dumps(obj: Any) -> str:
        return json.dumps(obj, default=Serializer._default, ensure_ascii=False)

    @staticmethod
    def loads(data: str) -> Any:
        return json.loads(data)

    @staticmethod
    def _default(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)
