import hashlib
import inspect
from typing import Any

from pkm.utils.types import Hashable
from pkm.utils.types import Serializable


class Symbol(Hashable, Serializable):
    def __init__(self, name: str):
        self._name = name
        creator = inspect.stack()[1]
        self._id = hashlib.md5(f"{name} {creator.filename} {creator.lineno}".encode()).hexdigest()
        self._attr = f"__sym_{self._name}_{self._id}__"

    def __str__(self):
        return f"Symbol({self._name})"

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return isinstance(other, Symbol) and self._id == other._id

    def __hash__(self):
        return hash(self._id)

    def __getstate__(self):
        return [self._name, self._id]

    def __setstate__(self, state):
        self._name, self._id = state
        self._attr = f"__sym_{self._name}_{self._id}__"

    def getattr(self, obj: Any, default=None) -> Any:
        return getattr(obj, self._attr, default)

    def setattr(self, obj: Any, value: Any):
        setattr(obj, self._attr, value)

    def hasattr(self, obj: Any) -> bool:
        return hasattr(obj, self._attr)
