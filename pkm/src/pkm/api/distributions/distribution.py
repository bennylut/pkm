from abc import abstractmethod
from typing import Protocol, Optional

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.packages.package import PackageDescriptor
from pkm.api.packages.package_metadata import PackageMetadata


class Distribution(Protocol):

    @property
    @abstractmethod
    def owner_package(self) -> PackageDescriptor:
        """
        :return: the package descriptor that this distribution belongs to
        """

    @abstractmethod
    def install_to(self, env: Environment, user_request: Optional[Dependency] = None, editable: bool = False):
        """
        installs this package into the given [env]
        :param env: the environment to install this package into
        :param user_request: if this package was requested by the user,
               supplying this field will mark the installation as user request
        :param editable: if true will install the distribution in editable mode (if such applicable)
        """

    @abstractmethod
    def extract_metadata(self, env: Environment) -> PackageMetadata:
        """
        extracts and returns metadata from this distribution
        :param env: the environment that this metadata should be relevant to
        :return: the extracted metadata
        """
