from typing import Callable

from prompt_toolkit.shortcuts import ProgressBarCounter

from pkm.utils.commons import Closeable


class Progress(Closeable):

    def __init__(self, counter: ProgressBarCounter, onclose: Callable):
        self._counter = counter
        self._onclose = onclose

    def close(self):
        self._counter.done = True
        self._onclose()

    @property
    def completed(self) -> int:
        return self._counter.items_completed

    @completed.setter
    def completed(self, value: int):
        self._counter.items_completed = value

    @property
    def total(self) -> int:
        return self._counter.total

    @total.setter
    def total(self, value: int):
        self._counter.total = value
