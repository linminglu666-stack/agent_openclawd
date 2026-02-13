from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional, TypeVar, ParamSpec
import inspect

P = ParamSpec('P')
T = TypeVar('T')


class ContractViolationError(Exception):
    def __init__(self, message: str, contract_type: str, function_name: str = ""):
        self.message = message
        self.contract_type = contract_type
        self.function_name = function_name
        super().__init__(f"[{contract_type}] {function_name}: {message}")


_contracts_enabled = True


def enable_contracts() -> None:
    global _contracts_enabled
    _contracts_enabled = True


def disable_contracts() -> None:
    global _contracts_enabled
    _contracts_enabled = False


def contracts_enabled() -> bool:
    return _contracts_enabled


def precondition(predicate: Callable[..., bool], message: str = ""):
    def decorator(f: Callable[P, T]) -> Callable[P, T]:
        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if not _contracts_enabled:
                return f(*args, **kwargs)
            
            try:
                if inspect.ismethod(f) or (args and hasattr(args[0], '__class__')):
                    if not predicate(args[0], *args[1:], **kwargs):
                        raise ContractViolationError(
                            message or f"Precondition failed: {predicate.__name__}",
                            "PRECONDITION",
                            f.__name__
                        )
                else:
                    if not predicate(*args, **kwargs):
                        raise ContractViolationError(
                            message or f"Precondition failed: {predicate.__name__}",
                            "PRECONDITION",
                            f.__name__
                        )
            except TypeError:
                pass
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


def postcondition(predicate: Callable[..., bool], message: str = ""):
    def decorator(f: Callable[P, T]) -> Callable[P, T]:
        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            result = f(*args, **kwargs)
            
            if not _contracts_enabled:
                return result
            
            try:
                if not predicate(result):
                    raise ContractViolationError(
                        message or f"Postcondition failed: {predicate.__name__}",
                        "POSTCONDITION",
                        f.__name__
                    )
            except TypeError:
                pass
            
            return result
        return wrapper
    return decorator


def invariant(predicate: Callable[..., bool], message: str = ""):
    def decorator(f: Callable[P, T]) -> Callable[P, T]:
        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if not _contracts_enabled:
                return f(*args, **kwargs)
            
            if args and hasattr(args[0], '__class__'):
                self_arg = args[0]
                try:
                    if not predicate(self_arg):
                        raise ContractViolationError(
                            message or f"Invariant check failed before: {predicate.__name__}",
                            "INVARIANT",
                            f.__name__
                        )
                except TypeError:
                    pass
                
                result = f(*args, **kwargs)
                
                try:
                    if not predicate(self_arg):
                        raise ContractViolationError(
                            message or f"Invariant check failed after: {predicate.__name__}",
                            "INVARIANT",
                            f.__name__
                        )
                except TypeError:
                    pass
                
                return result
            else:
                return f(*args, **kwargs)
        
        return wrapper
    return decorator


def require(predicate: Callable[..., bool], message: str = ""):
    return precondition(predicate, message)


def ensure(predicate: Callable[..., bool], message: str = ""):
    return postcondition(predicate, message)


def invariant_check(predicate: Callable[..., bool], message: str = ""):
    return invariant(predicate, message)
