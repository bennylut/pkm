from abc import abstractmethod, ABC
from dataclasses import dataclass
from pathlib import Path

from typing import Protocol, List, Set, Dict

from pkm.api.versions.version import Version
from pkm.utils.properties import cached_property


@dataclass(frozen=True)
class CompatibilityTag:
    interpreter: str
    abi: str
    platform: str

    @classmethod
    def parse_tags(cls, tag: str) -> "Set[CompatibilityTag]":
        tags = set()
        interpreters, abis, platforms = tag.split("-")
        for interpreter in interpreters.split("."):
            for abi in abis.split("."):
                for platform_ in platforms.split("."):
                    tags.add(cls(interpreter, abi, platform_))
        return tags

    def __str__(self):
        return f'{self.interpreter}-{self.abi}-{self.platform}'


class Environment(ABC):

    @property
    @abstractmethod
    def path(self) -> Path:
        ...

    @property
    @abstractmethod
    def interpreter_version(self) -> Version:
        ...

    @property
    @abstractmethod
    def interpreter_path(self) -> Path:
        ...

    @property
    @abstractmethod
    def compatibility_tags(self) -> Set[str]:
        ...

    @property
    @abstractmethod
    def markers(self) -> Dict[str, str]:
        ...

    @cached_property
    def markers_hash(self) -> str:
        sorted_markers = sorted(self.markers.items(), key=lambda item: item[0])
        marker_str = ';'.join(f"{k}={v}" for k, v in sorted_markers)
        return hashlib.md5(marker_str)
