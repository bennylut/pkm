from typing import Optional, NoReturn, Callable


class TextReader:
    def __init__(self, text: str, file_name: Optional[str] = None):
        self.text = text
        self.file_name = file_name
        self.position = 0

    def peek(self, amount: int = 1) -> str:
        p = self.position
        return self.text[p:p + amount]

    def is_not_empty(self) -> bool:
        return self.position < len(self.text)

    def read_digits(self) -> str:
        position = self.position
        self.until(lambda i, t: not t[i].isdigit())
        if self.position == position:
            self.raise_err('expecting digits')
        return self.text[position:self.position]

    def match(self, substr: str) -> bool:
        if self.peek(len(substr)) == substr:
            self.next(len(substr))
            return True

        return False

    def peek_prev(self, amount: int = 1) -> str:
        p = self.position
        start = max(0, p - amount)
        return self.text[start:p]

    def match_any(self, *substrs: str) -> Optional[str]:
        for substr in substrs:
            if self.match(substr):
                return substr

        return None

    def raise_err(self, msg: str, lines_to_show: int = 4) -> NoReturn:
        lines = self.text.splitlines(keepends=True)
        current_line = self.text.count('\n', 0, self.position)
        start_line = max(0, current_line - lines_to_show)
        sub_line_len = self.position - sum(len(it) for it in lines[:current_line])
        largest_line_len = max(len(lines[i]) if i < len(lines) else 0 for i in range(start_line, current_line + 1))
        pref = f'... after {start_line} lines ...\n\n' if start_line > 0 else ''
        largest_line_len = max(largest_line_len, len(pref))

        position_indicator = f"AT LINE {current_line}"
        if self.file_name:
            position_indicator = f"{self.file_name}:{current_line}"

        lines = ''.join(lines[start_line:current_line + 1])
        if not lines.endswith('\n'):
            lines += '\n'

        out = f"Parsing Failed: {msg} ({position_indicator})\n" \
              f"{'-' * largest_line_len}\n" \
              f"{pref}" \
              f"{lines}" \
              f"{'~' * sub_line_len}^"

        raise ValueError(out)

    def until_match(self, substr: str) -> str:
        pos = self.position

        try:
            self.position = self.text.index(substr, pos)
            return self.text[pos: self.position]
        except ValueError:
            return ''

    def until(self, predicate: Callable[[int, str], bool]) -> str:
        p = self.position
        for i in range(self.position, len(self.text)):
            if predicate(i, self.text):
                self.position = i
                return self.text[p:i]

        self.position = len(self.text)
        return self.text[p:self.position]

    def next(self, amount: int = 1) -> str:
        peek = self.peek(amount)
        self.position += len(peek)

        return peek

    def match_or_err(self, substr: str, err: str) -> None:
        if not self.match(substr):
            self.raise_err(err)

    def __str__(self):
        return f"TextReader(pos={self.position}, '{self.text[self.position: self.position + 25]}...')"

    def __repr__(self):
        return str(self)

    def read_ws(self, allow_new_lines: bool = True) -> str:
        p = self.position
        while self.is_not_empty():
            n = self.peek()
            if n == '\n' and not allow_new_lines:
                break
            elif not n.isspace():
                break

            self.next()

        return self.text[p:self.position]
