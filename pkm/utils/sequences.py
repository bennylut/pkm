from typing import TypeVar, Callable, Iterable, Sequence, Optional, Any

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


def index_of_or_none(seq: Sequence[_T], value: Any) -> Optional[int]:
    """
    :param seq: the sequence to search in
    :param value: the value to search for
    :return: the index of `value` in `seq` or `None` if `value not in seq`
    """
    try:
        return seq.index(value)
    except ValueError:
        return None


def single_or_fail(seq: Sequence[_T]) -> _T:
    if (l := len(seq)) != 1:
        raise ValueError(f"expecting single element, found: {l}")
    return seq[0]
