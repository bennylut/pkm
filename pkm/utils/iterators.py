from typing import TypeVar, Iterable, Callable, Dict, List, Optional, Tuple, Iterator

from pkm.utils.types import SupportHashCode

_T = TypeVar("_T")
_U = TypeVar("_U")
_K = TypeVar("_K", bound=SupportHashCode)


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


def distinct(it: Iterable[_T], key: Callable[[_T], _K] = lambda x: x) -> Iterator[_T]:
    """
    :param it: the iterator to run over
    :param key: key function by which to perform the comparison
    :return: iterator over `it` which only contain each item in it once
    """
    s = set()
    for item in it:
        item_key = key(item)
        if item_key not in s:
            s.add(item_key)
            yield item


def without(it: Iterable[_T], predicate: Callable[[_T], bool]) -> Iterator[_T]:
    """
    :param it: the iterator to run over
    :param predicate: predicate for items in `it`
    :return: iterator containing only items in `it` which `predicate` returned `False` for
    """
    return (v for v in it if not predicate(v))


def without_nones(it: Iterable[Optional[_T]]) -> Iterator[_T]:
    """
    :param it: the iterator to run over
    :return: iterator containing all the non-none items in `it`
    """
    return without(it, lambda x: x is None)


def first(it: Iterable[_T], default: _T) -> _T:
    """
    return the first value in the given iterable (does not have to be subscriptable)
    :param it: the iterator to run over
    :param default: the value to return if `it` if empty
    :return: the first value in `it` or `default` if `it` is empty
    """
    return next(iter(it), default)


def first_or_none(it: Iterable[_T]) -> Optional[_T]:
    """
    same as calling `first(it, None)`
    :param it: the iterator to run over
    :return: the first value in `it` or None if `it` is empty
    """
    return first(it, None)

