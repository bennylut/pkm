from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments import Environment
from pkm.api.versions.version import Version


@dataclass(frozen=True)
class PackageDescriptor:
    name: str
    version: Version

    def write(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'version': str(self.version),
        }

    @classmethod
    def read(cls, data: Dict[str, Any]) -> "PackageDescriptor":
        return cls(data['name'], Version.parse(data['version']))


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
        """
        :param environment: the environment that the dependencies should be calculated against
        :param extras: the extras to include in the dependencies calculation
        :return: the list of dependencies this package has in order to be installed into the given 
        [environment] with the given [extras] 
        """

    @abstractmethod
    def is_compatible_with(self, env: Environment):
        """
        :param env: the environment to check 
        :return: true if this package can be installed given its dependencies into the given environment 
        """

    @abstractmethod
    def install_to(self, env: Environment):
        """
        installs this package into the given [env]
        :param env: the environment to install this package into
        """
