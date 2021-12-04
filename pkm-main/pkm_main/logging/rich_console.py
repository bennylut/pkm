from rich.console import Console as _RichConsole
from rich.markup import escape
from pkm.logging.console import Console
import re

_rc = _RichConsole()

_MARKUP_REWRITE_RX = re.compile(r'(?P<rewrite>(?<!\\)\[\[.*?\]\])')  # noqa


def _rewrite(msg: str) -> str:
    split = re.split(_MARKUP_REWRITE_RX, msg)
    return ''.join(part[1:-1] if part.startswith('[[') else escape(part) for part in split)


class RichConsole(Console):

    def print(self, msg: str, newline: bool = True):
        _rc.print(_rewrite(msg), end='\n' if newline else '')

    def log(self, msg: str, newline: bool = True):
        _rc.log(_rewrite(msg), end='\n' if newline else '', _stack_offset=2)
