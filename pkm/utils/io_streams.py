from contextlib import contextmanager
from io import StringIO
from typing import Literal, ContextManager

import sys


@contextmanager
def capture(stream: Literal['stdout', 'stderr']) -> ContextManager[StringIO]:
    original = getattr(sys, stream)
    try:
        new_stream = StringIO()
        setattr(sys, stream, new_stream)
        yield new_stream
    finally:
        setattr(sys, stream, original)
