from typing import List, Dict, Any

from pkm.api.environments import Environment
from pkm.api.packages import Dependency, Package
from pkm.api.repositories import Repository
from pkm.api.versions.version import Version
from pkm.utils.properties import cached_property


class PyPiRepository(Repository):
    def accepts(self, dependency: Dependency) -> bool:
        return True

    def match(self, dependency: Dependency) -> List[Package]:
        pass


class _PyPiPackage(Package):

    def __init__(self, pypi: PyPiRepository, name: str, version: Version, metadata: Dict[str, Any]):
        self._name = name
        self._version = version
        self._pypi = pypi
        self._metadata = metadata

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> Version:
        return self._version

    @cached_property
    def dependencies(self) -> List[Dependency]:
        pass

    def is_compatible_with(self, env: Environment):
        pass

    def install_to(self, env: Environment):
        pass
