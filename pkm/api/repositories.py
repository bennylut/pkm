from abc import abstractmethod, ABC
from io import UnsupportedOperation
from typing import List, Dict

from pkm.api.versions.version_specifiers import AnyVersion

from pkm.api.packages import Dependency, Package


class Repository(ABC):

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    def accepts(self, dependency: Dependency) -> bool:
        """
        :param dependency: the dependency to check 
        :return: true if this repository knows how to handle the given [dependency]. 
                 e.g., pypi does not know how to handle local file dependency
        """
        ...

    @abstractmethod
    def match(self, dependency: Dependency) -> List[Package]:
        """
        :param dependency: the dependency to match 
        :return: list of all the packages in this repository that match the given [dependency]
        """
        ...

    def list(self, package_name: str) -> List[Package]:
        """
        :param package_name: the package to match 
        :return: list of all the packages that match the given [package_name]
        """
        dependency = Dependency(package_name, AnyVersion)
        if self.accepts(dependency):
            return self.match(dependency)
        raise UnsupportedOperation(f"Repository ({self.name}) does not support listing")


class CompoundRepository(Repository):

    def __init__(self, name: str, repositories: List[Repository]):
        super().__init__(name)
        self._repositories = repositories
        self._repositories_by_name: Dict[str, Repository] = {r.name: r for r in repositories}

    def accepts(self, dependency: Dependency) -> bool:
        return any(r.accepts(dependency) for r in self._repositories)

    def match(self, dependency: Dependency) -> List[Package]:
        for repo in self._repositories:
            if repo.accepts(dependency):
                return repo.match(dependency)
