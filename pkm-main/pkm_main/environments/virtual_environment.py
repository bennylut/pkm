from io import UnsupportedOperation
from pathlib import Path
from typing import Set, Dict, List, Optional

from pkm.api.environments.environment import Environment
from pkm.api.packages import PackageDescriptor
from pkm.api.versions.version import Version
from pkm.utils.iterators import find_first
from pkm.utils.properties import cached_property, clear_cached_properties

from pkm_main.environments.environment_introspection import EnvironmentIntrospection


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

    @property
    def path(self) -> Path:
        return self._path

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


def _find_interpreter(env_root: Path) -> Optional[Path]:
    return find_first((env_root / "bin/python", env_root / "bin/python.exe"), lambda it: it.exists())


class UninitializedVirtualEnvironment(Environment):
    """
    defines an uninitialized (= empty/non-existing directory) virtual environment
    use this together with a package from the local-pythons repository to install a specific python version
    into this environment, then you can call the [to_initialized] method to get a virtual-env instance.
    """

    def __init__(self, path: Path):
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    @property
    def interpreter_version(self) -> Version:
        raise UnsupportedOperation('uninitialized environment')

    @property
    def interpreter_path(self) -> Path:
        raise UnsupportedOperation('uninitialized environment')

    @property
    def compatibility_tags(self) -> Set[str]:
        return set()

    @property
    def markers(self) -> Dict[str, str]:
        return dict()

    @property
    def installed_packages(self) -> List["PackageDescriptor"]:
        return []

    def reload(self):
        pass

    def to_initialized(self) -> VirtualEnvironment:
        return VirtualEnvironment(self._path)
