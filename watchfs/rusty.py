from __future__ import annotations


class Some[T]:
    _value: T
    __match_args__ = ("_value",)

    def __init__(self, value: T) -> None:
        self._value = value

    def unwrap(self) -> T:
        return self._value

    def __repr__(self) -> str:
        return f"Some({self._value})"


class Ok[T]:
    _value: T
    __match_args__ = ("_value",)

    def __init__(self, value: T) -> None:
        self._value = value

    def ok(self) -> T:
        return self._value

    def __repr__(self) -> str:
        return f"Ok({self._value})"


class Err[E: Exception]:
    _e: E
    __match_args__ = ("_e",)

    def __init__(self, e: E) -> None:
        self._e = e

    def err(self) -> E:
        return self._e

    def __repr__(self) -> str:
        return f"Err({self._e})"


type Result[T, E: Exception] = Ok[T] | Err[E]
type Option[T] = Some[T] | None
