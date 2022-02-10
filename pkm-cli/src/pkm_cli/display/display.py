import os
from abc import abstractmethod
from contextlib import contextmanager
from rich.console import ConsoleRenderable, Console, ConsoleOptions, RenderResult
from rich.live import Live
from threading import RLock
from typing import Optional, Protocol, TypeVar, ContextManager, List


class InformationUnit(Protocol):
    @abstractmethod
    def dumb(self) -> ContextManager:
        ...

    @abstractmethod
    def rich(self) -> ContextManager[ConsoleRenderable]:
        ...


_T = TypeVar("_T", bound=InformationUnit)

console_lock = RLock()


class _LiveOutput(ConsoleRenderable):
    def __init__(self, console: Console):
        self._live_renderer: Optional[Live] = Live(self, console=console)
        self._live_components: List[ConsoleRenderable] = []
        self._live_renderer.__enter__()

    def __rich_console__(self, console: "Console", options: "ConsoleOptions") -> "RenderResult":
        return self._live_components

    @contextmanager
    def show(self, iu: InformationUnit):
        with iu.rich() as renderable:
            with console_lock:
                self._live_components = [*self._live_components, renderable]

            try:
                yield
            finally:
                with console_lock:
                    self._live_components = [c for c in self._live_components if c is not renderable]


class _Display:

    def __init__(self, dumb: Optional[bool] = None):
        self._console = Console()
        self._dumb = self._console.is_dumb_terminal if dumb is None else dumb
        self._live_output = None if self._dumb else _LiveOutput(self._console)

    def print(self, msg: str, *, newline: bool = True, use_markup: bool = True):
        with console_lock:
            self._console.print(msg, end=os.linesep if newline else '', markup=use_markup)

    @contextmanager
    def show(self, iu: _T) -> _T:
        if self._dumb:
            with iu.dumb():
                yield iu
        else:
            with self._live_output.show(iu):
                yield iu

    def is_dumb(self) -> bool:
        return self._dumb


Display = _Display()
