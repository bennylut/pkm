from abc import abstractmethod
from typing import Protocol, runtime_checkable


# _T = TypeVar("_T")
# _PARAMS: "typing.ParamSpec" = ParamSpec("_PARAMS")
#
# log_to_stderr(logging.DEBUG)
#
#
# class ProcessPoolExecutor(Closeable):
#
#     def __init__(self, num_proc=multiprocessing.cpu_count()):
#         print("STARTING POOL")
#         self.pool = multiprocessing.Pool(num_proc)
#
#     def execute(self, execution: Callable[_PARAMS, _T],
#                 *args: _PARAMS.args, **kwargs: _PARAMS.kwargs) -> Promise[_T]:
#         result = Deferred()
#
#         def _complete(x):
#             result.complete(x)
#
#         def _fail(x):
#             result.fail(x)
#
#         print("EXECUTING PROC")
#         # self.pool.apply_async(execution, args, kwargs, callback=result.complete, error_callback=result.fail)
#         r = self.pool.apply_async(execution, args, kwargs, callback=_complete, error_callback=_fail)
#         print("WAITING")
#         r.wait()
#
#         print(f"EXECUTED - result = {r} | {r.ready()}")
#         return result.promise()
#
#     def close(self):
#         print("CLOSING POOL")
#         self.pool.terminate()
#

@runtime_checkable
class IPCPackable(Protocol):

    @abstractmethod
    def __getstate__(self):
        ...

    @abstractmethod
    def __setstate__(self, state):
        ...
