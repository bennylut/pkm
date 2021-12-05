from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path

from typing import Protocol, List


@dataclass
class CompatibilityTag:
    interpreter: str
    abi: str
    platform: str

    @classmethod
    def parse_tags(cls, tag: str) -> Set[CompatibilityTag]:
        tags = set()
        interpreters, abis, platforms = tag.split("-")
        for interpreter in interpreters.split("."):
            for abi in abis.split("."):
                for platform_ in platforms.split("."):
                    tags.add(cls(interpreter, abi, platform_))
        return tags

    @classmethod
    def parse_tag(cls, tag: str) -> CompatibilityTag:
        return cls(*tag.split('-'))


class Environment(Protocol):

    @abstractmethod
    @property
    def path(self) -> Path:
        ...

    @abstractmethod
    @property
    def interpreter_path(self) -> Path:
        ...

    @abstractmethod
    @property
    def compatability_tags(self) -> Set[str]:
        ...

