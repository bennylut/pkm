from pathlib import Path
from typing import Set, Dict, List

from pkm.api.environments import Environment
from pkm.api.packages import PackageDescriptor
from pkm.api.versions.version import Version
from pkm.utils.properties import cached_property, clear_cached_properties

from pkm_main.environments.environment_introspection import EnvironmentIntrospection


class VirtualEnvironment(Environment):

    def __init__(self, path: Path):
        self._path = path

    @cached_property
    def _introspection(self) -> EnvironmentIntrospection:
        return EnvironmentIntrospection.remote(self.interpreter_path)

    @cached_property
    def interpreter_version(self) -> Version:
        return Version.parse(self._introspection.python_version)

    @property
    def path(self) -> Path:
        return self._path

    @cached_property
    def compatibility_tags(self) -> Set[str]:
        return set(self._introspection.compatibility_tags)

    @cached_property
    def interpreter_path(self) -> Path:
        interpreter_paths = list(self.path.rglob('**/bin/python'))
        if len(interpreter_paths) != 1:
            raise ValueError(f'could not decide on interpreter for environment {self.path}')

        return interpreter_paths[0]

    @property
    def markers(self) -> Dict[str, str]:
        return self._introspection.env_markers

    @cached_property
    def installed_packages(self) -> List[PackageDescriptor]:
        return [PackageDescriptor(name, Version.parse(version))
                for name, version in self._introspection.installed_packages.items()]

    def reload(self):
        clear_cached_properties(self)

