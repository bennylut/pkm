from abc import abstractmethod, ABC
from typing import List, Optional, Protocol

from dataclasses import dataclass

from pkm.api.versions.version import Version

from pkm.api.environments import Environment
from pkm.api.versions.version_specifiers import VersionSpecifier


@dataclass
class Dependency(Protocol):
    package_name: str
    version_spec: VersionSpecifier

    repository: Optional[str] = None


@dataclass
class PackageDescriptor:
    name: str
    version: Version


class Package(ABC):

    @abstractmethod
    @property
    def descriptor(self) -> PackageDescriptor:
        ...

    @property
    def name(self) -> str:
        return self.descriptor.name

    @property
    def version(self) -> Version:
        return self.descriptor.version

    @abstractmethod
    @property
    def dependencies(self) -> List[Dependency]:
        ...

    @abstractmethod
    def is_compatible_with(self, env: Environment):
        ...

    @abstractmethod
    def install_to(self, env: Environment):
        ...
