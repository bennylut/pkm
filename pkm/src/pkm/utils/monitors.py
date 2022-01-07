from typing import TypeVar


class Monitor:
    def is_monitoring(self) -> bool:
        return True

    def __enter__(self):
        self.on_start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.on_fail(exc_val)
        else:
            self.on_end()

    def on_start(self):
        ...

    def on_end(self):
        ...

    def on_fail(self, err: Exception):
        ...


def _do_nothing(*args, **kwargs):
    return _NoMonitor


class _NoMonitor(Monitor):
    def __getattr__(self, item):
        return _do_nothing

    def is_monitoring(self) -> bool:
        return False


_NoMonitor = _NoMonitor()

_T = TypeVar("_T", bound=Monitor)


def no_monitor() -> _T:
    return _NoMonitor
