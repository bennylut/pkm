from io import UnsupportedOperation
from pathlib import Path
from typing import Set, Dict, List, Optional, Literal

from pkm.api.environments.environment import Environment, UninitializedEnvironment
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.versions.version import Version
from pkm.utils.iterators import find_first
from pkm.utils.properties import cached_property, clear_cached_properties

from pkm_main.environments.environment_introspection import EnvironmentIntrospection

_PATH_KEY = {"purelib", "platlib", "scripts", "data"}


class VirtualEnvironment(Environment):

    def __init__(self, path: Path, interpreter_path: Optional[Path] = None):
        self._path = path
        if interpreter_path:
            self.interpreter_path = interpreter_path  # noqa

    @cached_property
    def _introspection(self) -> EnvironmentIntrospection:
        return EnvironmentIntrospection.remote(self.interpreter_path)

    @cached_property
    def interpreter_version(self) -> Version:
        return Version.parse(self._introspection.python_version)

    def site_packages_path(self, type: Literal['platlib', 'purelib'] = 'purelib') -> Path:
        return Path(self._introspection.paths[type])

    @property
    def path(self) -> Path:
        return self._path

    def sysconfig_path(self, type: str) -> Optional[Path]:
        if type not in _PATH_KEY or type not in self._introspection.paths:
            return None

        return Path(self._introspection.paths[type])

    @cached_property
    def compatibility_tags(self) -> Set[str]:
        return set(self._introspection.compatibility_tags)

    @cached_property
    def interpreter_path(self) -> Path:
        return _find_interpreter(self._path)

    @property
    def markers(self) -> Dict[str, str]:
        return self._introspection.env_markers

    @cached_property
    def installed_packages(self) -> List[PackageDescriptor]:
        return [PackageDescriptor(name, Version.parse(version))
                for name, version in self._introspection.installed_packages.items()]

    def reload(self):
        clear_cached_properties(self)

    @staticmethod
    def is_valid(path: Path) -> bool:
        return _find_interpreter(path) is not None

    @classmethod
    def create(cls, path: Path, python: Package):
        ue = UninitializedEnvironment(path)
        if not python.is_compatible_with(ue):
            raise UnsupportedOperation("incompatible interpreter")

        python.install_to(ue)
        return VirtualEnvironment(path)


def _find_interpreter(env_root: Path) -> Optional[Path]:
    return find_first((env_root / "bin/python", env_root / "bin/python.exe"), lambda it: it.exists())
