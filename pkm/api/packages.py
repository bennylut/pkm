from abc import abstractmethod
from typing import List, Optional

from dataclasses import dataclass

from pkm.api.versions.version import Version

from pkm.api.environments import VirtualEnv
from pkm.api.versions.version_specifiers import VersionSpecifier
from typing_extensions import Protocol


@dataclass
class Dependency(Protocol):
    package_name: str
    version_spec: VersionSpecifier

    repository: Optional[str] = None

class Package(Protocol):

    @abstractmethod
    @property
    def name(self) -> str:
        ...

    @abstractmethod
    @property
    def version(self) -> Version:
        ...

    @abstractmethod
    @property
    def dependencies(self) -> List[Dependency]:
        ...

    @abstractmethod
    def is_compatible_with(self, env: VirtualEnv):
        ...

    @abstractmethod
    def install_to(self, env: VirtualEnv):
        ...
