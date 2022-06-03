import typing
from typing import Optional


def x(p: Optional[int]):
    ...

xtypes = typing.get_type_hints(x)
print(xtypes)
