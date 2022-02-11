from time import sleep

import os
from abc import abstractmethod
from contextlib import contextmanager
from rich.console import ConsoleRenderable, Console, ConsoleOptions, RenderResult
from rich.live import Live
from threading import RLock, Thread
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
        self._live_renderer: Optional[Live] = Live(self, console=console, auto_refresh=False)
        self._live_components: List[ConsoleRenderable] = []
        self._live_renderer.__enter__()

        Thread(name="live output refresher", target=self._refresh_loop, daemon=True).start()

    def _refresh_loop(self):
        while True:
            self._live_renderer.refresh()
            sleep(0.2)

    def __rich_console__(self, console: "Console", options: "ConsoleOptions") -> "RenderResult":
        return self._live_components

    @contextmanager
    def show(self, iu: InformationUnit):
        with iu.rich() as renderable:
            with console_lock:
                self._live_components = [renderable, *self._live_components]

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

        if self._dumb:
            self.print("using dumb display")

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
