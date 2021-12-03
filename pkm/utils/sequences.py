from typing import TypeVar, Any, Callable, Iterable, Sequence, Optional
from typing_extensions import Protocol

_T = TypeVar("_T")


class SupportsLessThan(Protocol):
    def __lt__(self, __other: Any) -> bool: ...


def distinct(it: Iterable[_T], key: Callable[[_T], Any] = lambda x: x) -> Iterable[_T]:
    s = set()
    for item in it:
        item_key = key(item)
        if item_key not in s:
            s.add(item_key)
            yield item


def subiter(sq: Sequence[_T], offset: int = 0, length: Optional[int] = None) -> Iterable[_T]:
    if length is None:
        length = len(sq) - offset

    for i in range(offset, offset + length):
        yield sq[i]


def startswith(sq: Sequence[_T], prefix: Sequence[_T]) -> bool:
    if len(prefix) > len(sq):
        return False

    return all(s == p for s, p in zip(sq, prefix))


def argmin(seq: Sequence[_T], key: Optional[Callable[[_T], SupportsLessThan]]) -> int:
    if key is None:
        okey = seq.__getitem__
    else:
        okey = lambda i: key(seq[i])

    return min(range(len(seq)), key=okey)


def argmax(seq: Sequence[_T], key: Optional[Callable[[_T], SupportsLessThan]]) -> int:
    if key is None:
        okey = seq.__getitem__
    else:
        okey = lambda i: key(seq[i])

    return max(range(len(seq)), key=okey)
