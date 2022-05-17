from __future__ import annotations
from html.parser import HTMLParser
from dataclasses import dataclass
from typing import Callable, Dict, List, Union, Iterator
from pkm.utils.commons import IllegalStateException

ELM_MATCHER = Callable[["_Element"], bool]


@dataclass
class Element:
    tag: str
    attrs: Dict[str, str]
    children: List[Element]

    def data(self) -> str:
        return ''.join(d.attrs['value'] for d in self.children if d.tag == 'data')

    def _lookup(self, match: ELM_MATCHER, roots: bool) -> Iterator[Element]:
        nodes = [self]

        while nodes:
            node = nodes.pop()

            if match(node):
                yield node
                if not roots:
                    nodes.extend(node.children)
            else:
                nodes.extend(node.children)

    def select(self, *matchers: ELM_MATCHER) -> Iterator[Element]:
        if len(matchers) == 1:
            yield from self._lookup(matchers[0], False)
        else:
            rest = matchers[1:]
            for matched in self._lookup(matchers[0], True):
                yield from matched.select(*rest)


class BasicDomParser(HTMLParser):

    def __init__(self, *, convert_charrefs: bool = ...) -> None:
        super().__init__(convert_charrefs=convert_charrefs)
        self.dom = Element('root', {}, [])
        self._node: List[Element] = [self.dom]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Union[str, None]]]) -> None:
        new_element = Element(
            tag, {attr: (value if value is not None else "true") for attr, value in attrs}, []
        )

        self._node.append(new_element)

    def handle_endtag(self, tag: str) -> None:
        e = self._node.pop()
        if e.tag != tag:
            raise IllegalStateException(f"expecting {e.tag} to end but found an ending for {tag}")
        self._node[-1].children.append(e)

    def handle_data(self, data: str) -> None:
        data_element = Element(
            "data", {'value': data}, []
        )

        self._node[-1].children.append(data_element)
