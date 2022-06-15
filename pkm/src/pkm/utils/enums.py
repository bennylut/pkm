from enum import Enum
from typing import Type, TypeVar, Dict, Any

from pkm.utils.iterators import first_or_raise

_E = TypeVar("_E", bound=Enum)
_ENUM_KV_CACHE: Dict[Type, Dict[str, Enum]] = {}


def enum_by_name(enum_type: Type[_E], name: str) -> _E:
    if not (cache := _ENUM_KV_CACHE.get(enum_type)):
        cache = {e.name: e for e in enum_type}
        _ENUM_KV_CACHE[enum_type] = cache
    return cache[name]


def enum_by_value(enum_type: Type[_E], value: Any) -> _E:
    return first_or_raise(it for it in enum_type if it.value == value)
