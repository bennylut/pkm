from typing import TypeVar, Optional, Callable

_T = TypeVar("_T")


def unone(v: Optional[_T], on_none: Callable[[], _T]) -> _T:
    if v is None:
        return on_none()
    return v
