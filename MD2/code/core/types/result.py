from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

T = TypeVar('T')
U = TypeVar('U')
E = TypeVar('E')
F = TypeVar('F')


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def ok(self) -> T:
        return self.value

    def err(self) -> None:
        return None

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, default: T) -> T:
        return self.value

    def unwrap_err(self) -> Any:
        raise ValueError(f"Called unwrap_err on Ok: {self.value}")

    def expect(self, message: str) -> T:
        return self.value

    def expect_err(self, message: str) -> Any:
        raise ValueError(message)

    def map(self, f: Callable[[T], U]) -> Result[U, E]:
        return Ok(f(self.value))

    def map_err(self, f: Callable[[E], F]) -> Result[T, F]:
        return Ok(self.value)

    def and_then(self, f: Callable[[T], Result[U, E]]) -> Result[U, E]:
        return f(self.value)

    def or_else(self, f: Callable[[E], Result[T, F]]) -> Result[T, F]:
        return Ok(self.value)

    def unwrap_or_else(self, f: Callable[[E], T]) -> T:
        return self.value

    def __repr__(self) -> str:
        return f"Ok({self.value!r})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Ok):
            return self.value == other.value
        return False


@dataclass(frozen=True)
class Err(Generic[E]):
    error: E

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def ok(self) -> None:
        return None

    def err(self) -> E:
        return self.error

    def unwrap(self) -> Any:
        raise ValueError(f"Called unwrap on Err: {self.error}")

    def unwrap_or(self, default: T) -> T:
        return default

    def unwrap_err(self) -> E:
        return self.error

    def expect(self, message: str) -> Any:
        raise ValueError(message)

    def expect_err(self, message: str) -> E:
        return self.error

    def map(self, f: Callable[[T], U]) -> Result[U, E]:
        return Err(self.error)

    def map_err(self, f: Callable[[E], F]) -> Result[T, F]:
        return Err(f(self.error))

    def and_then(self, f: Callable[[T], Result[U, E]]) -> Result[U, E]:
        return Err(self.error)

    def or_else(self, f: Callable[[E], Result[T, F]]) -> Result[T, F]:
        return f(self.error)

    def unwrap_or_else(self, f: Callable[[E], T]) -> T:
        return f(self.error)

    def __repr__(self) -> str:
        return f"Err({self.error!r})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Err):
            return self.error == other.error
        return False


Result = Ok[T] | Err[E]


def ok(value: T) -> Result[T, E]:
    return Ok(value)


def err(error: E) -> Result[T, E]:
    return Err(error)


def from_option(value: T | None, error: E) -> Result[T, E]:
    if value is None:
        return Err(error)
    return Ok(value)


def from_exception(f: Callable[[], T]) -> Result[T, Exception]:
    try:
        return Ok(f())
    except Exception as e:
        return Err(e)


async def from_exception_async(f: Callable[[], T]) -> Result[T, Exception]:
    try:
        result = f()
        if hasattr(result, "__await__"):
            result = await result
        return Ok(result)
    except Exception as e:
        return Err(e)
