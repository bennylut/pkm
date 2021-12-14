import hashlib
from abc import abstractmethod, ABC
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set, Dict, Optional, TYPE_CHECKING

from pkm.api.versions.version import Version
from pkm.utils.properties import cached_property

if TYPE_CHECKING:
    from pkm.api.packages import PackageDescriptor


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
        """
        :return: the path for this environment root directory
        """

    @property
    @abstractmethod
    def interpreter_version(self) -> Version:
        """
        :return: the version of the environment's python interpreter
        """

    @property
    @abstractmethod
    def interpreter_path(self) -> Path:
        """
        :return: the path for the environment's python interpreter
        """

    @property
    @abstractmethod
    def compatibility_tags(self) -> Set[str]:
        """
        :return: pep425 compatability tags
        """

    @property
    @abstractmethod
    def markers(self) -> Dict[str, str]:
        """
        :return: pep508 environment markers  
        """

    @property
    @abstractmethod
    def installed_packages(self) -> List["PackageDescriptor"]:
        """
        :return: the list of packages currently installed in this environment, note that this list may be collected at previous time
                 if you need the most up to date list you should call the [reload] method prior to this method
        """

    @cached_property
    def markers_hash(self) -> str:
        """
        :return: a hash built from the environment's markers, can be used to identify instances of this environment
        """
        sorted_markers = sorted(self.markers.items(), key=lambda item: item[0])
        marker_str = ';'.join(f"{k}={v}" for k, v in sorted_markers)
        return hashlib.md5(marker_str).hexdigest()

    @abstractmethod
    def reload(self):
        """
        reload volatile information about this environment (like the installed packages)
        """

    def installed_version(self, package: str) -> Optional[Version]:
        """
        :param package: the package to check
        :return: the version of the given package that is installed in this environment or None if no such package is installed
        """
        return next((p.version for p in self.installed_packages if p.name == package), None)
