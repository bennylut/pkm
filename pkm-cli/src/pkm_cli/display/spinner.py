from time import time

from contextlib import contextmanager

from rich.console import ConsoleRenderable
from rich.spinner import Spinner as RichSpinner
from typing import ContextManager

from pkm_cli.display.display import InformationUnit, Display


class Spinner(InformationUnit):

    def __init__(self, description: str):
        self._description = description

    @contextmanager
    def dumb(self) -> ContextManager:
        starttime = time()
        Display.print(f"[START] {self._description}")
        yield
        Display.print(f"[END] {self._description}, took: {time() - starttime} seconds")

    @contextmanager
    def rich(self) -> ContextManager[ConsoleRenderable]:
        starttime = time()

        yield RichSpinner("dots", self._description)

        Display.print(f"Done {self._description}, took: {time() - starttime} seconds")
