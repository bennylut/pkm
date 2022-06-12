from __future__ import annotations

import multiprocessing
import os
import pickle
import sys
import traceback
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from queue import Queue, Empty
from subprocess import Popen, PIPE
from threading import Lock, Thread
from types import FunctionType
from typing import BinaryIO, Optional, Any, Callable, TypeVar, List, Dict, cast

from pkm.utils.commons import Closeable
from pkm.utils.promises import Promise, Deferred
from pkm.utils.types import ParamSpec

_T = TypeVar("_T")
_PARAMS: "typing.ParamSpec" = ParamSpec("_PARAMS")


@dataclass
class _StdWrite:
    msg: str
    stream_id: int


class WorkerException(Exception):
    def __init__(self, msg, workerstrace: str):
        super().__init__(msg)
        self.worker_stack_trace = workerstrace


class _StandardStreamPipe(StringIO):
    def __init__(self, target_stream: BinaryIO, stream_id: int, stream_lock: Lock):
        super(_StandardStreamPipe, self).__init__()
        self.target_stream = target_stream
        self.stream_id = stream_id
        self.stream_lock = stream_lock

    def write(self, __s: str) -> int:
        if __s:
            with self.stream_lock:
                pickle.dump(_StdWrite(__s, self.stream_id), self.target_stream)
                self.target_stream.flush()
        return len(__s)


class _Command(ABC):
    @abstractmethod
    def execute(self) -> Any:
        ...


@dataclass
class _CommandResult:
    result: Any = None
    err_strace: Optional[str] = None


class _Worker:

    def __init__(self):
        self._stdout: Optional[BinaryIO] = None  # use for logs (multiplexed)
        self._stderr: Optional[BinaryIO] = None  # use for commands out
        self._stdin: Optional[BinaryIO] = None  # use for commands in
        self._stdout_lock = Lock()

    def _attach_to_process(self):
        self._stdout = sys.stdout.buffer
        self._stderr = sys.stderr.buffer
        self._stdin = sys.stdin.buffer

        sys.stdout = _StandardStreamPipe(self._stdout, 0, self._stdout_lock)
        sys.stderr = _StandardStreamPipe(self._stdout, 1, self._stdout_lock)

    def run(self):
        self._attach_to_process()
        while True:
            cmd: _Command = pickle.load(self._stdin)
            try:
                result = cmd.execute()
                pickle.dump(_CommandResult(result), self._stderr)
                self._stderr.flush()
            except Exception as e:  # noqa
                err_strace = StringIO()
                traceback.print_exc(file=err_strace)
                pickle.dump(_CommandResult(err_strace=err_strace.getvalue()), self._stderr)
                self._stderr.flush()


class _WorkerHandler:
    def __init__(self, pool: ProcessPoolExecutor, name: str):
        self._pool = pool
        self._proc: Optional[Popen] = None
        self._threads: Optional[List[Thread]] = None
        self.name = name

    def _execute_worker(self):
        executable = sys.executable
        self._proc = Popen(
            args=[executable, "-u", str(Path(__file__).parent / "worker.py")],
            stderr=PIPE, stdout=PIPE, stdin=PIPE, bufsize=0,
            env=os.environ
        )

    def _should_terminate(self):
        return self._pool.is_closed() or self._proc.poll() is not None

    def _handle_log(self):
        try:
            stream = [sys.stdout, sys.stderr]
            while not self._should_terminate():
                write: _StdWrite = pickle.load(self._proc.stdout)
                stream[write.stream_id].write(write.msg)
        except EOFError:
            pass

    def __del__(self):
        if self._proc.poll() is not None:
            self._proc.kill()

    def _handle_work(self):
        q = self._pool._task_queue  # noqa
        try:
            while not self._should_terminate():

                try:
                    next_task: _Task = q.get(block=True, timeout=self._pool.max_inactivity_seconds)
                except Empty:
                    self.kill()
                    self._proc.wait()
                    return

                task_result: _TaskResult = cast(_TaskResult, next_task.result)
                next_task.result = None

                try:
                    if task_result.attach_worker(self):
                        pickle.dump(next_task, self._proc.stdin)
                        self._proc.stdin.flush()

                        proc_result: _CommandResult = pickle.load(self._proc.stderr)

                        if proc_result.err_strace:
                            task_result.deferred.fail(
                                Exception(
                                    f"Worker Execution Failure, Worker Stacktrace was: \n\n{proc_result.err_strace}"))
                        else:
                            task_result.deferred.complete(proc_result.result)
                except BaseException as e:
                    task_result.deferred.fail(e)
                finally:
                    q.task_done()
        finally:
            # noinspection PyProtectedMember
            self._pool._removed_worker(self)

    def kill(self):
        self._proc.kill()

    def join(self):
        for t in self._threads:
            t.join()
        self._proc.wait()

    def start(self):
        self._execute_worker()
        log_thread = Thread(target=self._handle_log, daemon=True)
        work_thread = Thread(target=self._handle_work, daemon=True)
        self._threads = [log_thread, work_thread]
        log_thread.start()
        work_thread.start()


@dataclass
class _Task(_Command):
    function: FunctionType
    args: List[Any]
    kwargs: Dict[str, Any]
    result: _TaskResult

    def execute(self) -> Any:
        return self.function(*self.args, **self.kwargs)


class _TaskResult:
    def __init__(self):
        self.deferred = Deferred(self._on_cancel)
        self._canceled = False
        self._attached_worker: Optional[_WorkerHandler] = None
        self._lock = Lock()

    def attach_worker(self, worker: _WorkerHandler) -> bool:
        with self._lock:
            if self._canceled:
                return False
            self._attached_worker = worker

        return True

    def _on_cancel(self) -> bool:
        if self._canceled or self.deferred.promise().is_completed():
            with self._lock:
                self._canceled = True
                if self._attached_worker:
                    self._attached_worker.kill()

        return True


class ProcessPoolExecutor(Closeable):

    def __init__(
            self, max_workers: int = multiprocessing.cpu_count(), task_queue: Optional[Queue] = None,
            max_inactivity_seconds: int = 15):
        self._closed = False
        self._task_queue: Queue[_Task] = task_queue or Queue()
        self._workers_lock = Lock()
        self._next_worker_id = 0
        self._workers: Dict[str, _WorkerHandler] = {}
        self._max_workers = max_workers
        self.max_inactivity_seconds = max_inactivity_seconds

    def execute(self, execution: Callable[_PARAMS, _T],
                *args: _PARAMS.args, **kwargs: _PARAMS.kwargs) -> Promise[_T]:

        assert not self._closed or execution == sys.exit, "attempting execution after/during shutdown"

        result = _TaskResult()

        # noinspection PyTypeChecker
        self._task_queue.put(_Task(execution, args, kwargs, result))

        self._spawn_new_worker_if_needed()

        return result.deferred.promise()

    def _removed_worker(self, worker: _WorkerHandler):
        with self._workers_lock:
            del self._workers[worker.name]

        self._spawn_new_worker_if_needed()

    def _spawn_new_worker_if_needed(self):
        new_worker = None
        with self._workers_lock:
            n_workers = len(self._workers)
            if self._task_queue.unfinished_tasks > n_workers and n_workers < self._max_workers:
                new_worker = _WorkerHandler(self, f"worker {self._next_worker_id}")
                self._next_worker_id += 1
                self._workers[new_worker.name] = new_worker
        if new_worker:
            new_worker.start()

    def close(self):
        self._closed = True

        workers = list(self._workers.values())
        for _ in workers:
            self.execute(sys.exit, 0)

        for worker in workers:
            worker.join()

    def is_closed(self) -> bool:
        return self._closed
