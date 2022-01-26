from abc import abstractmethod
import os

from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit import HTML, print_formatted_text
from prompt_toolkit.shortcuts import ProgressBar
from threading import RLock
from typing import Optional, Iterable, Protocol, TypeVar

from pkm_cli.display.progress import Progress, ProgressProto, DumbProgress

_T = TypeVar("_T")


class _DisplyProto(Protocol):

    @abstractmethod
    def print(self, msg: str, *, formatted: bool = True, newline: bool = True):
        ...

    @abstractmethod
    def progressbar(
            self, label: str, total: int = 100) -> ProgressProto:
        ...


class _Display(_DisplyProto):

    def __init__(self):
        self._progress: Optional[ProgressBar] = None
        self._progress_users = 0
        self._lock = RLock()

    def print(self, msg: str, *, formatted: bool = True, newline: bool = True):
        msg = HTML(msg) if formatted else msg
        end = os.linesep if newline else ''
        print_formatted_text(msg, end=end)

    def progressbar(
            self, label: str, total: int = 100) -> ProgressProto:
        with self._lock:
            if self._progress:
                self._progress_users += 1
            else:
                self._progress = ProgressBar()
                self._progress.__enter__()
                self._progress_users = 1

        def close():
            with self._lock:
                self._progress_users -= 1
                if self._progress_users == 0:
                    self._progress.__exit__()
                    self._progress = None

        return Progress(self._progress(None, HTML(label), total=total), close)


class _DumbDisplay(_DisplyProto):
    def print(self, msg: str, *, formatted: bool = True, newline: bool = True):
        print(msg, end='\n' if newline else '')

    def progressbar(self, label: str, total: int = 100) -> ProgressProto:
        return DumbProgress(label, total)


try:
    patch_stdout().__enter__() # noqa
    Display = _Display()
except: # noqa
    Display = _DumbDisplay()
