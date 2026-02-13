from __future__ import annotations

from dataclasses import dataclass, field, replace, fields, asdict
from typing import Any, Dict, List, Type, TypeVar, get_type_hints
from copy import deepcopy

T = TypeVar('T')


def immutable(cls: Type[T]) -> Type[T]:
    if hasattr(cls, '__dataclass_fields__'):
        cls.__dataclass_params__ = type(cls.__dataclass_params__)(frozen=True)
    else:
        cls = dataclass(cls, frozen=True)
    return cls


def evolve(obj: T, **changes: Any) -> T:
    if hasattr(obj, '__dataclass_fields__'):
        return replace(obj, **changes)
    raise TypeError(f"Object of type {type(obj)} is not a dataclass instance")


def to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, '__dataclass_fields__'):
        return asdict(obj)
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()
    if hasattr(obj, 'dict'):
        return obj.dict()
    return dict(obj)


def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
    if hasattr(cls, 'model_validate'):
        return cls.model_validate(data)
    if hasattr(cls, 'parse_obj'):
        return cls.parse_obj(data)
    if hasattr(cls, '__dataclass_fields__'):
        return cls(**data)
    raise TypeError(f"Cannot create {cls} from dict")


class ImmutableMixin:
    __slots__ = ()
    
    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(f"Cannot modify immutable object {type(self).__name__}")
    
    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"Cannot modify immutable object {type(self).__name__}")
    
    def evolve(self: T, **changes: Any) -> T:
        return evolve(self, **changes)
    
    def to_dict(self) -> Dict[str, Any]:
        return to_dict(self)


class VersionedMixin:
    _version: int = 0
    _history: List[Any] = []
    
    def get_version(self) -> int:
        return self._version
    
    def get_history(self) -> List[Any]:
        return self._history.copy()
    
    def with_version(self: T, **changes: Any) -> T:
        new_obj = evolve(self, **changes)
        if hasattr(new_obj, '_version'):
            object.__setattr__(new_obj, '_version', self._version + 1)
        if hasattr(new_obj, '_history'):
            object.__setattr__(new_obj, '_history', self._history + [self])
        return new_obj


class FrozenList:
    __slots__ = ('_items',)
    
    def __init__(self, items: List[Any] = None):
        object.__setattr__(self, '_items', tuple(items) if items else ())
    
    def __getitem__(self, index: int) -> Any:
        return self._items[index]
    
    def __len__(self) -> int:
        return len(self._items)
    
    def __iter__(self):
        return iter(self._items)
    
    def __contains__(self, item: Any) -> bool:
        return item in self._items
    
    def __repr__(self) -> str:
        return f"FrozenList({list(self._items)})"
    
    def __eq__(self, other: Any) -> bool:
        if isinstance(other, FrozenList):
            return self._items == other._items
        if isinstance(other, (list, tuple)):
            return self._items == tuple(other)
        return False
    
    def __hash__(self) -> int:
        return hash(self._items)
    
    def append(self, item: Any) -> 'FrozenList':
        return FrozenList(list(self._items) + [item])
    
    def remove(self, item: Any) -> 'FrozenList':
        new_items = [i for i in self._items if i != item]
        return FrozenList(new_items)
    
    def to_list(self) -> List[Any]:
        return list(self._items)


class FrozenDict:
    __slots__ = ('_data', '_hash')
    
    def __init__(self, data: Dict[str, Any] = None):
        d = dict(data) if data else {}
        object.__setattr__(self, '_data', d)
        object.__setattr__(self, '_hash', hash(tuple(sorted(d.items()))))
    
    def __getitem__(self, key: str) -> Any:
        return self._data[key]
    
    def __contains__(self, key: str) -> bool:
        return key in self._data
    
    def __iter__(self):
        return iter(self._data)
    
    def __len__(self) -> int:
        return len(self._data)
    
    def __repr__(self) -> str:
        return f"FrozenDict({self._data})"
    
    def __eq__(self, other: Any) -> bool:
        if isinstance(other, FrozenDict):
            return self._data == other._data
        if isinstance(other, dict):
            return self._data == other
        return False
    
    def __hash__(self) -> int:
        return self._hash
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
    
    def keys(self):
        return self._data.keys()
    
    def values(self):
        return self._data.values()
    
    def items(self):
        return self._data.items()
    
    def with_item(self, key: str, value: Any) -> 'FrozenDict':
        new_data = dict(self._data)
        new_data[key] = value
        return FrozenDict(new_data)
    
    def without(self, key: str) -> 'FrozenDict':
        new_data = {k: v for k, v in self._data.items() if k != key}
        return FrozenDict(new_data)
    
    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)
