from collections import defaultdict
from typing import TypeVar, Any, Callable, Iterable, Sequence, Optional, Protocol, Dict, List, Tuple

_T = TypeVar("_T")
_U = TypeVar("_U")


class SupportsLessThan(Protocol):
    def __lt__(self, __other: Any) -> bool: ...


class SupportHashCode(Protocol):
    def __hash__(self): ...

    def __eq__(self, other): ...


_K = TypeVar("_K", bound=SupportHashCode)


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


def groupby(seq: Iterable[_T], key: Callable[[_T], _K]) -> Dict[_K, List[_T]]:
    """
    :param seq: sequence to group
    :param key: a key function, the seq items will be grouped by it
    :return:
    """
    result: Dict[_U, List[_T]] = {}
    for item in seq:
        k = key(item)
        l = result.get(k)
        if l is None:
            result[k] = l = []
        l.append(item)

    return result


def find_first(seq: Iterable[_T], match: Callable[[_T], bool], none_value: Optional[_T] = None) -> Optional[_T]:
    """
    :param seq: the sequence to look in
    :param match: predicate for items in the sequence
    :param none_value: result for no match
    :return: the first item in the sequence that match or non_value if such not found
    """
    return next((it for it in seq if match(it)), none_value)


def partition(seq: Iterable[_T], match: Callable[[_T], bool]) -> Tuple[List[_T], List[_T]]:
    """
    :param seq: the sequence to partition
    :param match: predicate for item in the sequence
    :return: two lists, the first with items that match and the second containing the rest
    """

    t, f = [], []
    for item in seq:
        if match(item):
            t.append(item)
        else:
            f.append(item)

    return t, f
