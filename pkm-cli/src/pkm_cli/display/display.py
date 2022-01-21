import os

from prompt_toolkit import HTML, print_formatted_text
from prompt_toolkit.shortcuts import ProgressBar
from threading import RLock
from typing import Optional, Iterable, TypeVar

from pkm_cli.display.progress import Progress

_T = TypeVar("_T")


# noinspection PyMethodMayBeStatic
class _Display:

    def __init__(self):
        self._progress: Optional[ProgressBar] = None
        self._progress_users = 0
        self._lock = RLock()

    def print(self, msg: str, *, formatted: bool = True, newline: bool = True):
        msg = HTML(msg) if formatted else msg
        end = os.linesep if newline else ''
        print_formatted_text(msg, end=end)

    def progressbar(
            self, label: str, iterable: Optional[Iterable[_T]] = None,
            total: int = 100) -> Progress:
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

        return Progress(self._progress(iterable, HTML(label), total=total), close)


Display = _Display()
