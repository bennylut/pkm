from __future__ import annotations

from abc import abstractmethod, ABC
from typing import TypeVar, Generic, Iterator, Iterable, Callable, Union, Optional, MutableSequence, Sequence, Generator

from pkm.utils.commons import unone

_T = TypeVar("_T")
_U = TypeVar("_U")


class PipeTransformer(ABC, Generic[_T, _U]):
    @abstractmethod
    def __call__(self, target: Iterable[_T]) -> Iterable[_U]:
        ...

    def __ror__(self, other: Pipe[_T]) -> Pipe[_U]:
        return Pipe(self(other._iterable))  # noqa


class PipeTerminator(ABC, Generic[_T, _U]):
    @abstractmethod
    def __call__(self, target: Iterable[_T]) -> _U:
        ...

    def __ror__(self, other: Pipe[_T]) -> _U:
        return self(other._iterable)  # noqa


class Pipe(Generic[_T]):
    def __init__(self, iterable: Iterable[_T]):
        self._iterable = iterable

    def __iter__(self) -> Iterator[_T]:
        return iter(self._iterable)


def pipe(iterable: Union[Iterable[_T], Generator[_T]]) -> Pipe[_T]:
    return Pipe(iterable)


def p_first_or(default: _T) -> PipeTerminator[_T, _T]:
    class _FirstOr(PipeTerminator[_T, _T]):
        def __call__(self, target: Iterable[_T]) -> _T:
            for item in target:
                return item
            return default

    return _FirstOr()


def p_first_or_none() -> PipeTerminator[_T, Optional[_T]]:
    class _FirstOrNone(PipeTerminator[_T, Optional[_T]]):
        def __call__(self, target: Iterable[_T]) -> Optional[_T]:
            for item in target:
                return item
            return None

    return _FirstOrNone()


def p_limit(n: int) -> PipeTransformer[_T, _T]:
    class _Limit(PipeTransformer[_T, _T]):
        def __call__(self, target: Iterable[_T]) -> Iterable[_U]:
            i = 0
            for v in target:
                if (i := i + 1) > n:
                    break
                yield v

    return _Limit()


def p_collect(into: Optional[MutableSequence[_T]] = None) -> PipeTerminator[_T, Sequence[_T]]:
    into = unone(into, list)  # noqa

    class _Collect(PipeTerminator[_T, Sequence[_T]]):
        def __call__(self, target: Iterable[_T]) -> Sequence[_T]:
            into.extend(target)
            return into

    return _Collect()


def p_find_or(selector: Callable[[_T], bool], default: _T) -> PipeTerminator[_T, _T]:
    class _FindOr(PipeTerminator[_T, _T]):
        def __call__(self, target: Iterable[_T]) -> _T:
            for v in target:
                if selector(v):
                    return v
            return default

    return _FindOr()


def p_find_or_none(selector: Callable[[_T], bool]) -> PipeTerminator[_T, Optional[_T]]:
    return p_find_or(selector, None)


def p_filter(selector: Callable[[_T], bool]) -> PipeTransformer[_T, _T]:
    class _Filter(PipeTransformer[_T, _T]):
        def __call__(self, target: Iterable[_T]) -> Iterable[_T]:
            for v in target:
                if selector(v):
                    yield v

    return _Filter()


def p_map(mapper: Callable[[_T], _U]) -> PipeTransformer[_T, _U]:
    class _Map(PipeTransformer[_T, _U]):
        def __call__(self, target: Iterable[_T]) -> Iterable[_U]:
            for v in target:
                yield mapper(v)

    return _Map()
