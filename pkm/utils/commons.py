from typing import TypeVar, Optional, Callable, Protocol, Any

_T = TypeVar("_T")


def unone(v: Optional[_T], on_none: Callable[[], _T]) -> _T:
    """
    :param v: the value to check
    :param on_none: callable to execute in the case where v is None
    :return:  `v` if `v` is not None otherwise `on_none()`
    """
    if v is None:
        return on_none()
    return v


def unone_raise(v: Optional[_T], on_none: Callable[[], Exception] = lambda: ValueError('unexpected None')) -> _T:
    """
        :param v: the value to check
        :param on_none: callable to execute in the case where v is None
        :return:  `v` if `v` is not None otherwise raises the exception returned by `on_none()`
        """
    if v is None:
        raise on_none()
    return v


def take_if(value: _T, predicate: Callable[[_T], bool]) -> Optional[_T]:
    """
    :param value: the value to check
    :param predicate: predicate accepting the value
    :return: `value` if `predicate(value)` is `True` otherwise `None`
    """
    if predicate(value):
        return value
    return None


# Common protocols

class SupportsLessThan(Protocol):
    def __lt__(self, __other: Any) -> bool: ...


class SupportHashCode(Protocol):
    def __hash__(self): ...

    def __eq__(self, other): ...
