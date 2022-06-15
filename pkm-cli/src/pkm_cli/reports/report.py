from __future__ import annotations
from abc import abstractmethod, ABC
from contextlib import contextmanager
from typing import ContextManager, Optional, Set, Dict

from rich import markup
from rich.control import strip_control_codes

from pkm_cli.display.display import Display


class ReportUList:
    def __init__(self, report: Report, item_prefix: str = "-"):
        self._report = report
        self._item_prefix = item_prefix
        self.empty = True

    def item(self, text: str):
        self._report.writeln(f" {self._item_prefix} {text}", 3)
        self.empty = False


class ReportOList:
    def __init__(self, report: Report):
        self._report = report
        self.index = 1

    def item(self, text: str):
        self._report.writeln(f" {self.index}. {text}", 3)
        self.index += 1


# noinspection PyMethodMayBeStatic
class Report(ABC):

    def __init__(self):
        self._indentation = ""

    @abstractmethod
    def display(self, options: Dict[str, bool]):
        ...

    @abstractmethod
    def display_options(self):
        ...

    def option_help(self, name: str, help_: str):
        self.writeln(f"[[orange1]{name}[/]]: {help_}")

    def writeln(self, msg: str = "", back_indent: int = 0):
        indent = self._indentation
        if back_indent > 0:
            indent = indent[:-back_indent]
        Display.print(indent + msg)

    def paragraph(self, text: str):
        lines = []
        while len(text) > 80:
            line_end = text.rindex(' ', 0, 80)
            skip = 1
            if line_end == 0:
                skip = 0

            lines.append(text[:line_end])
            text = text[line_end + skip:]

        if text:
            lines.append(text)

        for line in lines:
            self.writeln(line)
        self.writeln()

    @contextmanager
    def indent(self, indent: str):
        identation = self._indentation
        self._indentation = identation + indent
        yield
        self._indentation = identation

    @contextmanager
    def ulist(self, item_prefix='-', empty_text: Optional[str] = None) -> ContextManager[ReportUList]:
        ulist = ReportUList(self, item_prefix)
        with self.indent(f'   '):
            yield ulist
            if ulist.empty and empty_text:
                self.writeln(empty_text, 2)

    @contextmanager
    def olist(self, empty_text: Optional[str] = None) -> ContextManager[ReportOList]:
        with self.indent(f'   '):
            olist = ReportOList(self)
            yield olist
            if olist.index == 1 and empty_text:
                self.writeln(empty_text, 2)

    def header(self, caption: str):
        caption_length = len(markup.render(caption).plain)
        self.writeln(caption)
        self.writeln('-' * caption_length)

    @contextmanager
    def section(self, caption: str):
        self.header(f"[dark_olive_green2]{caption}[/]")
        yield
        self.writeln()
