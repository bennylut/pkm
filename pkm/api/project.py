from abc import ABC, abstractmethod
from typing import List, Optional, Literal, Sequence

from pkm.api.dependencies.dependency import Dependency
from pkm.api.packages import Package


class Project(Package, ABC):

    @abstractmethod
    def install_dependencies(self, new_dependencies: Optional[List[Dependency]] = None):
        """
        install the dependencies of this project to its assigned environments
        :param new_dependencies: if given, resolve and add these dependencies to this project and then install
        """

    @abstractmethod
    def remove_dependencies(self, packages: List[str]):
        """
        remove and uninstall all dependencies that are related to the given list of packages
        :param packages: the list of package names to remove
        """

    @abstractmethod
    def build(self, formats: Sequence[Literal['wheel', 'sdist']] = ('wheel', 'sdist')):
        """
        build distribution files from this project
        :param formats: the required distribution formats to build
        """
