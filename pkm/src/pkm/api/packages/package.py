import re
from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from pkm.api.versions.version import Version
from pkm.api.versions.version_specifiers import SpecificVersion
from pkm.utils.http.http_monitors import FetchResourceMonitor

from pkm.utils.monitors import no_monitor

if TYPE_CHECKING:
    from pkm.api.environments.environment import Environment
    from pkm.api.dependencies.dependency import Dependency


@dataclass(frozen=True)
class PackageDescriptor:
    name: str
    version: Version

    def __post_init__(self):
        super().__setattr__('name', PackageDescriptor.normalize_name(self.name))

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

    @staticmethod
    def normalize_name(package_name: str) -> str:
        """
        normalize package names (see: https://packaging.python.org/en/latest/specifications/core-metadata/)

        A valid name consists only of ASCII letters and numbers, period, underscore and hyphen.
        It must start and end with a letter or number.
        Distribution names are limited to those which match the following regex (run with re.IGNORECASE):
        `^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$`

        this function replace any non valid chars in the name with '-'
        and then consecutive runs of chars in '-_.' are replaced with a single dash
        finally '-' chars are removed from the start and end of the name

        :param package_name: the package name to normalize
        :return: the normalized name
        """
        # .sub(r"[-_.]+", "-", package_name)
        if not (result := re.sub("[^A-Z0-9]+", '-', package_name, flags=re.IGNORECASE).strip('-').lower()):
            raise ValueError(f"empty name after normalization (un-normalized name: '{package_name}')")
        return result


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
    def _all_dependencies(self, environment: "Environment", monitor: FetchResourceMonitor) -> List["Dependency"]:
        """
        :param environment: the environment that the dependencies should be calculated against
        :param monitor: in case where this method requires fetching the package, this will be used as a monitor
        :return: a list of all the package dependencies (for any environment and extras)
        """

    def dependencies(
            self, environment: "Environment",
            extras: Optional[List[str]] = None, *, monitor: FetchResourceMonitor = no_monitor()) -> List["Dependency"]:
        """
        :param environment: the environment that the dependencies should be calculated against
        :param extras: the extras to include in the dependencies calculation
        :param monitor: in case where this method requires fetching the package, this will be used as a monitor
        :return: the list of dependencies this package has in order to be installed into the given
        [environment] with the given [extras]
        """

        return [d for d in self._all_dependencies(environment, monitor=monitor) if
                d.is_applicable_for(environment, extras)]

    @abstractmethod
    def is_compatible_with(self, env: "Environment") -> bool:
        """
        :param env: the environment to check
        :return: true if this package can be installed given its dependencies into the given environment
        """

    @abstractmethod
    def install_to(self, env: "Environment", user_request: Optional["Dependency"] = None,
                   *, monitor: FetchResourceMonitor = no_monitor()):
        """
        installs this package into the given `env`
        :param env: the environment to install this package into
        :param user_request: if this package was requested by the user,
               supplying this field will mark the installation as user request
        :param monitor: in case where installing the package requires fetching it, this will be used as a monitor
        """

    def __str__(self):
        return f"{self.name} {self.version}"

    def __repr__(self):
        return f"Package({str(self)})"