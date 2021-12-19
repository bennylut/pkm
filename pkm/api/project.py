from abc import ABC, abstractmethod
from typing import List, Optional, Literal, Sequence

from pkm.api.dependencies.dependency import Dependency
from pkm.api.packages.package import Package
from pkm.api.repositories import Repository


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

    @property
    @abstractmethod
    def repository(self) -> "ProjectRepository":
        """
        :return: the repository defined by this project
        """


class ProjectRepository(Repository, ABC):

    def __init__(self, project: Project):
        super().__init__(f"{project.name}'s repository")
        self.project = project

    @abstractmethod
    def _do_match_non_project(self, dependency: Dependency) -> List[Package]:
        """
        this method is called by the actual [match] method of this repository for any packages that are not its project 
        
        :param dependency: the dependency to match 
        :return: list of all the packages in this repository that match the given [dependency]
        """
        ...

    def _do_match(self, dependency: Dependency) -> List[Package]:
        if dependency.package_name == self.project.name:
            return [self.project]

        return self._do_match_non_project(dependency)

