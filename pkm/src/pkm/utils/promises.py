from __future__ import annotations

import typing
import warnings
from abc import ABC, abstractmethod
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock, Condition
from typing import TypeVar, Generic, Callable, Any, Optional, List, Union, TYPE_CHECKING

from pkm.utils.types import ParamSpec, Mapper, Supplier

if TYPE_CHECKING:
    from pkm.utils.multiproc import ProcessPoolExecutor

_T = TypeVar("_T")
_U = TypeVar("_U")
_PARAMS: "typing.ParamSpec" = ParamSpec("_PARAMS")


class Promise(ABC, Generic[_T]):

    @abstractmethod
    def when_completed(self, callback: Callable[[Promise[_T]], _U]) -> Promise[_U]:
        """
        adds a step to the promise chain, when this promise is completed,
        it will be passed through the given `callback`, the callback in response can return a new value or raise
        a new exception which will be the result of the returned `promise`
        :param callback: the calback function to call when this promise completes
        :return: a new promise which will be resolved by the return value of the given `callback`
        """

    @abstractmethod
    def result(self, wait: bool = True) -> _T:
        """
        gets the result of this promise.
        if this promise failed, this method will raise the exception that were given as the cause of the failure
        if this promise is not completed and `wait` is False - raise a value-error
        if this promise is not completed and `wait` is not given or True,
        waits until the promise completes before returning its result
        :param wait: whether or not to wait for the promise to complete
        :return: the result of the completed promise
        """

    @abstractmethod
    def is_completed(self) -> bool:
        """
        :return: True if this promise is completed, False otherwise
        """

    @abstractmethod
    def is_failed(self) -> bool:
        """
        :return: True if this promise is completed with failure, False otherwise
        """

    @abstractmethod
    def request_cancel(self):
        """
        flag the process that promised this promise that the user wants it to cancel its operation,
        it is implementation dependant if the process will respond to this cancelation request
        """

    def is_succeeded(self) -> bool:
        """
        :return: True if this promise is completed without failure
        """
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


def await_all_promises_or_cancel(promises: List[Promise]):
    try:
        await_all_promises(promises)
    except Exception as e:
        print("DBG: canceling all promises")
        for p in [uncanceled for uncanceled in promises if not uncanceled.request_cancel()]:
            try:
                print("DBG: failed to cancel, awaiting result...")
                p.result()
            except BaseException as ie:
                warnings.warn(f"multiple errors while waiting for promises to complete: {ie}")
        raise e


def await_all_promises(promises: List[Promise], ignore_error: bool = False):
    for p in promises:
        try:
            p.result()
        except BaseException as e:
            if not ignore_error:
                raise e


class Deferred(Generic[_T]):
    """
    object represents a deffered result, allows a using-process to return a promise connected to this deffered result
    """

    def __init__(self, cancel_handler: Optional[Supplier[bool]] = None):
        self._promise: _SimplePromise[_T] = _SimplePromise()
        if cancel_handler:
            self._promise.request_cancel = cancel_handler

    def promise(self) -> Promise[_T]:
        return self._promise

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

                deferred = Deferred(self.request_cancel)

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

    def request_cancel(self) -> bool:
        return False

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
    def __init__(
            self, future: Future,
            result_mapper: Mapper[Future, _T] = _default_future_wrapping_promise_result_mapper):

        super().__init__()
        self._future = future

        def done_callback(fu: Future):
            try:
                self._complete(result_mapper(fu))
            except BaseException as e:
                self._fail(e)

        future.add_done_callback(done_callback)

    def request_cancel(self) -> bool:
        return self._future.cancel()
