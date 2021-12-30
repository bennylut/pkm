from abc import abstractmethod
from typing import Protocol, Optional

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.packages.package import PackageDescriptor
from pkm.api.packages.package_metadata import PackageMetadata
from pkm.api.repositories.repository import Repository


class Distribution(Protocol):

    @property
    @abstractmethod
    def owner_package(self) -> PackageDescriptor:
        """
        :return: the package descriptor that this distribution belongs to
        """

    @abstractmethod
    def install_to(self, env: Environment, build_packages_repo: Repository, user_request: Optional[Dependency] = None):
        """
        installs this package into the given [env]
        :param env: the environment to install this package into
        :param build_packages_repo: in the case where installing this package requires build, any packages required for
               the build system will be fetched from this repo
        :param user_request: if this package was requested by the user,
               supplying this field will mark the installation as user request
        """

    @abstractmethod
    def extract_metadata(self, env: Environment, build_packages_repo: Repository) -> PackageMetadata:
        """
        extracts and returns metadata from this distribution
        :param env: the environment that this metadata should be relevant to
        :param build_packages_repo: in the case where extracting the metadata requires build, any packages required for
               the build system will be fetched from this repo
        :return: the extracted metadata
        """
