from pathlib import Path
from typing import Optional, List, Sequence, Literal

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments import Environment
from pkm.api.packages import PackageDescriptor
from pkm.api.project import Project


class PkmProject(Project):

    def __init__(self, path: Path, ):
        super().__init__()



    def install_dependencies(self, new_dependencies: Optional[List[Dependency]] = None):
        pass

    def remove_dependencies(self, packages: List[str]):
        pass

    def build(self, formats: Sequence[Literal['wheel', 'sdist']] = ('wheel', 'sdist')):
        pass

    @property
    def descriptor(self) -> PackageDescriptor:
        pass

    def dependencies(self, environment: Environment, extras: Optional[List[str]] = None) -> List[Dependency]:
        pass

    def is_compatible_with(self, env: Environment):
        pass

    def install_to(self, env: Environment):
        pass

    ...
