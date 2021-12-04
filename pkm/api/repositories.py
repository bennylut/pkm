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
        ...

    @abstractmethod
    def match(self, dependency: Dependency) -> List[Package]:
        ...

    def list(self, package_name: str) -> List[Package]:
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
        if dependency.repository is not None:
            repo = self._repositories_by_name.get(dependency.repository)
            if repo is None:
                return False
            return repo.accepts(dependency)

        return any(r.accepts(dependency) for r in self._repositories)

    def match(self, dependency: Dependency) -> List[Package]:
        if dependency.repository is not None:
            repo = self._repositories_by_name.get(dependency.repository)
            if repo is None:
                raise KeyError(f"undefined repository required: {dependency.repository}")

            return repo.match(dependency)

        for repo in self._repositories:
            if repo.accepts(dependency):
                return repo.match(dependency)
