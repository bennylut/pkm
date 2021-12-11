from dataclasses import dataclass
from typing import List

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments import Environment
from pkm.api.packages import Package, PackageDescriptor


@dataclass
class PackageRequest:
    requester: Package
    dependency: Dependency


class PackageInstallationPlan:

    @property
    def environment(self) -> Environment:
        """
        :return: the environment that this plan was generated for
        """
        ...

    def packages_to_remove(self) -> List[str]:
        """
        :return: list of package names to remove from the environment
        """

    def packages_to_install(self) -> List[Package]:
        """
        :return: list of packages to install to the environment
        """

    def expectation_after_install(self) -> List[PackageDescriptor]:
        """
        :return: the list of package descriptor expected to exist in the given environment after following this plan
        """

    def requesters_of(self, package: str) -> List[PackageRequest]:
        """
        :param package: package which exists in [packages_to_install]
        :return: information about the packages that requires the given [package]
        and the exact requiring dependency of those packages
        """
