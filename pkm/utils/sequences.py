from typing import TypeVar, Callable, Iterable, Sequence, Optional

from pkm.utils.commons import SupportHashCode, SupportsLessThan

_T = TypeVar("_T")
_U = TypeVar("_U")
_K = TypeVar("_K", bound=SupportHashCode)


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


