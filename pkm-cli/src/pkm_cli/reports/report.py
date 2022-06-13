from abc import abstractmethod, ABC
from contextlib import contextmanager

from pkm_cli.display.display import Display


# noinspection PyMethodMayBeStatic
class Report(ABC):

    @abstractmethod
    def display(self):
        ...

    def display_options(self):
        ...

    def _header(self, caption: str):
        Display.print(caption)
        Display.print('-' * len(caption))

    @contextmanager
    def _section(self, caption: str):
        self._header(caption)
        yield
        Display.print("")
