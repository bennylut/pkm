from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import List, Optional

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments import Environment
from pkm.api.versions.version import Version


@dataclass
class PackageDescriptor:
    name: str
    version: Version


class Package(ABC):

    @property
    @abstractmethod
    def descriptor(self) -> PackageDescriptor:
        ...

    @property
    def name(self) -> str:
        return self.descriptor.name

    @property
    def version(self) -> Version:
        return self.descriptor.version


    @abstractmethod
    def dependencies(self, environment: Environment, extras: Optional[List[str]] = None) -> List[Dependency]:
        ...

    @abstractmethod
    def is_compatible_with(self, env: Environment):
        ...

    @abstractmethod
    def install_to(self, env: Environment):
        ...
