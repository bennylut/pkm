from typing import TypeVar, MutableMapping, Optional, Callable

from pkm.utils.types import SupportHashCode

_K = TypeVar("_K", bound=SupportHashCode)
_V = TypeVar("_V")
_M = TypeVar("_M", bound=MutableMapping)
_SENTINAL = object()


def put_if_absent(d: MutableMapping[_K, _V], key: _K, value: _V) -> bool:
    """
    sets `d[key]=value` if `key not in d`
    :param d: the dict to mutate
    :param key: the key to assign
    :param value: the value to set if `key not in d`
    :return: true if `value` was set (`key` was not in `d`), false otherwise.
    """
    if key in d:
        return False
    d[key] = value
    return True


def get_or_put(d: MutableMapping[_K, _V], key: _K, value_provider: Callable[[], _V]):
    """
    :param d: the dict to look in
    :param key: the key to get
    :param value_provider: function providing a new value for `d[key]` in the case where no such value already exists
    :return: `d[key]` if such value exists otherwise set `d[key] = value_provider()` and then returns `d[key]`
    """
    if (value := d.get(key, _SENTINAL)) is _SENTINAL:
        d[key] = value = value_provider()

    return value


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
