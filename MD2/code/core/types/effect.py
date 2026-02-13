from __future__ import annotations

import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, ParamSpec

P = ParamSpec('P')
T = TypeVar('T')


class EffectType(Enum):
    IO = "io"
    STATE = "state"
    ASYNC = "async"
    RANDOM = "random"
    TIME = "time"
    NETWORK = "network"
    DB = "db"


class EffectTracker:
    _effects: List[Dict[str, Any]] = []
    _enabled: bool = True
    
    @classmethod
    def enable(cls) -> None:
        cls._enabled = True
    
    @classmethod
    def disable(cls) -> None:
        cls._enabled = False
    
    @classmethod
    def record(cls, func_name: str, effects: tuple, args: tuple = (), kwargs: Optional[Dict] = None) -> None:
        if not cls._enabled:
            return
        cls._effects.append({
            "func": func_name,
            "effects": [e.value for e in effects],
            "timestamp": time.time(),
            "args_repr": repr(args)[:200] if args else None,
            "kwargs_keys": list(kwargs.keys()) if kwargs else None,
        })
    
    @classmethod
    def get_effects(cls) -> List[Dict[str, Any]]:
        return cls._effects.copy()
    
    @classmethod
    def get_effects_by_type(cls, effect_type: EffectType) -> List[Dict[str, Any]]:
        return [e for e in cls._effects if effect_type.value in e["effects"]]
    
    @classmethod
    def clear(cls) -> None:
        cls._effects.clear()
    
    @classmethod
    def summary(cls) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for effect in cls._effects:
            for e in effect["effects"]:
                counts[e] = counts.get(e, 0) + 1
        return counts


def effect(*effect_types: EffectType):
    def decorator(f: Callable[P, T]) -> Callable[P, T]:
        f._effects = effect_types
        
        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            EffectTracker.record(f.__name__, effect_types, args, kwargs)
            return f(*args, **kwargs)
        
        wrapper._effects = effect_types
        return wrapper
    return decorator


def effect_async(*effect_types: EffectType):
    def decorator(f: Callable[P, T]) -> Callable[P, T]:
        f._effects = effect_types
        
        @wraps(f)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            EffectTracker.record(f.__name__, effect_types, args, kwargs)
            return await f(*args, **kwargs)
        
        wrapper._effects = effect_types
        return wrapper
    return decorator


def get_function_effects(func: Callable) -> Optional[tuple]:
    return getattr(func, '_effects', None)


def has_effect(func: Callable, effect_type: EffectType) -> bool:
    effects = get_function_effects(func)
    return effects is not None and effect_type in effects
