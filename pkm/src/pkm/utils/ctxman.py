from typing import ContextManager, TypeVar
from weakref import finalize

_T = TypeVar("_T")


def with_gc_context(contextman: ContextManager[_T]) -> _T:
    result = contextman.__enter__()
    finalize(result, contextman.__exit__, None, None, None)
    return result
