from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from pkm.api.dependencies.dependency import Dependency
from pkm.api.versions.version import Version
from pkm.api.versions.version_specifiers import SpecificVersion

if TYPE_CHECKING:
    from pkm.api.repositories.repository import Repository
    from pkm.api.environments.environment import Environment
    from pkm.api.dependencies.dependency import Dependency


@dataclass(frozen=True)
class PackageDescriptor:
    name: str
    version: Version

    def __post_init__(self):
        super().__setattr__('name', self.name.lower())

    def to_dependency(self) -> "Dependency":
        from pkm.api.dependencies.dependency import Dependency
        return Dependency(self.name, SpecificVersion(self.version))

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
    def _all_dependencies(self, environment: "Environment") -> List[Dependency]:
        """
        :param environment: the environment that the dependencies should be calculated against
        :return: a list of all the package dependencies (for any environment and extras)
        """

    def dependencies(self, environment: "Environment", extras: Optional[List[str]] = None) -> List[Dependency]:
        """
        :param environment: the environment that the dependencies should be calculated against
        :param extras: the extras to include in the dependencies calculation
        :return: the list of dependencies this package has in order to be installed into the given 
        [environment] with the given [extras] 
        """

        return [d for d in self._all_dependencies(environment) if d.is_applicable_for(environment, extras)]

    @abstractmethod
    def is_compatible_with(self, env: "Environment") -> bool:
        """
        :param env: the environment to check 
        :return: true if this package can be installed given its dependencies into the given environment 
        """

    @abstractmethod
    def install_to(self, env: "Environment",
                   build_packages_repo: "Repository",
                   user_request: Optional[Dependency] = None):
        """
        installs this package into the given [env]
        :param env: the environment to install this package into
        :param build_packages_repo: in the case where installing this package requires build, any packages required for
               the build system will be fetched from this repo
        :param user_request: if this package was requested by the user,
               supplying this field will mark the installation as user request
        """

    def __str__(self):
        return f"{self.name} {self.version}"

    def __repr__(self):
        return f"Package({str(self)})"
