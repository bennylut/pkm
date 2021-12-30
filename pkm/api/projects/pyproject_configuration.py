from dataclasses import dataclass
from typing import List, Optional

from pkm.api.dependencies.dependency import Dependency
from pkm.config.configuration import TomlFileConfiguration, computed_based_on


@dataclass
class BuildSystemConfig:
    requirements: List[Dependency]
    build_backend: str
    backend_path: Optional[str]


class PyProjectConfiguration(TomlFileConfiguration):

    @computed_based_on("build-system")
    def build_system(self) -> BuildSystemConfig:
        build_system = self['build-system']
        requirements = [Dependency.parse_pep508(dep) for dep in build_system['requires']]
        build_backend = build_system.get('build-backend')
        backend_path = build_system.get('backend-path')

        return BuildSystemConfig(requirements, build_backend, backend_path)
