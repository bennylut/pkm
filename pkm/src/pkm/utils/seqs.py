from __future__ import annotations

import itertools
from typing import TypeVar, Generic, Iterator, Callable, Optional, List, Iterable

_T = TypeVar("_T")
_U = TypeVar("_U")


def seq(iterator: Iterable[_T]) -> Seq[_T]:
    return Seq(iter(iterator))


class Seq(Generic[_T], Iterator[_T]):

    def __init__(self, iterator: Iterator[_T]):
        self._iter = iterator

    def __next__(self) -> _T:
        return next(self._iter)

    def map(self, mapper: Callable[[_T], _U]) -> Seq[_U]:
        return Seq(mapper(it) for it in self._iter)

    def flatmap(self, mapper: Callable[[_T], Iterable[_U]]) -> Seq[_U]:
        return Seq((item for collection in self.map(mapper) for item in collection))

    def map_not_none(self, mapper: Callable[[_T], _U]) -> Seq[_U]:
        return Seq(m for it in self._iter if (m := mapper(it)) is not None)

    def filter(self, accept: Callable[[_T], bool]) -> Seq[_T]:
        return Seq(it for it in self._iter if accept(it))

    def chain(self, other: Iterator[_T]):
        return Seq(itertools.chain(self._iter, other))

    def first_or(self, default: _T) -> _T:
        try:
            return next(self._iter)
        except StopIteration:
            return default

    def first_or_none(self) -> Optional[_T]:
        return self.first_or(None)

    def find_or(self, accept: Callable[[_T], bool], default: _T) -> _T:
        return self.filter(accept).first_or(default)

    def find_or_none(self, accept: Callable[[_T], bool]) -> Optional[_T]:
        return self.find_or(accept, None)

    def limit(self, amount: int) -> Seq[_T]:
        return Seq(itertools.islice(self._iter, amount))

    def for_each(self, op: Callable[[_T], None]) -> None:
        for it in self._iter:
            op(it)

    def to_list(self, into: Optional[List[_T]] = None) -> List[_T]:
        if into:
            into.extend(self._iter)
        else:
            into = list(self._iter)

        return into
