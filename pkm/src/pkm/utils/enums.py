from enum import Enum
from typing import Type, TypeVar, Dict

_E = TypeVar("_E", bound=Enum)
_ENUM_KV_CACHE: Dict[Type, Dict[str, Enum]] = {}


def enum_value_of(enum_type: Type[_E], name: str) -> _E:
    if not (cache := _ENUM_KV_CACHE.get(enum_type)):
        cache = {e.name: e for e in enum_type}
        _ENUM_KV_CACHE[enum_type] = cache
    return cache[name]
