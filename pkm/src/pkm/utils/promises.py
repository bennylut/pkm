from __future__ import annotations
from abc import ABC, abstractmethod
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock, Condition
from typing import TypeVar, Generic, Callable, Any, Optional, List, Union, TYPE_CHECKING
import typing

from pkm.utils.commons import UnsupportedOperationException
from pkm.utils.types import ParamSpec

_T = TypeVar("_T")
_U = TypeVar("_U")
_PARAMS: "typing.ParamSpec" = ParamSpec("_PARAMS")

if TYPE_CHECKING:
    from pkm.utils.ipc import ProcessPoolExecutor


class Promise(ABC, Generic[_T]):

    @abstractmethod
    def when_completed(self, callback: Callable[[Promise[_T]], _U]) -> Promise[_U]:
        ...

    @abstractmethod
    def result(self, wait: bool = True) -> _T:
        ...

    @abstractmethod
    def is_completed(self) -> bool:
        ...

    @abstractmethod
    def is_failed(self) -> bool:
        ...

    @abstractmethod
    def request_cancel(self):
        ...

    def is_succeeded(self) -> bool:
        return self.is_completed() and not self.is_failed()

    @classmethod
    def wrap_future(cls, future: Future, result_mapper: Callable[[Future], _T]) -> Promise[_T]:
        return _FutureWrappingPromise(future, result_mapper)

    @classmethod
    def execute(cls, executor: Union[ThreadPoolExecutor, "ProcessPoolExecutor", None], mtd: Callable[_PARAMS, _T],
                *args: _PARAMS.args, **kwargs: _PARAMS.kwargs) -> Promise[_T]:

        if executor is None:
            try:
                return Promise.create_completed(result=mtd(*args, **kwargs))
            except BaseException as e:
                return Promise.create_completed(err=e)

        if isinstance(executor, ThreadPoolExecutor):
            return cls.wrap_future(executor.submit(mtd, *args, **kwargs), lambda fu: fu.result())

        return executor.execute(mtd, *args, **kwargs)

    @classmethod
    def create_completed(cls, result: Optional[_T] = None, err: Optional[BaseException] = None) -> Promise[_T]:
        promise = _SimplePromise()

        if err is None:
            # noinspection PyProtectedMember
            promise._complete(result)
        else:
            # noinspection PyProtectedMember
            promise._fail(err)

        return promise


def await_all_promises(promises: List[Promise]):
    for p in promises:
        p.result()


class Deferred(Generic[_T]):

    def __init__(self):
        outer = self

        class InnerSimplePromise(_SimplePromise[_T]):
            def request_cancel(self):
                outer._cancel_requested = True

        self._promise: InnerSimplePromise[_T] = InnerSimplePromise()
        self._cancel_requested: bool = False

    def promise(self) -> Promise[_T]:
        return self._promise

    def is_cancel_requested(self) -> bool:
        return self._cancel_requested

    def complete(self, result: _T):
        # noinspection PyProtectedMember
        self._promise._complete(result)

    def fail(self, failure: BaseException):
        # noinspection PyProtectedMember
        self._promise._fail(failure)


def _default_future_wrapping_promise_result_mapper(fu: Future) -> Any:
    return fu.result()


class _SimplePromise(Promise[_T]):

    def __init__(self):
        self._wait_lock = Condition(Lock())
        self._result: Optional[_T] = None
        self._err: Optional[BaseException] = None
        self._done: bool = False
        self._listeners: List[Callable[[], None]] = []

    def when_completed(self, callback: Callable[[Promise[_T]], _U]) -> Promise[_U]:

        with self._wait_lock:
            if not self._done:

                deferred = Deferred()

                def callback_wrapper():
                    # noinspection PyShadowingNames
                    try:
                        deferred.complete(callback(self))
                    except BaseException as e:
                        deferred.fail(e)

                self._listeners.append(callback_wrapper)
                return deferred.promise()

        try:
            return Promise.create_completed(result=callback(self))
        except BaseException as e:
            return Promise.create_completed(err=e)

    def result(self, wait: bool = True) -> _T:
        while True:
            with self._wait_lock:
                if self._done:
                    if self._err:
                        raise self._err
                    return self._result

                if not wait:
                    raise ValueError("promise not completed yet")

                self._wait_lock.wait()

    def is_completed(self) -> bool:
        return self._done

    def is_failed(self) -> bool:
        return self._done and self._err

    def request_cancel(self):
        raise UnsupportedOperationException()

    def _complete(self, result: _T):
        with self._wait_lock:
            if self._done:
                raise ValueError("already completed")
            self._result = result
            self._done = True
            self._wait_lock.notify_all()
            listeners = self._listeners
            self._listeners = None

        for listener in listeners:
            listener()

    def _fail(self, err: BaseException):
        if err is None:
            raise ValueError("exception must be given")

        with self._wait_lock:
            if self._done:
                raise ValueError("already completed")

            self._err = err
            self._done = True
            self._wait_lock.notify_all()
            listeners = self._listeners
            self._listeners = None

        for listener in listeners:
            listener()


class _FutureWrappingPromise(_SimplePromise[_T]):
    def __init__(self, future: Future,
                 result_mapper: Callable[[Future], _T] = _default_future_wrapping_promise_result_mapper):

        super().__init__()
        self._future = future

        def done_callback(fu: Future):
            try:
                self._complete(result_mapper(fu))
            except BaseException as e:
                self._fail(e)

        future.add_done_callback(done_callback)

    def request_cancel(self):
        self._future.cancel()
