from abc import abstractmethod
import re
from typing import Match, Protocol


class Console(Protocol):

    @abstractmethod
    def print(self, msg: str, newline: bool = True):
        ...

    def log(self, msg: str, newline: bool = True):
        return self.print(msg, newline)


_MARKUP_CLEANUP_RX = re.compile(r'(?P<keep>\\\[\[.*?\]\])|(?P<drop>\[\[.*?\]\])')  # noqa


def _MARKUP_CLEANUP_REPL(match: Match) -> str:
    keep = match.group('keep')
    return keep[1:] if keep else ''


class BasicConsole(Console):
    def print(self, msg: str, newline: bool = True):
        msg = re.sub(_MARKUP_CLEANUP_RX, _MARKUP_CLEANUP_REPL, msg)
        print(msg)


console: Console = BasicConsole()
