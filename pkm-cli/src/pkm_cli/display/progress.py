from typing import Callable

from prompt_toolkit.shortcuts import ProgressBarCounter

from pkm.utils.commons import Closeable


class ProgressProto(Closeable):
    completed: int
    total: int


class Progress(ProgressProto):

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


class DumbProgress(ProgressProto):
    def __init__(self, message: str, total: int = 100) -> None:
        super().__init__()
        self.completed = 0
        self.total = total
        self._message = message
        print(f"[START] {message}")

    def close(self):
        print(f"[END] {self._message}")
