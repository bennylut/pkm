import re
from re import finditer
from typing import List, Iterator

# taken from: 200_success's answer in: https://stackoverflow.com/questions/29916065/how-to-do-camelcase-split-in-python
_CAMMELCASE_RX = re.compile('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)')


def split_camel_case(txt: str) -> Iterator[str]:
    return (m.group(0) for m in finditer(_CAMMELCASE_RX, txt))


def camel_case_to_upper_snake_case(txt: str):
    return "_".join(it.upper() for it in split_camel_case(txt))
