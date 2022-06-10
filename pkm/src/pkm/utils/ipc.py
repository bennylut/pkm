import multiprocessing
from abc import abstractmethod, ABC
from types import FunctionType
from typing import Dict, Any, List, Callable, TypeVar, Protocol, runtime_checkable

from pkm.utils.commons import Closeable
from pkm.utils.promises import Promise, Deferred

from pkm.utils.types import ParamSpec
import typing

_T = TypeVar("_T")
_PARAMS: "typing.ParamSpec" = ParamSpec("_PARAMS")


class ProcessPoolExecutor(Closeable):

    def __init__(self, num_proc=multiprocessing.cpu_count()):
        self.pool = multiprocessing.Pool(num_proc)

    def execute(self, execution: Callable[_PARAMS, _T],
                *args: _PARAMS.args, **kwargs: _PARAMS.kwargs) -> Promise[_T]:
        result = Deferred()
        self.pool.apply_async(execution, args, kwargs, callback=result.complete, error_callback=result.fail)
        return result.promise()

    def close(self):
        self.pool.terminate()


@runtime_checkable
class IPCPackable(Protocol):

    @abstractmethod
    def __getstate__(self):
        ...

    @abstractmethod
    def __setstate__(self, state):
        ...
