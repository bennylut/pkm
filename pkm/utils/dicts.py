from typing import TypeVar, MutableMapping, Optional, Callable

from pkm.utils.sequences import SupportHashCode

_K = TypeVar("_K", bound=SupportHashCode)
_V = TypeVar("_V")
_M = TypeVar("_M", bound=MutableMapping)


def remove_by_value(
        d: "_M[_K, _V]", value: Optional[_V] = None,
        match: Optional[Callable[[_V], bool]] = None) -> "_M[_K, _V]":
    """
    remove items from [d] if they either match the given [match] function
    or if no [match] function given, if they are equals to the given [value]

    :param d: the dict to remove items from
    :param value: if supplied, the value to remove
    :param match: if supplied, matcher for the values to remove
    :return: [d]
    """

    if match:
        keys_to_remove = [k for k, v in d.items() if match(v)]
    else:
        keys_to_remove = [k for k, v in d.items() if v == value]

    for k in keys_to_remove:
        del d[k]

    return d
